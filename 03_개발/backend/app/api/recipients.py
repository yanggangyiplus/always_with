from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import guardian, own_recipient
from app.db.models import CareRecipient, User, now
from app.db.session import get_db

router = APIRouter(prefix="/api/recipients")


class RecipientIn(BaseModel):
    type: Literal["senior", "child"]
    display_name: str = Field(min_length=1, max_length=30)
    birth_year: int | None = Field(None, ge=1900, le=2100)
    consent_confirmed: bool = False  # 아이: 법정대리인 동의


class RecipientPatch(BaseModel):
    display_name: str | None = Field(None, min_length=1, max_length=30)
    birth_year: int | None = Field(None, ge=1900, le=2100)
    consent_confirmed: bool | None = None


def out(r: CareRecipient) -> dict:
    return {
        "id": r.id, "type": r.type, "display_name": r.display_name, "birth_year": r.birth_year,
        "linked": r.user_id is not None, "consent_confirmed": r.consent_confirmed_at is not None,
        "beta": r.type == "child",
    }


@router.post("", status_code=201)
def create(body: RecipientIn, user: User = Depends(guardian), db: Session = Depends(get_db)):
    r = CareRecipient(guardian_id=user.id, type=body.type, display_name=body.display_name, birth_year=body.birth_year)
    if body.type == "child" and body.consent_confirmed:
        r.consent_confirmed_at = now()
    db.add(r)
    db.commit()
    return out(r)


@router.get("")
def list_(user: User = Depends(guardian), db: Session = Depends(get_db)):
    return [out(r) for r in db.scalars(select(CareRecipient).where(CareRecipient.guardian_id == user.id))]


@router.patch("/{recipient_id}")
def patch(recipient_id: int, body: RecipientPatch, user: User = Depends(guardian), db: Session = Depends(get_db)):
    r = own_recipient(db, user, recipient_id)
    for k in ("display_name", "birth_year"):
        if getattr(body, k) is not None:
            setattr(r, k, getattr(body, k))
    if body.consent_confirmed and r.type == "child" and not r.consent_confirmed_at:
        r.consent_confirmed_at = now()
    db.commit()
    return out(r)
