from datetime import timedelta

from app.api import invites
from app.db.models import Camera, Event, FeedbackSample, Invite, now
from app.services.events import create_event
from tests.conftest import signup


def child_camera(client, g, consent=True):
    r = client.post("/api/recipients", json={"type": "child", "display_name": "하늘", "consent_confirmed": consent}, headers=g).json()
    c = client.post("/api/cameras", json={"recipient_id": r["id"], "name": "거실"}, headers=g)
    return r, c


def test_auth(client):
    signup(client, "a@x.com", "guardian")
    body = {"email": "a@x.com", "password": "password1", "role": "guardian"}
    assert client.post("/api/auth/register", json=body).status_code == 409
    assert client.post("/api/auth/login", json={"email": "a@x.com", "password": "wrongpass1"}).status_code == 401
    assert client.post("/api/auth/register", json={**body, "email": "b@x.com", "password": "short"}).status_code == 422
    token = client.post("/api/auth/login", json={"email": "a@x.com", "password": "password1"}).json()["access_token"]
    me = client.get("/api/me", headers={"Authorization": f"Bearer {token}"}).json()
    assert me["role"] == "guardian"
    r = client.get("/api/me")
    assert r.status_code == 401 and r.json()["code"] == 401


def test_invite_flow(client, db, guardian, parent):
    r = client.post("/api/recipients", json={"type": "senior", "display_name": "엄마"}, headers=guardian).json()
    # 연결 전에는 카메라를 등록할 수 없다
    assert client.post("/api/cameras", json={"recipient_id": r["id"], "name": "방"}, headers=guardian).status_code == 400
    code = client.post("/api/invites", json={"recipient_id": r["id"]}, headers=guardian).json()["code"]
    assert len(code) == 6
    # 동의 없이는 연결되지 않고, 코드도 소모되지 않는다
    assert client.post("/api/invites/accept", json={"code": code, "consent": False}, headers=parent).status_code == 400
    assert client.get("/api/links", headers=parent).json() == []
    assert client.post("/api/invites/accept", json={"code": code, "consent": True}, headers=parent).status_code == 200
    assert client.post("/api/invites/accept", json={"code": code, "consent": True}, headers=parent).status_code == 400  # 1회용
    assert client.get("/api/links", headers=guardian).json()[0]["status"] == "active"
    assert client.post("/api/cameras", json={"recipient_id": r["id"], "name": "방"}, headers=guardian).status_code == 201


def test_invite_expiry_and_lock(client, db, guardian, parent):
    r = client.post("/api/recipients", json={"type": "senior", "display_name": "엄마"}, headers=guardian).json()
    code = client.post("/api/invites", json={"recipient_id": r["id"]}, headers=guardian).json()["code"]
    inv = db.query(Invite).one()
    inv.expires_at = now() - timedelta(seconds=1)
    db.commit()
    assert client.post("/api/invites/accept", json={"code": code, "consent": True}, headers=parent).status_code == 400
    for _ in range(invites.MAX_FAILS - 1):
        client.post("/api/invites/accept", json={"code": "000000", "consent": True}, headers=parent)
    assert client.post("/api/invites/accept", json={"code": code, "consent": True}, headers=parent).status_code == 429


def test_child_consent_and_permissions(client, guardian):
    r, c = child_camera(client, guardian, consent=False)
    assert c.status_code == 400
    assert client.patch(f"/api/recipients/{r['id']}", json={"consent_confirmed": True}, headers=guardian).json()["beta"] is True
    assert client.post("/api/cameras", json={"recipient_id": r["id"], "name": "거실"}, headers=guardian).status_code == 201
    other = signup(client, "o@x.com", "guardian")
    assert client.patch(f"/api/recipients/{r['id']}", json={"display_name": "x"}, headers=other).status_code == 403
    assert client.get("/api/recipients", headers=other).json() == []
    assert client.get("/api/cameras", headers=other).json() == []


def test_camera_status_and_pause(client, guardian):
    _, c = child_camera(client, guardian)
    cid = c.json()["id"]
    assert c.json()["status"] == "offline"
    assert client.post(f"/api/cameras/{cid}/heartbeat", headers=guardian).json()["status"] == "connected"
    assert client.patch(f"/api/cameras/{cid}", json={"paused": True}, headers=guardian).json()["status"] == "paused"


