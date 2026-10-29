---
name: fall-rule-eval
description: 낙상 판정 규칙을 바꾼 뒤 전후 수치를 다시 재고 리포트를 갱신한다. "기준값 바꿨어", "정확도 다시", "오탐 확인", "평가 돌려줘" 요청에 사용한다.
---

# fall-rule-eval

낙상 기준값(`03_개발/backend/app/services/fall_rule.py`의 `LYING_DEG`, `UPRIGHT_DEG`, `LYING_SEC`, `UPRIGHT_WINDOW`)을 바꾸면 반드시 실행한다.

1. 바꾸기 전 `03_개발/ml/eval/results.md`를 `results.before.md`로 복사해 둔다.
2. `cd 03_개발 && python ml/eval/eval_fall_rule.py`를 실행한다.
3. 재현율, 오탐률, 경보 지연을 이전 값과 나란히 비교한다.
4. 새로 틀린 건과 새로 맞은 건을 건별 표에서 찾아 이유를 한 줄씩 적는다.
5. `cd 03_개발/backend && python -m pytest -q`가 통과하는지 확인한다.
6. `03_개발/docs/평가리포트.md`의 수치와 해석을 갱신한다. 실행하지 않은 수치는 쓰지 않는다.

규칙:

- 시나리오를 추가해 점수를 올리지 않는다. 시나리오를 바꾸면 v0와 v1을 모두 다시 잰다.
- 합성 시퀀스 결과는 실제 정확도가 아니라고 리포트에 남긴다.
- 실제 영상 평가를 추가하면 합성 결과와 표를 나눠 쓴다.
