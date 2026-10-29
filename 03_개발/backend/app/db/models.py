from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Index, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def now() -> datetime:
    # SQLite는 tz를 저장하지 않으므로 naive UTC로 통일
    return datetime.now(UTC).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True)
    password_hash: Mapped[str]
    role: Mapped[str]  # guardian | parent
    created_at: Mapped[datetime] = mapped_column(default=now)


class CareRecipient(Base):
    __tablename__ = "care_recipients"
    id: Mapped[int] = mapped_column(primary_key=True)
    guardian_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))  # 부모님 계정, 아이는 없음
    type: Mapped[str]  # senior | child
    display_name: Mapped[str]
    birth_year: Mapped[int | None]
    consent_confirmed_at: Mapped[datetime | None]


class Invite(Base):
    __tablename__ = "invites"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String, unique=True)
    issuer_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    recipient_id: Mapped[int] = mapped_column(ForeignKey("care_recipients.id"))
    expires_at: Mapped[datetime]
    used_at: Mapped[datetime | None]


class Link(Base):
    __tablename__ = "links"
    id: Mapped[int] = mapped_column(primary_key=True)
    guardian_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    parent_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    recipient_id: Mapped[int] = mapped_column(ForeignKey("care_recipients.id"))
    status: Mapped[str] = mapped_column(default="active")
    consented_at: Mapped[datetime] = mapped_column(default=now)


class Camera(Base):
    __tablename__ = "cameras"
    id: Mapped[int] = mapped_column(primary_key=True)
    recipient_id: Mapped[int] = mapped_column(ForeignKey("care_recipients.id"))
    name: Mapped[str]
    location_label: Mapped[str | None]
    last_seen_at: Mapped[datetime | None]
    paused: Mapped[bool] = mapped_column(default=False)
    recipient: Mapped[CareRecipient] = relationship()


class Zone(Base):
    __tablename__ = "zones"
    id: Mapped[int] = mapped_column(primary_key=True)
    camera_id: Mapped[int] = mapped_column(ForeignKey("cameras.id"))
    name: Mapped[str]
    purpose: Mapped[str]  # danger | bed
    x: Mapped[float]
    y: Mapped[float]
    w: Mapped[float]
    h: Mapped[float]
    active_from: Mapped[str | None]  # "HH:MM", 취침 구역만
    active_to: Mapped[str | None]
    dwell_sec: Mapped[int]


class Event(Base):
    __tablename__ = "events"
    __table_args__ = (Index("ix_events_camera_occurred", "camera_id", "occurred_at"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    camera_id: Mapped[int] = mapped_column(ForeignKey("cameras.id"))
    type: Mapped[str]  # fall | danger_zone | bed_exit
    zone_id: Mapped[int | None] = mapped_column(ForeignKey("zones.id"))
    source: Mapped[str] = mapped_column(default="live")  # live | upload
    occurred_at: Mapped[datetime] = mapped_column(default=now)
    score: Mapped[float | None]
    status: Mapped[str] = mapped_column(default="new")  # new | acknowledged | false_alarm
    clip_path: Mapped[str | None]
    clip_status: Mapped[str] = mapped_column(default="none")
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    reviewed_at: Mapped[datetime | None]
    camera: Mapped[Camera] = relationship()


class FeedbackSample(Base):
    __tablename__ = "feedback_samples"
    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"))
    label: Mapped[str]
    keypoints_path: Mapped[str | None]  # 관절 좌표만 저장, 원본 영상은 저장하지 않음
    created_at: Mapped[datetime] = mapped_column(default=now)


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    event_id: Mapped[int | None] = mapped_column(ForeignKey("events.id"))
    type: Mapped[str]
    sent_at: Mapped[datetime] = mapped_column(default=now)
    read_at: Mapped[datetime | None]
    event: Mapped[Event | None] = relationship()


class PushSubscription(Base):
    __tablename__ = "push_subscriptions"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    endpoint: Mapped[str] = mapped_column(String, unique=True)
    keys: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(default=now)


class Post(Base):
    """안부 피드: 부모님과 보호자가 서로 올리는 짧은 글. 위치는 글을 올릴 때 직접 고른 경우에만 붙는다."""
    __tablename__ = "posts"
    id: Mapped[int] = mapped_column(primary_key=True)
    recipient_id: Mapped[int] = mapped_column(ForeignKey("care_recipients.id"), index=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    text: Mapped[str]
    lat: Mapped[float | None]
    lng: Mapped[float | None]
    created_at: Mapped[datetime] = mapped_column(default=now)


class Need(Base):
    """부모님이 올린 '필요한 것'. 보호자가 주문하면 상태가 바뀐다."""
    __tablename__ = "needs"
    id: Mapped[int] = mapped_column(primary_key=True)
    recipient_id: Mapped[int] = mapped_column(ForeignKey("care_recipients.id"), index=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str]
    note: Mapped[str | None]
    url: Mapped[str | None]
    status: Mapped[str] = mapped_column(default="requested")  # requested | ordered | delivered
    created_at: Mapped[datetime] = mapped_column(default=now)


class Plan(Base):
    """같이 보는 일정. starts_at은 입력한 그대로의 현지 시각 'YYYY-MM-DDTHH:MM'."""
    __tablename__ = "plans"
    id: Mapped[int] = mapped_column(primary_key=True)
    recipient_id: Mapped[int] = mapped_column(ForeignKey("care_recipients.id"), index=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str]
    starts_at: Mapped[str]
    note: Mapped[str | None]


class Message(Base):
    """가족 채팅. 방은 보호자 한 명당 하나(보호자 + 연결된 부모님·아이 계정)."""
    __tablename__ = "messages"
    id: Mapped[int] = mapped_column(primary_key=True)
    guardian_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    text: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(default=now)


class LocationShare(Base):
    """위치 공유: 본인이 켠 동안만 마지막 위치 한 점을 보관한다. 끄면 위치를 지운다."""
    __tablename__ = "location_shares"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    sharing: Mapped[bool] = mapped_column(default=False)
    lat: Mapped[float | None]
    lng: Mapped[float | None]
    updated_at: Mapped[datetime | None]


class PostPhoto(Base):
    """피드 사진. 브라우저에서 줄여 보낸 JPEG(최대 2MB)를 DB에 그대로 둔다."""
    __tablename__ = "post_photos"
    id: Mapped[int] = mapped_column(primary_key=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id"), index=True)
    data: Mapped[bytes] = mapped_column(LargeBinary)


class PostLike(Base):
    __tablename__ = "post_likes"
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id"), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)


class OAuthAccount(Base):
    """소셜 로그인 연결: 제공자가 준 고유 번호(sub)로 우리 계정을 찾는다."""
    __tablename__ = "oauth_accounts"
    provider: Mapped[str] = mapped_column(primary_key=True)
    sub: Mapped[str] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))


class PostAudience(Base):
    """글을 볼 수 있는 가족. 행이 하나도 없으면 가족 전체에게 보인다."""
    __tablename__ = "post_audience"
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id"), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)


class MessageRef(Base):
    """채팅 메시지가 답장하는 피드 글."""
    __tablename__ = "message_refs"
    message_id: Mapped[int] = mapped_column(ForeignKey("messages.id"), primary_key=True)
    post_id: Mapped[int] = mapped_column(index=True)  # 글이 지워져도 메시지는 남으므로 외래키를 걸지 않는다
