from typing import Literal

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.db.models import CareRecipient, LocationShare, Message, MessageRef, Need, Plan, Post, PostAudience, PostLike, PostPhoto, User, now
from app.db.session import get_db

router = APIRouter(prefix="/api")


def my_recipients(db: Session, user: User) -> dict[int, CareRecipient]:
    q = select(CareRecipient).where(or_(CareRecipient.guardian_id == user.id, CareRecipient.user_id == user.id))
    return {r.id: r for r in db.scalars(q)}


def pick(db: Session, user: User, recipient_id: int | None) -> int:
    """글을 올릴 대상. 부모님은 본인 하나뿐이라 생략할 수 있다."""
    mine = my_recipients(db, user)
    rid = recipient_id if recipient_id is not None else next(iter(mine), None)
    if not mine:
        raise HTTPException(400, "먼저 돌봄 대상을 추가해 주세요")
    if rid not in mine:
        raise HTTPException(403, "권한이 없습니다")
    return rid


def own(db: Session, user: User, model, item_id: int):
    item = db.get(model, item_id)
    if not item or item.recipient_id not in my_recipients(db, user):
        raise HTTPException(404, "찾을 수 없습니다")
    return item


def rows(db: Session, user: User, model, order, *where):
    ids = my_recipients(db, user).keys()
    return db.scalars(select(model).where(model.recipient_id.in_(ids), *where).order_by(*order)).all()


def family(db: Session, user: User) -> tuple[int, dict[int, str]]:
    """내가 속한 가족: (보호자 id, {계정 id: 보여 줄 이름}). 보호자는 '보호자', 부모님·아이는 등록한 이름."""
    if user.role == "guardian":
        gid = user.id
    else:
        mine = next(iter(my_recipients(db, user).values()), None)
        if not mine:
            raise HTTPException(403, "보호자와 연결한 뒤에 사용할 수 있습니다")
        gid = mine.guardian_id
    names = {gid: "보호자"}
    for r in db.scalars(select(CareRecipient).where(CareRecipient.guardian_id == gid, CareRecipient.user_id.is_not(None))):
        names[r.user_id] = r.display_name
    return gid, names


def out(db: Session, item, names: dict[int, str]) -> dict:
    d = {c.name: getattr(item, c.name) for c in item.__table__.columns}
    if hasattr(item, "recipient_id"):
        d["recipient_name"] = db.get(CareRecipient, item.recipient_id).display_name
    return d | {"author_name": names.get(item.author_id, "알 수 없음")}


class PostIn(BaseModel):
    audience: list[int] | None = None  # 볼 수 있는 가족(계정 id). 비우면 전체
    text: str = Field(min_length=1, max_length=500)
    lat: float | None = Field(None, ge=-90, le=90)
    lng: float | None = Field(None, ge=-180, le=180)


MAX_PHOTOS, MAX_PHOTO_BYTES = 5, 2_000_000


def audiences(db: Session, post_ids: list[int]) -> dict[int, set[int]]:
    out: dict[int, set[int]] = {}
    for post_id, uid in db.execute(select(PostAudience.post_id, PostAudience.user_id).where(PostAudience.post_id.in_(post_ids))):
        out.setdefault(post_id, set()).add(uid)
    return out


def can_see(user: User, p: Post, aud: set[int]) -> bool:
    """쓴 사람이거나, 공개 범위가 전체이거나, 범위에 내가 들어 있으면 볼 수 있다. 같은 가족인지는 호출하는 쪽이 정한다."""
    return p.author_id == user.id or not aud or user.id in aud


def family_posts(db: Session, user: User, gid: int) -> list[tuple[Post, set[int]]]:
    q = select(Post).join(CareRecipient, CareRecipient.id == Post.recipient_id).where(CareRecipient.guardian_id == gid).order_by(Post.id.desc())
    posts = db.scalars(q).all()
    aud = audiences(db, [p.id for p in posts])
    return [(p, aud.get(p.id, set())) for p in posts if can_see(user, p, aud.get(p.id, set()))]


