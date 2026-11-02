from app.services.fall_rule import FallRule

C = [1.0] * 17


def pose(lying):
    xy = [(0, 0)] * 17
    sh, hip = ((100, 100), (200, 100)) if lying else ((100, 100), (100, 200))
    for i in (5, 6):
        xy[i] = sh
    for i in (11, 12):
        xy[i] = hip
    return xy


def run(frames):
    r = FallRule()
    return [r.update(t, pose(lying), C) for t, lying in frames]


def test_fall_after_standing():
    out = run([(0, False), (1, False), (2, True), (2.5, True), (3.1, True), (4, True)])
    assert out == [False, False, False, False, True, False]


def test_lying_without_standing_is_not_fall():
    assert not any(run([(t, True) for t in range(10)]))


def test_bending_briefly_is_not_fall():
    assert not any(run([(0, False), (1, True), (1.5, True), (2, False)]))


def test_leaning_on_floor_is_fall_only_when_box_is_wide():
    def run_lean(aspect):
        r, xy = FallRule(), [(0, 0)] * 17
        for i in (5, 6):
            xy[i] = (0, 0)
        for i in (11, 12):
            xy[i] = (80, 100)  # 몸통 기울기 약 39도
        r.update(0, pose(False), C)
        return [r.update(t, xy, C, aspect) for t in (1, 2.2, 3)]
    assert any(run_lean(1.5))
    assert not any(run_lean(0.5))
    assert not any(run_lean(None))
