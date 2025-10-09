from fastapi import APIRouter

router = APIRouter(prefix="/ultra", tags=["Ultra"])

@router.get("/health")
def ultra_health():
    return {"status": "ultra working"}
