"""규칙 기반 낙상 판정: 몸통(어깨-엉덩이)이 눕혀진 채 일정 시간 유지되고, 직전에 서 있었으면 낙상."""
import math

L_SH, R_SH, L_HIP, R_HIP = 5, 6, 11, 12
MIN_CONF = 0.5
LYING_DEG = 60     # 수직 대비 몸통 기울기가 이 이상이면 누움
UPRIGHT_DEG = 30   # 이 미만이면 서 있음
LYING_SEC = 1.0
UPRIGHT_WINDOW = 5.0


def torso_angle(xy, conf):
    """몸통의 수직 대비 기울기(도). 어깨·엉덩이 중 하나라도 신뢰도가 낮으면 None."""
    if min(conf[i] for i in (L_SH, R_SH, L_HIP, R_HIP)) < MIN_CONF:
        return None
    sx, sy = (xy[L_SH][0] + xy[R_SH][0]) / 2, (xy[L_SH][1] + xy[R_SH][1]) / 2
    hx, hy = (xy[L_HIP][0] + xy[R_HIP][0]) / 2, (xy[L_HIP][1] + xy[R_HIP][1]) / 2
    return math.degrees(math.atan2(abs(sx - hx), abs(sy - hy) or 1e-6))


class FallRule:
    def __init__(self):
        self.last_upright = None
        self.lying_since = None

    def update(self, t, xy, conf):
        """프레임 하나를 넣고 낙상이면 True. 한 번 True가 나오면 다시 일어설 때까지 False."""
        a = torso_angle(xy, conf)
        if a is None:
            return False
        if a < UPRIGHT_DEG:
            self.last_upright, self.lying_since = t, None
            return False
        if a < LYING_DEG:
            return False
        if self.lying_since is None:
            self.lying_since = t
        fell = (t - self.lying_since >= LYING_SEC and self.last_upright is not None
                and self.lying_since - self.last_upright <= UPRIGHT_WINDOW)
        if fell:
            self.last_upright = None  # 같은 낙상을 반복 보고하지 않는다
        return fell
