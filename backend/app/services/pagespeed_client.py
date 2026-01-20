"""
PageSpeed Insights API Client
"""

from dataclasses import dataclass
from typing import Optional

import httpx

PAGESPEED_API_URL = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"


@dataclass
class PageSpeedResult:
    """PageSpeed Insights result"""
    available: bool
    performance_score: Optional[int] = None
    lcp_ms: Optional[int] = None
    inp_ms: Optional[int] = None
    cls: Optional[float] = None
    fcp_ms: Optional[int] = None
    ttfb_ms: Optional[int] = None
    error: Optional[str] = None


async def pagespeed_fetch(
    url: str,
    device: str = "mobile",
    api_key: Optional[str] = None,
    timeout: float = 60.0
) -> PageSpeedResult:
    """
    Fetch PageSpeed Insights data for a URL

    Args:
        url: Target URL to analyze
        device: "mobile" or "desktop"
        api_key: Google API key (optional but recommended)
        timeout: Request timeout in seconds

    Returns:
        PageSpeedResult with Core Web Vitals and performance score
    """
    params = {
        "url": url,
        "strategy": device.upper() if device.upper() in ["MOBILE", "DESKTOP"] else "MOBILE",
        "category": "PERFORMANCE"
    }

    if api_key:
        params["key"] = api_key

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(PAGESPEED_API_URL, params=params)

            if response.status_code != 200:
                return PageSpeedResult(
                    available=False,
                    error=f"API error: {response.status_code}"
                )

            data = response.json()

        lighthouse = data.get("lighthouseResult", {})
        categories = lighthouse.get("categories", {})
        audits = lighthouse.get("audits", {})

        # Performance score (0-1 -> 0-100)
        perf_score = categories.get("performance", {}).get("score")
        if perf_score is not None:
            perf_score = int(perf_score * 100)

        # Largest Contentful Paint
        lcp = audits.get("largest-contentful-paint", {}).get("numericValue")
        lcp_ms = int(lcp) if lcp is not None else None

        # Interaction to Next Paint (INP replaces FID)
        inp = audits.get("interaction-to-next-paint", {}).get("numericValue")
        inp_ms = int(inp) if inp is not None else None

        # Cumulative Layout Shift
        cls_val = audits.get("cumulative-layout-shift", {}).get("numericValue")

        # First Contentful Paint
        fcp = audits.get("first-contentful-paint", {}).get("numericValue")
        fcp_ms = int(fcp) if fcp is not None else None

        # Time to First Byte
        ttfb = audits.get("server-response-time", {}).get("numericValue")
        ttfb_ms = int(ttfb) if ttfb is not None else None

        return PageSpeedResult(
            available=True,
            performance_score=perf_score,
            lcp_ms=lcp_ms,
            inp_ms=inp_ms,
            cls=round(cls_val, 3) if cls_val is not None else None,
            fcp_ms=fcp_ms,
            ttfb_ms=ttfb_ms
        )

    except httpx.TimeoutException:
        return PageSpeedResult(
            available=False,
            error="PageSpeed API timeout"
        )
    except Exception as e:
        return PageSpeedResult(
            available=False,
            error=f"PageSpeed API error: {str(e)}"
        )
