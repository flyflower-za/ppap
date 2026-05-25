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
                # Lower red range
                lower_red1 = np.array([0, 50, 50])
                upper_red1 = np.array([10, 255, 255])
                # Upper red range
                lower_red2 = np.array([160, 50, 50])
                upper_red2 = np.array([180, 255, 255])

                mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
                mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
                mask = mask1 + mask2

                # Morphological operations to remove noise
                kernel = np.ones((5, 5), np.uint8)
                mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
                mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

                # Find contours
                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                for cnt in contours:
                    area = cv2.contourArea(cnt)
                    # Filter out very small red text/noise and extremely large red blocks
                    if 1000 < area < 500000:
                        x, y, w, h = cv2.boundingRect(cnt)
                        aspect_ratio = float(w) / h
                        # Stamps are usually circular/elliptical/square
                        if 0.5 < aspect_ratio < 2.0:
                            total_stamps += 1
                            stamps_info.append({
                                "page": page_idx + 1,
                                "area": int(area),
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
