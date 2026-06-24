import logging
import cv2
import numpy as np
from typing import List
from app.engine.base import BaseOperator, DocumentContext, OperatorResult

logger = logging.getLogger(__name__)

class StampDetectionOperator(BaseOperator):
    """
    Operator to detect physical red seals/stamps in a PDF document using OpenCV.
    """
    def __init__(self):
        super().__init__(name="StampDetectionOperator")

    @property
    def provides(self) -> List[str]:
        return ["detected_stamps"]

    @property
    def requires(self) -> List[str]:
        return ["pdf_bytes"]

    @staticmethod
    def _merge_nearby(candidates: List[dict], merge_gap: int = 40) -> List[dict]:
        """
        Merge stamp candidates whose bounding boxes are within *merge_gap*
        pixels of each other.  Uses a simple union-find so that chains of
        nearby fragments all collapse into one stamp.

        This keeps cross-page seam stamps (骑缝章) intact because they live
        on different pages and are never passed in together.
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

        # Merge any two candidates whose bbox gap < merge_gap
        for i in range(n):
            ci = candidates[i]
            for j in range(i + 1, n):
                cj = candidates[j]
                # Horizontal gap
                gap_x = max(0, max(ci["x"], cj["x"]) - min(ci["x"] + ci["w"], cj["x"] + cj["w"]))
                # Vertical gap
                gap_y = max(0, max(ci["y"], cj["y"]) - min(ci["y"] + ci["h"], cj["y"] + cj["h"]))
                if gap_x < merge_gap and gap_y < merge_gap:
                    union(i, j)

        # Group by root
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
                logger.info(f"  Merged {len(indices)} fragments → bbox=({x0},{y0},{x1-x0},{y1-y0})")

        return merged

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

            for page_idx, page in enumerate(doc):
                # Render page to image at ~150 DPI for good balance of speed and detection
                zoom = 2.0
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat, alpha=False)
                
                # Convert fitz pixmap to numpy array for OpenCV
                img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
                
                # If RGB, convert to BGR for OpenCV
                if pix.n == 3:
                    img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
                elif pix.n == 4:
                    img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGBA2BGR)
                else:
                    # Grayscale? Cannot detect red stamps reliably, skip
                    continue

                # Convert to HSV
                hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)

                # Red color wraps around in HSV
                lower_red1 = np.array([0, 50, 50])
                upper_red1 = np.array([10, 255, 255])
                lower_red2 = np.array([160, 50, 50])
                upper_red2 = np.array([180, 255, 255])

                mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
                mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
                mask = mask1 + mask2

                # Morphological: dilate first to merge nearby red fragments into
                # a single connected region, then clean up noise
                dilate_kernel = np.ones((7, 7), np.uint8)
                mask = cv2.dilate(mask, dilate_kernel, iterations=2)

                kernel = np.ones((3, 3), np.uint8)
                mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

                # Find contours
                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                red_pixel_count = cv2.countNonZero(mask)
                logger.info(f"Stamp detection page {page_idx + 1}: red_pixels={red_pixel_count}, raw_contours={len(contours)}")

                page_candidates = []

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

                    logger.info(
                        f"  contour: area={area}, aspect={aspect_ratio:.2f}, "
                        f"circularity={circularity:.3f}, bbox=({x},{y},{w},{h})"
                    )

                    if circularity < 0.2:
                        continue

                    page_candidates.append({
                        "x": x, "y": y, "w": w, "h": h,
                        "area": area, "circularity": circularity
                    })

            # Merge nearby candidates on the same page into single stamps.
            # Fragments of the same stamp (border arcs, text, star) that
            # survived contour detection get merged here.
            # Cross-page seam stamps (骑缝章) are unaffected — they live on
            # different pages and are never merged together.
            merged = self._merge_nearby(page_candidates, merge_gap=40)

            for det in merged:
                x, y, w, h = det["x"], det["y"], det["w"], det["h"]
                pad_x = int(w * 0.15)
                pad_y = int(h * 0.15)
                x0 = max(0, x - pad_x)
                y0 = max(0, y - pad_y)
                x1 = x + w + pad_x
                y1 = y + h + pad_y

                total_stamps += 1
                stamps_info.append({
                    "page": page_idx + 1,
                    "area": det["area"],
                    "circularity": det["circularity"],
                    "bounding_box": [int(x0/zoom), int(y0/zoom), int(x1/zoom), int(y1/zoom)]
                })

            doc.close()

            context.shared_state["detected_stamps"] = stamps_info
            
            if total_stamps > 0:
                return OperatorResult(
                    operator_name=self.name,
                    pass_status=True,
                    message=f"共检测到 {total_stamps} 个物理红色印章/公章。",
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
