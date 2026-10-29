import secrets
from datetime import UTC, datetime, timedelta
from typing import Literal
from urllib.parse import quote, urlencode

import httpx
import jwt
from fastapi import APIRouter, Cookie, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password, make_token
from app.db.models import OAuthAccount, User
from app.db.session import get_db

router = APIRouter(prefix="/api/auth/oauth")

# 제공자별 주소. scope를 비운 카카오는 콘솔에서 동의항목으로 이메일을 켠 경우에만 이메일이 온다.
PROVIDERS = {
    "google": dict(auth="https://accounts.google.com/o/oauth2/v2/auth", token="https://oauth2.googleapis.com/token",
                   me="https://www.googleapis.com/oauth2/v3/userinfo", scope="openid email"),
    "kakao": dict(auth="https://kauth.kakao.com/oauth/authorize", token="https://kauth.kakao.com/oauth/token",
                  me="https://kapi.kakao.com/v2/user/me", scope=""),
    "naver": dict(auth="https://nid.naver.com/oauth2.0/authorize", token="https://nid.naver.com/oauth2.0/token",
                  me="https://openapi.naver.com/v1/nid/me", scope=""),
}
Provider = Literal["google", "kakao", "naver"]


def creds(p: str) -> tuple[str, str]:
    return getattr(settings, f"{p}_client_id"), getattr(settings, f"{p}_client_secret")


def redirect_uri(p: str) -> str:
    return f"{settings.public_url}/api/auth/oauth/{p}/callback"


def back(fragment: str) -> RedirectResponse:
    return RedirectResponse(f"{settings.public_url}/oauth#{fragment}", status_code=303)


def fail(msg: str) -> RedirectResponse:
    return back(f"error={quote(msg)}")


@router.get("/providers")
def providers():
    return {p: bool(creds(p)[0]) for p in PROVIDERS}


@router.get("/{provider}/start")
def start(provider: Provider, role: Literal["guardian", "parent"] | None = None):
    client_id, _ = creds(provider)
    if not client_id:
        return fail("아직 이 로그인 방식이 연결되지 않았어요")
    nonce = secrets.token_urlsafe(16)
    exp = datetime.now(UTC) + timedelta(minutes=10)
    state = jwt.encode({"p": provider, "role": role, "n": nonce, "exp": exp}, settings.jwt_secret, algorithm="HS256")
    q = {"response_type": "code", "client_id": client_id, "redirect_uri": redirect_uri(provider), "state": state}
    if PROVIDERS[provider]["scope"]:
        q["scope"] = PROVIDERS[provider]["scope"]
    r = RedirectResponse(f"{PROVIDERS[provider]['auth']}?{urlencode(q)}", status_code=303)
    r.set_cookie("oauth_nonce", nonce, max_age=600, httponly=True, samesite="lax")  # 다른 사람이 만든 로그인 요청을 내 브라우저에서 끝내지 못하게 한다
    return r


def fetch_profile(provider: str, code: str, state: str) -> dict:
    """제공자에서 (고유 번호, 이메일, 이메일 확인 여부)를 받아 온다. 테스트에서는 이 함수를 바꿔 끼운다."""
    cfg, (client_id, secret) = PROVIDERS[provider], creds(provider)
    with httpx.Client(timeout=10) as c:
        t = c.post(cfg["token"], data={"grant_type": "authorization_code", "code": code, "client_id": client_id,
                                       "client_secret": secret, "redirect_uri": redirect_uri(provider), "state": state})
        t.raise_for_status()
        d = c.get(cfg["me"], headers={"Authorization": f"Bearer {t.json()['access_token']}"})
        d.raise_for_status()
    d = d.json()
    if provider == "google":
        return {"sub": d["sub"], "email": d.get("email"), "verified": d.get("email_verified") is True}
    if provider == "kakao":
        a = d.get("kakao_account", {})
        return {"sub": str(d["id"]), "email": a.get("email"), "verified": a.get("is_email_verified") is True and a.get("is_email_valid") is True}
    r = d["response"]
    return {"sub": r["id"], "email": r.get("email"), "verified": bool(r.get("email"))}


@router.get("/{provider}/callback")
def callback(provider: Provider, code: str | None = None, state: str = "", error: str | None = None,
             oauth_nonce: str | None = Cookie(None), db: Session = Depends(get_db)):
    try:
        s = jwt.decode(state, settings.jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError:
        return fail("로그인 요청이 만료되었어요. 다시 시도해 주세요")
    if s["p"] != provider or not oauth_nonce or not secrets.compare_digest(s["n"], oauth_nonce):
        return fail("로그인 요청을 확인할 수 없어요. 같은 브라우저에서 다시 시도해 주세요")
    if error or not code:
        return fail("로그인을 취소했어요")
    try:
        prof = fetch_profile(provider, code, state)
    except (httpx.HTTPError, KeyError, ValueError):
        return fail("로그인 정보를 가져오지 못했어요. 잠시 후 다시 시도해 주세요")

    link = db.get(OAuthAccount, (provider, prof["sub"]))
    user = db.get(User, link.user_id) if link else None
    if not user:
        email = (prof["email"] or "").lower()
        # 이메일을 제공자가 확인해 준 경우에만 같은 이메일의 기존 계정에 붙인다. 아니면 남의 계정을 가로챌 수 있다.
        user = db.scalar(select(User).where(User.email == email)) if email and prof["verified"] else None
        if not user:
            if not s["role"]:
                return fail("처음 오셨네요. 가입하기에서 보호자인지 부모님·아이인지 고른 뒤 다시 시도해 주세요")
            if not email or db.scalar(select(User).where(User.email == email)):
                email = f"{provider}-{prof['sub']}@social.invalid"  # 이메일이 없거나 확인되지 않은 경우
            user = User(email=email, password_hash=hash_password(secrets.token_urlsafe(32)), role=s["role"])
            db.add(user)
            db.flush()
        db.add(OAuthAccount(provider=provider, sub=prof["sub"], user_id=user.id))
        db.commit()
    r = back(f"token={make_token(user.id)}")
    r.delete_cookie("oauth_nonce")
    return r
