from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")  # backend 폴더의 .env(git 제외)도 읽는다

    database_url: str = "sqlite:///./always_with.db"
    clip_dir: str = ""  # 비우면 backend/clips. 배포에서는 영구 디스크 경로를 넣는다
    jwt_secret: str = "change-me"  # 배포 전 환경변수로 교체
    cors_origins: list[str] = ["http://localhost:5173"]
    # 소셜 로그인: 각 개발자 콘솔에서 발급한 값을 환경변수로 넣는다 (예: GOOGLE_CLIENT_ID)
    public_url: str = "http://localhost:5173"  # 브라우저가 보는 주소. 콘솔의 Redirect URI는 {public_url}/api/auth/oauth/{provider}/callback
    # Web Push: `python scripts/gen_vapid.py`로 만든 값을 환경변수로 넣는다. 비어 있으면 푸시는 보내지 않는다
    vapid_private_key: str = ""
    vapid_public_key: str = ""
    vapid_subject: str = "mailto:admin@example.com"
    google_client_id: str = ""
    google_client_secret: str = ""
    kakao_client_id: str = ""  # 카카오는 REST API 키
    kakao_client_secret: str = ""
    naver_client_id: str = ""
    naver_client_secret: str = ""


settings = Settings()
