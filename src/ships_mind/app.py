from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .config import settings
from .meshtastic_gateway import GatewayConfig, MeshtasticGateway
from .models import QuestionCreate, ReplyCreate
from .queue_manager import QueueManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app = FastAPI(title="Ship's Core Communications Console")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

queue_manager = QueueManager(
    settings.data_dir,
    settings.responder_id,
    settings.active_timeout_seconds,
)
gateway = MeshtasticGateway(
    GatewayConfig(
        mode=settings.meshtastic_mode,
        device=settings.meshtastic_device,
        channel=settings.meshtastic_channel,
        responder_id=settings.responder_id,
    )
)


async def dispatch_next_question() -> None:
    expired = await queue_manager.expire_active_question()
    if expired is not None:
        logger.warning("Question %s timed out", expired.id)

    active = await queue_manager.active_question()
    if active is not None:
        return

    next_question = await queue_manager.next_queued()
    if next_question is None:
        return

    activated = await queue_manager.mark_active(next_question.id)
    if activated is None:
        return

    gateway.send_question(activated)


@app.on_event("startup")
async def startup_event() -> None:
    gateway.connect()
    await dispatch_next_question()


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "index.html",
        {"request": request, "responder_id": settings.responder_id},
    )


@app.get("/api/state")
async def get_state():
    return await queue_manager.state(gateway.online)


@app.post("/api/questions")
async def submit_question(payload: QuestionCreate):
    question = await queue_manager.enqueue(payload)
    await dispatch_next_question()
    return question


@app.post("/api/reply")
async def submit_reply(payload: ReplyCreate):
    answered = await queue_manager.answer_active(payload)
    if answered is None:
        raise HTTPException(status_code=409, detail="There is no active question to answer.")

    await dispatch_next_question()
    return answered