def test_zones(client, guardian):
    _, c = child_camera(client, guardian)
    cid = c.json()["id"]
    zone = {"name": "주방", "purpose": "danger", "x": 0.1, "y": 0.1, "w": 0.3, "h": 0.3}
    assert client.post(f"/api/cameras/{cid}/zones", json=zone, headers=guardian).status_code == 400  # 오프라인
    client.post(f"/api/cameras/{cid}/heartbeat", headers=guardian)
    z = client.post(f"/api/cameras/{cid}/zones", json=zone, headers=guardian)
    assert z.status_code == 201 and z.json()["dwell_sec"] == 3
    assert client.post(f"/api/cameras/{cid}/zones", json={**zone, "x": 0.9}, headers=guardian).status_code == 422
    bed = {**zone, "purpose": "bed", "name": "침대"}
    assert client.post(f"/api/cameras/{cid}/zones", json=bed, headers=guardian).status_code == 422  # 시간대 없음
    bed.update(active_from="21:00", active_to="07:00")
    assert client.post(f"/api/cameras/{cid}/zones", json=bed, headers=guardian).json()["dwell_sec"] == 30
    assert client.post(f"/api/cameras/{cid}/zones", json=zone, headers=guardian).status_code == 201
    assert client.post(f"/api/cameras/{cid}/zones", json=zone, headers=guardian).status_code == 400  # 4개째
    assert client.delete(f"/api/zones/{z.json()['id']}", headers=guardian).status_code == 204
    assert len(client.get(f"/api/cameras/{cid}/zones", headers=guardian).json()) == 2


def test_zone_rejected_for_senior(client, db, guardian, parent):
    r = client.post("/api/recipients", json={"type": "senior", "display_name": "엄마"}, headers=guardian).json()
    code = client.post("/api/invites", json={"recipient_id": r["id"]}, headers=guardian).json()["code"]
    client.post("/api/invites/accept", json={"code": code, "consent": True}, headers=parent)
    cid = client.post("/api/cameras", json={"recipient_id": r["id"], "name": "방"}, headers=guardian).json()["id"]
    client.post(f"/api/cameras/{cid}/heartbeat", headers=parent)  # 부모님 기기가 송출
    z = {"name": "a", "purpose": "danger", "x": 0, "y": 0, "w": 0.5, "h": 0.5}
    assert client.post(f"/api/cameras/{cid}/zones", json=z, headers=guardian).status_code == 400


def test_events_and_notifications(client, db, guardian):
    _, c = child_camera(client, guardian)
    cam = db.get(Camera, c.json()["id"])
    ev = create_event(db, cam, "fall", 0.9)
    assert create_event(db, cam, "fall", 0.95) is None  # 60초 쿨다운
    cam.paused = True
    assert create_event(db, cam, "bed_exit") is None  # 일시정지 중에는 알리지 않음
    cam.paused = False
    assert create_event(db, cam, "bed_exit") is not None

    notes = client.get("/api/notifications", headers=guardian).json()
    assert len(notes) == 2 and notes[1]["title"] == "낙상 의심 · 하늘"
    assert client.post(f"/api/notifications/{notes[0]['id']}/read", headers=guardian).json()["read_at"]

    assert len(client.get("/api/events", headers=guardian).json()) == 2
    assert len(client.get("/api/events?status=false_alarm", headers=guardian).json()) == 0
    d = client.patch(f"/api/events/{ev.id}", json={"status": "false_alarm"}, headers=guardian).json()
    assert d["status"] == "false_alarm" and db.query(FeedbackSample).count() == 1
    # 처리된 이벤트는 다시 바뀌지 않는다
    assert client.patch(f"/api/events/{ev.id}", json={"status": "acknowledged"}, headers=guardian).json()["status"] == "false_alarm"
    assert client.get(f"/api/events/{ev.id}/clip", headers=guardian).status_code == 404
    other = signup(client, "o@x.com", "guardian")
    assert client.get(f"/api/events/{ev.id}", headers=other).status_code == 403
    assert client.get("/api/events/999", headers=guardian).status_code == 404


