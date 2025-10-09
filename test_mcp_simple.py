from fastapi import APIRouter

test_router = APIRouter(prefix="/test", tags=["Test"])

@test_router.get("/health")
async def test_health():
    return {"status": "test working"}
