from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.schemas.note import NoteCreate, NoteResponse
from app.models.note import Note
from app.models.user import User
from app.api.deps import get_current_user
from datetime import datetime
import uuid

router = APIRouter(prefix="/notes", tags=["Notes"])


@router.post("", response_model=NoteResponse)
async def create_note(
    note: NoteCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a note on a file."""
    # Verify file exists and user has access
    from app.models.file import File
    file_result = await db.execute(select(File).where(File.id == note.file_id))
    file = file_result.scalar_one_or_none()

    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

    # Create note
    db_note = Note(
        id=str(uuid.uuid4()),
        file_id=note.file_id,
        author_id=current_user.id,
        content=note.content,
    )

    db.add(db_note)
    await db.commit()
    await db.refresh(db_note)

    return NoteResponse(
        id=db_note.id,
        file_id=db_note.file_id,
        author_id=db_note.author_id,
        author_name=current_user.full_name,
        content=db_note.content,
        created_at=db_note.created_at,
        updated_at=db_note.updated_at,
    )


@router.get("/file/{file_id}", response_model=List[NoteResponse])
async def get_file_notes(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all notes for a file."""
    from app.models.file import File
    from sqlalchemy import select

    # Verify file exists
    file_result = await db.execute(select(File).where(File.id == file_id))
    file = file_result.scalar_one_or_none()

    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

    # Get notes with author info
    result = await db.execute(
        select(Note, User)
        .join(User, Note.author_id == User.id)
        .where(Note.file_id == file_id)
        .order_by(Note.created_at.desc())
    )

    notes = []
    for note, user in result.all():
        notes.append(
            NoteResponse(
                id=note.id,
                file_id=note.file_id,
                author_id=note.author_id,
                author_name=user.full_name,
                content=note.content,
                created_at=note.created_at,
                updated_at=note.updated_at,
            )
        )

    return notes


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(
    note_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a note (only by author or admin)."""
    result = await db.execute(select(Note).where(Note.id == note_id))
    note = result.scalar_one_or_none()

    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found",
        )

    # Check ownership
    if note.author_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this note",
        )

    await db.delete(note)
    await db.commit()
