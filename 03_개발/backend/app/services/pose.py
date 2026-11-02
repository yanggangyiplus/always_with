import logging
import threading
import time
from collections import deque
from pathlib import Path

import cv2
import numpy as np
from sqlalchemy.orm import Session

from app.db.models import Camera
from app.services import clips
from app.services.events import create_event
from app.services.fall_rule import FallRule, torso_angle

MODEL_PATH = Path(__file__).resolve().parents[3] / "ml" / "yolo26n-pose.pt"
_lock = threading.Lock()  # 모델 하나를 요청들이 같이 쓰므로 한 번에 하나씩 추론한다
_model = None
PRE_SEC, POST_SEC = 5.0, 5.0  # 낙상 앞뒤로 남기는 클립 길이
_bufs: dict[int, deque] = {}  # 카메라별 최근 PRE_SEC 프레임(메모리에만 있고, 낙상일 때만 파일이 된다)
_pending: dict[int, list] = {}  # 낙상 직후 POST_SEC 동안 모으는 프레임
_said: dict[int, float] = {}
_fall_until: dict[int, float] = {}  # 낙상으로 판정한 뒤 화면에 문구를 계속 띄울 시각
FALL_SHOW_SEC = 8.0
log = logging.getLogger("uvicorn.error")
_rules: dict[int, FallRule] = {}  # shortcut: 프로세스 메모리, 서버를 여러 개 띄우면 카메라 상태가 갈라진다


def fall_active(camera_id: int) -> bool:
    return time.monotonic() < _fall_until.get(camera_id, 0)


def _say(camera_id: int, t: float, text: str) -> None:
    """카메라마다 1초에 한 줄, 지금 무엇을 보고 있는지 서버 터미널에 남긴다. 알림이 안 올 때 원인을 찾는 용도다."""
    if t - _said.get(camera_id, -9) >= 1:
        _said[camera_id] = t
        log.info("camera %s: %s", camera_id, text)


def analyze(db: Session, camera: Camera, jpeg: bytes) -> bytes:
    global _model
    frame = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)
    if frame is None:
        raise ValueError("이미지를 읽을 수 없습니다")
    with _lock:
        if _model is None:
            from ultralytics import YOLO  # 서버 시작과 테스트를 느리게 하지 않도록 첫 요청에 불러온다
            _model = YOLO(str(MODEL_PATH))
        r = _model(frame, verbose=False)[0]
    jpg = cv2.imencode(".jpg", r.plot(), [cv2.IMWRITE_JPEG_QUALITY, 70])[1].tobytes()
    t = time.monotonic()
    buf = _bufs.setdefault(camera.id, deque())
    buf.append((t, jpg))
    while t - buf[0][0] > PRE_SEC:
        buf.popleft()
    if camera.id in _pending:
        _pending[camera.id].append((t, jpg))
    if r.keypoints is None or not len(r.boxes):
        _say(camera.id, t, "사람이 보이지 않아요")
    else:
        i = int(r.boxes.xywh[:, 2:].prod(dim=1).argmax())  # 다인이면 가장 큰 사람
        rule = _rules.setdefault(camera.id, FallRule())
        w, h = r.boxes.xywh[i][2:].tolist()
        xy, conf = r.keypoints.xy[i].tolist(), r.keypoints.conf[i].tolist()
        angle = torso_angle(xy, conf)
        _say(camera.id, t, f"사람 {len(r.boxes)}명, 몸통 기울기 " + ("계산 못 함(어깨·엉덩이가 안 보임)" if angle is None else f"{angle:.0f}도")
             + f", 박스 가로/세로 {w / max(h, 1):.2f}")
        if rule.update(t, xy, conf, w / max(h, 1)):
            _fall_until[camera.id] = t + FALL_SHOW_SEC  # 이벤트가 쿨다운으로 생략돼도 화면에는 알린다
            ev = create_event(db, camera, "fall", float(r.boxes.conf[i]))
            log.info("camera %s: 낙상 판정 → %s", camera.id, f"이벤트 {ev.id}" if ev else "만들지 않음(일시정지 또는 60초 안에 같은 이벤트)")
            if ev:
                ev.clip_status = "saving"
                db.commit()
                _pending[camera.id] = list(buf)
                threading.Timer(POST_SEC, _finish, (ev.id, camera.id)).start()
    return jpg


def _finish(event_id: int, camera_id: int) -> None:
    clips.save(event_id, _pending.pop(camera_id, []))
