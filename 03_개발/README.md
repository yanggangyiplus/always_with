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
| `backend/app/services/` | `pose.py`(YOLO 추론), `fall_rule.py`(낙상 규칙), `events.py`(이벤트 생성), `clips.py`(낙상 클립 저장), `push.py`(Web Push 발송) |
| `backend/app/core/` | 설정, 비밀번호 해시, 토큰 |
| `backend/tests/` | pytest 24개 |
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
- 낙상 클립(앞뒤 약 5초씩)은 `ffmpeg`로 만들어서 `backend/clips/`에 저장해요(git에서 제외). `ffmpeg`가 없으면 클립 상태가 `failed`가 되고 이벤트와 알림은 그대로 가요.
- 데이터베이스(`always_with.db`)는 처음 켤 때 자동으로 만들어져요. 마이그레이션은 없어요.

점검용 스크립트와 평가는 아래처럼 돌려요.

```bash
cd backend && python -m pytest -q
python ../ml/eval/eval_fall_rule.py
python ../ml/run_camera.py <camera_id> --show --conf 0.25 --no-mirror
```

## 환경변수

모두 선택이에요. 없으면 기본값으로 켜져요. 값은 환경변수로 넣거나, `backend/.env.example`을 `backend/.env`로 복사해서 채워요(`.env`는 git에 올라가지 않아요).

| 이름 | 기본값 | 설명 |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite:///./always_with.db` | DB 주소 |
| `JWT_SECRET` | `change-me` | 배포 전에 반드시 바꿔요 |
| `PUBLIC_URL` | `http://localhost:5173` | 브라우저가 보는 주소 |
| `CORS_ORIGINS` | `["http://localhost:5173"]` | 허용할 출처 |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | 없음 | 구글 로그인 |
| `KAKAO_CLIENT_ID`, `KAKAO_CLIENT_SECRET` | 없음 | 카카오 로그인(REST API 키, 동의항목에서 이메일 켜기) |
| `NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET` | 없음 | 네이버 로그인 |
| `VAPID_PRIVATE_KEY`, `VAPID_PUBLIC_KEY`, `VAPID_SUBJECT` | 없음 | Web Push. `python scripts/gen_vapid.py`로 만들어요. 키가 없으면 푸시 버튼이 보이지 않고 인앱 알림만 가요 |
| `DATABASE_URL`, `CLIP_DIR` | `backend/always_with.db`, `backend/clips` | 배포에서는 영구 디스크 경로로 바꿔요 |

Web Push는 `localhost` 또는 HTTPS에서만 켜져요. 키는 저장소에 올리지 않아요.

## 소셜 로그인 연결

각 개발자 콘솔에서 앱을 만들고 아래 주소를 Redirect URI(Callback URL)로 등록해요. 로컬 기본값은 `http://localhost:5173/api/auth/oauth/{google|kakao|naver}/callback`이에요. 발급한 ID와 비밀 값을 `backend/.env`에 넣고 백엔드를 다시 켜요.

| 제공자 | 콘솔 | 확인할 것 |
| --- | --- | --- |
| 구글 | Google Cloud Console의 사용자 인증 정보에서 OAuth 클라이언트 ID(웹 애플리케이션) 만들기 | 승인된 리디렉션 URI 등록 |
| 카카오 | 카카오 디벨로퍼스에서 앱 만들기, 카카오 로그인 켜기 | REST API 키를 ID로 사용, Redirect URI 등록, 동의항목에서 이메일 켜기(이메일 동의는 앱 설정에 따라 제한될 수 있어요) |
| 네이버 | 네이버 개발자센터에서 애플리케이션 등록, 네이버 로그인 선택 | 서비스 URL과 Callback URL 등록, 제공 정보에서 이메일 선택 |

키가 들어가면 로그인 화면의 해당 버튼이 켜져요(`GET /api/auth/oauth/providers`). 키가 없는 제공자는 "준비 중"으로 보여요. 제공자 응답을 읽는 부분은 가짜 서버로 테스트했고, 실제 제공자와의 로그인은 키를 넣고 확인해야 해요.

## 구글 로그인 켜기

