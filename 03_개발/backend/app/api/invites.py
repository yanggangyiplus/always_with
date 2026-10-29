import secrets
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.deps import current_user, guardian, own_recipient
from app.db.models import CareRecipient, Invite, Link, User, now
from app.db.session import get_db

router = APIRouter(prefix="/api")
MAX_FAILS, LOCK = 5, timedelta(minutes=10)
# shortcut: 오입력 횟수를 프로세스 메모리에 보관, 서버를 여러 대로 늘리면 DB로 옮긴다
_fails: dict[int, tuple[int, object]] = {}


class InviteIn(BaseModel):
    recipient_id: int


class Accept(BaseModel):
    code: str = Field(pattern=r"^\d{6}$")
    consent: bool


@router.post("/invites", status_code=201)
def issue(body: InviteIn, user: User = Depends(guardian), db: Session = Depends(get_db)):
    r = own_recipient(db, user, body.recipient_id)
    if r.type == "child" and not r.consent_confirmed_at:
        raise HTTPException(400, "법정대리인 동의 후 아이 계정을 연결할 수 있습니다")
    if r.user_id:
        raise HTTPException(409, "이미 연결되었습니다")
    while db.scalar(select(Invite).where(Invite.code == (code := f"{secrets.randbelow(10**6):06d}"))):
        pass
    inv = Invite(code=code, issuer_id=user.id, recipient_id=r.id, expires_at=now() + timedelta(minutes=10))
    db.add(inv)
    db.commit()
    return {"code": code, "expires_at": inv.expires_at}


@router.post("/invites/accept")
def accept(body: Accept, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if user.role != "parent":
        raise HTTPException(403, "부모님 계정만 코드를 입력할 수 있습니다")
    count, since = _fails.get(user.id, (0, now()))
    if count >= MAX_FAILS:
        if now() - since < LOCK:
            raise HTTPException(429, "오입력이 많아 10분간 잠겼습니다")
        count = 0
    inv = db.scalar(select(Invite).where(Invite.code == body.code))
    if not inv or inv.used_at or inv.expires_at < now():
        _fails[user.id] = (count + 1, now())
        raise HTTPException(400, "만료되었거나 사용된 코드입니다")
    if not body.consent:
        raise HTTPException(400, "동의가 필요합니다")
    _fails.pop(user.id, None)
    inv.used_at = now()
    db.get(CareRecipient, inv.recipient_id).user_id = user.id
    link = Link(guardian_id=inv.issuer_id, parent_id=user.id, recipient_id=inv.recipient_id)
    db.add(link)
    db.commit()
    return {"id": link.id, "status": link.status}


@router.get("/links")
def links(user: User = Depends(current_user), db: Session = Depends(get_db)):
    q = select(Link).where(or_(Link.guardian_id == user.id, Link.parent_id == user.id))
    return [{"id": l.id, "recipient_id": l.recipient_id, "status": l.status, "consented_at": l.consented_at}
            for l in db.scalars(q)]
