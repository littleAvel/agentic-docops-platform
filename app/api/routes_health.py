from fastapi import APIRouter

router = APIRouter(tags=["health"])

@router.get("/")
def root():
    return {"service": "docops", "version": "0.1.0"}

@router.get("/health")
def health():
    return {"status": "ok"}

@router.get("/ready")
def ready():
    return {"ready": True}
