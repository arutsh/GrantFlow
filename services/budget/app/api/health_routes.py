from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}
