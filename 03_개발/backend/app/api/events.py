from datetime import datetime
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import guardian
from app.db.models import Camera, CareRecipient, Event, FeedbackSample, User, now
from app.db.session import get_db

router = APIRouter(prefix="/api/events")
PAGE_SIZE = 20


class EventPatch(BaseModel):
    status: Literal["acknowledged", "false_alarm"]


def out(e: Event) -> dict:
    r = e.camera.recipient
    return {
        "id": e.id, "type": e.type, "zone_id": e.zone_id, "source": e.source, "occurred_at": e.occurred_at,
        "score": e.score, "status": e.status, "clip_status": e.clip_status,
        "camera_id": e.camera_id, "camera_name": e.camera.name,
        "recipient_name": r.display_name, "recipient_type": r.type, "beta": r.type == "child",
    }


def own_event(db: Session, user: User, event_id: int) -> Event:
    e = db.get(Event, event_id)
    if not e:
        raise HTTPException(404, "이벤트를 찾을 수 없습니다")
    if e.camera.recipient.guardian_id != user.id:
        raise HTTPException(403, "권한이 없습니다")
    return e


@router.get("")
def list_(status: Literal["new", "acknowledged", "false_alarm"] | None = None,
          from_: datetime | None = Query(None, alias="from"), to: datetime | None = None,
          page: int = Query(1, ge=1), user: User = Depends(guardian), db: Session = Depends(get_db)):
    q = select(Event).join(Camera).join(CareRecipient).where(CareRecipient.guardian_id == user.id)
    if status:
        q = q.where(Event.status == status)
    if from_:
        q = q.where(Event.occurred_at >= from_)
    if to:
        q = q.where(Event.occurred_at <= to)
    q = q.order_by(Event.occurred_at.desc(), Event.id.desc()).limit(PAGE_SIZE).offset((page - 1) * PAGE_SIZE)
    return [out(e) for e in db.scalars(q)]


@router.get("/{event_id}")
def detail(event_id: int, user: User = Depends(guardian), db: Session = Depends(get_db)):
    return out(own_event(db, user, event_id))


@router.patch("/{event_id}")
def update(event_id: int, body: EventPatch, user: User = Depends(guardian), db: Session = Depends(get_db)):
    e = own_event(db, user, event_id)
    if e.status == "new":  # 미확인에서만 전이, 이미 처리됐으면 최신 상태를 그대로 돌려줌
        e.status, e.reviewed_by, e.reviewed_at = body.status, user.id, now()
        if body.status == "false_alarm":
            db.add(FeedbackSample(event_id=e.id, label="false_alarm"))
        db.commit()
    return out(e)


@router.get("/{event_id}/clip")
def clip(event_id: int, user: User = Depends(guardian), db: Session = Depends(get_db)):
    e = own_event(db, user, event_id)
    if not e.clip_path or not Path(e.clip_path).is_file():
        raise HTTPException(404, "클립이 없습니다")
    return FileResponse(e.clip_path, media_type="video/mp4")
