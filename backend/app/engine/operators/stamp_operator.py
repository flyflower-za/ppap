import json
import asyncio
import base64
import logging
import cv2
import numpy as np
from typing import List, Optional
from app.engine.base import BaseOperator, DocumentContext, OperatorResult
from app.services.ai_config_service import get_ai_config

logger = logging.getLogger(__name__)


async def _get_ai_config(model_type: str = "vision", requested_model: str = None) -> dict:
    return await get_ai_config(model_type=model_type, requested_model=requested_model)


class StampDetectionOperator(BaseOperator):
    """
    Operator to detect physical red seals/stamps in a PDF document.

    Two-stage cascade:
      1. HSV coarse detection — fast, high-recall candidate finding
         (improved S threshold = 80 to reduce false positives).
      2. VLM verification — when AI is configured, each candidate region
         is cropped and sent to a vision model that confirms whether it is
         a real seal and extracts the seal text.  Non-seal candidates
         (red text, red borders, decorative elements) are filtered out.

    Falls back to HSV-only (with tightened thresholds) when AI is unavailable.
    """
    def __init__(self):
        super().__init__(name="StampDetectionOperator")

    @property
    def provides(self) -> List[str]:
        return ["detected_stamps"]

    @property
    def requires(self) -> List[str]:
        return ["pdf_bytes"]

    # ── HSV helpers ──────────────────────────────────────────────

    @staticmethod
    def _merge_nearby(candidates: List[dict], merge_gap: int = 40) -> List[dict]:
        """
        Merge stamp candidates whose bounding boxes are within *merge_gap*
        pixels of each other.  Uses union-find so that chains of nearby
        fragments collapse into one stamp.
        """
        if not candidates:
            return []

        n = len(candidates)
        parent = list(range(n))

        def find(i):
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i

        def union(a, b):
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb

        for i in range(n):
            ci = candidates[i]
            for j in range(i + 1, n):
                cj = candidates[j]
                gap_x = max(0, max(ci["x"], cj["x"]) - min(ci["x"] + ci["w"], cj["x"] + cj["w"]))
                gap_y = max(0, max(ci["y"], cj["y"]) - min(ci["y"] + ci["h"], cj["y"] + cj["h"]))
                if gap_x < merge_gap and gap_y < merge_gap:
                    union(i, j)

        groups: dict = {}
        for i in range(n):
            r = find(i)
            groups.setdefault(r, []).append(i)

        merged = []
        for indices in groups.values():
            x0 = min(candidates[i]["x"] for i in indices)
            y0 = min(candidates[i]["y"] for i in indices)
            x1 = max(candidates[i]["x"] + candidates[i]["w"] for i in indices)
            y1 = max(candidates[i]["y"] + candidates[i]["h"] for i in indices)
            total_area = sum(candidates[i]["area"] for i in indices)
            best_circ = max(candidates[i]["circularity"] for i in indices)
            merged.append({
                "x": x0, "y": y0,
                "w": x1 - x0, "h": y1 - y0,
                "area": total_area,
                "circularity": round(best_circ, 3)
            })
            if len(indices) > 1:
                logger.info(f"  Merged {len(indices)} fragments -> bbox=({x0},{y0},{x1-x0},{y1-y0})")

        return merged

    def _hsv_detect(self, page_img: np.ndarray, page_idx: int) -> List[dict]:
        """
        Run HSV-based red-color detection on a rendered page image.
        Returns a list of candidate dicts (unmerged).
        """
        # Convert to BGR (fitz -> RGB, then BGR for OpenCV)
        h, w = page_img.shape[:2]
        if len(page_img.shape) == 3 and page_img.shape[2] == 3:
            img_bgr = cv2.cvtColor(page_img, cv2.COLOR_RGB2BGR)
        elif len(page_img.shape) == 3 and page_img.shape[2] == 4:
            img_bgr = cv2.cvtColor(page_img, cv2.COLOR_RGBA2BGR)
        else:
            return []

        hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)

        # ── Improved red threshold ─────────────────────────────────
        # Raised S from 50 to 80 to reduce false positives from
        # red text, red page borders, and pink highlights.
        lower_red1 = np.array([0, 80, 80])
        upper_red1 = np.array([10, 255, 255])
        lower_red2 = np.array([160, 80, 80])
        upper_red2 = np.array([180, 255, 255])

        mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
        mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
        mask = mask1 + mask2

        dilate_kernel = np.ones((5, 5), np.uint8)
        mask = cv2.dilate(mask, dilate_kernel, iterations=1)

        kernel = np.ones((3, 3), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        red_pixel_count = cv2.countNonZero(mask)
        logger.info(
            f"  HSV page {page_idx + 1}: red_pixels={red_pixel_count},"
            f" raw_contours={len(contours)}"
        )

        candidates = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < 500:
                continue

            x, y, w, h = cv2.boundingRect(cnt)
            aspect_ratio = float(w) / h
            if aspect_ratio < 0.3 or aspect_ratio > 3.0:
                continue

            perimeter = cv2.arcLength(cnt, True)
            if perimeter == 0:
                continue
            circularity = 4 * np.pi * area / (perimeter * perimeter)

            if circularity < 0.2:
                continue

            candidates.append({
                "x": x, "y": y, "w": w, "h": h,
                "area": area, "circularity": circularity
            })

        return candidates

    # ── VLM verification ──────────────────────────────────────────

    async def _verify_candidate_vlm(
        self, image_bytes: bytes, idx: int
    ) -> Optional[dict]:
        """
        Send a single cropped candidate region to VLM for verification
        and text extraction.  Returns None if verification fails
        (API error, timeout) or the decoded JSON dict on success.
        """
        try:
            ai_config = await _get_ai_config("vision")
            if not ai_config.get("enabled") or not ai_config.get("api_key"):
                return None

            from openai import AsyncOpenAI
            client = AsyncOpenAI(
                api_key=ai_config["api_key"],
                base_url=ai_config.get("base_url", "https://api.openai.com/v1")
            )

            b64 = base64.b64encode(image_bytes).decode("utf-8")

            system_prompt = (
                "你是一个印章识别专家。请判断图片中是否包含红色公章/印章。\n"
                "如果包含印章，请提取印章中的可见文字。\n"
                "必须且只能返回以下 JSON 格式，不要包含其他内容：\n"
                '{"is_stamp": true/false, "stamp_text": "印章中的文字", "confidence": 0.0-1.0}\n'
                '如果图片中不是印章（例如红色文字、红色边框、装饰元素等），'
                '请返回 {"is_stamp": false, "stamp_text": "", "confidence": 0.0}'
            )

            response = await asyncio.wait_for(
                client.chat.completions.create(
                    model=ai_config.get("vision_model", "gpt-4o"),
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": "请判断该图片是否为红色印章："},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{b64}",
                                        "detail": "high"
                                    }
                                }
                            ]
                        }
                    ],
                    max_tokens=256,
                    temperature=0.1,
                    response_format={"type": "json_object"}
                ),
                timeout=30.0
            )

            raw = response.choices[0].message.content
            # Strip markdown fences just in case
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            return json.loads(cleaned)

        except asyncio.TimeoutError:
            logger.warning(f"  VLM candidate {idx} timed out (30s), treating as non-stamp")
            return None
        except Exception as e:
            logger.warning(f"  VLM candidate {idx} failed: {e}")
            return None

    async def _verify_candidates_vlm(
        self, crop_jpegs: List[bytes], page_idx: int
    ) -> List[Optional[dict]]:
        """
        Verify multiple candidates from the same page in parallel via VLM.
        """
        tasks = [
            self._verify_candidate_vlm(pix, i)
            for i, pix in enumerate(pixmaps)
        ]
        results = await asyncio.gather(*tasks)
        return results

    # ── Main execute ──────────────────────────────────────────────

    async def execute(self, context: DocumentContext, **kwargs) -> OperatorResult:
        pdf_bytes = context.shared_state.get("pdf_bytes")
        if not pdf_bytes:
            try:
                with open(context.file_path, "rb") as f:
                    pdf_bytes = f.read()
            except Exception as e:
                return OperatorResult(
                    operator_name=self.name,
                    pass_status=False,
                    message=f"无法加载 PDF 文件以进行印章检测: {e}"
                )

        try:
            import fitz
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")

            total_stamps = 0
            stamps_info = []
            vlm_available = None  # lazy check

            for page_idx, page in enumerate(doc):
                zoom = 2.0
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat, alpha=False)

                # Convert to numpy
                img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                    pix.height, pix.width, pix.n
                )

                # ── Stage 1: HSV coarse detection ──
                page_candidates = self._hsv_detect(img_array, page_idx)
                if not page_candidates:
                    continue

                # ── Merge nearby fragments ──
                merged = self._merge_nearby(page_candidates, merge_gap=15)

                # ── Stage 2: VLM verification ──
                if vlm_available is None:
                    ai_cfg = await _get_ai_config("vision")
                    vlm_available = (
                        ai_cfg.get("enabled") and bool(ai_cfg.get("api_key"))
                    )

                if vlm_available:
                    # Crop each candidate region from the full page image
                    crop_bytes_list = []
                    for det in merged:
                        x, y, w, h = det["x"], det["y"], det["w"], det["h"]
                        pad_x = int(w * 0.15)
                        pad_y = int(h * 0.15)
                        x0 = max(0, x - pad_x)
                        y0 = max(0, y - pad_y)
                        x1 = min(pix.width, x + w + pad_x)
                        y1 = min(pix.height, y + h + pad_y)

                        crop = img_array[y0:y1, x0:x1]
                        # Encode crop as JPEG bytes
                        crop_bgr = cv2.cvtColor(crop, cv2.COLOR_RGB2BGR)
                        _, jpeg_bytes = cv2.imencode(".jpg", crop_bgr,
                                                      [int(cv2.IMWRITE_JPEG_QUALITY), 90])
                        crop_bytes_list.append(jpeg_bytes.tobytes())

                    vlm_results = await self._verify_candidates_vlm(
                        crop_bytes_list, page_idx
                    )

                    # Filter: keep only VLM-confirmed stamps
                    verified_stamps = []
                    for det, vlm_res in zip(merged, vlm_results):
                        is_stamp = vlm_res and vlm_res.get("is_stamp", False)
                        if not is_stamp:
                            logger.info(
                                f"  VLM rejected candidate page {page_idx + 1}"
                                f" bbox=({det['x']},{det['y']},{det['w']},{det['h']})"
                                f" — not a real seal"
                            )
                            continue

                        stamp_text = vlm_res.get("stamp_text", "")
                        confidence = vlm_res.get("confidence", 0.0)
                        verified_stamps.append({**det, "stamp_text": stamp_text, "confidence": confidence})

                    for det in verified_stamps:
                        x, y, w, h = det["x"], det["y"], det["w"], det["h"]
                        total_stamps += 1
                        stamps_info.append({
                            "page": page_idx + 1,
                            "area": det["area"],
                            "circularity": det["circularity"],
                            "stamp_text": det.get("stamp_text", ""),
                            "confidence": det.get("confidence", 0.0),
                            "bounding_box": [
                                int(x / zoom), int(y / zoom),
                                int((x + w) / zoom), int((y + h) / zoom)
                            ]
                        })
                else:
                    # ── Fallback: HSV-only with improved thresholds ──
                    for det in merged:
                        x, y, w, h = det["x"], det["y"], det["w"], det["h"]
                        total_stamps += 1
                        stamps_info.append({
                            "page": page_idx + 1,
                            "area": det["area"],
                            "circularity": det["circularity"],
                            "bounding_box": [
                                int(x / zoom), int(y / zoom),
                                int((x + w) / zoom), int((y + h) / zoom)
                            ]
                        })

            doc.close()

            context.shared_state["detected_stamps"] = stamps_info

            if total_stamps > 0:
                return OperatorResult(
                    operator_name=self.name,
                    pass_status=True,
                    message=f"共检测到 {total_stamps} 个物理红色印章/公章。"
                            + ("（经 AI 视觉验证）" if vlm_available else ""),
                    extracted_data={"stamps": stamps_info, "count": total_stamps}
                )
            else:
                return OperatorResult(
                    operator_name=self.name,
                    pass_status=False,
                    message="未检测到物理红色印章。",
                    extracted_data={"stamps": [], "count": 0}
                )

        except Exception as e:
            logger.error(f"Stamp detection failed: {e}")
            return OperatorResult(
                operator_name=self.name,
                pass_status=False,
                message=f"印章检测发生错误: {e}"
            )
