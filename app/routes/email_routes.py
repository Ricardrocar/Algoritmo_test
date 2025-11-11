from fastapi import APIRouter
from app.core.config import get_settings

router = APIRouter(prefix="/emails", tags=["emails"])

@router.get("/health")
def health():
    return {"status": "ok"}
@router.get("/version")
def version():
    s = get_settings()
    return {"name": s.APP_NAME, "version": s.APP_VERSION}

