"""
HTML Parser - SEO関連情報の抽出
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Set
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup


@dataclass
class HtmlAnalysisResult:
    """HTML analysis result"""
    title: str = ""
    meta_description: str = ""
    canonical: str = ""
    robots_meta: str = ""
    headings: Dict[str, List[str]] = field(default_factory=lambda: {"h1": [], "h2": [], "h3": []})
    text_stats: Dict[str, int] = field(default_factory=lambda: {"text_length_chars": 0, "text_length_words_est": 0})
    links: Dict[str, Any] = field(default_factory=lambda: {"internal_count": 0, "external_count": 0, "external_domains": []})
    images: Dict[str, Any] = field(default_factory=lambda: {"count": 0, "with_alt": 0, "alt_ratio": 0.0})
    full_text: str = ""  # For intent analysis


def is_internal_link(href: str, base_url: str) -> bool:
    """Check if a link is internal to the same domain"""
    if not href or href.startswith("#") or href.startswith("javascript:"):
        return True  # Treat anchors and JS as internal

    try:
        base_parsed = urlparse(base_url)
        href_parsed = urlparse(urljoin(base_url, href))

        # Same domain = internal
        return base_parsed.netloc.lower() == href_parsed.netloc.lower()
    except Exception:
        return True


def parse_html(html: str, base_url: str) -> HtmlAnalysisResult:
    """
    Parse HTML and extract SEO-related information

    Args:
        html: HTML content string
        base_url: Base URL for resolving relative links

    Returns:
        HtmlAnalysisResult with extracted data
    """
    if not html:
        return HtmlAnalysisResult()

    soup = BeautifulSoup(html, 'lxml')

    # Title
    title = ""
    title_tag = soup.find('title')
    if title_tag:
        title = title_tag.get_text(strip=True)

    # Meta description
    meta_description = ""
    meta_desc_tag = soup.find('meta', attrs={'name': 'description'})
    if meta_desc_tag:
        meta_description = meta_desc_tag.get('content', '')

    # Canonical
    canonical = ""
    canonical_tag = soup.find('link', rel='canonical')
    if canonical_tag:
        canonical = canonical_tag.get('href', '')

    # Robots meta
    robots_meta = ""
    robots_tag = soup.find('meta', attrs={'name': 'robots'})
    if robots_tag:
        robots_meta = robots_tag.get('content', '')

    # Headings
    headings = {
        'h1': [],
        'h2': [],
        'h3': []
    }
    for level in ['h1', 'h2', 'h3']:
        for tag in soup.find_all(level):
            text = tag.get_text(strip=True)
            if text:
                headings[level].append(text)

    # Text stats
    # Remove script and style elements
    for script in soup(["script", "style", "noscript"]):
        script.decompose()

    full_text = soup.get_text(separator=' ', strip=True)
    text_length_chars = len(full_text)
    # Estimate words: for Japanese, roughly 2 characters per word
    text_length_words_est = text_length_chars // 2

    text_stats = {
        'text_length_chars': text_length_chars,
        'text_length_words_est': text_length_words_est
    }

    # Links
    all_links = soup.find_all('a', href=True)
    internal_count = 0
    external_count = 0
    external_domains: Set[str] = set()

    for a in all_links:
        href = a.get('href', '')
        if is_internal_link(href, base_url):
            internal_count += 1
        else:
            external_count += 1
            try:
                domain = urlparse(urljoin(base_url, href)).netloc
                if domain:
                    external_domains.add(domain)
            except Exception:
                pass

    links = {
        'internal_count': internal_count,
        'external_count': external_count,
        'external_domains': list(external_domains)
    }

    # Images
    all_images = soup.find_all('img')
    image_count = len(all_images)
    with_alt = sum(1 for img in all_images if img.get('alt'))
    alt_ratio = with_alt / image_count if image_count > 0 else 0.0

    images = {
        'count': image_count,
        'with_alt': with_alt,
        'alt_ratio': round(alt_ratio, 3)
    }

    return HtmlAnalysisResult(
        title=title,
        meta_description=meta_description,
        canonical=canonical,
        robots_meta=robots_meta,
        headings=headings,
        text_stats=text_stats,
        links=links,
        images=images,
        full_text=full_text
    )
