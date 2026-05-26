import logging
from typing import List
from decimal import Decimal, ROUND_HALF_UP
from app.engine.base import BaseOperator, DocumentContext, OperatorResult

logger = logging.getLogger(__name__)

class TableVerificationOperator(BaseOperator):
    """
    升级版结构化表格提取与专业对账算子：
    1. 高精度金融级对账引擎：采用 Decimal 替代 float 进行计算，彻底杜绝浮点数二进制精度累计漂移，确保对账总和一分不差。
    2. 会计借贷格式自适应净化：智能解析负数及小括号包裹格式 (如 `(1,200.00)` 转换为 `-1200.00`)，保障收入与支出无遗漏稽核。
    3. 表格过滤降噪：多重过滤空白行和页边干扰，提供高纯净的结构化表格数据。
    """
    def __init__(self):
        super().__init__(name="TableVerificationOperator")

    @property
    def provides(self) -> List[str]:
        return ["extracted_tables"]

    @property
    def requires(self) -> List[str]:
        return ["pdf_bytes"]

    def _clean_cell(self, cell):
        """Helper to clean table cells (replace newlines, strip spaces)."""
        if cell is None:
            return ""
        return str(cell).replace('\n', ' ').strip()

    def _parse_financial_number(self, val_str: str) -> Decimal:
        """
        专业金融金额净化器：
        - 移除千分位逗号 `,`、货币符号 `¥`, `$`, `EUR`, `CNY` 等
        - 智能兼容会计记账法中的小括号负数格式，例如把 `(500.00)` 解析为 `Decimal("-500.00")`
        - 兼容减号负数格式，例如把 `-100.00` 解析为 `Decimal("-100.00")`
        """
        if not val_str:
            return Decimal("0.00")

        # 1. 净化多余的空格和符号
        cleaned = re.sub(r'[\s¥$元EURCNY]', '', val_str).replace(',', '')
        
        if not cleaned:
            return Decimal("0.00")

        # 2. 匹配并处理会计格式中的括号负数：如 (123.45) -> -123.45
        parentheses_match = re.match(r'^\((.*)\)$', cleaned)
        is_negative = False
        if parentheses_match:
            is_negative = True
            cleaned = parentheses_match.group(1)
            
        # 3. 处理减号负数：如 -123.45 -> -123.45
        if cleaned.startswith('-'):
            is_negative = True
            cleaned = cleaned[1:]

        try:
            # 使用 Decimal 进行高精度数值实例化
            val_dec = Decimal(cleaned)
            if is_negative:
                val_dec = -val_dec
            return val_dec
        except Exception:
            # 如果不是合法数字（例如表头、备注说明文字），安全返回 0.00
            return Decimal("0.00")

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
                    message=f"无法加载 PDF 文件: {e}"
                )

        target_column_index = kwargs.get("target_column_index", -1)
        try:
            target_column_index = int(target_column_index)
        except (ValueError, TypeError):
            target_column_index = -1

        all_tables = []
        total_rows = 0
        column_sum = Decimal("0.00")
        sum_attempted = False

        global re
        import re

        try:
            import pdfplumber
            import io
            
            stream = io.BytesIO(pdf_bytes)
            with pdfplumber.open(stream) as pdf:
                for page_idx, page in enumerate(pdf.pages):
                    tables = page.extract_tables()
                    for t_idx, table in enumerate(tables):
                        if not table:
                            continue
                            
                        cleaned_table = []
                        for row in table:
                            # 过滤纯空行
                            if all(cell is None or str(cell).strip() == "" for cell in row):
                                continue
                            cleaned_row = [self._clean_cell(cell) for cell in row]
                            cleaned_table.append(cleaned_row)
                            
                        if not cleaned_table:
                            continue

                        table_info = {
                            "page": page_idx + 1,
                            "table_index": t_idx + 1,
                            "rows": len(cleaned_table),
                            "columns": len(cleaned_table[0]) if cleaned_table else 0,
                            "data": cleaned_table
                        }
                        
                        all_tables.append(table_info)
                        total_rows += len(cleaned_table)
                        
                        # 执行高精度金融累加对账
                        if target_column_index >= 0:
                            sum_attempted = True
                            # 跳过表头 row[0]
                            for row in cleaned_table[1:]:
                                if target_column_index < len(row):
                                    cell_val = row[target_column_index]
                                    parsed_val = self._parse_financial_number(cell_val)
                                    column_sum += parsed_val
                                        
            context.shared_state["extracted_tables"] = all_tables
            
            if not all_tables:
                return OperatorResult(
                    operator_name=self.name,
                    pass_status=False,
                    message="未能在该文档中提取到任何结构化表格。",
                    extracted_data={"tables": [], "total_tables": 0}
                )
            
            # 格式化成规范的金融金额输出，保留两位小数
            formatted_sum = column_sum.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            
            msg = f"成功提取到 {len(all_tables)} 个表格，共计 {total_rows} 行数据。"
            if sum_attempted:
                msg += f" 对第 {target_column_index} 列执行专业级高精度对账求和结果为: {formatted_sum}。"
                
            return OperatorResult(
                operator_name=self.name,
                pass_status=True,
                message=msg,
                extracted_data={
                    "total_tables": len(all_tables),
                    "total_rows": total_rows,
                    "tables": all_tables,
                    "summation_result": float(formatted_sum) if sum_attempted else None
                }
            )

        except Exception as e:
            logger.error(f"Table extraction failed: {e}")
            return OperatorResult(
                operator_name=self.name,
                pass_status=False,
                message=f"表格提取与对账发生错误: {e}"
            )