def seen_post(db: Session, user: User, post_id: int) -> Post:
    """내가 볼 수 있는 글만 돌려준다. 못 보는 글은 있는지도 알려 주지 않는다."""
    gid = family(db, user)[0]
    p = db.get(Post, post_id)
    if p and db.get(CareRecipient, p.recipient_id).guardian_id == gid and can_see(user, p, audiences(db, [p.id]).get(p.id, set())):
        return p
    raise HTTPException(404, "찾을 수 없습니다")


def post_out(db: Session, user: User, posts: list[Post], names: dict[int, str]) -> list[dict]:
    ids = [p.id for p in posts]
    photos: dict[int, list[int]] = {}
    for post_id, photo_id in db.execute(select(PostPhoto.post_id, PostPhoto.id).where(PostPhoto.post_id.in_(ids)).order_by(PostPhoto.id)):
        photos.setdefault(post_id, []).append(photo_id)
    likes = dict(db.execute(select(PostLike.post_id, func.count()).where(PostLike.post_id.in_(ids)).group_by(PostLike.post_id)).all())
    mine = set(db.scalars(select(PostLike.post_id).where(PostLike.post_id.in_(ids), PostLike.user_id == user.id)))
    aud = audiences(db, ids)
    return [out(db, p, names) | {"photo_ids": photos.get(p.id, []), "likes": likes.get(p.id, 0), "liked": p.id in mine,
                                  "audience_names": [names[u] for u in sorted(aud.get(p.id, set())) if u in names]} for p in posts]


@router.get("/posts")
def list_posts(user: User = Depends(current_user), db: Session = Depends(get_db)):
    gid, names = family(db, user)
    return post_out(db, user, [p for p, _ in family_posts(db, user, gid)[:50]], names)


