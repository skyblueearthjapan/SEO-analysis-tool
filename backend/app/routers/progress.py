"""
Progress router - 成果トラッキングAPI (Appendix AC, AD, AE, AF)
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.db_models import Site, ProgressSnapshot
from app.services.progress import (
    get_progress_comparison,
    get_snapshot_history,
    get_serp_timeseries,
    get_crawl_error_timeseries,
    get_backlink_timeseries,
    save_progress_snapshot,
    extract_metrics_from_result,
)
from app.services.story_generator import (
    generate_improvement_story,
    build_story_input_from_progress,
)
from app.services.analyzers.serp_rank_gsc_timeseries import get_serp_trend_data
from app.services.analyzers.crawl_error_timeseries import (
    get_crawl_error_trend_data,
    get_crawl_error_breakdown,
)
from app.services.analyzers.backlink_timeseries import get_backlink_trend_data

router = APIRouter()


async def get_site_or_404(db: AsyncSession, site_id: UUID) -> Site:
    """Helper to get site or raise 404"""
    result = await db.execute(select(Site).where(Site.site_id == site_id))
    site = result.scalar_one_or_none()
    if site is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Site not found: {site_id}",
        )
    return site


@router.get("/{site_id}/progress")
async def get_site_progress(
    site_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Get progress comparison for a site (Before/After)

    Returns baseline vs current metrics comparison with calculated diff.
    """
    await get_site_or_404(db, site_id)

    comparison = await get_progress_comparison(db, site_id)
    if not comparison:
        return {
            "message": "Not enough data for comparison",
            "baseline": None,
            "current": None,
            "diff": None,
        }

    return comparison


