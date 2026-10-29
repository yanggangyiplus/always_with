import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import read_token
from app.db.models import Camera, CareRecipient, User
from app.db.session import get_db

bearer = HTTPBearer(auto_error=False)


def current_user(creds: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)) -> User:
    try:
        user = db.get(User, read_token(creds.credentials)) if creds else None
    except (jwt.PyJWTError, KeyError, ValueError):
        user = None
    if not user:
        raise HTTPException(401, "인증이 필요합니다")
    return user


def guardian(user: User = Depends(current_user)) -> User:
    if user.role != "guardian":
        raise HTTPException(403, "보호자만 사용할 수 있습니다")
    return user


def own_recipient(db: Session, user: User, recipient_id: int) -> CareRecipient:
    r = db.get(CareRecipient, recipient_id)
    if not r:
        raise HTTPException(404, "돌봄 대상을 찾을 수 없습니다")
    if r.guardian_id != user.id:
        raise HTTPException(403, "권한이 없습니다")
    return r


def get_camera(db: Session, user: User, camera_id: int, allow_parent: bool = False) -> Camera:
    c = db.get(Camera, camera_id)
    if not c:
        raise HTTPException(404, "카메라를 찾을 수 없습니다")
    r = c.recipient
    if r.guardian_id != user.id and not (allow_parent and r.user_id == user.id):
        raise HTTPException(403, "권한이 없습니다")
    return c
