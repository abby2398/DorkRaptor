from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from typing import Optional
import uuid

from app.core.database import get_db
from app.models.finding import Finding
from app.models.scan import Scan

router = APIRouter()

VALID_SEVERITIES = ["critical", "high", "medium", "low", "info"]
VALID_CATEGORIES = [
    "sensitive_files", "admin_panels", "directory_listings", "backup_files",
    "config_files", "credentials", "documents", "database_dumps",
    "cloud_storage", "github_leaks", "api_endpoints", "other"
]
VALID_SOURCES = ["google", "bing", "duckduckgo", "yandex", "github", "cloud_scan"]


@router.get("/scan/{scan_id}")
async def get_scan_findings(
    scan_id: str,
    severity: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    try:
        scan_uuid = uuid.UUID(scan_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid scan ID")

    query = select(Finding).where(Finding.scan_id == scan_uuid)

    if severity and severity.lower() in VALID_SEVERITIES:
        query = query.where(Finding.severity == severity.lower())

    if category and category.lower() in VALID_CATEGORIES:
        query = query.where(Finding.category == category.lower())

    if source and source.lower() in VALID_SOURCES:
        query = query.where(Finding.source == source.lower())

    query = query.order_by(desc(Finding.discovered_at)).offset(skip).limit(limit)

    result = await db.execute(query)
    findings = result.scalars().all()
    return [f.to_dict() for f in findings]


@router.get("/scan/{scan_id}/stats")
async def get_scan_stats(scan_id: str, db: AsyncSession = Depends(get_db)):
    try:
        scan_uuid = uuid.UUID(scan_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid scan ID")

    severity_counts = {}
    for sev in VALID_SEVERITIES:
        count_result = await db.execute(
            select(func.count(Finding.id)).where(
                Finding.scan_id == scan_uuid,
                Finding.severity == sev
            )
        )
        severity_counts[sev] = count_result.scalar() or 0

    category_counts = {}
    for cat in VALID_CATEGORIES:
        count_result = await db.execute(
            select(func.count(Finding.id)).where(
                Finding.scan_id == scan_uuid,
                Finding.category == cat
            )
        )
        count = count_result.scalar() or 0
        if count > 0:
            category_counts[cat] = count

    source_counts = {}
    for src in VALID_SOURCES:
        count_result = await db.execute(
            select(func.count(Finding.id)).where(
                Finding.scan_id == scan_uuid,
                Finding.source == src
            )
        )
        count = count_result.scalar() or 0
        if count > 0:
            source_counts[src] = count

    return {
        "severity_distribution": severity_counts,
        "category_distribution": category_counts,
        "source_distribution": source_counts,
        "total": sum(severity_counts.values()),
    }


@router.get("/{finding_id}")
async def get_finding(finding_id: str, db: AsyncSession = Depends(get_db)):
    try:
        finding_uuid = uuid.UUID(finding_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid finding ID")

    result = await db.execute(select(Finding).where(Finding.id == finding_uuid))
    finding = result.scalar_one_or_none()

    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")

    return finding.to_dict()
