"""
Crawl Error Time Series Analyzer (Appendix AE)

Collects crawl error data and saves to time series for trend tracking.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import CrawlErrorTimeSeries


@dataclass
class CrawlErrorCollectionResult:
    """Result of crawl error time series collection"""
    success: bool
    records_saved: int
    error: Optional[str] = None


async def collect_crawl_errors(
    db: AsyncSession,
    site_id: UUID,
    pages: List[Dict[str, Any]],
) -> CrawlErrorCollectionResult:
    """
    Collect crawl error data from analysis pages and save to time series.

    This extracts HTTP errors, redirect issues, and other crawl problems
    from the analysis result and saves them for trend tracking.

    Args:
        db: Database session
        site_id: Site UUID
        pages: List of analyzed pages (from analysis_result["pages"])

    Returns:
        CrawlErrorCollectionResult with success status and record count
    """
    try:
        # Aggregate errors by type
        error_counts: Dict[str, int] = {}
        error_samples: Dict[str, List[str]] = {}

        for page in pages:
            fetch = page.get("fetch", {})
            url = page.get("url", "")
            status_code = fetch.get("status_code", 200)

            # Check for HTTP errors
            if status_code >= 400:
                error_type = f"http_{status_code}"
                error_counts[error_type] = error_counts.get(error_type, 0) + 1
                if error_type not in error_samples:
                    error_samples[error_type] = []
                if len(error_samples[error_type]) < 5:
                    error_samples[error_type].append(url)

            # Check for redirect issues (too many redirects)
            redirect_chain = fetch.get("redirect_chain", [])
            if len(redirect_chain) > 3:
                error_type = "redirect_chain_long"
                error_counts[error_type] = error_counts.get(error_type, 0) + 1
                if error_type not in error_samples:
                    error_samples[error_type] = []
                if len(error_samples[error_type]) < 5:
                    error_samples[error_type].append(url)

            # Check for robots/noindex issues
            html = page.get("html", {})
            robots_meta = html.get("robots_meta", "")
            if "noindex" in robots_meta.lower():
                error_type = "noindex"
                error_counts[error_type] = error_counts.get(error_type, 0) + 1
                if error_type not in error_samples:
                    error_samples[error_type] = []
                if len(error_samples[error_type]) < 5:
                    error_samples[error_type].append(url)

        # Save time series records
        records_saved = 0
        for error_type, count in error_counts.items():
            record = CrawlErrorTimeSeries(
                site_id=site_id,
                error_type=error_type,
                error_count=count,
                sample_urls=error_samples.get(error_type, []),
                recorded_date=datetime.utcnow(),
            )
            db.add(record)
            records_saved += 1

        if records_saved > 0:
            await db.flush()

        return CrawlErrorCollectionResult(
            success=True,
            records_saved=records_saved,
        )

    except Exception as e:
        return CrawlErrorCollectionResult(
            success=False,
            records_saved=0,
            error=str(e),
        )


async def get_crawl_error_trend_data(
    db: AsyncSession,
    site_id: UUID,
    days: int = 30,
) -> List[Dict[str, Any]]:
    """
    Get crawl error trend data for charting.

    Args:
        db: Database session
        site_id: Site UUID
        days: Number of days to look back

    Returns:
        List of data points for trend chart
    """
    from datetime import timedelta
    from sqlalchemy import select, and_, func

    cutoff = datetime.utcnow() - timedelta(days=days)

    # Group by date and sum error counts
    stmt = (
        select(
            func.date(CrawlErrorTimeSeries.recorded_date).label("date"),
            func.sum(CrawlErrorTimeSeries.error_count).label("total_errors"),
        )
        .where(
            and_(
                CrawlErrorTimeSeries.site_id == site_id,
                CrawlErrorTimeSeries.recorded_date >= cutoff,
            )
        )
        .group_by(func.date(CrawlErrorTimeSeries.recorded_date))
        .order_by(func.date(CrawlErrorTimeSeries.recorded_date))
    )

    result = await db.execute(stmt)
    rows = result.all()

    return [
        {
            "date": row.date.isoformat() if hasattr(row.date, 'isoformat') else str(row.date),
            "total_errors": int(row.total_errors) if row.total_errors else 0,
        }
        for row in rows
    ]


async def get_crawl_error_breakdown(
    db: AsyncSession,
    site_id: UUID,
    days: int = 30,
) -> Dict[str, int]:
    """
    Get crawl error breakdown by type.

    Args:
        db: Database session
        site_id: Site UUID
        days: Number of days to look back

    Returns:
        Dictionary of error_type -> count
    """
    from datetime import timedelta
    from sqlalchemy import select, and_, func

    cutoff = datetime.utcnow() - timedelta(days=days)

    stmt = (
        select(
            CrawlErrorTimeSeries.error_type,
            func.sum(CrawlErrorTimeSeries.error_count).label("total"),
        )
        .where(
            and_(
                CrawlErrorTimeSeries.site_id == site_id,
                CrawlErrorTimeSeries.recorded_date >= cutoff,
            )
        )
        .group_by(CrawlErrorTimeSeries.error_type)
    )

    result = await db.execute(stmt)
    rows = result.all()

    return {
        row.error_type: int(row.total) if row.total else 0
        for row in rows
    }
