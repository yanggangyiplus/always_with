import json
from pathlib import Path

from fastapi import APIRouter, Depends

from app.api.deps import current_user

router = APIRouter(prefix="/api")
METRICS = Path(__file__).resolve().parents[3] / "results" / "metrics.json"


@router.get("/reports/model", dependencies=[Depends(current_user)])
def model_report():
    if not METRICS.is_file():
        return {"evaluated": False, "message": "아직 모델 평가를 실시하지 않았습니다"}
    return {"evaluated": True, **json.loads(METRICS.read_text())}