def test_report_and_push(client, guardian):
    assert client.get("/api/reports/model", headers=guardian).json()["evaluated"] is False
    sub = {"endpoint": "https://push/1", "keys": {"p256dh": "a", "auth": "b"}}
    assert client.post("/api/push/subscribe", json=sub, headers=guardian).status_code == 201
    assert client.post("/api/push/subscribe", json=sub, headers=guardian).status_code == 201  # 중복 등록 허용


def test_analyze(client, guardian, parent):
    import cv2
    import numpy as np
    _, c = child_camera(client, guardian)
    url = f"/api/cameras/{c.json()['id']}/analyze"
    jpg = cv2.imencode(".jpg", np.zeros((120, 160, 3), np.uint8))[1].tobytes()
    r = client.post(url, content=jpg, headers={**guardian, "content-type": "image/jpeg"})
    assert r.status_code == 200 and r.headers["content-type"] == "image/jpeg"
    assert client.post(url, content=b"junk", headers={**guardian, "content-type": "image/jpeg"}).status_code == 400
    assert client.post(url, content=jpg, headers={**parent, "content-type": "image/jpeg"}).status_code == 403


def linked_senior(client, guardian, parent):
    r = client.post("/api/recipients", json={"type": "senior", "display_name": "엄마"}, headers=guardian).json()
    code = client.post("/api/invites", json={"recipient_id": r["id"]}, headers=guardian).json()["code"]
    client.post("/api/invites/accept", json={"code": code, "consent": True}, headers=parent)
    return r


def test_family_feed_needs_plans(client, guardian, parent):
    r = linked_senior(client, guardian, parent)
    other = signup(client, "o@x.com", "guardian")

    # 부모님은 대상을 생략해도 본인 피드에 올라가고, 보호자도 같이 본다. 위치는 선택이다.
    assert client.post("/api/posts", json={"text": "밥 먹었어요", "lat": 37.5, "lng": 127.0}, headers=parent).status_code == 201
    assert client.post("/api/posts", json={"text": "잘 지내시죠?", "recipient_id": r["id"]}, headers=guardian).status_code == 201
    assert [p["text"] for p in client.get("/api/posts", headers=guardian).json()] == ["잘 지내시죠?", "밥 먹었어요"]
    assert client.post("/api/posts", json={"text": "x", "lat": 1}, headers=parent).status_code == 422
    # 남의 가족에는 보이지도 올릴 수도 없다
    assert client.get("/api/posts", headers=other).json() == []
    assert client.post("/api/posts", json={"text": "x"}, headers=other).status_code == 400  # 돌봄 대상이 없는 보호자

    n = client.post("/api/needs", json={"title": "치약", "url": "https://shop.example/1"}, headers=parent).json()
    assert client.post("/api/needs", json={"title": "x", "url": "javascript:1"}, headers=parent).status_code == 422
    assert client.patch(f"/api/needs/{n['id']}", json={"status": "delivered"}, headers=guardian).json()["status"] == "delivered"
    assert client.patch(f"/api/needs/{n['id']}", json={"status": "delivered"}, headers=other).status_code == 404
    assert client.get("/api/needs", headers=parent).json()[0]["status"] == "delivered"

    p = client.post("/api/plans", json={"title": "병원", "starts_at": "2026-11-05T10:30"}, headers=guardian).json()
    client.post("/api/plans", json={"title": "지난 일정", "starts_at": "2026-10-01T09:00"}, headers=parent)
    assert [x["title"] for x in client.get("/api/plans?from=2026-11-01", headers=parent).json()] == ["병원"]
    assert client.delete(f"/api/plans/{p['id']}", headers=other).status_code == 404
    assert client.delete(f"/api/plans/{p['id']}", headers=parent).status_code == 204


