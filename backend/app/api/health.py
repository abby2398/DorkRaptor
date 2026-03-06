from fastapi import APIRouter
from app.dorks.database import get_total_dork_count

router = APIRouter()


@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "DorkRaptor",
        "version": "1.0.0",
        "dork_database_size": get_total_dork_count(),
    }
