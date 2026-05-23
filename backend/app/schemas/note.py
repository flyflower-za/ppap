from pydantic import BaseModel, ConfigDict
from datetime import datetime


class NoteBase(BaseModel):
    """Base note schema."""
    content: str


class NoteCreate(NoteBase):
    """Note creation schema."""
    file_id: str


class NoteResponse(NoteBase):
    """Note response schema."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    file_id: str
    author_id: str
    author_name: str  # Derived from user
    created_at: datetime
    updated_at: datetime
