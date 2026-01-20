"""
Progress Tracking Service - 成果トラッキング (Appendix AC)

Before/After比較、進捗スナップショット保存、時系列データ取得
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import (
    ProgressSnapshot,
    SerpTimeSeries,
    CrawlErrorTimeSeries,
    BacklinkTimeSeries,
)


async def save_progress_snapshot(
    db: AsyncSession,
    site_id: UUID,
    result_id: Optional[UUID],
    snapshot_type: str,
    metrics: Dict[str, Any],
) -> ProgressSnapshot:
    """
    Save a progress snapshot after analysis

    Args:
        db: Database session
        site_id: Site UUID
        result_id: Analysis result UUID
        snapshot_type: Type of snapshot (before, after, periodic)
        metrics: Metrics dictionary

    Returns:
        Created ProgressSnapshot
    """
    snapshot = ProgressSnapshot(
        site_id=site_id,
        result_id=result_id,
        snapshot_type=snapshot_type,
        pagespeed_score=metrics.get("pagespeed", {}).get("performance_score"),
        intent_missing_count=metrics.get("content", {}).get("intent_missing_count"),
        avg_position=metrics.get("gsc", {}).get("avg_position"),
        ctr=metrics.get("gsc", {}).get("ctr"),
        todo_total=metrics.get("todos", {}).get("total"),
        todo_done=metrics.get("todos", {}).get("done"),
        metrics_json=metrics,
    )
    db.add(snapshot)
    await db.flush()
    await db.refresh(snapshot)
    return snapshot


def extract_metrics_from_result(analysis_json: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract trackable metrics from analysis result

    Args:
        analysis_json: Full analysis result JSON

    Returns:
        Metrics dictionary for progress tracking
    """
    pages = analysis_json.get("pages", [])
    official = None
    for p in pages:
        if p.get("page_type") == "official_homepage":
            official = p
            break

    if not official:
        return {}

    tech = official.get("tech", {})
    content = official.get("content", {})
    html = official.get("html", {})
    gsc = official.get("search_console", {})
    pagespeed = tech.get("pagespeed", {})

    # Count missing intents
    intent_coverage = content.get("intent_coverage", {})
    missing_count = sum(1 for v in intent_coverage.values() if v == 0)

    # Count todos
    todos = analysis_json.get("todos", [])
    todo_total = len(todos)
    todo_done = 0  # Not tracked in initial analysis

    return {
        "pagespeed": {
            "performance_score": pagespeed.get("performance_score"),
            "lcp_ms": pagespeed.get("lcp_ms"),
            "inp_ms": pagespeed.get("inp_ms"),
            "cls": pagespeed.get("cls"),
        },
        "content": {
            "intent_missing_count": missing_count,
            "word_count": html.get("text_stats", {}).get("text_length_words_est", 0),
            "h2_count": len(html.get("headings", {}).get("h2", [])),
        },
        "schema": {
            "has_faq": html.get("structured_data", {}).get("has_faq_schema", False),
            "has_organization": html.get("structured_data", {}).get("has_organization_schema", False),
        },
        "gsc": {
            "impressions": _sum_gsc_metric(gsc, "impressions"),
            "clicks": _sum_gsc_metric(gsc, "clicks"),
            "ctr": gsc.get("brand_query_summary", {}).get("brand_ctr"),
            "avg_position": _avg_gsc_position(gsc),
        },
        "todos": {
            "total": todo_total,
            "done": todo_done,
        },
    }


def _sum_gsc_metric(gsc: Dict[str, Any], metric: str) -> Optional[int]:
    """Sum a metric from GSC top queries"""
    if not gsc.get("available"):
        return None
    top_queries = gsc.get("top_queries", [])
    if not top_queries:
        return None
    return sum(q.get(metric, 0) for q in top_queries)


def _avg_gsc_position(gsc: Dict[str, Any]) -> Optional[float]:
    """Calculate average position from GSC top queries"""
    if not gsc.get("available"):
        return None
    top_queries = gsc.get("top_queries", [])
    if not top_queries:
        return None
    positions = [q.get("position") for q in top_queries if q.get("position") is not None]
    if not positions:
        return None
    return round(sum(positions) / len(positions), 2)


