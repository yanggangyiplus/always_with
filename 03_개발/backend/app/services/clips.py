import shutil
import subprocess
from pathlib import Path

from app.core.config import settings
from app.db.models import Event
from app.db.session import SessionLocal

CLIP_DIR = Path(settings.clip_dir) if settings.clip_dir else Path(__file__).resolve().parents[2] / "clips"  # shortcut: 로컬 디스크, 배포하면 오브젝트 스토리지로 옮기고 보관 기간을 둔다


def encode(frames: list[tuple[float, bytes]], path: Path) -> bool:
    """(시각, JPEG) 목록을 브라우저가 재생하는 H.264 mp4로 만든다. 프레임 간격이 일정하지 않아 평균 fps를 쓴다."""
    if len(frames) < 2 or not shutil.which("ffmpeg"):
        return False
    fps = max(1.0, min(30.0, (len(frames) - 1) / max(frames[-1][0] - frames[0][0], 0.1)))
    path.parent.mkdir(exist_ok=True)
    p = subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", f"{fps:.2f}", "-i", "-",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(path)],
        input=b"".join(j for _, j in frames), capture_output=True, timeout=60)
    return p.returncode == 0 and path.is_file()


def save(event_id: int, frames: list[tuple[float, bytes]]) -> None:
    path = CLIP_DIR / f"{event_id}.mp4"
    ok = encode(frames, path)
    with SessionLocal() as db:
        e = db.get(Event, event_id)
        e.clip_path, e.clip_status = (str(path), "ready") if ok else (None, "failed")
        db.commit()
