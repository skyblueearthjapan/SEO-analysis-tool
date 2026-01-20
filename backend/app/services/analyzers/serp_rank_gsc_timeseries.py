"""
SERP Rank GSC Time Series Analyzer (Appendix AD)

Collects SERP position data from Google Search Console and saves to time series.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import SerpTimeSeries


@dataclass
class SerpCollectionResult:
    """Result of SERP time series collection"""
    success: bool
    records_saved: int
    error: Optional[str] = None


async def collect_serp_timeseries(
    db: AsyncSession,
    site_id: UUID,
    pages: List[Dict[str, Any]],
    device: str = "mobile",
) -> SerpCollectionResult:
    """
    Collect SERP position data from analysis pages and save to time series.

    This extracts position data from GSC queries in the analysis result
    and saves them as time series records for trend tracking.

    Args:
        db: Database session
        site_id: Site UUID
        pages: List of analyzed pages (from analysis_result["pages"])
        device: Device type (mobile/desktop)

    Returns:
        SerpCollectionResult with success status and record count
    """
    try:
        records_saved = 0

        for page in pages:
            # Only process pages with GSC data
            gsc = page.get("search_console", {})
            if not gsc.get("available"):
                continue

            page_url = page.get("url", "")
            top_queries = gsc.get("top_queries", [])

            for query_data in top_queries:
                query = query_data.get("query", "")
                position = query_data.get("position")

                if not query or position is None:
                    continue

                # Create time series record
                record = SerpTimeSeries(
                    site_id=site_id,
                    query=query,
                    position=float(position),
                    url=page_url,
                    device=device,
                    recorded_date=datetime.utcnow(),
                )
                db.add(record)
                records_saved += 1

        if records_saved > 0:
            await db.flush()

        return SerpCollectionResult(
            success=True,
            records_saved=records_saved,
        )

    except Exception as e:
        return SerpCollectionResult(
            success=False,
            records_saved=0,
            error=str(e),
        )


async def get_serp_trend_data(
    db: AsyncSession,
    site_id: UUID,
    query: Optional[str] = None,
    days: int = 30,
) -> List[Dict[str, Any]]:
    """
    Get SERP trend data for charting.

    Args:
        db: Database session
        site_id: Site UUID
        query: Optional specific query to filter
        days: Number of days to look back

    Returns:
        List of data points for trend chart
    """
    from datetime import timedelta
    from sqlalchemy import select, and_, func

    cutoff = datetime.utcnow() - timedelta(days=days)

    # Group by date and calculate average position
    if query:
        # Single query trend
        stmt = (
            select(
                func.date(SerpTimeSeries.recorded_date).label("date"),
                func.avg(SerpTimeSeries.position).label("avg_position"),
            )
            .where(
                and_(
                    SerpTimeSeries.site_id == site_id,
                    SerpTimeSeries.query == query,
                    SerpTimeSeries.recorded_date >= cutoff,
                )
            )
            .group_by(func.date(SerpTimeSeries.recorded_date))
            .order_by(func.date(SerpTimeSeries.recorded_date))
        )
    else:
        # All queries average
        stmt = (
            select(
                func.date(SerpTimeSeries.recorded_date).label("date"),
                func.avg(SerpTimeSeries.position).label("avg_position"),
            )
            .where(
                and_(
                    SerpTimeSeries.site_id == site_id,
                    SerpTimeSeries.recorded_date >= cutoff,
                )
            )
            .group_by(func.date(SerpTimeSeries.recorded_date))
            .order_by(func.date(SerpTimeSeries.recorded_date))
        )

    result = await db.execute(stmt)
    rows = result.all()

    return [
        {
            "date": row.date.isoformat() if hasattr(row.date, 'isoformat') else str(row.date),
            "avg_position": round(float(row.avg_position), 2) if row.avg_position else None,
        }
        for row in rows
    ]
