import json
import logging
import threading

from pywebpush import WebPushException, webpush
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import PushSubscription
from app.db.session import SessionLocal

log = logging.getLogger(__name__)


def enabled() -> bool:
    return bool(settings.vapid_private_key and settings.vapid_public_key)


def send_all(subs: list[dict], payload: dict) -> None:
    """구독마다 보낸다. 브라우저가 만료됐다고 답한 구독(404, 410)은 지운다."""
    dead = []
    for s in subs:
        try:
            webpush(subscription_info={"endpoint": s["endpoint"], "keys": s["keys"]}, data=json.dumps(payload, ensure_ascii=False),
                    vapid_private_key=settings.vapid_private_key, vapid_claims={"sub": settings.vapid_subject}, ttl=3600)
        except WebPushException as e:
            if e.response is not None and e.response.status_code in (404, 410):
                dead.append(s["endpoint"])
            else:
                log.warning("푸시 발송 실패: %s", e)
        except Exception as e:  # 잘못된 키 값 등. 한 구독의 실패가 나머지를 막지 않게 한다
            log.warning("푸시 발송 실패: %s", e)
    if dead:
        with SessionLocal() as db:
            db.execute(delete(PushSubscription).where(PushSubscription.endpoint.in_(dead)))
            db.commit()


def notify(db: Session, user_id: int, title: str, body: str, url: str) -> None:
    """키가 설정돼 있으면 사용자의 모든 기기에 푸시를 보낸다. 요청이 느려지지 않게 스레드에서 보낸다."""
    if not enabled():
        return
    subs = [{"endpoint": s.endpoint, "keys": s.keys} for s in db.scalars(select(PushSubscription).where(PushSubscription.user_id == user_id))]
    if subs:
        threading.Thread(target=send_all, args=(subs, {"title": title, "body": body, "url": url}), daemon=True).start()
