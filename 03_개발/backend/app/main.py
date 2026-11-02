from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from starlette.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from app.api import auth, cameras, events, family, invites, notifications, oauth, recipients, reports, zones
from app.core.config import settings
from app.db import models  # noqa: F401  (테이블 등록)
from app.db.session import Base, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title="Always with", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["*"], allow_headers=["*"])
for m in (auth, invites, recipients, cameras, zones, events, notifications, reports, family, oauth):
    app.include_router(m.router)


@app.exception_handler(HTTPException)
async def http_error(_: Request, exc: HTTPException):
    return JSONResponse({"code": exc.status_code, "message": exc.detail}, status_code=exc.status_code)


@app.get("/api/health")
def health():
    return {"status": "ok"}


DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if DIST.is_dir():  # 배포에서는 빌드한 화면도 같이 내보낸다 (개발 중에는 Vite가 맡는다)
    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        if path.startswith("api/"):
            raise HTTPException(404, "찾을 수 없어요")
        f = (DIST / path).resolve()
        return FileResponse(f if f.is_file() and DIST in f.parents else DIST / "index.html")