async def get_progress_comparison(
    db: AsyncSession,
    site_id: UUID,
) -> Optional[Dict[str, Any]]:
    """
    Get baseline vs current comparison

    Args:
        db: Database session
        site_id: Site UUID

    Returns:
        Comparison dictionary with baseline, current, and diff
    """
    # Get baseline (first snapshot)
    baseline_result = await db.execute(
        select(ProgressSnapshot)
        .where(ProgressSnapshot.site_id == site_id)
        .order_by(ProgressSnapshot.created_at.asc())
        .limit(1)
    )
    baseline = baseline_result.scalar_one_or_none()

    # Get current (latest snapshot)
    current_result = await db.execute(
        select(ProgressSnapshot)
        .where(ProgressSnapshot.site_id == site_id)
        .order_by(ProgressSnapshot.created_at.desc())
        .limit(1)
    )
    current = current_result.scalar_one_or_none()

    if not baseline or not current:
        return None

    # If same snapshot, return None
    if baseline.id == current.id:
        return None

    # Calculate diff
    diff = calculate_diff(baseline.metrics_json or {}, current.metrics_json or {})

    return {
        "baseline": {
            "id": str(baseline.id),
            "captured_at": baseline.created_at.isoformat(),
            "metrics": baseline.metrics_json or {},
        },
        "current": {
            "id": str(current.id),
            "captured_at": current.created_at.isoformat(),
            "metrics": current.metrics_json or {},
        },
        "diff": diff,
    }


