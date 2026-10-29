from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.db.models import Notification, PushSubscription, User, now
from app.db.session import get_db

router = APIRouter(prefix="/api")
LABEL = {"fall": "낙상 의심", "danger_zone": "위험 구역 접근", "bed_exit": "취침 구역 이탈", "offline": "카메라 오프라인"}


class Subscribe(BaseModel):
    endpoint: str
    keys: dict


def out(n: Notification) -> dict:
    e = n.event
    who = e.camera.recipient.display_name if e else ""
    return {
        "id": n.id, "event_id": n.event_id, "type": n.type, "title": f"{LABEL.get(n.type, n.type)} · {who}".strip(" ·"),
        "camera_name": e.camera.name if e else None, "sent_at": n.sent_at, "read_at": n.read_at,
    }


@router.get("/notifications")
def list_(user: User = Depends(current_user), db: Session = Depends(get_db)):
    q = select(Notification).where(Notification.user_id == user.id).order_by(Notification.sent_at.desc(), Notification.id.desc())
    return [out(n) for n in db.scalars(q)]


@router.post("/notifications/{notification_id}/read")
def read(notification_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    n = db.get(Notification, notification_id)
    if not n or n.user_id != user.id:
        raise HTTPException(404, "알림을 찾을 수 없습니다")
    n.read_at = n.read_at or now()
    db.commit()
    return out(n)


# 구독 정보만 저장한다. 실제 Web Push 발송은 VAPID 키 설정 후 별도 작업
@router.post("/push/subscribe", status_code=201)
def subscribe(body: Subscribe, user: User = Depends(current_user), db: Session = Depends(get_db)):
    sub = db.scalar(select(PushSubscription).where(PushSubscription.endpoint == body.endpoint))
    if sub:
        sub.user_id, sub.keys = user.id, body.keys
    else:
        db.add(PushSubscription(user_id=user.id, endpoint=body.endpoint, keys=body.keys))
    db.commit()
    return {"ok": True}
