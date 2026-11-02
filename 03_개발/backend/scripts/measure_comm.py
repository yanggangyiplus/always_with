"""연결된 두 계정에서 피드·채팅이 서로 몇 초 만에 보이는지 잰다. 사용: python scripts/measure_comm.py http://localhost:8001
화면은 3초마다 새로 불러오므로(Feed.tsx, Chat.tsx) 같은 주기로 불러오는 두 계정을 흉내 낸다. 보내는 쪽은 번갈아 바뀐다."""
import json, random, statistics, sys, threading, time, uuid

import httpx

BASE = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://localhost:8001"
N, POLL = 10, 3.0  # 방향마다 N번씩 (피드 2N, 채팅 2N)


def signup(role):
    r = httpx.post(f"{BASE}/api/auth/register", json={"email": f"{uuid.uuid4().hex[:8]}@t.com", "password": "password123", "name": role, "role": role}).json()
    return {"Authorization": f"Bearer {r['access_token']}"}


a, b = signup("guardian"), signup("parent")
rid = httpx.post(f"{BASE}/api/recipients", json={"type": "senior", "display_name": "엄마"}, headers=a).json()["id"]
code = httpx.post(f"{BASE}/api/invites", json={"recipient_id": rid}, headers=a).json()["code"]
assert httpx.post(f"{BASE}/api/invites/accept", json={"code": code, "consent": True}, headers=b).status_code == 200

seen: dict[str, float] = {}  # 받는 쪽이 본문을 처음 본 시각 ("이름:글")
lock, stop = threading.Lock(), threading.Event()


def poller(name, h):
    nxt = time.monotonic() + random.uniform(0, POLL)  # 화면을 연 시점이 제각각인 것을 흉내 낸다
    while not stop.is_set():
        time.sleep(max(0, nxt - time.monotonic()))
        nxt += POLL
        try:
            texts = [p["text"] for p in httpx.get(f"{BASE}/api/posts", headers=h, timeout=10).json()]
            texts += [m["text"] for m in httpx.get(f"{BASE}/api/chat", headers=h, timeout=10).json()]
        except httpx.HTTPError:
            continue
        now = time.monotonic()  # 응답을 받은 시각에 화면이 바뀐다
        with lock:
            for t in texts:
                seen.setdefault(f"{name}:{t}", now)


threads = [threading.Thread(target=poller, args=(n, h), daemon=True) for n, h in (("a", a), ("b", b))]
[t.start() for t in threads]
time.sleep(1)

result = {}
for kind, path in (("피드", "/api/posts"), ("채팅", "/api/chat")):
    lat = []
    for i in range(2 * N):
        sender, receiver, h = ("a", "b", a) if i % 2 == 0 else ("b", "a", b)
        text = f"{kind}-{i}-{uuid.uuid4().hex[:6]}"
        t0 = time.monotonic()
        assert httpx.post(f"{BASE}{path}", json={"text": text}, headers=h).status_code == 201
        while f"{receiver}:{text}" not in seen and time.monotonic() - t0 < 15:
            time.sleep(0.05)
        t = seen.get(f"{receiver}:{text}")
        lat.append(round(t - t0, 2) if t else None)
        time.sleep(random.uniform(0.5, 3))
    ok = [x for x in lat if x is not None]
    result[kind] = {"n": len(lat), "within_5s": sum(x <= 5 for x in ok), "missing": len(lat) - len(ok),
                    "median": statistics.median(ok), "max": max(ok), "all": lat}
stop.set()
print(json.dumps(result, ensure_ascii=False, indent=1))
