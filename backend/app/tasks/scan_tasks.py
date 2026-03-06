"""
DorkRaptor Celery Task Worker
Background processing for reconnaissance scans
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional
import uuid

from celery import Celery
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.scan import Scan
from app.models.finding import Finding
from app.dorks.database import get_all_dorks
from app.services.search_engine import SearchOrchestrator
from app.services.ai_analyzer import analyze_with_ai
from app.services.github_scanner import GitHubLeakScanner, CloudExposureScanner

logger = logging.getLogger(__name__)

celery_app = Celery(
    "dorkraptor",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    broker_connection_retry_on_startup=True,
)

VALID_SEVERITIES = {"critical", "high", "medium", "low", "info"}
VALID_CATEGORIES = {
    "sensitive_files", "admin_panels", "directory_listings", "backup_files",
    "config_files", "credentials", "documents", "database_dumps",
    "cloud_storage", "github_leaks", "api_endpoints", "other"
}
VALID_SOURCES = {"google", "bing", "duckduckgo", "yandex", "github", "cloud_scan"}


def make_session_factory():
    """
    Create a brand-new engine + session factory bound to the CURRENT event loop.
    Must be called from inside the async context (after the loop is created).
    """
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
        # Keep the pool small — this engine is per-task and will be disposed
        pool_size=2,
        max_overflow=0,
    )
    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return engine, factory


def run_async(coro):
    """Run an async coroutine in a brand-new event loop (Celery workers are sync)."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()
        asyncio.set_event_loop(None)


@celery_app.task(bind=True, name="tasks.run_scan", max_retries=2)
def run_scan_task(self, scan_id: str, openai_key: Optional[str] = None, github_token: Optional[str] = None):
    logger.info(f"Starting scan task for scan_id: {scan_id}")
    try:
        run_async(_execute_scan(scan_id, openai_key, github_token))
    except Exception as e:
        logger.error(f"Scan task failed: {e}")
        try:
            run_async(_mark_scan_failed(scan_id, str(e)))
        except Exception:
            pass
        raise


async def _execute_scan(scan_id: str, openai_key: Optional[str], github_token: Optional[str]):
    # Engine + session factory created HERE — inside the fresh event loop
    engine, SessionLocal = make_session_factory()

    try:
        async with SessionLocal() as db:
            result = await db.execute(select(Scan).where(Scan.id == uuid.UUID(scan_id)))
            scan = result.scalar_one_or_none()

            if not scan:
                logger.error(f"Scan {scan_id} not found")
                return

            domain = scan.domain
            scan.status = "running"
            scan.started_at = datetime.now(timezone.utc)
            await db.commit()

            try:
                all_findings = []
                seen_urls = set()

                # === Phase 1: Dork Scanning ===
                logger.info(f"Phase 1: Dork scanning for {domain}")
                dorks = get_all_dorks(domain)
                scan.dorks_total = len(dorks)
                await db.commit()

                orchestrator = SearchOrchestrator()
                batch_size = 5
                for i in range(0, min(len(dorks), 100), batch_size):
                    batch = dorks[i:i + batch_size]
                    tasks = [orchestrator.search_all_engines(d["query"]) for d in batch]
                    results_batch = await asyncio.gather(*tasks, return_exceptions=True)

                    for dork_info, search_results in zip(batch, results_batch):
                        if isinstance(search_results, list):
                            for r in search_results:
                                if r.url not in seen_urls:
                                    seen_urls.add(r.url)
                                    all_findings.append({
                                        "url": r.url,
                                        "title": r.title,
                                        "snippet": r.snippet,
                                        "dork_query": dork_info["query"],
                                        "source": r.engine,
                                        "category": dork_info["category"],
                                    })

                    scan.dorks_executed = i + len(batch)
                    await db.commit()

                # === Phase 2: GitHub Leak Detection ===
                logger.info(f"Phase 2: GitHub scan for {domain}")
                try:
                    github_scanner = GitHubLeakScanner(token=github_token)
                    github_findings = await github_scanner.scan_domain(domain)
                    for f in github_findings:
                        if f["url"] not in seen_urls:
                            seen_urls.add(f["url"])
                            all_findings.append(f)
                except Exception as e:
                    logger.warning(f"GitHub scan error: {e}")

                # === Phase 3: Cloud Exposure ===
                logger.info(f"Phase 3: Cloud scan for {domain}")
                try:
                    cloud_scanner = CloudExposureScanner()
                    cloud_findings = await cloud_scanner.scan_domain(domain)
                    for f in cloud_findings:
                        if f["url"] not in seen_urls:
                            seen_urls.add(f["url"])
                            all_findings.append(f)
                except Exception as e:
                    logger.warning(f"Cloud scan error: {e}")

                # === Phase 4: AI Analysis ===
                logger.info(f"Phase 4: AI analysis of {len(all_findings)} findings")
                if all_findings:
                    all_findings = await analyze_with_ai(all_findings, domain, openai_key)

                # === Phase 5: Save to DB ===
                severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}

                for fd in all_findings:
                    sev = fd.get("severity", "info").lower()
                    cat = fd.get("category", "other").lower()
                    src = fd.get("source", "bing").lower()

                    if sev not in VALID_SEVERITIES:
                        sev = "info"
                    if cat not in VALID_CATEGORIES:
                        cat = "other"
                    if src not in VALID_SOURCES:
                        src = "bing"

                    finding = Finding(
                        scan_id=uuid.UUID(scan_id),
                        url=fd["url"],
                        title=fd.get("title", ""),
                        snippet=fd.get("snippet", ""),
                        dork_query=fd.get("dork_query", ""),
                        source=src,
                        category=cat,
                        severity=sev,
                        ai_explanation=fd.get("ai_explanation", ""),
                    )
                    db.add(finding)
                    severity_counts[sev] = severity_counts.get(sev, 0) + 1

                scan.status = "completed"
                scan.completed_at = datetime.now(timezone.utc)
                scan.total_findings = len(all_findings)
                scan.critical_count = severity_counts["critical"]
                scan.high_count = severity_counts["high"]
                scan.medium_count = severity_counts["medium"]
                scan.low_count = severity_counts["low"]
                scan.info_count = severity_counts["info"]
                await db.commit()
                logger.info(f"Scan {scan_id} completed with {len(all_findings)} findings")

            except Exception as e:
                logger.error(f"Scan execution error: {e}", exc_info=True)
                scan.status = "failed"
                scan.error_message = str(e)
                scan.completed_at = datetime.now(timezone.utc)
                await db.commit()
                raise
    finally:
        await engine.dispose()


async def _mark_scan_failed(scan_id: str, error: str):
    engine, SessionLocal = make_session_factory()
    try:
        async with SessionLocal() as db:
            result = await db.execute(select(Scan).where(Scan.id == uuid.UUID(scan_id)))
            scan = result.scalar_one_or_none()
            if scan:
                scan.status = "failed"
                scan.error_message = error
                scan.completed_at = datetime.now(timezone.utc)
                await db.commit()
    finally:
        await engine.dispose()