def test_chat_location_and_child_account(client, guardian, parent):
    r = linked_senior(client, guardian, parent)
    other = signup(client, "o@x.com", "guardian")
    kid_login = signup(client, "kid@x.com", "parent")

    # 아이도 동의를 확인한 뒤에야 계정을 연결할 수 있다
    kid = client.post("/api/recipients", json={"type": "child", "display_name": "하늘"}, headers=guardian).json()
    assert client.post("/api/invites", json={"recipient_id": kid["id"]}, headers=guardian).status_code == 400
    client.patch(f"/api/recipients/{kid['id']}", json={"consent_confirmed": True}, headers=guardian)
    code = client.post("/api/invites", json={"recipient_id": kid["id"]}, headers=guardian).json()["code"]
    assert client.post("/api/invites/accept", json={"code": code, "consent": True}, headers=kid_login).status_code == 200

    # 채팅: 가족 모두가 같은 방을 보고, 다른 가족은 못 본다
    client.post("/api/chat", json={"text": "저녁 뭐 먹을까?"}, headers=guardian)
    client.post("/api/chat", json={"text": "치킨!"}, headers=kid_login)
    msgs = client.get("/api/chat", headers=parent).json()
    assert [(m["author_name"], m["text"]) for m in msgs] == [("보호자", "저녁 뭐 먹을까?"), ("하늘", "치킨!")]
    assert client.get(f"/api/chat?after={msgs[0]['id']}", headers=guardian).json()[0]["text"] == "치킨!"
    assert client.get("/api/chat", headers=other).json() == []
    unlinked = signup(client, "u@x.com", "parent")
    assert client.get("/api/chat", headers=unlinked).status_code == 403

    # 위치: 끄면 못 보내고, 켠 사람의 마지막 위치만 보이고, 끄면 지워진다
    spot = {"lat": 37.5, "lng": 127.0}
    assert client.post("/api/location", json=spot, headers=kid_login).status_code == 409
    client.put("/api/location/share", json={"on": True}, headers=kid_login)
    client.post("/api/location", json=spot, headers=kid_login)
    seen = {m["name"]: m for m in client.get("/api/location", headers=guardian).json()["members"]}
    assert seen["하늘"]["lat"] == 37.5 and seen["엄마"]["sharing"] is False and seen["엄마"]["lat"] is None
    client.put("/api/location/share", json={"on": False}, headers=kid_login)
    assert {m["name"]: m for m in client.get("/api/location", headers=guardian).json()["members"]}["하늘"]["lat"] is None


def test_feed_photos_likes(client, guardian, parent):
    linked_senior(client, guardian, parent)
    other = signup(client, "o@x.com", "guardian")
    jpg = b"\xff\xd8\xff" + b"x" * 100
    hdr = lambda h: {**h, "content-type": "image/jpeg"}
    pid = client.post("/api/posts", json={"text": "오늘 산책"}, headers=parent).json()["id"]

    assert client.post(f"/api/posts/{pid}/photos", content=jpg, headers=hdr(parent)).status_code == 201
    assert client.post(f"/api/posts/{pid}/photos", content=b"png?", headers=hdr(parent)).status_code == 400
    assert client.post(f"/api/posts/{pid}/photos", content=jpg, headers=hdr(guardian)).status_code == 403  # 남이 올린 글
    for _ in range(4):
        client.post(f"/api/posts/{pid}/photos", content=jpg, headers=hdr(parent))
    assert client.post(f"/api/posts/{pid}/photos", content=jpg, headers=hdr(parent)).status_code == 400  # 5장까지

    post = client.get("/api/posts", headers=guardian).json()[0]
    assert len(post["photo_ids"]) == 5 and post["likes"] == 0
    got = client.get(f"/api/posts/{pid}/photos/{post['photo_ids'][0]}", headers=guardian)
    assert got.content == jpg and got.headers["content-type"] == "image/jpeg"
    assert client.get(f"/api/posts/{pid}/photos/{post['photo_ids'][0]}", headers=other).status_code == 404

    assert client.post(f"/api/posts/{pid}/like", headers=guardian).json() == {"liked": True, "likes": 1}
    assert client.get("/api/posts", headers=guardian).json()[0]["liked"] is True
    assert client.post(f"/api/posts/{pid}/like", headers=guardian).json() == {"liked": False, "likes": 0}

    # 내 글만 고치고, 사진을 한 장씩 지우고, 글째로 지울 수 있다
    assert client.patch(f"/api/posts/{pid}", json={"text": "남의 글"}, headers=guardian).status_code == 403
    assert client.patch(f"/api/posts/{pid}", json={"text": "수정한 글"}, headers=parent).json()["text"] == "수정한 글"
    assert client.delete(f"/api/posts/{pid}/photos/{post['photo_ids'][0]}", headers=guardian).status_code == 403
    assert client.delete(f"/api/posts/{pid}/photos/{post['photo_ids'][0]}", headers=parent).status_code == 204
    assert len(client.get("/api/posts", headers=guardian).json()[0]["photo_ids"]) == 4
    assert client.delete(f"/api/posts/{pid}", headers=guardian).status_code == 403
    assert client.delete(f"/api/posts/{pid}", headers=parent).status_code == 204
    assert client.get("/api/posts", headers=guardian).json() == []


