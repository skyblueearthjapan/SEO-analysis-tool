"""
Analyzers package - Time Series data collectors (Appendix AD, AE, AF)

Each analyzer is responsible for:
1. Fetching data from external sources (GSC, crawl logs, backlink APIs)
2. Saving time series records to the database
3. Returning success/failure status for the checklist
"""

from app.services.analyzers.serp_rank_gsc_timeseries import (
    collect_serp_timeseries,
    SerpCollectionResult,
)
from app.services.analyzers.crawl_error_timeseries import (
    collect_crawl_errors,
    CrawlErrorCollectionResult,
)
from app.services.analyzers.backlink_timeseries import (
    collect_backlinks,
    BacklinkCollectionResult,
)

__all__ = [
    "collect_serp_timeseries",
    "SerpCollectionResult",
    "collect_crawl_errors",
    "CrawlErrorCollectionResult",
    "collect_backlinks",
    "BacklinkCollectionResult",
]
