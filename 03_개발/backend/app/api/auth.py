from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.core.security import hash_password, make_token, verify_password
from app.db.models import User
from app.db.session import get_db

router = APIRouter(prefix="/api")


class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class Register(Credentials):
    role: Literal["guardian", "parent"]


def user_out(u: User) -> dict:
    return {"id": u.id, "email": u.email, "role": u.role}


@router.post("/auth/register", status_code=201)
def register(body: Register, db: Session = Depends(get_db)):
    u = User(email=body.email.lower(), password_hash=hash_password(body.password), role=body.role)
    db.add(u)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "이미 가입된 이메일입니다")
    return {"access_token": make_token(u.id), "user": user_out(u)}


@router.post("/auth/login")
def login(body: Credentials, db: Session = Depends(get_db)):
    u = db.scalar(select(User).where(User.email == body.email.lower()))
    if not u or not verify_password(body.password, u.password_hash):
        raise HTTPException(401, "이메일 또는 비밀번호가 올바르지 않습니다")
    return {"access_token": make_token(u.id), "user": user_out(u)}


@router.get("/me")
def me(user: User = Depends(current_user)):
    return user_out(user)
