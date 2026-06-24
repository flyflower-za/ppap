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

                # Morphological operations
                kernel = np.ones((3, 3), np.uint8)
                mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
                mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

                # Find contours
                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                red_pixel_count = cv2.countNonZero(mask)
                logger.info(f"Stamp detection page {page_idx + 1}: red_pixels={red_pixel_count}, raw_contours={len(contours)}")

                page_h, page_w = img_bgr.shape[:2]
                page_area = page_w * page_h

                for cnt in contours:
                    area = cv2.contourArea(cnt)
                    # Area filter: minimum 1000px (~250px² at 2x zoom = ~1.2cm stamp)
                    # Maximum 40% of page area to exclude full-page red backgrounds
                    if area < 1000 or area > page_area * 0.4:
                        continue

                    x, y, w, h = cv2.boundingRect(cnt)
                    aspect_ratio = float(w) / h
                    if aspect_ratio < 0.3 or aspect_ratio > 3.0:
                        continue

                    # Circularity filter: real stamps are circular/elliptical
                    # Circle ≈ 1.0, square ≈ 0.78, text/lines < 0.3
                    perimeter = cv2.arcLength(cnt, True)
                    if perimeter == 0:
                        continue
                    circularity = 4 * np.pi * area / (perimeter * perimeter)
                    if circularity < 0.4:
                        logger.debug(f"  Rejected contour: area={area}, aspect={aspect_ratio:.2f}, circularity={circularity:.3f}")
                        continue

                    logger.info(f"  Stamp found: area={area}, aspect={aspect_ratio:.2f}, circularity={circularity:.3f}")
                    total_stamps += 1
                    stamps_info.append({
                        "page": page_idx + 1,
                        "area": int(area),
                        "circularity": round(circularity, 3),
                        "bounding_box": [int(x/zoom), int(y/zoom), int((x+w)/zoom), int((y+h)/zoom)]
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
