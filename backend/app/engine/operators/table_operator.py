import logging
from typing import List
from app.engine.base import BaseOperator, DocumentContext, OperatorResult

logger = logging.getLogger(__name__)

class TableVerificationOperator(BaseOperator):
    """
    Operator to extract and structure tables from a PDF document using pdfplumber.
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
        column_sum = 0.0
        sum_attempted = False

        try:
            import pdfplumber
            import io
            
            # Use BytesIO to read from memory
            stream = io.BytesIO(pdf_bytes)
            with pdfplumber.open(stream) as pdf:
                for page_idx, page in enumerate(pdf.pages):
                    # extract_tables() returns a list of tables on the page
                    tables = page.extract_tables()
                    for t_idx, table in enumerate(tables):
                        if not table:
                            continue
                            
                        # Clean the table data
                        cleaned_table = []
                        for row in table:
                            # Filter out completely empty rows
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
                        
                        # Experimental numeric summation if target_column_index is valid
                        if target_column_index >= 0:
                            sum_attempted = True
                            # Start from row 1 assuming row 0 is header
                            for row in cleaned_table[1:]:
                                if target_column_index < len(row):
                                    cell_val = row[target_column_index]
                                    # Very basic currency/numeric cleanup
                                    num_str = cell_val.replace(',', '').replace('¥', '').replace('$', '').strip()
                                    try:
                                        column_sum += float(num_str)
                                    except ValueError:
                                        pass
                                        
            context.shared_state["extracted_tables"] = all_tables
            
            if not all_tables:
                return OperatorResult(
                    operator_name=self.name,
                    pass_status=False,
                    message="未能在该文档中提取到任何结构化表格。",
                    extracted_data={"tables": [], "total_tables": 0}
                )
            
            msg = f"成功提取到 {len(all_tables)} 个表格，共计 {total_rows} 行数据。"
            if sum_attempted:
                msg += f" 对第 {target_column_index} 列尝试数值求和结果为: {column_sum:.2f}。"
                
            return OperatorResult(
                operator_name=self.name,
                pass_status=True,
                message=msg,
                extracted_data={
                    "total_tables": len(all_tables),
                    "total_rows": total_rows,
                    "tables": all_tables,
                    "summation_result": column_sum if sum_attempted else None
                }
            )

        except Exception as e:
            logger.error(f"Table extraction failed: {e}")
            return OperatorResult(
                operator_name=self.name,
                pass_status=False,
                message=f"表格提取发生错误: {e}"
            )
