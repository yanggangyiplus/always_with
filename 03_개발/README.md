# 03_개발

개발의 중심 질문은 "어떻게 동작하는가"예요. 가족은 피드, 채팅, 부탁, 일정, 위치로 서로 소통하고, 위험 알림은 프론트가 웹캠 프레임을 서버로 보내면 서버가 관절을 찾고 규칙으로 낙상을 판정해 이벤트를 만들어요.

## 목차

- [구조](#구조)
- [실행](#실행)
- [환경변수](#환경변수)
- [주요 기능](#주요-기능)
- [문서](#문서)

## 구조

| 경로 | 내용 |
| --- | --- |
| `backend/app/api/` | 인증, 초대, 돌봄 대상, 카메라, 구역, 이벤트, 알림, 리포트, 가족(피드, 채팅 등), 소셜 로그인 |
| `backend/app/services/` | `pose.py`(YOLO 추론), `fall_rule.py`(낙상 규칙), `events.py`(이벤트 생성) |
| `backend/app/core/` | 설정, 비밀번호 해시, 토큰 |
| `backend/tests/` | pytest 20개 |
| `frontend/src/pages/` | 화면 |
| `frontend/src/lib/` | API 호출, 로그인 상태, 위치 |
| `ml/run_camera.py` | 서버 없이 웹캠으로 판정을 점검하는 스크립트 |
| `ml/eval/` | 낙상 규칙 전후 비교 스크립트와 결과 |
| `docs/` | 아키텍처, 안정성, 평가 리포트 |

## 실행

필요한 것은 Python 3.11 이상, Node.js 20 이상이에요.

```bash
# 백엔드 (8000)
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# 프론트엔드 (5173)
cd frontend
npm install
npm run dev
```

- 관절 검출 모델 `yolo26n-pose.pt`는 저장소에 없고(`*.pt`는 git에서 제외), `ml/`에 두어야 해요. 첫 분석 요청 때 불러와요.
- 데이터베이스(`always_with.db`)는 처음 켤 때 자동으로 만들어져요. 마이그레이션은 없어요.

점검용 스크립트와 평가는 아래처럼 돌려요.

```bash
cd backend && python -m pytest -q
python ../ml/eval/eval_fall_rule.py
python ../ml/run_camera.py <camera_id> --show --conf 0.25 --no-mirror
```

## 환경변수

모두 선택이에요. 없으면 기본값으로 켜져요.

| 이름 | 기본값 | 설명 |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite:///./always_with.db` | DB 주소 |
| `JWT_SECRET` | `change-me` | 배포 전에 반드시 바꿔요 |
| `PUBLIC_URL` | `http://localhost:5173` | 브라우저가 보는 주소 |
| `CORS_ORIGINS` | `["http://localhost:5173"]` | 허용할 출처 |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | 없음 | 구글 로그인 |
| `KAKAO_CLIENT_ID`, `KAKAO_CLIENT_SECRET` | 없음 | 카카오 로그인(REST API 키, 동의항목에서 이메일 켜기) |
| `NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET` | 없음 | 네이버 로그인 |

소셜 로그인은 각 개발자 콘솔의 Redirect URI에 `{PUBLIC_URL}/api/auth/oauth/{google|kakao|naver}/callback`을 등록해야 해요.

## 주요 기능

- 이메일 로그인과 소셜 로그인 코드(키 없이는 "준비 중")
- 보호자, 부모님, 아이 계정과 초대 코드(6자리, 10분 만료, 1회용)
- 카메라 등록과 웹캠 스트림, 관절 오버레이
- 낙상 규칙 판정, 이벤트 타임라인, 오탐 신고, 성능 리포트
- 아이 카메라의 구역 설정 API
- 가족 피드(사진 5장, 좋아요, 공개 범위), 채팅(피드 글 답장), 일정, 부탁해, 위치 공유
- 피드와 채팅은 3초마다 새로 불러와 연결된 계정에 몇 초 안에 보여요

## 문서

- [아키텍처](./docs/아키텍처.md)
- [안정성](./docs/안정성.md)
- [평가 리포트](./docs/평가리포트.md)