@router.get("/{site_id}/progress/history")
async def get_site_progress_history(
    site_id: UUID,
    limit: int = Query(default=10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """
    Get progress snapshot history for a site

    Returns list of snapshots ordered by date (newest first).
    """
    await get_site_or_404(db, site_id)

    history = await get_snapshot_history(db, site_id, limit)
    return {"items": history, "total": len(history)}


@router.post("/{site_id}/progress/snapshot")
async def create_progress_snapshot(
    site_id: UUID,
    result_id: Optional[UUID] = None,
    snapshot_type: str = "manual",
    db: AsyncSession = Depends(get_db),
):
    """
    Create a manual progress snapshot

    Typically called after making improvements to track progress.
    """
    await get_site_or_404(db, site_id)

    # If result_id provided, extract metrics from it
    metrics = {}
    if result_id:
        from app.models.db_models import AnalysisResult

        result = await db.execute(
            select(AnalysisResult).where(
                AnalysisResult.site_id == site_id,
                AnalysisResult.result_id == result_id,
            )
        )
        analysis_result = result.scalar_one_or_none()
        if analysis_result:
            metrics = extract_metrics_from_result(analysis_result.analysis_json)

    snapshot = await save_progress_snapshot(
        db,
        site_id=site_id,
        result_id=result_id,
        snapshot_type=snapshot_type,
        metrics=metrics,
    )
    await db.commit()

    return {
        "id": str(snapshot.id),
        "site_id": str(snapshot.site_id),
        "snapshot_type": snapshot.snapshot_type,
        "created_at": snapshot.created_at.isoformat(),
    }


@router.post("/{site_id}/progress/baseline")
async def set_baseline(
    site_id: UUID,
    snapshot_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Mark a snapshot as the baseline for comparison

    The baseline is used as the reference point for Before/After comparisons.
    """
    await get_site_or_404(db, site_id)

    # Get the snapshot
    result = await db.execute(
        select(ProgressSnapshot).where(
            ProgressSnapshot.site_id == site_id,
            ProgressSnapshot.id == snapshot_id,
        )
    )
    snapshot = result.scalar_one_or_none()

    if not snapshot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Snapshot not found: {snapshot_id}",
        )

    # Update snapshot type to baseline
    snapshot.snapshot_type = "before"
    await db.commit()

    return {
        "ok": True,
        "snapshot_id": str(snapshot.id),
        "snapshot_type": snapshot.snapshot_type,
    }


# ============================================================
# Time Series Endpoints (Appendix AD, AE, AF)
# ============================================================


@router.get("/{site_id}/serp-timeseries")
async def get_site_serp_timeseries(
    site_id: UUID,
    query: Optional[str] = None,
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    """
    Get SERP ranking time series data (Appendix AD)

    Returns position history for tracked queries.
    """
    await get_site_or_404(db, site_id)

    data = await get_serp_timeseries(db, site_id, query, days)
    return {"items": data, "total": len(data)}


@router.get("/{site_id}/crawl-errors-timeseries")
async def get_site_crawl_errors_timeseries(
    site_id: UUID,
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    """
    Get crawl error time series data (Appendix AE)

    Returns error count history by error type.
    """
    await get_site_or_404(db, site_id)

    data = await get_crawl_error_timeseries(db, site_id, days)
    return {"items": data, "total": len(data)}


@router.get("/{site_id}/backlinks-timeseries")
async def get_site_backlinks_timeseries(
    site_id: UUID,
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    """
    Get backlink time series data (Appendix AF)

    Returns backlink count history.
    """
    await get_site_or_404(db, site_id)

    data = await get_backlink_timeseries(db, site_id, days)
    return {"items": data, "total": len(data)}


# ============================================================
# Trend Data Endpoints for Charts (Appendix AG)
# ============================================================


@router.get("/{site_id}/timeseries/serp")
async def get_serp_trend(
    site_id: UUID,
    query: Optional[str] = None,
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    """
    Get SERP trend data for charts (Appendix AG)

    Returns aggregated daily position data ready for Recharts.
    """
    await get_site_or_404(db, site_id)

    data = await get_serp_trend_data(db, site_id, query, days)
    return {"series": data, "query": query}


@router.get("/{site_id}/timeseries/crawl-errors")
async def get_crawl_error_trend(
    site_id: UUID,
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    """
    Get crawl error trend data for charts (Appendix AG)

    Returns daily error counts by type ready for Recharts.
    """
    await get_site_or_404(db, site_id)

    data = await get_crawl_error_trend_data(db, site_id, days)
    breakdown = await get_crawl_error_breakdown(db, site_id, days)
    return {"series": data, "breakdown": breakdown}


@router.get("/{site_id}/timeseries/backlinks")
async def get_backlink_trend(
    site_id: UUID,
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    """
    Get backlink trend data for charts (Appendix AG)

    Returns daily backlink metrics ready for Recharts.
    """
    await get_site_or_404(db, site_id)

    data = await get_backlink_trend_data(db, site_id, days)
    return {"series": data}


# ============================================================
# Improvement Story (Appendix AI)
# ============================================================


@router.get("/{site_id}/story")
async def get_improvement_story(
    site_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Generate improvement story for the site (Appendix AI)

    Returns a markdown narrative describing the improvements made
    and the observed changes in metrics.
    """
    site = await get_site_or_404(db, site_id)

    # Get progress comparison
    comparison = await get_progress_comparison(db, site_id)

    if not comparison or not comparison.get("baseline") or not comparison.get("current"):
        return {
            "site_id": str(site_id),
            "story_markdown": "## 改善レポート\n\nまだ比較データがありません。複数回の解析を実行すると、改善ストーリーが生成されます。",
        }

    # Build story input from progress data
    story_input = build_story_input_from_progress(
        baseline=comparison.get("baseline"),
        current=comparison.get("current"),
        completed_todos=[],  # TODO: Get completed todos from DB
        site_name=site.name,
        url="",
    )

    # Generate story
    story = generate_improvement_story(story_input)

    return {
        "site_id": str(site_id),
        "range": {
            "from": story_input.range_from,
            "to": story_input.range_to,
        },
        "story_markdown": story,
    }
