"""낙상 규칙 전후 비교: 직접 만든 관절 시퀀스(합성) 26건으로 기준선(v0)과 현재 규칙(v1)을 비교한다.
실제 영상이 아니라 몸통 기울기 궤적을 가정한 것이므로, 수치는 '규칙이 이 상황들에서 어떻게 움직이는가'만 보여 준다.

사용: python ml/eval/eval_fall_rule.py   (결과는 ml/eval/results.md에 저장)
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app.services.fall_rule import FallRule, torso_angle  # noqa: E402

FPS = 10


def pose(angle):
    """몸통 길이 100, 수직 대비 angle도로 기울어진 관절 17개 (어깨·엉덩이만 의미 있음)."""
    import math
    dx, dy = 100 * math.sin(math.radians(angle)), 100 * math.cos(math.radians(angle))
    xy = [(0, 0)] * 17
    for i in (5, 6):
        xy[i] = (0, 0)
    for i in (11, 12):
        xy[i] = (dx, dy)
    return xy


def seq(*segs):
    """(초, 시작각도[, 끝각도[, 신뢰도]]) 구간들을 이어 (t, angle, conf) 프레임 목록으로 만든다."""
    out, t = [], 0.0
    for s in segs:
        dur, a0 = s[0], s[1]
        a1 = s[2] if len(s) > 2 else a0
        c = s[3] if len(s) > 3 else 1.0
        n = int(dur * FPS)
        for k in range(n):
            out.append((t, a0 + (a1 - a0) * k / max(n - 1, 1), c))
            t += 1 / FPS
    return out


# (이름, 낙상 여부, 프레임) — 낙상 시작 시각은 첫 번째로 기울기 60도를 넘는 프레임
CASES = [
    ("F01 서 있다가 옆으로 쓰러짐(90°, 3초)", 1, seq((3, 5), (3, 90))),
    ("F02 70°로 눕고 2초 유지", 1, seq((3, 5), (2, 70))),
    ("F03 0.5초 만에 쓰러져 3초 유지", 1, seq((3, 5), (0.5, 5, 85), (3, 85))),
    ("F04 휘청(40°)한 뒤 쓰러짐", 1, seq((2, 5), (1, 40), (3, 85))),
    ("F05 걷다가(5~15° 흔들림) 쓰러짐", 1, seq(*[(0.5, 5 if i % 2 else 15) for i in range(8)], (2, 80))),
    ("F06 쓰러진 뒤 관절 신뢰도 0.3초 하락", 1, seq((3, 5), (1, 90), (0.3, 90, 90, 0.2), (2, 90))),
    ("F07 65°로 겨우 눕고 1.2초 유지", 1, seq((3, 5), (1.2, 65))),
    ("F08 쓰러졌다 1.1초 만에 일어남", 1, seq((3, 5), (1.1, 90), (3, 5))),
    ("F09 3초에 걸쳐 천천히 주저앉음", 1, seq((3, 5), (3, 5, 80), (3, 80))),
    ("F10 1초만 서 있다가 쓰러짐", 1, seq((1, 5), (3, 90))),
    ("F11 카메라 쪽으로 쓰러짐(몸통이 짧아져 기울기 20°로 보임)", 1, seq((3, 5), (3, 20))),
    ("F12 쓰러져 2초, 일어났다 다시 쓰러짐", 1, seq((3, 5), (2, 90), (3, 5), (2, 90))),
    ("N01 10초 서 있음", 0, seq((10, 5))),
    ("N02 걷기(5~15° 흔들림)", 0, seq(*[(0.5, 5 if i % 2 else 15) for i in range(20)])),
    ("N03 바닥 물건 줍기(60° 0.8초)", 0, seq((3, 5), (0.8, 62), (3, 5))),
    ("N04 신발 끈 묶기(50° 5초)", 0, seq((2, 5), (5, 50), (2, 5))),
    ("N05 의자에 앉기(몸통 10°)", 0, seq((10, 10))),
    ("N06 앉아서 뒤로 기대기(25~35°)", 0, seq((10, 30))),
    ("N07 몸 숙이기 스트레칭 3회(75° 0.6초씩)", 0, seq(*[x for _ in range(3) for x in ((2, 5), (0.6, 75))], (2, 5))),
    ("N08 처음부터 소파에 누워 있음(85°)", 0, seq((10, 85))),
    ("N09 서 있다가 관절이 안 보임(신뢰도 0.2, 5초)", 0, seq((3, 5), (5, 85, 85, 0.2))),
    ("N10 아이가 바닥에서 앉았다 구르기(20°↔80° 0.7초)", 0, seq(*[x for _ in range(4) for x in ((1, 20), (0.7, 80))])),
    ("N11 누워 자다가 일어남", 0, seq((10, 85), (3, 5))),
    ("N12 [어려움] 서 있다가 4초에 걸쳐 소파에 일부러 누움", 0, seq((3, 5), (4, 5, 85), (10, 85))),
    ("N13 [어려움] 정원일: 65°로 3초 숙임", 0, seq((3, 5), (3, 65), (3, 5))),
    ("N14 [어려움] 팔굽혀펴기/요가(75° 5초)", 0, seq((2, 5), (5, 75), (2, 5))),
]


class NaiveRule:
    """v0 비교용: 몸통이 60도 이상인 프레임이 한 번이라도 있으면 낙상. 서 있었는지, 지속 시간은 보지 않는다."""

    def __init__(self):
        self.fired = False

    def update(self, t, xy, conf):
        a = torso_angle(xy, conf)
        if a is not None and a >= 60 and not self.fired:
            self.fired = True
            return True
        return False


def run(rule_cls, frames):
    """처음 경보가 울린 시각을 돌려준다. 없으면 None."""
    r = rule_cls()
    for t, a, c in frames:
        if r.update(t, pose(a), [c] * 17):
            return t
    return None


def onset(frames):
    return next((t for t, a, _ in frames if a >= 60), None)


def metrics(rule_cls):
    tp = fp = fn = tn = 0
    delays, rows = [], []
    for name, label, frames in CASES:
        t = run(rule_cls, frames)
        hit = t is not None
        tp += hit and label == 1
        fn += (not hit) and label == 1
        fp += hit and label == 0
        tn += (not hit) and label == 0
        if hit and label == 1 and onset(frames) is not None:
            delays.append(max(t - onset(frames), 0))
        rows.append((name, label, hit))
    return dict(tp=tp, fp=fp, fn=fn, tn=tn, recall=tp / (tp + fn), fpr=fp / (fp + tn),
                precision=tp / (tp + fp) if tp + fp else 0, delay=sum(delays) / len(delays) if delays else 0), rows


if __name__ == "__main__":
    m0, r0 = metrics(NaiveRule)
    m1, r1 = metrics(FallRule)
    assert len(CASES) == 26 and m1["tp"] + m1["fn"] == 12 and m1["fp"] + m1["tn"] == 14
    lines = ["# 낙상 규칙 전후 비교 (합성 관절 시퀀스 26건)", "",
             "낙상 12건, 일상 동작 14건(까다로운 3건 포함). 실제 영상이 아니라 몸통 기울기 궤적을 직접 만든 것이라 실제 정확도가 아닙니다.",
             "v0은 비교용 단순 기준선(기울기 60° 이상이면 즉시 낙상), v1은 `backend/app/services/fall_rule.py`의 현재 규칙입니다.", "",
             "| 지표 | v0 단순 기준선 | v1 현재 규칙 |", "|---|---|---|"]
    for k, label, f in [("recall", "재현율(낙상 12건 중 잡은 비율)", "{:.0%}"), ("fpr", "오탐률(일상 14건 중 울린 비율)", "{:.0%}"),
                        ("precision", "정밀도", "{:.0%}"), ("delay", "경보 지연(낙상 시작→경보, 초)", "{:.1f}")]:
        lines.append(f"| {label} | {f.format(m0[k])} | {f.format(m1[k])} |")
    lines.append(f"| 혼동 (TP/FN/FP/TN) | {m0['tp']}/{m0['fn']}/{m0['fp']}/{m0['tn']} | {m1['tp']}/{m1['fn']}/{m1['fp']}/{m1['tn']} |")
    lines += ["", "## 건별 결과 (울림=경보 발생)", "", "| 시나리오 | 정답 | v0 | v1 |", "|---|---|---|---|"]
    for (n, lab, h0), (_, _, h1) in zip(r0, r1):
        ok = lambda h: ("울림" if h else "안 울림") + (" ✅" if h == bool(lab) else " ❌")
        lines.append(f"| {n} | {'낙상' if lab else '일상'} | {ok(h0)} | {ok(h1)} |")
    out = ROOT / "ml" / "eval" / "results.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
