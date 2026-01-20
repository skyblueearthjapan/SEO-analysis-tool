"""
Google Search Console API Client
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

# Note: Requires google-api-python-client and google-auth
# pip install google-api-python-client google-auth-oauthlib


@dataclass
class TopQuery:
    """Search Console query data"""
    query: str
    impressions: int
    clicks: int
    ctr: float
    position: float
    query_intent: str = "unknown"


@dataclass
class BrandQuerySummary:
    """Brand query summary"""
    brand_queries_present: bool = False
    brand_impressions: int = 0
    brand_ctr: float = 0.0


@dataclass
class GSCResult:
    """Google Search Console result"""
    available: bool
    time_window_days: Optional[int] = None
    top_queries: List[TopQuery] = field(default_factory=list)
    brand_query_summary: BrandQuerySummary = field(default_factory=BrandQuerySummary)
    error: Optional[str] = None


async def gsc_fetch_url_metrics(
    site_property: str,
    url: str,
    days: int = 28,
    max_queries: int = 20,
    credentials_path: Optional[str] = None
) -> GSCResult:
    """
    Fetch Search Console metrics for a specific URL

    Args:
        site_property: GSC property (e.g., "sc-domain:example.com")
        url: Target URL to get metrics for
        days: Number of days to look back
        max_queries: Maximum number of queries to return
        credentials_path: Path to Google credentials JSON

    Returns:
        GSCResult with query data
    """
    if not credentials_path:
        return GSCResult(
            available=False,
            error="GSC credentials not configured"
        )

    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        # Build credentials
        credentials = service_account.Credentials.from_service_account_file(
            credentials_path,
            scopes=['https://www.googleapis.com/auth/webmasters.readonly']
        )

        # Build service
        service = build('searchconsole', 'v1', credentials=credentials)

        # Calculate date range
        end_date = datetime.now().date() - timedelta(days=3)  # GSC has ~3 day delay
        start_date = end_date - timedelta(days=days)

        # Query request
        request = {
            'startDate': start_date.isoformat(),
            'endDate': end_date.isoformat(),
            'dimensions': ['query'],
            'dimensionFilterGroups': [{
                'filters': [{
                    'dimension': 'page',
                    'operator': 'equals',
                    'expression': url
                }]
            }],
            'rowLimit': max_queries,
            'startRow': 0
        }

        # Execute query
        response = service.searchanalytics().query(
            siteUrl=site_property,
            body=request
        ).execute()

        rows = response.get('rows', [])

        top_queries = []
        for row in rows:
            query = TopQuery(
                query=row['keys'][0],
                impressions=int(row.get('impressions', 0)),
                clicks=int(row.get('clicks', 0)),
                ctr=round(row.get('ctr', 0.0), 4),
                position=round(row.get('position', 0.0), 1)
            )
            top_queries.append(query)

        return GSCResult(
            available=True,
            time_window_days=days,
            top_queries=top_queries
        )

    except ImportError:
        return GSCResult(
            available=False,
            error="Google API client not installed"
        )
    except Exception as e:
        return GSCResult(
            available=False,
            error=f"GSC API error: {str(e)}"
        )


def classify_query_intents(
    queries: List[TopQuery],
    brand_terms: Optional[List[str]] = None
) -> List[TopQuery]:
    """
    Classify query intents and compute brand summary

    Args:
        queries: List of TopQuery objects
        brand_terms: List of brand-related terms

    Returns:
        Updated queries with intent classification
    """
    if not brand_terms:
        brand_terms = []

    brand_terms_lower = [t.lower() for t in brand_terms]

    for query in queries:
        query_lower = query.query.lower()

        # Check brand intent
        if any(term in query_lower for term in brand_terms_lower):
            query.query_intent = "brand"
            continue

        # Price intent
        price_keywords = ["価格", "料金", "費用", "値段", "いくら", "cost", "price", "pricing"]
        if any(k in query_lower for k in price_keywords):
            query.query_intent = "price"
            continue

        # Compare intent
        compare_keywords = ["比較", "違い", "vs", "おすすめ", "ランキング", "compare", "best"]
        if any(k in query_lower for k in compare_keywords):
            query.query_intent = "compare"
            continue

        # Visit intent
        visit_keywords = ["場所", "行き方", "アクセス", "住所", "地図", "location", "address", "directions"]
        if any(k in query_lower for k in visit_keywords):
            query.query_intent = "visit"
            continue

        # Default to info
        query.query_intent = "info"

    return queries


def compute_brand_summary(
    queries: List[TopQuery],
    brand_terms: Optional[List[str]] = None
) -> BrandQuerySummary:
    """
    Compute brand query summary

    Args:
        queries: List of classified queries
        brand_terms: List of brand-related terms

    Returns:
        BrandQuerySummary with aggregated brand metrics
    """
    if not queries:
        return BrandQuerySummary()

    brand_queries = [q for q in queries if q.query_intent == "brand"]

    if not brand_queries:
        return BrandQuerySummary(brand_queries_present=False)

    total_impressions = sum(q.impressions for q in brand_queries)
    total_clicks = sum(q.clicks for q in brand_queries)
    brand_ctr = total_clicks / total_impressions if total_impressions > 0 else 0.0

    return BrandQuerySummary(
        brand_queries_present=True,
        brand_impressions=total_impressions,
        brand_ctr=round(brand_ctr, 4)
    )