@router.post("/posts", status_code=201)
def add_post(body: PostIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if (body.lat is None) != (body.lng is None):
        raise HTTPException(422, "위치는 위도와 경도를 함께 보내야 합니다")
    names = family(db, user)[1]
    # 나를 뺀 가족만 고를 수 있다. 가족 전부를 골랐으면 '전체'와 같으므로 비워 둔다.
    others = set(names) - {user.id}
    chosen = set(body.audience or [])
    if not chosen <= others:
        raise HTTPException(422, "가족이 아닌 사람은 고를 수 없습니다")
    p = Post(recipient_id=pick(db, user, None), author_id=user.id, text=body.text, lat=body.lat, lng=body.lng)
    db.add(p)
    db.flush()
    if chosen and chosen != others:
        db.add_all(PostAudience(post_id=p.id, user_id=u) for u in chosen)
    db.commit()
    return post_out(db, user, [p], names)[0]


class PostPatch(BaseModel):
    text: str = Field(min_length=1, max_length=500)


def mine_post(db: Session, user: User, post_id: int) -> Post:
    p = seen_post(db, user, post_id)
    if p.author_id != user.id:
        raise HTTPException(403, "내가 올린 글만 바꿀 수 있습니다")
    return p


@router.patch("/posts/{post_id}")
def edit_post(post_id: int, body: PostPatch, user: User = Depends(current_user), db: Session = Depends(get_db)):
    p = mine_post(db, user, post_id)
    p.text = body.text
    db.commit()
    return post_out(db, user, [p], family(db, user)[1])[0]


@router.delete("/posts/{post_id}/photos/{photo_id}", status_code=204)
def del_photo(post_id: int, photo_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    p = mine_post(db, user, post_id)
    ph = db.get(PostPhoto, photo_id)
    if not ph or ph.post_id != p.id:
        raise HTTPException(404, "사진을 찾을 수 없습니다")
    db.delete(ph)
    db.commit()


@router.post("/posts/{post_id}/photos", status_code=201)
def add_photo(post_id: int, data: bytes = Body(media_type="image/jpeg"), user: User = Depends(current_user), db: Session = Depends(get_db)):
    p = mine_post(db, user, post_id)
    if not data.startswith(b"\xff\xd8"):
        raise HTTPException(400, "JPEG 사진만 올릴 수 있습니다")
    if len(data) > MAX_PHOTO_BYTES:
        raise HTTPException(413, "사진이 너무 큽니다")
    if db.scalar(select(func.count()).where(PostPhoto.post_id == p.id)) >= MAX_PHOTOS:
        raise HTTPException(400, f"사진은 {MAX_PHOTOS}장까지 올릴 수 있습니다")
    ph = PostPhoto(post_id=p.id, data=data)
    db.add(ph)
    db.commit()
    return {"id": ph.id}


@router.get("/posts/{post_id}/photos/{photo_id}")
def get_photo(post_id: int, photo_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    seen_post(db, user, post_id)
    ph = db.get(PostPhoto, photo_id)
    if not ph or ph.post_id != post_id:
        raise HTTPException(404, "사진을 찾을 수 없습니다")
    return Response(ph.data, media_type="image/jpeg", headers={"Cache-Control": "private, max-age=86400"})


@router.post("/posts/{post_id}/like")
def toggle_like(post_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    p = seen_post(db, user, post_id)
    like = db.get(PostLike, (p.id, user.id))
    if like:
        db.delete(like)
    else:
        db.add(PostLike(post_id=p.id, user_id=user.id))
    db.commit()
    return {"liked": not like, "likes": db.scalar(select(func.count()).where(PostLike.post_id == p.id))}


@router.delete("/posts/{post_id}", status_code=204)
def del_post(post_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    p = mine_post(db, user, post_id)
    for m in (PostPhoto, PostLike, PostAudience):
        db.execute(delete(m).where(m.post_id == p.id))
    db.delete(p)
    db.commit()


class NeedIn(BaseModel):
    recipient_id: int | None = None
    title: str = Field(min_length=1, max_length=50)
    note: str | None = Field(None, max_length=200)
    url: str | None = Field(None, max_length=500, pattern=r"^https?://")


@router.get("/needs")
def list_needs(user: User = Depends(current_user), db: Session = Depends(get_db)):
    names = family(db, user)[1]
    return [out(db, n, names) for n in rows(db, user, Need, [Need.status == "delivered", Need.id.desc()])]


@router.post("/needs", status_code=201)
def add_need(body: NeedIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    n = Need(recipient_id=pick(db, user, body.recipient_id), author_id=user.id, title=body.title, note=body.note, url=body.url)
    db.add(n)
    db.commit()
    return out(db, n, family(db, user)[1])


class NeedPatch(BaseModel):
    status: Literal["requested", "delivered"]  # 체크 해제 / 체크


@router.patch("/needs/{need_id}")
def set_need(need_id: int, body: NeedPatch, user: User = Depends(current_user), db: Session = Depends(get_db)):
    n = own(db, user, Need, need_id)
    n.status = body.status
    db.commit()
    return out(db, n, family(db, user)[1])


class PlanIn(BaseModel):
    recipient_id: int | None = None
    title: str = Field(min_length=1, max_length=50)
    starts_at: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$")
    note: str | None = Field(None, max_length=200)


@router.get("/plans")
def list_plans(from_: str = Query("0000-00-00", alias="from", pattern=r"^\d{4}-\d{2}-\d{2}$"),
               to: str = Query("9999-99-99", pattern=r"^\d{4}-\d{2}-\d{2}$"),
               user: User = Depends(current_user), db: Session = Depends(get_db)):
    names = family(db, user)[1]
    return [out(db, p, names) for p in rows(db, user, Plan, [Plan.starts_at], Plan.starts_at >= from_, Plan.starts_at < to + "T99")]


@router.post("/plans", status_code=201)
def add_plan(body: PlanIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    p = Plan(recipient_id=pick(db, user, body.recipient_id), author_id=user.id, title=body.title, starts_at=body.starts_at, note=body.note)
    db.add(p)
    db.commit()
    return out(db, p, family(db, user)[1])


@router.delete("/plans/{plan_id}", status_code=204)
def del_plan(plan_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    db.delete(own(db, user, Plan, plan_id))
    db.commit()


class MessageIn(BaseModel):
    text: str = Field(min_length=1, max_length=500)
    post_id: int | None = None  # 답장하는 피드 글


def quotes(db: Session, user: User, msgs: list[Message]) -> dict[int, dict]:
    """메시지가 답장하는 글을 보여 줄 모양으로 만든다. 채팅방은 가족 전체가 보므로, 내가 못 보는 글은 내용을 숨긴다."""
    refs = dict(db.execute(select(MessageRef.message_id, MessageRef.post_id).where(MessageRef.message_id.in_([m.id for m in msgs]))).all())
    ids = list(refs.values())
    posts = {p.id: p for p in db.scalars(select(Post).where(Post.id.in_(ids)))}
    aud = audiences(db, ids)
    photos = dict(db.execute(select(PostPhoto.post_id, func.count()).where(PostPhoto.post_id.in_(ids)).group_by(PostPhoto.post_id)).all())
    names = family(db, user)[1]
    out_: dict[int, dict] = {}
    for mid, pid in refs.items():
        p = posts.get(pid)
        out_[mid] = ({"gone": True} if not p else {"hidden": True} if not can_see(user, p, aud.get(pid, set()))
                     else {"id": p.id, "author_name": names.get(p.author_id, "알 수 없음"), "text": p.text[:80], "photos": photos.get(pid, 0)})
    return out_


@router.get("/chat")
def list_chat(after: int = 0, user: User = Depends(current_user), db: Session = Depends(get_db)):
    gid, names = family(db, user)
    q = select(Message).where(Message.guardian_id == gid, Message.id > after).order_by(Message.id.desc()).limit(100)
    msgs = list(reversed(db.scalars(q).all()))
    qs = quotes(db, user, msgs)
    return [out(db, m, names) | {"quote": qs.get(m.id)} for m in msgs]


@router.post("/chat", status_code=201)
def send_chat(body: MessageIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    gid, names = family(db, user)
    if body.post_id is not None:
        seen_post(db, user, body.post_id)  # 내가 볼 수 있는 글에만 답장할 수 있다
    m = Message(guardian_id=gid, author_id=user.id, text=body.text)
    db.add(m)
    db.flush()
    if body.post_id is not None:
        db.add(MessageRef(message_id=m.id, post_id=body.post_id))
    db.commit()
    return out(db, m, names) | {"quote": quotes(db, user, [m]).get(m.id)}


class ShareIn(BaseModel):
    on: bool


class SpotIn(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


def share_row(db: Session, user_id: int) -> LocationShare:
    return db.get(LocationShare, user_id) or LocationShare(user_id=user_id, sharing=False)


@router.get("/location")
def get_location(user: User = Depends(current_user), db: Session = Depends(get_db)):
    names = family(db, user)[1]
    members = []
    for uid, name in names.items():
        if uid != user.id:
            r = share_row(db, uid)
            members.append({"user_id": uid, "name": name, "sharing": r.sharing, "lat": r.lat, "lng": r.lng, "updated_at": r.updated_at})
    return {"me": {"sharing": share_row(db, user.id).sharing}, "members": members}


@router.put("/location/share", status_code=204)
def set_share(body: ShareIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    family(db, user)
    r = share_row(db, user.id)
    r.sharing = body.on
    if not body.on:
        r.lat = r.lng = r.updated_at = None
    db.merge(r)
    db.commit()


@router.post("/location", status_code=204)
def put_location(body: SpotIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    r = share_row(db, user.id)
    if not r.sharing:
        raise HTTPException(409, "위치 공유가 꺼져 있습니다")
    r.lat, r.lng, r.updated_at = body.lat, body.lng, now()
    db.merge(r)
    db.commit()
