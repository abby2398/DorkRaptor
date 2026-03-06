from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel, validator
from typing import Optional, List
import uuid
import re

from app.core.database import get_db
from app.models.scan import Scan

router = APIRouter()


class ScanCreate(BaseModel):
    domain: str
    openai_key: Optional[str] = None
    github_token: Optional[str] = None
    modules: Optional[List[str]] = ["dorks", "github", "cloud"]

    @validator("domain")
    def validate_domain(cls, v):
        v = v.strip().lower()
        v = re.sub(r'^https?://', '', v)
        v = re.sub(r'^www\.', '', v)
        v = v.split('/')[0]
        pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z]{2,})+$'
        if not re.match(pattern, v):
            raise ValueError("Invalid domain format")
        return v


@router.post("/")
async def create_scan(scan_data: ScanCreate, db: AsyncSession = Depends(get_db)):
    scan = Scan(
        domain=scan_data.domain,
        status="pending",
        scan_config={
            "modules": scan_data.modules,
            "has_openai": bool(scan_data.openai_key),
            "has_github": bool(scan_data.github_token),
        },
    )
    db.add(scan)
    await db.commit()
    await db.refresh(scan)

    try:
        from app.tasks.scan_tasks import run_scan_task
        task = run_scan_task.apply_async(
            args=[str(scan.id)],
            kwargs={
                "openai_key": scan_data.openai_key,
                "github_token": scan_data.github_token,
            },
        )
        scan.celery_task_id = task.id
        await db.commit()
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Celery unavailable: {e}")

    return scan.to_dict()


@router.get("/")
async def list_scans(skip: int = 0, limit: int = 20, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Scan).order_by(desc(Scan.created_at)).offset(skip).limit(limit)
    )
    scans = result.scalars().all()
    return [s.to_dict() for s in scans]


@router.get("/{scan_id}")
async def get_scan(scan_id: str, db: AsyncSession = Depends(get_db)):
    try:
        scan_uuid = uuid.UUID(scan_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid scan ID")

    result = await db.execute(select(Scan).where(Scan.id == scan_uuid))
    scan = result.scalar_one_or_none()

    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    return scan.to_dict()


@router.delete("/{scan_id}")
async def delete_scan(scan_id: str, db: AsyncSession = Depends(get_db)):
    try:
        scan_uuid = uuid.UUID(scan_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid scan ID")

    result = await db.execute(select(Scan).where(Scan.id == scan_uuid))
    scan = result.scalar_one_or_none()

    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    await db.delete(scan)
    await db.commit()
    return {"message": "Scan deleted successfully"}


@router.get("/{scan_id}/progress")
async def get_scan_progress(scan_id: str, db: AsyncSession = Depends(get_db)):
    try:
        scan_uuid = uuid.UUID(scan_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid scan ID")

    result = await db.execute(select(Scan).where(Scan.id == scan_uuid))
    scan = result.scalar_one_or_none()

    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    progress = 0
    if scan.dorks_total and scan.dorks_total > 0:
        progress = min(int((scan.dorks_executed / scan.dorks_total) * 100), 95)
    if scan.status == "completed":
        progress = 100

    return {
        "scan_id": str(scan.id),
        "status": scan.status,
        "progress": progress,
        "dorks_executed": scan.dorks_executed or 0,
        "dorks_total": scan.dorks_total or 0,
        "findings_so_far": scan.total_findings or 0,
    }