def test_social_login(client, monkeypatch):
    from urllib.parse import parse_qs, urlparse

    from app.api import oauth
    from app.core.config import settings
    monkeypatch.setattr(settings, "google_client_id", "gid")
    profile = {"sub": "g-1", "email": "Social@x.com", "verified": True}
    monkeypatch.setattr(oauth, "fetch_profile", lambda *a: profile)

    def run(role=None):
        r = client.get("/api/auth/oauth/google/start" + (f"?role={role}" if role else ""), follow_redirects=False)
        assert r.status_code == 303 and r.headers["location"].startswith("https://accounts.google.com/")
        state = parse_qs(urlparse(r.headers["location"]).query)["state"][0]
        return client.get(f"/api/auth/oauth/google/callback?code=c&state={state}", follow_redirects=False).headers["location"]

    assert client.get("/api/auth/oauth/providers").json() == {"google": True, "kakao": False, "naver": False}
    # 설정이 없는 제공자는 시작하지 않는다
    assert "error=" in client.get("/api/auth/oauth/kakao/start", follow_redirects=False).headers["location"]
    # 처음 오는 사람은 역할을 골라야 한다
    assert "error=" in run()
    done = run("guardian")
    token = done.split("token=")[1]
    me = client.get("/api/me", headers={"Authorization": f"Bearer {token}"}).json()
    assert me["email"] == "social@x.com" and me["role"] == "guardian"
    # 다시 로그인하면 같은 계정이다 (역할을 안 골라도 된다)
    assert client.get("/api/me", headers={"Authorization": f"Bearer {run().split('token=')[1]}"}).json()["id"] == me["id"]

    # 확인된 같은 이메일이면 기존 비밀번호 계정에 붙는다
    signup(client, "same@x.com", "guardian")
    profile.update(sub="g-2", email="same@x.com")
    mine = client.post("/api/auth/login", json={"email": "same@x.com", "password": "password1"}).json()["user"]["id"]
    assert client.get("/api/me", headers={"Authorization": f"Bearer {run('parent').split('token=')[1]}"}).json()["id"] == mine
    # 확인되지 않은 이메일이면 붙지 않고 별도 계정이 된다
    signup(client, "other@x.com", "guardian")
    profile.update(sub="g-3", email="other@x.com", verified=False)
    new = client.get("/api/me", headers={"Authorization": f"Bearer {run('guardian').split('token=')[1]}"}).json()
    assert new["email"] == "google-g-3@social.invalid"

    # 다른 브라우저에서 만든 요청(쿠키 없음)이나 위조된 state는 거부한다
    state = parse_qs(urlparse(client.get("/api/auth/oauth/google/start?role=guardian", follow_redirects=False).headers["location"]).query)["state"][0]
    client.cookies.clear()
    assert "error=" in client.get(f"/api/auth/oauth/google/callback?code=c&state={state}", follow_redirects=False).headers["location"]
    assert "error=" in client.get("/api/auth/oauth/google/callback?code=c&state=forged", follow_redirects=False).headers["location"]


