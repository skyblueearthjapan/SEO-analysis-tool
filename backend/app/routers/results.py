"""
Results router - 解析結果・レポートAPI
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.db_models import AIReport, AnalysisResult, Site
from app.models.schemas import (
    AnalysisResultListItem,
    AnalysisResultListResponse,
    AnalysisResultResponse,
    ReportRegenerateRequest,
    ReportRegenerateResponse,
    ReportResponse,
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


@router.get("", response_model=AnalysisResultListResponse)
async def list_analysis_results(
    site_id: UUID,
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
) -> AnalysisResultListResponse:
    """List analysis results for a site"""
    await get_site_or_404(db, site_id)

    result = await db.execute(
        select(AnalysisResult)
        .where(AnalysisResult.site_id == site_id)
        .order_by(AnalysisResult.generated_at.desc())
        .limit(limit)
    )
    results = result.scalars().all()

    return AnalysisResultListResponse(
        items=[
            AnalysisResultListItem(
                result_id=r.result_id,
                job_id=r.job_id,
                generated_at=r.generated_at,
                diagnosis_main_cause=r.diagnosis_main_cause
            )
            for r in results
        ]
    )


@router.get("/{result_id}", response_model=AnalysisResultResponse)
async def get_analysis_result(
    site_id: UUID,
    result_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> AnalysisResultResponse:
    """Get a single analysis result with full JSON"""
    await get_site_or_404(db, site_id)

    result = await db.execute(
        select(AnalysisResult).where(
            AnalysisResult.site_id == site_id,
            AnalysisResult.result_id == result_id
        )
    )
    analysis_result = result.scalar_one_or_none()

    if analysis_result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Result not found: {result_id}"
        )

    return AnalysisResultResponse(
        result_id=analysis_result.result_id,
        job_id=analysis_result.job_id,
        generated_at=analysis_result.generated_at,
        analysis_json=analysis_result.analysis_json
    )


@router.get("/{result_id}/report", response_model=ReportResponse)
async def get_report(
    site_id: UUID,
    result_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> ReportResponse:
    """Get the AI-generated report for a result"""
    await get_site_or_404(db, site_id)

    # Check result exists
    result = await db.execute(
        select(AnalysisResult).where(
            AnalysisResult.site_id == site_id,
            AnalysisResult.result_id == result_id
        )
    )
    analysis_result = result.scalar_one_or_none()

    if analysis_result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Result not found: {result_id}"
        )

    # Get latest report
    report_result = await db.execute(
        select(AIReport)
        .where(AIReport.result_id == result_id)
        .order_by(AIReport.created_at.desc())
        .limit(1)
    )
    report = report_result.scalar_one_or_none()

    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report not found for result: {result_id}"
        )

    return ReportResponse(
        result_id=result_id,
        report_markdown=report.report_markdown
    )


@router.get("/{result_id}/todos/{todo_id}")
async def get_todo_detail(
    site_id: UUID,
    result_id: UUID,
    todo_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get a single todo with its detail from the analysis result"""
    await get_site_or_404(db, site_id)

    result = await db.execute(
        select(AnalysisResult).where(
            AnalysisResult.site_id == site_id,
            AnalysisResult.result_id == result_id
        )
    )
    analysis_result = result.scalar_one_or_none()

    if analysis_result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Result not found: {result_id}"
        )

    # Find todo in analysis_json
    todos = analysis_result.analysis_json.get("todos", [])
    todo = None
    for t in todos:
        if t.get("todo_id") == todo_id:
            todo = t
            break

    if todo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Todo not found: {todo_id}"
        )

    return {"todo": todo}


@router.post("/{result_id}/report/regenerate", response_model=ReportRegenerateResponse)
async def regenerate_report(
    site_id: UUID,
    result_id: UUID,
    request: Optional[ReportRegenerateRequest] = None,
    db: AsyncSession = Depends(get_db)
) -> ReportRegenerateResponse:
    """Regenerate the AI report for a result"""
    await get_site_or_404(db, site_id)

    # Check result exists
    result = await db.execute(
        select(AnalysisResult)
        .options(selectinload(AnalysisResult.job))
        .where(
            AnalysisResult.site_id == site_id,
            AnalysisResult.result_id == result_id
        )
    )
    analysis_result = result.scalar_one_or_none()

    if analysis_result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Result not found: {result_id}"
        )

    # Get ai_prompt_payload from analysis_json
    analysis_json = analysis_result.analysis_json
    ai_payload = analysis_json.get("ai_prompt_payload")

    if ai_payload is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No AI prompt payload in analysis result"
        )

    # Override report style if provided
    if request and request.report_style:
        ai_payload["report_style"] = request.report_style

    # Generate new report
    from app.services.ai_reporter import generate_report_md
    from app.config import get_thresholds

    cfg = get_thresholds()
    report_md = await generate_report_md(ai_payload, cfg)

    # Save new report
    new_report = AIReport(
        result_id=result_id,
        job_id=analysis_result.job_id,
        report_markdown=report_md,
        model_name="gpt-4o",  # or anthropic model
        prompt_version="1.0"
    )
    db.add(new_report)
    await db.flush()
    await db.refresh(new_report)

    return ReportRegenerateResponse(
        ok=True,
        report_id=new_report.report_id
    )
