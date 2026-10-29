from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.cameras import status_of
from app.api.deps import get_camera, guardian
from app.db.models import Zone, User
from app.db.session import get_db

router = APIRouter(prefix="/api")
MAX_ZONES, MIN_SIZE = 3, 0.05
HHMM = r"^([01]\d|2[0-3]):[0-5]\d$"


class ZoneIn(BaseModel):
    name: str = Field(min_length=1, max_length=30)
    purpose: Literal["danger", "bed"]
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    w: float = Field(ge=MIN_SIZE, le=1)
    h: float = Field(ge=MIN_SIZE, le=1)
    active_from: str | None = Field(None, pattern=HHMM)
    active_to: str | None = Field(None, pattern=HHMM)
    dwell_sec: int | None = Field(None, ge=1, le=3600)

    @model_validator(mode="after")
    def check(self):
        if self.x + self.w > 1 or self.y + self.h > 1:
            raise ValueError("구역이 화면 밖으로 벗어납니다")
        if self.purpose == "bed" and not (self.active_from and self.active_to):
            raise ValueError("취침 구역은 취침 시간대가 필요합니다")
        return self


def out(z: Zone) -> dict:
    return {c: getattr(z, c) for c in ("id", "camera_id", "name", "purpose", "x", "y", "w", "h", "active_from", "active_to", "dwell_sec")}


@router.post("/cameras/{camera_id}/zones", status_code=201)
def create(camera_id: int, body: ZoneIn, user: User = Depends(guardian), db: Session = Depends(get_db)):
    c = get_camera(db, user, camera_id)
    if c.recipient.type != "child":
        raise HTTPException(400, "위험·취침 구역은 아이 카메라에만 지정할 수 있습니다")
    if status_of(c) == "offline":
        raise HTTPException(400, "카메라가 오프라인이면 구역을 설정할 수 없습니다")
    if len(db.scalars(select(Zone).where(Zone.camera_id == c.id)).all()) >= MAX_ZONES:
        raise HTTPException(400, f"구역은 카메라당 최대 {MAX_ZONES}개입니다")
    data = body.model_dump()
    data["dwell_sec"] = data["dwell_sec"] or (3 if body.purpose == "danger" else 30)  # 기본 기준 시간
    if body.purpose == "danger":
        data["active_from"] = data["active_to"] = None
    z = Zone(camera_id=c.id, **data)
    db.add(z)
    db.commit()
    return out(z)


@router.get("/cameras/{camera_id}/zones")
def list_(camera_id: int, user: User = Depends(guardian), db: Session = Depends(get_db)):
    get_camera(db, user, camera_id)
    return [out(z) for z in db.scalars(select(Zone).where(Zone.camera_id == camera_id))]


@router.delete("/zones/{zone_id}", status_code=204)
def delete(zone_id: int, user: User = Depends(guardian), db: Session = Depends(get_db)):
    z = db.get(Zone, zone_id)
    if not z:
        raise HTTPException(404, "구역을 찾을 수 없습니다")
    get_camera(db, user, z.camera_id)
    db.delete(z)
    db.commit()
