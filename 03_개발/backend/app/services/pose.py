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
from app.services.fall_rule import FallRule

MODEL_PATH = Path(__file__).resolve().parents[3] / "ml" / "yolo26n-pose.pt"
_lock = threading.Lock()  # 모델 하나를 요청들이 같이 쓰므로 한 번에 하나씩 추론한다
_model = None
PRE_SEC, POST_SEC = 5.0, 5.0  # 낙상 앞뒤로 남기는 클립 길이
_bufs: dict[int, deque] = {}  # 카메라별 최근 PRE_SEC 프레임(메모리에만 있고, 낙상일 때만 파일이 된다)
_pending: dict[int, list] = {}  # 낙상 직후 POST_SEC 동안 모으는 프레임
_rules: dict[int, FallRule] = {}  # shortcut: 프로세스 메모리, 서버를 여러 개 띄우면 카메라 상태가 갈라진다


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
    if r.keypoints is not None and len(r.boxes):
        i = int(r.boxes.xywh[:, 2:].prod(dim=1).argmax())  # 다인이면 가장 큰 사람
        rule = _rules.setdefault(camera.id, FallRule())
        if rule.update(t, r.keypoints.xy[i].tolist(), r.keypoints.conf[i].tolist()):
            ev = create_event(db, camera, "fall", float(r.boxes.conf[i]))
            if ev:
                ev.clip_status = "saving"
                db.commit()
                _pending[camera.id] = list(buf)
                threading.Timer(POST_SEC, _finish, (ev.id, camera.id)).start()
    return jpg


def _finish(event_id: int, camera_id: int) -> None:
    clips.save(event_id, _pending.pop(camera_id, []))
