from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///./always_with.db"
    jwt_secret: str = "change-me"  # 배포 전 환경변수로 교체
    cors_origins: list[str] = ["http://localhost:5173"]
    # 소셜 로그인: 각 개발자 콘솔에서 발급한 값을 환경변수로 넣는다 (예: GOOGLE_CLIENT_ID)
    public_url: str = "http://localhost:5173"  # 브라우저가 보는 주소. 콘솔의 Redirect URI는 {public_url}/api/auth/oauth/{provider}/callback
    google_client_id: str = ""
    google_client_secret: str = ""
    kakao_client_id: str = ""  # 카카오는 REST API 키
    kakao_client_secret: str = ""
    naver_client_id: str = ""
    naver_client_secret: str = ""


settings = Settings()
