from datetime import timedelta

from fastapi import APIRouter, Body, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user, get_camera, guardian, own_recipient
from app.db.models import Camera, CareRecipient, User, now
from app.db.session import get_db
from app.services import pose

router = APIRouter(prefix="/api/cameras")
OFFLINE_AFTER = timedelta(seconds=30)


class CameraIn(BaseModel):
    recipient_id: int
    name: str = Field(min_length=1, max_length=30)
    location_label: str | None = Field(None, max_length=30)


class CameraPatch(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=30)
    paused: bool | None = None


def status_of(c: Camera) -> str:
    if c.paused:
        return "paused"
    return "connected" if c.last_seen_at and now() - c.last_seen_at < OFFLINE_AFTER else "offline"


def out(c: Camera) -> dict:
    r = c.recipient
    return {
        "id": c.id, "name": c.name, "location_label": c.location_label, "status": status_of(c),
        "recipient_id": r.id, "recipient_name": r.display_name, "recipient_type": r.type, "beta": r.type == "child",
    }


@router.post("", status_code=201)
def create(body: CameraIn, user: User = Depends(guardian), db: Session = Depends(get_db)):
    r = own_recipient(db, user, body.recipient_id)
    # NFR-07: 동의 전에는 카메라 연결을 시작하지 않는다
    if r.type == "child" and not r.consent_confirmed_at:
        raise HTTPException(400, "법정대리인 동의 후 카메라를 등록할 수 있습니다")
    if r.type == "senior" and not r.user_id:
        raise HTTPException(400, "부모님이 연결에 동의한 후 카메라를 등록할 수 있습니다")
    c = Camera(recipient_id=r.id, name=body.name, location_label=body.location_label)
    db.add(c)
    db.commit()
    return out(c)


@router.get("")
def list_(user: User = Depends(guardian), db: Session = Depends(get_db)):
    q = select(Camera).join(CareRecipient).where(CareRecipient.guardian_id == user.id)
    return [out(c) for c in db.scalars(q)]


@router.post("/{camera_id}/heartbeat")
def heartbeat(camera_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    c = get_camera(db, user, camera_id, allow_parent=True)
    c.last_seen_at = now()
    db.commit()
    return out(c)


@router.post("/{camera_id}/analyze")
def analyze(camera_id: int, frame: bytes = Body(media_type="image/jpeg"), user: User = Depends(guardian), db: Session = Depends(get_db)):
    """브라우저가 보낸 프레임에서 관절을 찾아 그린 JPEG를 돌려주고, 낙상이면 이벤트를 만든다."""
    c = get_camera(db, user, camera_id)
    try:
        return Response(pose.analyze(db, c, frame), media_type="image/jpeg")
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.patch("/{camera_id}")
def patch(camera_id: int, body: CameraPatch, user: User = Depends(guardian), db: Session = Depends(get_db)):
    c = get_camera(db, user, camera_id)
    if body.name is not None:
        c.name = body.name
    if body.paused is not None:
        c.paused = body.paused
    db.commit()
    return out(c)