def test_post_audience(client, guardian, parent):
    linked_senior(client, guardian, parent)
    kid_login = signup(client, "kid@x.com", "parent")
    kid = client.post("/api/recipients", json={"type": "child", "display_name": "하늘", "consent_confirmed": True}, headers=guardian).json()
    code = client.post("/api/invites", json={"recipient_id": kid["id"]}, headers=guardian).json()["code"]
    client.post("/api/invites/accept", json={"code": code, "consent": True}, headers=kid_login)
    uid = lambda h: client.get("/api/me", headers=h).json()["id"]
    g, p, k = uid(guardian), uid(parent), uid(kid_login)
    texts = lambda h: [x["text"] for x in client.get("/api/posts", headers=h).json()]

    # 기본은 전체: 가족 모두가 본다 (아이는 엄마의 가족이기도 하다)
    client.post("/api/posts", json={"text": "전체 공개"}, headers=guardian)
    assert texts(parent) == texts(kid_login) == ["전체 공개"]

    # 아이에게만: 엄마에게는 보이지 않고, 쓴 사람과 고른 사람에게만 보인다
    hid = client.post("/api/posts", json={"text": "하늘에게만", "audience": [k]}, headers=guardian).json()
    assert texts(parent) == ["전체 공개"] and texts(kid_login)[0] == "하늘에게만" and texts(guardian)[0] == "하늘에게만"
    assert hid["audience_names"] == ["하늘"]
    # 보이지 않는 글에는 좋아요도 사진 조회도 할 수 없다
    assert client.post(f"/api/posts/{hid['id']}/like", headers=parent).status_code == 404
    client.post(f"/api/posts/{hid['id']}/photos", content=b"\xff\xd8\xff", headers={**guardian, "content-type": "image/jpeg"})
    assert client.get(f"/api/posts/{hid['id']}/photos/1", headers=parent).status_code == 404
    assert client.post(f"/api/posts/{hid['id']}/like", headers=kid_login).status_code == 200

    # 나를 뺀 가족 전부를 고르면 전체와 같다. 가족이 아닌 사람은 고를 수 없다.
    assert client.post("/api/posts", json={"text": "모두 골랐어요", "audience": [p, k]}, headers=guardian).json()["audience_names"] == []
    assert client.post("/api/posts", json={"text": "x", "audience": [9999]}, headers=guardian).status_code == 422
    # 아이가 쓴 글은 보호자만 보게 할 수 있다
    client.post("/api/posts", json={"text": "비밀", "audience": [g]}, headers=kid_login)
    assert "비밀" in texts(guardian) and "비밀" not in texts(parent)


def test_chat_reply_to_post(client, guardian, parent):
    linked_senior(client, guardian, parent)
    kid_login = signup(client, "kid@x.com", "parent")
    kid = client.post("/api/recipients", json={"type": "child", "display_name": "하늘", "consent_confirmed": True}, headers=guardian).json()
    code = client.post("/api/invites", json={"recipient_id": kid["id"]}, headers=guardian).json()["code"]
    client.post("/api/invites/accept", json={"code": code, "consent": True}, headers=kid_login)
    k = client.get("/api/me", headers=kid_login).json()["id"]

    open_post = client.post("/api/posts", json={"text": "산책 다녀왔어요"}, headers=parent).json()
    secret = client.post("/api/posts", json={"text": "하늘에게만 보이는 비밀", "audience": [k]}, headers=guardian).json()

    # 보이는 글에는 답장할 수 있고, 인용이 함께 온다
    r = client.post("/api/chat", json={"text": "좋아 보여요", "post_id": open_post["id"]}, headers=guardian).json()
    assert r["quote"] == {"id": open_post["id"], "author_name": "엄마", "text": "산책 다녀왔어요", "photos": 0}
    # 내가 못 보는 글에는 답장할 수 없다
    assert client.post("/api/chat", json={"text": "x", "post_id": secret["id"]}, headers=parent).status_code == 404

    # 하늘이 비밀 글에 답장하면, 채팅방의 엄마는 인용 내용을 볼 수 없다
    client.post("/api/chat", json={"text": "고마워요", "post_id": secret["id"]}, headers=kid_login)
    by = lambda h: {m["text"]: m["quote"] for m in client.get("/api/chat", headers=h).json()}
    assert by(kid_login)["고마워요"]["text"] == "하늘에게만 보이는 비밀"
    assert by(parent)["고마워요"] == {"hidden": True}
    assert by(guardian)["고마워요"]["text"] == "하늘에게만 보이는 비밀"

    # 글이 지워져도 메시지는 남고 '삭제된 글'로 보인다
    client.delete(f"/api/posts/{open_post['id']}", headers=parent)
    assert by(guardian)["좋아 보여요"] == {"gone": True}
