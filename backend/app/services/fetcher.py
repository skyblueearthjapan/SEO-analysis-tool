"""
HTTP Fetcher - URL取得 + リダイレクト追跡
"""

from dataclasses import dataclass
from typing import List, Optional

import httpx


@dataclass
class FetchResult:
    """HTTP fetch result with redirect chain"""
    status_code: int
    final_url: str
    redirect_chain: List[str]
    html: str
    content_type: str
    error: Optional[str] = None


async def http_fetch(
    url: str,
    user_agent: str = "SEOBot/1.0 (+https://example.com/bot)",
    timeout: float = 30.0,
    follow_redirects: bool = True
) -> FetchResult:
    """
    Fetch URL and track redirect chain

    Args:
        url: Target URL to fetch
        user_agent: User-Agent header value
        timeout: Request timeout in seconds
        follow_redirects: Whether to follow redirects

    Returns:
        FetchResult with status, final URL, redirect chain, and HTML content
    """
    redirect_chain: List[str] = []

    try:
        async with httpx.AsyncClient(
            follow_redirects=follow_redirects,
            timeout=timeout
        ) as client:
            response = await client.get(
                url,
                headers={
                    "User-Agent": user_agent,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "ja,en;q=0.9",
                }
            )

            # Build redirect chain from history
            for r in response.history:
                redirect_chain.append(str(r.url))

            content_type = response.headers.get("content-type", "")

            # Get HTML content
            html = ""
            if "text/html" in content_type or "application/xhtml+xml" in content_type:
                html = response.text

            return FetchResult(
                status_code=response.status_code,
                final_url=str(response.url),
                redirect_chain=redirect_chain,
                html=html,
                content_type=content_type
            )

    except httpx.TimeoutException:
        return FetchResult(
            status_code=0,
            final_url=url,
            redirect_chain=[],
            html="",
            content_type="",
            error="Request timeout"
        )
    except httpx.ConnectError as e:
        return FetchResult(
            status_code=0,
            final_url=url,
            redirect_chain=[],
            html="",
            content_type="",
            error=f"Connection error: {str(e)}"
        )
    except Exception as e:
        return FetchResult(
            status_code=0,
            final_url=url,
            redirect_chain=[],
            html="",
            content_type="",
            error=f"Fetch error: {str(e)}"
        )


def compute_mobile_hint(html: str, cfg: dict) -> str:
    """
    Compute mobile-friendly hint based on HTML content

    Args:
        html: HTML content
        cfg: Thresholds configuration

    Returns:
        "pass", "warn", "fail", or "not_available"
    """
    if not html:
        return "not_available"

    html_lower = html.lower()

    # Check for viewport meta tag
    has_viewport = 'name="viewport"' in html_lower or "name='viewport'" in html_lower

    # Check for responsive meta content
    has_responsive = "width=device-width" in html_lower

    if has_viewport and has_responsive:
        return "pass"
    elif has_viewport:
        return "warn"
    else:
        return "fail"
