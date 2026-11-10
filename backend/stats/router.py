from fastapi import APIRouter, Depends

from core.dependencies import require_admin
from stats import service

router = APIRouter(prefix="/api/stats", tags=["Stats"])


@router.get("/summary")
def summary(_admin: dict = Depends(require_admin)):
    return service.booking_summary()
