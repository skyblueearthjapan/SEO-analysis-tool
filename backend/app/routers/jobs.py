"""
Analysis Jobs router - 解析ジョブ管理API
"""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.db_models import AnalysisJob, AnalysisJobTarget, Page, Site
from app.models.schemas import (
    AnalysisJobCreate,
    AnalysisJobListResponse,
    AnalysisJobResponse,
    AnalysisJobRunResponse,
    AnalysisJobTarget as AnalysisJobTargetSchema,
)

router = APIRouter()


async def get_site_or_404(db: AsyncSession, site_id: UUID) -> Site:
    """Helper to get site or raise 404"""
    result = await db.execute(
        select(Site).where(Site.site_id == site_id)
    )
    site = result.scalar_one_or_none()
    if site is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Site not found: {site_id}"
        )
    return site


async def run_analysis_job_async(job_id: UUID, db_url: str):
    """Background task to run analysis job"""
    # Import here to avoid circular imports
    from app.services.analysis_pipeline import run_analysis_job
    await run_analysis_job(job_id, db_url)


@router.post("", response_model=AnalysisJobResponse, status_code=status.HTTP_201_CREATED)
async def create_analysis_job(
    site_id: UUID,
    job_in: AnalysisJobCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
) -> AnalysisJobResponse:
    """Create a new analysis job"""
    await get_site_or_404(db, site_id)

    # Validate targets exist
    page_ids = [t.page_id for t in job_in.targets]
    result = await db.execute(
        select(Page).where(
            Page.site_id == site_id,
            Page.page_id.in_(page_ids)
        )
    )
    found_pages = {p.page_id for p in result.scalars().all()}
    missing = set(page_ids) - found_pages
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Pages not found: {list(missing)}"
        )

    # Validate: exactly 1 official, at most 2 competitors
    official_count = sum(1 for t in job_in.targets if t.role.value == "official")
    competitor_count = sum(1 for t in job_in.targets if t.role.value == "competitor")

    if official_count != 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Exactly 1 official page is required"
        )
    if competitor_count > 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At most 2 competitor pages are allowed"
        )

    # Create job
    job = AnalysisJob(
        site_id=site_id,
        device=job_in.device.value,
        locale=job_in.locale,
        target_country=job_in.target_country,
        enable_pagespeed=job_in.enable_pagespeed,
        enable_gsc=job_in.enable_gsc,
        enable_ai_report=job_in.enable_ai_report,
        gsc_property=job_in.gsc_property,
        brand_terms=job_in.brand_terms,
        status="queued"
    )
    db.add(job)
    await db.flush()

    # Add targets
    for target in job_in.targets:
        job_target = AnalysisJobTarget(
            job_id=job.job_id,
            page_id=target.page_id,
            role=target.role.value,
            sort_order=target.sort_order
        )
        db.add(job_target)

    await db.commit()
    await db.refresh(job)

    # Queue background task
    from app.config import get_settings
    settings = get_settings()
    background_tasks.add_task(run_analysis_job_async, job.job_id, settings.database_url)

    return AnalysisJobResponse(
        job_id=job.job_id,
        site_id=job.site_id,
        status=job.status,
        error_message=job.error_message,
        created_at=job.created_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
        targets=[
            AnalysisJobTargetSchema(
                page_id=t.page_id,
                role=t.role,
                sort_order=t.sort_order
            )
            for t in job_in.targets
        ]
    )


@router.get("", response_model=AnalysisJobListResponse)
async def list_analysis_jobs(
    site_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> AnalysisJobListResponse:
    """List all analysis jobs for a site"""
    await get_site_or_404(db, site_id)

    result = await db.execute(
        select(AnalysisJob)
        .where(AnalysisJob.site_id == site_id)
        .order_by(AnalysisJob.created_at.desc())
    )
    jobs = result.scalars().all()

    return AnalysisJobListResponse(
        items=[
            AnalysisJobResponse(
                job_id=job.job_id,
                site_id=job.site_id,
                status=job.status,
                error_message=job.error_message,
                created_at=job.created_at,
                started_at=job.started_at,
                finished_at=job.finished_at
            )
            for job in jobs
        ]
    )


@router.get("/{job_id}", response_model=AnalysisJobResponse)
async def get_analysis_job(
    site_id: UUID,
    job_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> AnalysisJobResponse:
    """Get a single analysis job with targets"""
    await get_site_or_404(db, site_id)

    result = await db.execute(
        select(AnalysisJob)
        .options(selectinload(AnalysisJob.targets))
        .where(
            AnalysisJob.site_id == site_id,
            AnalysisJob.job_id == job_id
        )
    )
    job = result.scalar_one_or_none()

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job not found: {job_id}"
        )

    return AnalysisJobResponse(
        job_id=job.job_id,
        site_id=job.site_id,
        status=job.status,
        error_message=job.error_message,
        created_at=job.created_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
        targets=[
            AnalysisJobTargetSchema(
                page_id=t.page_id,
                role=t.role,
                sort_order=t.sort_order
            )
            for t in sorted(job.targets, key=lambda x: x.sort_order)
        ]
    )


@router.post("/{job_id}/run", response_model=AnalysisJobRunResponse)
async def run_analysis_job(
    site_id: UUID,
    job_id: UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
) -> AnalysisJobRunResponse:
    """Trigger execution of an analysis job"""
    await get_site_or_404(db, site_id)

    result = await db.execute(
        select(AnalysisJob).where(
            AnalysisJob.site_id == site_id,
            AnalysisJob.job_id == job_id
        )
    )
    job = result.scalar_one_or_none()

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job not found: {job_id}"
        )

    if job.status not in ["queued", "failed"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job cannot be run in status: {job.status}"
        )

    # Reset status if failed
    job.status = "queued"
    job.error_message = None
    await db.flush()

    # Queue background task
    from app.config import get_settings
    settings = get_settings()
    background_tasks.add_task(run_analysis_job_async, job.job_id, settings.database_url)

    return AnalysisJobRunResponse(ok=True)
