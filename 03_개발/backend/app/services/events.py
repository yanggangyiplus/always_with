from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Camera, Event, Notification, now

COOLDOWN = timedelta(seconds=60)


def create_event(db: Session, camera: Camera, type: str, score: float | None = None,
                 zone_id: int | None = None, source: str = "live") -> Event | None:
    """이벤트와 인앱 알림을 만든다. 일시정지 카메라이거나 60초 내 같은 이벤트가 있으면 만들지 않는다."""
    if camera.paused:
        return None
    recent = db.scalar(select(Event).where(
        Event.camera_id == camera.id, Event.type == type, Event.zone_id == zone_id,
        Event.occurred_at >= now() - COOLDOWN))
    if recent:
        return None
    ev = Event(camera_id=camera.id, type=type, zone_id=zone_id, score=score, source=source)
    db.add(ev)
    db.flush()
    db.add(Notification(user_id=camera.recipient.guardian_id, event_id=ev.id, type=type))
    db.commit()
    return ev