def calculate_diff(baseline: Dict[str, Any], current: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate metric differences between baseline and current

    Args:
        baseline: Baseline metrics
        current: Current metrics

    Returns:
        Dictionary of differences
    """
    diff: Dict[str, Any] = {}

    # PageSpeed score
    b_ps = baseline.get("pagespeed", {}).get("performance_score")
    c_ps = current.get("pagespeed", {}).get("performance_score")
    if b_ps is not None and c_ps is not None:
        diff["pagespeed_score"] = c_ps - b_ps

    # LCP
    b_lcp = baseline.get("pagespeed", {}).get("lcp_ms")
    c_lcp = current.get("pagespeed", {}).get("lcp_ms")
    if b_lcp is not None and c_lcp is not None:
        diff["lcp_ms"] = c_lcp - b_lcp

    # Intent missing count
    b_im = baseline.get("content", {}).get("intent_missing_count", 0)
    c_im = current.get("content", {}).get("intent_missing_count", 0)
    diff["intent_missing"] = c_im - b_im

    # H2 count
    b_h2 = baseline.get("content", {}).get("h2_count", 0)
    c_h2 = current.get("content", {}).get("h2_count", 0)
    diff["h2_count"] = c_h2 - b_h2

    # CTR
    b_ctr = baseline.get("gsc", {}).get("ctr")
    c_ctr = current.get("gsc", {}).get("ctr")
    if b_ctr is not None and c_ctr is not None:
        diff["ctr"] = round(c_ctr - b_ctr, 4)

    # Avg Position (lower is better, so negative diff is good)
    b_pos = baseline.get("gsc", {}).get("avg_position")
    c_pos = current.get("gsc", {}).get("avg_position")
    if b_pos is not None and c_pos is not None:
        diff["avg_position"] = round(c_pos - b_pos, 2)

    # Impressions
    b_imp = baseline.get("gsc", {}).get("impressions")
    c_imp = current.get("gsc", {}).get("impressions")
    if b_imp is not None and c_imp is not None:
        diff["impressions"] = c_imp - b_imp

    # Clicks
    b_clk = baseline.get("gsc", {}).get("clicks")
    c_clk = current.get("gsc", {}).get("clicks")
    if b_clk is not None and c_clk is not None:
        diff["clicks"] = c_clk - b_clk

    # ToDo completion
    b_todo = baseline.get("todos", {}).get("total", 0)
    c_todo = current.get("todos", {}).get("total", 0)
    diff["todo_total"] = c_todo - b_todo

    return diff


async def get_snapshot_history(
    db: AsyncSession,
    site_id: UUID,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """
    Get snapshot history for a site

    Args:
        db: Database session
        site_id: Site UUID
        limit: Maximum number of snapshots to return

    Returns:
        List of snapshot dictionaries
    """
    result = await db.execute(
        select(ProgressSnapshot)
        .where(ProgressSnapshot.site_id == site_id)
        .order_by(ProgressSnapshot.created_at.desc())
        .limit(limit)
    )
    snapshots = result.scalars().all()

    return [
        {
            "id": str(s.id),
            "result_id": str(s.result_id) if s.result_id else None,
            "snapshot_type": s.snapshot_type,
            "pagespeed_score": s.pagespeed_score,
            "intent_missing_count": s.intent_missing_count,
            "avg_position": s.avg_position,
            "ctr": s.ctr,
            "todo_total": s.todo_total,
            "todo_done": s.todo_done,
            "created_at": s.created_at.isoformat(),
        }
        for s in snapshots
    ]


# ============================================================
# Time Series Functions (Appendix AD, AE, AF)
# ============================================================

async def save_serp_timeseries(
    db: AsyncSession,
    site_id: UUID,
    query: str,
    position: float,
    url: Optional[str] = None,
    device: str = "mobile",
) -> SerpTimeSeries:
    """Save SERP ranking time series data (Appendix AD)"""
    record = SerpTimeSeries(
        site_id=site_id,
        query=query,
        position=position,
        url=url,
        device=device,
    )
    db.add(record)
    await db.flush()
    return record


async def get_serp_timeseries(
    db: AsyncSession,
    site_id: UUID,
    query: Optional[str] = None,
    days: int = 30,
) -> List[Dict[str, Any]]:
    """Get SERP ranking time series data"""
    from datetime import timedelta

    cutoff = datetime.utcnow() - timedelta(days=days)

    stmt = (
        select(SerpTimeSeries)
        .where(
            and_(
                SerpTimeSeries.site_id == site_id,
                SerpTimeSeries.recorded_date >= cutoff,
            )
        )
        .order_by(SerpTimeSeries.recorded_date.asc())
    )

    if query:
        stmt = stmt.where(SerpTimeSeries.query == query)

    result = await db.execute(stmt)
    records = result.scalars().all()

    return [
        {
            "id": str(r.id),
            "query": r.query,
            "position": r.position,
            "url": r.url,
            "device": r.device,
            "recorded_date": r.recorded_date.isoformat(),
        }
        for r in records
    ]


async def save_crawl_error_timeseries(
    db: AsyncSession,
    site_id: UUID,
    error_type: str,
    error_count: int,
    sample_urls: Optional[List[str]] = None,
) -> CrawlErrorTimeSeries:
    """Save crawl error time series data (Appendix AE)"""
    record = CrawlErrorTimeSeries(
        site_id=site_id,
        error_type=error_type,
        error_count=error_count,
        sample_urls=sample_urls,
    )
    db.add(record)
    await db.flush()
    return record


async def get_crawl_error_timeseries(
    db: AsyncSession,
    site_id: UUID,
    days: int = 30,
) -> List[Dict[str, Any]]:
    """Get crawl error time series data"""
    from datetime import timedelta

    cutoff = datetime.utcnow() - timedelta(days=days)

    result = await db.execute(
        select(CrawlErrorTimeSeries)
        .where(
            and_(
                CrawlErrorTimeSeries.site_id == site_id,
                CrawlErrorTimeSeries.recorded_date >= cutoff,
            )
        )
        .order_by(CrawlErrorTimeSeries.recorded_date.asc())
    )
    records = result.scalars().all()

    return [
        {
            "id": str(r.id),
            "error_type": r.error_type,
            "error_count": r.error_count,
            "sample_urls": r.sample_urls,
            "recorded_date": r.recorded_date.isoformat(),
        }
        for r in records
    ]


async def save_backlink_timeseries(
    db: AsyncSession,
    site_id: UUID,
    total_backlinks: int,
    referring_domains: int,
    new_backlinks: Optional[int] = None,
    lost_backlinks: Optional[int] = None,
) -> BacklinkTimeSeries:
    """Save backlink time series data (Appendix AF)"""
    record = BacklinkTimeSeries(
        site_id=site_id,
        total_backlinks=total_backlinks,
        referring_domains=referring_domains,
        new_backlinks=new_backlinks,
        lost_backlinks=lost_backlinks,
    )
    db.add(record)
    await db.flush()
    return record


async def get_backlink_timeseries(
    db: AsyncSession,
    site_id: UUID,
    days: int = 30,
) -> List[Dict[str, Any]]:
    """Get backlink time series data"""
    from datetime import timedelta

    cutoff = datetime.utcnow() - timedelta(days=days)

    result = await db.execute(
        select(BacklinkTimeSeries)
        .where(
            and_(
                BacklinkTimeSeries.site_id == site_id,
                BacklinkTimeSeries.recorded_date >= cutoff,
            )
        )
        .order_by(BacklinkTimeSeries.recorded_date.asc())
    )
    records = result.scalars().all()

    return [
        {
            "id": str(r.id),
            "total_backlinks": r.total_backlinks,
            "referring_domains": r.referring_domains,
            "new_backlinks": r.new_backlinks,
            "lost_backlinks": r.lost_backlinks,
            "recorded_date": r.recorded_date.isoformat(),
        }
        for r in records
    ]
