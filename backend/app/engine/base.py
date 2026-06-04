from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class OperatorResult(BaseModel):
    """Standardized output structure for any Verification Operator"""
    operator_name: str
    pass_status: bool = True
    confidence: float = 1.0
    message: str = ""
    # Store any operator-specific outputs (like extracted text, coordinates, bounding boxes)
    extracted_data: Dict[str, Any] = Field(default_factory=dict)

class DocumentContext(BaseModel):
    """Represents the document state passed through the engine"""
    file_path: str
    file_type: Optional[str] = None
    # Shared state cache between operators
    # Example: OCR operator extracts text, stores it here. LLM operator reads it.
    shared_state: Dict[str, Any] = Field(default_factory=dict)
    # Node outputs cache for structured workflow variables
    node_outputs: Dict[str, Dict[str, Any]] = Field(default_factory=dict)

class BaseOperator(ABC):
    """Abstract Base Class for all Verification Operators"""
    
    def __init__(self, name: str):
        self.name = name

    @property
    @abstractmethod
    def provides(self) -> List[str]:
        """List of state keys this operator populates in DocumentContext.shared_state"""
        return []

    @property
    @abstractmethod
    def requires(self) -> List[str]:
        """List of state keys this operator requires to run"""
        return []

    @abstractmethod
    async def execute(self, context: DocumentContext, **kwargs) -> OperatorResult:
        """
        Execute the operator logic.
        :param context: The shared document context containing file path and previous operator results.
        :param kwargs: Operator specific configuration (e.g. prompt, regex pattern).
        :return: OperatorResult indicating pass/fail and extracted data.
        """
        pass
