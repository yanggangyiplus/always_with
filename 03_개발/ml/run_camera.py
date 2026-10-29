"""웹캠 → yolo26n-pose → 규칙 판정 → 낙상 이벤트 생성 (서버 없이 단독 실행하는 점검용).
사이트에서 쓰려면 서버만 켜면 된다: 브라우저가 프레임을 서버로 보내 같은 판정을 한다.

사용: cd backend && .venv/bin/python ../ml/run_camera.py <camera_id> [--source 0] [--show]
"""
import argparse
import sys
import time
from pathlib import Path

import cv2
from ultralytics import YOLO

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
from app.db.models import Camera, now  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.services.events import create_event  # noqa: E402
from app.services.fall_rule import FallRule  # noqa: E402

p = argparse.ArgumentParser()
p.add_argument("camera_id", type=int)
p.add_argument("--source", default="0", help="웹캠 번호 또는 영상 파일 경로")
p.add_argument("--model", default=str(Path(__file__).with_name("yolo26n-pose.pt")))
p.add_argument("--show", action="store_true", help="관절 미리보기 창 (q로 종료)")
p.add_argument("--conf", type=float, default=0.25, help="사람 검출 최소 신뢰도 (낮추면 상반신만 보일 때도 잡힘)")
p.add_argument("--no-mirror", action="store_true", help="미리보기 좌우반전 끄기")
args = p.parse_args()

model = YOLO(args.model)
cap = cv2.VideoCapture(int(args.source) if args.source.isdigit() else args.source)
if not cap.isOpened():
    sys.exit("카메라를 열 수 없습니다. macOS는 터미널에 카메라 권한이 필요합니다.")

db = SessionLocal()
camera = db.get(Camera, args.camera_id) or sys.exit(f"camera {args.camera_id} 없음")
rule, last_beat, fall_until = FallRule(), 0.0, 0.0
try:
    while cap.isOpened():
        ok, frame = cap.read()
        if not ok:
            break
        t = time.monotonic()
        if t - last_beat > 10:  # 앱에서 '연결됨'으로 보이게 한다
            camera.last_seen_at, last_beat = now(), t
            db.commit()
            db.refresh(camera)  # 앱에서 일시정지한 상태를 반영한다
        r = model(frame, conf=args.conf, verbose=False)[0]
        if r.keypoints is not None and len(r.boxes):
            i = int(r.boxes.xywh[:, 2:].prod(dim=1).argmax())  # 다인이면 가장 큰 사람
            if rule.update(t, r.keypoints.xy[i].tolist(), r.keypoints.conf[i].tolist()):
                ev = create_event(db, camera, "fall", float(r.boxes.conf[i]))
                fall_until = t + 3
                print("낙상 감지 → 이벤트", ev.id if ev else "(쿨다운/일시정지로 생략)", flush=True)
        if args.show:
            view = r.plot()
            if not args.no_mirror:
                view = cv2.flip(view, 1)  # 추론은 원본, 표시만 반전한다
            if not len(r.boxes):
                cv2.putText(view, "no person", (20, 110), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
            if t < fall_until:
                cv2.putText(view, "FALL", (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 4)
            cv2.imshow("always-with", view)
            if cv2.waitKey(1) == ord("q"):
                break
finally:
    cap.release()
    cv2.destroyAllWindows()
