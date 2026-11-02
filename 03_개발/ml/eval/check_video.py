"""영상 한 개에 모델과 낙상 규칙을 돌려 0.5초마다 몸통 기울기와 박스 비율을 보여 주고, 낙상으로 판정한 시각을 알려 준다.
사용: python ml/eval/check_video.py 영상경로   (ml/yolo26n-pose.pt가 필요하다)"""
import sys
from pathlib import Path

import cv2
from ultralytics import YOLO

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app.services.fall_rule import FallRule, torso_angle  # noqa: E402

model, rule = YOLO(str(ROOT / "ml" / "yolo26n-pose.pt")), FallRule()
cap = cv2.VideoCapture(sys.argv[1])
fps = cap.get(cv2.CAP_PROP_FPS) or 24
fired, n = None, 0
print("초   사람  기울기  박스비율")
while True:
    ok, frame = cap.read()
    if not ok:
        break
    t, n = n / fps, n + 1
    r = model(frame, verbose=False)[0]
    people = len(r.boxes)
    if r.keypoints is None or not people:
        row = f"{t:4.1f}  0"
    else:
        i = int(r.boxes.xywh[:, 2:].prod(dim=1).argmax())
        xy, conf = r.keypoints.xy[i].tolist(), r.keypoints.conf[i].tolist()
        w, h = r.boxes.xywh[i][2:].tolist()
        a = torso_angle(xy, conf)
        if rule.update(t, xy, conf, w / max(h, 1)) and fired is None:
            fired = t
        row = f"{t:4.1f}  {people}  {'-' if a is None else round(a)}  {w / max(h, 1):.2f}"
    if n % int(fps / 2 or 1) == 1:
        print(row)
print("낙상 판정 시각:", f"{fired:.1f}초" if fired is not None else "없음")
