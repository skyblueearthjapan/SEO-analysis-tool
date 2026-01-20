"""
Backlink Time Series Analyzer (Appendix AF)

Collects backlink data and saves to time series for trend tracking.
Note: Full backlink data requires external API (Ahrefs/Majestic/Moz).
This implementation provides a placeholder that can be extended.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import BacklinkTimeSeries


@dataclass
class BacklinkCollectionResult:
    """Result of backlink time series collection"""
    success: bool
    records_saved: int
    source: str  # "external_api" | "internal_estimate" | "skipped"
    error: Optional[str] = None


async def collect_backlinks(
    db: AsyncSession,
    site_id: UUID,
    pages: List[Dict[str, Any]],
    external_api_enabled: bool = False,
) -> BacklinkCollectionResult:
    """
    Collect backlink data and save to time series.

    Currently uses internal link analysis as a proxy.
    When external_api_enabled is True, will integrate with
    Ahrefs/Majestic/Moz API.

    Args:
        db: Database session
        site_id: Site UUID
        pages: List of analyzed pages (from analysis_result["pages"])
        external_api_enabled: Whether to use external backlink API

    Returns:
        BacklinkCollectionResult with success status
    """
    try:
        # External API integration (future)
        if external_api_enabled:
            # TODO: Integrate with Ahrefs/Majestic/Moz API
            # result = await _fetch_from_external_api(site_id, pages)
            return BacklinkCollectionResult(
                success=False,
                records_saved=0,
                source="external_api",
                error="External backlink API not configured",
            )

        # Internal estimate based on link analysis
        # Count external links pointing to the site (from analyzed pages)
        total_external_links = 0
        referring_pages = set()

        for page in pages:
            html = page.get("html", {})
            links = html.get("links", {})

            # Count external links that might be backlinks
            # (This is a simplified proxy - real backlinks need external API)
            external_count = links.get("external_links_count", 0)
            if external_count > 0:
                total_external_links += external_count
                referring_pages.add(page.get("url", ""))

        # Only save if we have meaningful data
        if total_external_links > 0:
            record = BacklinkTimeSeries(
                site_id=site_id,
                total_backlinks=total_external_links,
                referring_domains=len(referring_pages),
                new_backlinks=None,  # Requires historical comparison
                lost_backlinks=None,
                recorded_date=datetime.utcnow(),
            )
            db.add(record)
            await db.flush()

            return BacklinkCollectionResult(
                success=True,
                records_saved=1,
                source="internal_estimate",
            )

        return BacklinkCollectionResult(
            success=True,
            records_saved=0,
            source="internal_estimate",
        )

    except Exception as e:
        return BacklinkCollectionResult(
            success=False,
            records_saved=0,
            source="internal_estimate",
            error=str(e),
        )


async def get_backlink_trend_data(
    db: AsyncSession,
    site_id: UUID,
    days: int = 30,
) -> List[Dict[str, Any]]:
    """
    Get backlink trend data for charting.

    Args:
        db: Database session
        site_id: Site UUID
        days: Number of days to look back

    Returns:
        List of data points for trend chart
    """
    from datetime import timedelta
    from sqlalchemy import select, and_

    cutoff = datetime.utcnow() - timedelta(days=days)

    stmt = (
        select(BacklinkTimeSeries)
        .where(
            and_(
                BacklinkTimeSeries.site_id == site_id,
                BacklinkTimeSeries.recorded_date >= cutoff,
            )
        )
        .order_by(BacklinkTimeSeries.recorded_date)
    )

    result = await db.execute(stmt)
    records = result.scalars().all()

    return [
        {
            "date": r.recorded_date.date().isoformat(),
            "total_backlinks": r.total_backlinks,
            "referring_domains": r.referring_domains,
            "new_backlinks": r.new_backlinks,
            "lost_backlinks": r.lost_backlinks,
        }
        for r in records
    ]
