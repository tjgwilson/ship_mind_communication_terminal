from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class QuestionStatus(str, Enum):
    queued = "queued"
    active = "active"
    timed_out = "timed_out"
    answered = "answered"


class Question(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    text: str = Field(min_length=1, max_length=100)
    status: QuestionStatus = QuestionStatus.queued
    created_at: str = Field(default_factory=utc_now)
    sent_at: str | None = None
    timed_out_at: str | None = None
    answered_at: str | None = None
    reply_text: str | None = None


class QuestionCreate(BaseModel):
    text: str = Field(min_length=1, max_length=100)


class ReplyCreate(BaseModel):
    reply_text: str = Field(min_length=1, max_length=1200)


class PanelState(BaseModel):
    active_question: Question | None
    current_questions: list[Question]
    answered_questions: list[Question]
    radio_online: bool
    radio_error: str | None = None
    responder_id: str
    last_transmission: str | None