1. [Google Cloud Console](https://console.cloud.google.com)에서 프로젝트를 만들어요.
2. 「API 및 서비스」의 「OAuth 동의 화면」에서 앱 이름, 지원 이메일을 넣고, 테스트 중에는 사용자 유형을 「외부」, 상태를 「테스트」로 두고 본인 계정을 테스트 사용자에 추가해요.
3. 「사용자 인증 정보」에서 「OAuth 클라이언트 ID 만들기」를 눌러 애플리케이션 유형을 「웹 애플리케이션」으로 골라요.
4. 「승인된 리디렉션 URI」에 `http://localhost:5173/api/auth/oauth/google/callback`을 넣어요. 배포 주소가 있으면 `https://배포주소/api/auth/oauth/google/callback`도 추가해요.
5. 만들어진 클라이언트 ID와 보안 비밀을 `backend/.env`에 넣어요.

   ```
   GOOGLE_CLIENT_ID=...
   GOOGLE_CLIENT_SECRET=...
   ```

   배포할 때는 `PUBLIC_URL`도 배포 주소로 맞춰요.
6. 백엔드를 다시 켜면 로그인 화면의 「Google로 로그인」 버튼이 켜져요.

## 앱으로 설치

웹앱을 설치형(PWA)으로 만들어서 별도 스토어 없이 홈 화면에 추가할 수 있어요.

- 안드로이드 크롬과 데스크톱 크롬, 엣지: 로그인 화면과 상단의 「앱 설치」 버튼을 누르면 설치 창이 떠요.
- 아이폰 사파리: 「앱 설치」 버튼이 공유 메뉴의 「홈 화면에 추가」 방법을 알려 줘요.
- 설치 후에는 주소창 없이 앱처럼 열려요. 이미 설치한 기기에서는 버튼이 보이지 않아요.
- 설치 창은 `localhost` 또는 HTTPS에서만 떠요. 스토어 앱(앱스토어, 플레이스토어)은 아니에요.

## Render에 배포

`Dockerfile`과 `render.yaml`을 저장소 루트(이 폴더)에 두었어요. 백엔드가 빌드한 화면까지 함께 내보내서 서비스 하나로 돌아가요.

1. Render 대시보드에서 「New」의 「Blueprint」로 저장소를 연결하고 Blueprint Path에 `03_개발/render.yaml`을 적어요. 설정 안의 `rootDir`이 `03_개발`에서 Dockerfile을 찾게 해 줘요.
2. 저장소를 직접 `Web Service`로 연결할 때는 Root Directory를 `03_개발`로 지정해요.
3. 비밀 값(`PUBLIC_URL`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `VAPID_*`)은 대시보드에서 직접 넣어요.
4. `PUBLIC_URL`에 배포된 주소(`https://...onrender.com`)를 넣고, 구글 콘솔의 리디렉션 URI에 `{PUBLIC_URL}/api/auth/oauth/google/callback`을 추가해요.
5. DB와 낙상 클립은 `/data` 영구 디스크에 저장돼요. 영구 디스크는 유료 요금제에서만 붙어요.

이미지에서 모델 파일(`yolo26n-pose.pt`)은 빌드할 때 내려받아요. 이 설정으로 실제 빌드와 배포는 아직 해보지 못했어요.

## Hugging Face Spaces에 배포

카드 없이 올릴 수 있어요. 같은 `Dockerfile`을 쓰고, 포트는 7860이에요.

1. [Hugging Face](https://huggingface.co/new-space)에서 Space를 만들어요. SDK는 「Docker」, 공개 범위는 원하는 대로 골라요.
2. Space의 「Settings」에서 「Variables and secrets」에 아래 값을 넣어요.
   - `JWT_SECRET`: 길고 아무렇게나 만든 문자열(Secret)
   - `PUBLIC_URL`: `https://{계정}-{space이름}.hf.space`
   - `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`: 구글 로그인을 쓸 때(Secret)
   - `VAPID_PRIVATE_KEY`, `VAPID_PUBLIC_KEY`: 푸시를 쓸 때(Secret)
3. 이 폴더에서 `./deploy_hf.sh 계정/space이름`을 실행해요. 비밀번호를 물으면 write 권한 토큰을 넣어요.
4. Space 화면에서 빌드가 끝나길 기다려요. 처음은 모델과 torch를 받느라 오래 걸려요.
5. 구글 콘솔의 리디렉션 URI에 `{PUBLIC_URL}/api/auth/oauth/google/callback`을 추가해요.

무료 Space는 디스크가 영구가 아니어서 재시작하거나 다시 배포하면 DB와 클립이 지워져요. 접속이 없으면 잠들어요. 웹캠은 `hf.space` 주소를 직접 열어야 쓸 수 있어요(Hugging Face 화면에 끼워 넣은 형태에서는 권한이 막힐 수 있어요). 빌드와 배포는 아직 해보지 못했어요.

## 주요 기능

- 이메일 로그인과 소셜 로그인 코드(키 없이는 "준비 중")
- 홈 화면에 추가하는 앱 설치(PWA)
- 보호자, 부모님, 아이 계정과 초대 코드(6자리, 10분 만료, 1회용)
- 카메라 등록과 웹캠 스트림, 관절 오버레이
- 낙상 규칙 판정, 이벤트 타임라인, 오탐 신고, 성능 리포트
- 아이 카메라의 구역 설정(화면에서 드래그 또는 위치 버튼, 저장과 삭제, 라이브 화면에 겹쳐 표시)
- 가족 피드(사진 5장, 좋아요, 공개 범위), 채팅(피드 글 답장), 일정, 부탁해, 위치 공유(가족 마지막 위치를 지도에 핀으로 표시)
- 피드와 채팅은 3초마다 새로 불러와 연결된 계정에 몇 초 안에 보여요

## 문서

- [아키텍처](./docs/아키텍처.md)
- [안정성](./docs/안정성.md)
- [평가 리포트](./docs/평가리포트.md)
