"""
Comparator - 競合比較（diff計算）
"""

from typing import Any, Dict, List, Optional
from uuid import uuid4


def diff_pages(
    source: Dict[str, Any],
    target: Dict[str, Any],
    kind: str,
    cfg: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create diff between two pages (source = official, target = competitor/third-party)

    Args:
        source: Source page analysis (official_homepage)
        target: Target page analysis (competitor or third_party)
        kind: "official_vs_competitor" or "official_vs_third_party"
        cfg: Configuration dictionary

    Returns:
        Comparison object with diff details
    """
    # H2 count delta (source - target)
    source_h2_count = len(source.get("html", {}).get("headings", {}).get("h2", []))
    target_h2_count = len(target.get("html", {}).get("headings", {}).get("h2", []))
    h2_count_delta = source_h2_count - target_h2_count

    # Missing intent items (items target has that source doesn't)
    source_coverage = source.get("content", {}).get("intent_coverage", {})
    target_coverage = target.get("content", {}).get("intent_coverage", {})
    missing_intent_items = compute_missing_intent_items(source_coverage, target_coverage)

    # FAQ schema delta
    source_has_faq = source.get("html", {}).get("structured_data", {}).get("has_faq_schema", False)
    target_has_faq = target.get("html", {}).get("structured_data", {}).get("has_faq_schema", False)
    faq_schema_delta = int(source_has_faq) - int(target_has_faq)

    # Performance score delta
    source_perf = source.get("tech", {}).get("pagespeed", {}).get("performance_score")
    target_perf = target.get("tech", {}).get("pagespeed", {}).get("performance_score")
    performance_score_delta = None
    if source_perf is not None and target_perf is not None:
        performance_score_delta = source_perf - target_perf

    # Mobile hint delta
    source_mobile = source.get("tech", {}).get("mobile_friendly_hint", "not_available")
    target_mobile = target.get("tech", {}).get("mobile_friendly_hint", "not_available")
    mobile_hint_delta = f"{source_mobile}->{target_mobile}"

    # Title/Snippet pattern notes
    title_pattern_notes = extract_title_pattern_notes(source, target)
    snippet_pattern_notes = extract_snippet_pattern_notes(source, target)

    return {
        "comparison_id": str(uuid4()),
        "kind": kind,
        "source_page_id": source.get("page_id", ""),
        "target_page_id": target.get("page_id", ""),
        "diff": {
            "structure": {
                "h2_count_delta": h2_count_delta,
                "missing_intent_items": missing_intent_items,
                "faq_schema_delta": faq_schema_delta
            },
            "tech": {
                "performance_score_delta": performance_score_delta,
                "mobile_hint_delta": mobile_hint_delta
            },
            "serp": {
                "title_pattern_notes": title_pattern_notes,
                "snippet_pattern_notes": snippet_pattern_notes
            }
        }
    }


def compute_missing_intent_items(
    source_coverage: Dict[str, float],
    target_coverage: Dict[str, float]
) -> List[str]:
    """
    Find intent items that target has but source is missing

    Args:
        source_coverage: Source page intent coverage
        target_coverage: Target page intent coverage

    Returns:
        List of intent items missing in source but present in target
    """
    missing = []

    for item, target_score in target_coverage.items():
        source_score = source_coverage.get(item, 0)
        # Target has it (score > 0) but source doesn't
        if target_score > 0 and source_score == 0:
            missing.append(item)

    return missing


def extract_title_pattern_notes(
    source: Dict[str, Any],
    target: Dict[str, Any]
) -> List[str]:
    """
    Extract notes about title pattern differences

    Args:
        source: Source page analysis
        target: Target page analysis

    Returns:
        List of pattern notes
    """
    notes = []

    source_title = source.get("html", {}).get("title", "")
    target_title = target.get("html", {}).get("title", "")

    # Length comparison
    if len(source_title) < len(target_title) - 10:
        notes.append(f"競合のtitleが長い ({len(target_title)}文字 vs {len(source_title)}文字)")

    # Check for common SEO patterns in competitor
    if "|" in target_title and "|" not in source_title:
        notes.append("競合はtitleにブランド区切り(|)を使用")

    if "【" in target_title or "】" in target_title:
        notes.append("競合はtitleに【】括弧を使用")

    # Check for year mentions
    import datetime
    current_year = str(datetime.datetime.now().year)
    if current_year in target_title and current_year not in source_title:
        notes.append(f"競合のtitleに{current_year}年が含まれている")

    return notes


def extract_snippet_pattern_notes(
    source: Dict[str, Any],
    target: Dict[str, Any]
) -> List[str]:
    """
    Extract notes about meta description / snippet pattern differences

    Args:
        source: Source page analysis
        target: Target page analysis

    Returns:
        List of pattern notes
    """
    notes = []

    source_desc = source.get("html", {}).get("meta_description", "")
    target_desc = target.get("html", {}).get("meta_description", "")

    # Check if competitor has description but source doesn't
    if not source_desc and target_desc:
        notes.append("競合にはmeta descriptionがあるが、自社にはない")

    # Length comparison
    if source_desc and target_desc:
        if len(source_desc) < len(target_desc) - 20:
            notes.append(f"競合のmeta descriptionが長い ({len(target_desc)}文字 vs {len(source_desc)}文字)")

    # Check for call-to-action patterns
    cta_patterns = ["今すぐ", "無料", "予約", "お問い合わせ", "詳しく"]
    for pattern in cta_patterns:
        if pattern in target_desc and pattern not in source_desc:
            notes.append(f"競合のdescriptionに「{pattern}」が含まれている")
            break

    return notes


def build_comparisons(
    pages: List[Dict[str, Any]],
    cfg: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Build all comparison objects

    Args:
        pages: List of page analysis objects
        cfg: Configuration dictionary

    Returns:
        List of comparison objects
    """
    comparisons = []

    # Find official page
    official = None
    for page in pages:
        if page.get("page_type") == "official_homepage":
            official = page
            break

    if not official:
        return comparisons

    # Compare with competitors
    for page in pages:
        if page.get("page_type") == "competitor_page":
            comparison = diff_pages(official, page, "official_vs_competitor", cfg)
            comparisons.append(comparison)

    # Compare with third-party pages
    for page in pages:
        if page.get("page_type") == "third_party_profile_page":
            comparison = diff_pages(official, page, "official_vs_third_party", cfg)
            comparisons.append(comparison)

    return comparisons
