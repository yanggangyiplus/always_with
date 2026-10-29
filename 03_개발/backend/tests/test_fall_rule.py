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
