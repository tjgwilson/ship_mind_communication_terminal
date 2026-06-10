from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

from .models import PanelState, Question, QuestionCreate, QuestionStatus, ReplyCreate, utc_now


class QueueManager:
    def __init__(self, data_dir: Path, responder_id: str, active_timeout_seconds: int) -> None:
        self._lock = asyncio.Lock()
        self._data_dir = data_dir
        self._queue_file = data_dir / "questions.json"
        self._responder_id = responder_id
        self._active_timeout_seconds = active_timeout_seconds
        self._questions: list[Question] = []
        self._last_transmission: str | None = None
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._load()

    def _load(self) -> None:
        if not self._queue_file.exists():
            self._questions = []
            return

        raw = json.loads(self._queue_file.read_text())
        self._questions = [Question.model_validate(item) for item in raw]

    def _save(self) -> None:
        payload = [question.model_dump(mode="json") for question in self._questions]
        self._queue_file.write_text(json.dumps(payload, indent=2))

    def _active_question_unlocked(self) -> Question | None:
        return next((q for q in self._questions if q.status == QuestionStatus.active), None)

    def _queued_questions_unlocked(self) -> list[Question]:
        return [q for q in self._questions if q.status == QuestionStatus.queued]

    def _current_questions_unlocked(self) -> list[Question]:
        current = [
            q
            for q in self._questions
            if q.status in {QuestionStatus.queued, QuestionStatus.active, QuestionStatus.timed_out}
        ]
        return list(reversed(current[-24:]))

    def _answered_questions_unlocked(self) -> list[Question]:
        answered = [q for q in self._questions if q.status == QuestionStatus.answered]
        return list(reversed(answered[-12:]))

    def _parse_timestamp(self, value: str | None) -> datetime | None:
        if not value:
            return None
        return datetime.fromisoformat(value)

    def _expire_active_question_unlocked(self) -> Question | None:
        active = self._active_question_unlocked()
        if active is None:
            return None

        sent_at = self._parse_timestamp(active.sent_at)
        if sent_at is None:
            return None

        age_seconds = (datetime.now(timezone.utc) - sent_at).total_seconds()
        if age_seconds < self._active_timeout_seconds:
            return None

        active.status = QuestionStatus.timed_out
        active.timed_out_at = utc_now()
        self._save()
        return active

    async def enqueue(self, payload: QuestionCreate) -> Question:
        async with self._lock:
            question = Question(text=payload.text.strip())
            self._questions.append(question)
            self._save()
            return question

    async def mark_active(self, question_id: str) -> Question | None:
        async with self._lock:
            active = self._active_question_unlocked()
            if active is not None:
                return None

            for question in self._questions:
                if question.id == question_id and question.status == QuestionStatus.queued:
                    question.status = QuestionStatus.active
                    question.sent_at = utc_now()
                    self._last_transmission = question.sent_at
                    self._save()
                    return question

            return None

    async def answer_active(self, payload: ReplyCreate) -> Question | None:
        async with self._lock:
            active = self._active_question_unlocked()
            if active is None:
                return None

            active.status = QuestionStatus.answered
            active.reply_text = payload.reply_text.strip()
            active.answered_at = utc_now()
            self._save()
            return active

    async def clear_pending(self) -> None:
        async with self._lock:
            self._questions = [
                question for question in self._questions if question.status == QuestionStatus.answered
            ]
            self._last_transmission = None
            self._save()

    async def next_queued(self) -> Question | None:
        async with self._lock:
            return next((q for q in self._questions if q.status == QuestionStatus.queued), None)

    async def expire_active_question(self) -> Question | None:
        async with self._lock:
            return self._expire_active_question_unlocked()

    async def active_question(self) -> Question | None:
        async with self._lock:
            return self._active_question_unlocked()

    async def state(self, radio_online: bool) -> PanelState:
        async with self._lock:
            self._expire_active_question_unlocked()
            return PanelState(
                active_question=self._active_question_unlocked(),
                current_questions=self._current_questions_unlocked(),
                answered_questions=self._answered_questions_unlocked(),
                radio_online=radio_online,
                responder_id=self._responder_id,
                last_transmission=self._last_transmission,
            )
