"""Candidate notes — written directly by humans, or approved from agent proposals."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.errors import AppError, ErrorCode
from app.models import Candidate, CandidateNote
from app.services import activity

MAX_NOTE_LENGTH = 2000


def add_note(
    db: Session,
    candidate: Candidate,
    body: str,
    *,
    source: str = "recruiter",
    author: str = "recruiter",
    approval_id: int | None = None,
) -> CandidateNote:
    body = (body or "").strip()
    if not body:
        raise AppError(ErrorCode.validation_error, "Note body must not be empty.")
    if len(body) > MAX_NOTE_LENGTH:
        raise AppError(
            ErrorCode.validation_error, f"Note is too long (max {MAX_NOTE_LENGTH} characters)."
        )
    note = CandidateNote(candidate_id=candidate.id, body=body, source=source, author=author)
    db.add(note)
    db.flush()
    activity.log(
        db,
        "note_added",
        f"Note added to {candidate.full_name} ({source}).",
        approval_id=approval_id,
        candidate_id=candidate.id,
        payload={"note_id": note.id, "source": source},
    )
    return note
