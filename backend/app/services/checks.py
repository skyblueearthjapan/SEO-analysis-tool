"""
Analysis Checks Builder - 解析チェックリスト生成モジュール (Appendix V)

解析実行結果のチェックリストを生成し、各解析モジュールの実行状態を記録する。
ToDoとの紐付け（source_checks）にも使用される。
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional


CheckStatus = Literal["done", "partial", "skipped", "not_supported"]

ANALYSIS_CHECK_CODES = [
    "fetch",
    "html_basic",
    "headings",
    "text_stats",
    "links",
    "images_alt",
    "structured_data",
    "pagespeed",
    "search_console",
    "intent_coverage",
    "competitor_diff",
    "backlinks",
    "serp_rank",
    "keyword_research",
    "site_crawl",
    "log_analysis",
    "duplicate_cannibalization"
]


@dataclass
class AnalyzerMeta:
    """解析モジュールのメタ情報"""
    code: str
    status: CheckStatus
    notes: List[str] = field(default_factory=list)
    evidence_ids: List[str] = field(default_factory=list)


@dataclass
class AnalysisContext:
    """解析実行コンテキスト"""
    # Feature flags
    pagespeed_enabled: bool = False
    pagespeed_ok: bool = False
    gsc_enabled: bool = False
    gsc_ok: bool = False

    # Page counts
    competitor_count: int = 0

    # Evidence IDs by check code
    evidence_ids: Dict[str, List[str]] = field(default_factory=dict)

    # Additional notes by check code
    notes: Dict[str, List[str]] = field(default_factory=dict)


def build_analysis_checks(ctx: AnalysisContext) -> Dict[str, Any]:
    """
    解析チェックリストを生成する

    Args:
        ctx: 実行コンテキスト（設定/ページ数/機能フラグ/タイムアウト等を含む）

    Returns:
        analysis_checks オブジェクト（schema_version + checks）
    """
    checks: Dict[str, Dict[str, Any]] = {}

    # Core checks (always executed)
    core_checks = [
        "fetch",
        "html_basic",
        "headings",
        "text_stats",
        "links",
        "images_alt",
        "structured_data",
        "intent_coverage"
    ]

    for code in core_checks:
        checks[code] = {
            "status": "done",
            "notes": ctx.notes.get(code, []),
            "evidence_ids": ctx.evidence_ids.get(code, [])
        }

    # Optional: PageSpeed
    if ctx.pagespeed_enabled:
        if ctx.pagespeed_ok:
            checks["pagespeed"] = {
                "status": "done",
                "notes": ctx.notes.get("pagespeed", []),
                "evidence_ids": ctx.evidence_ids.get("pagespeed", [])
            }
        else:
            checks["pagespeed"] = {
                "status": "partial",
                "notes": ctx.notes.get("pagespeed", ["pagespeed disabled/timeout/key missing"]),
                "evidence_ids": ctx.evidence_ids.get("pagespeed", [])
            }
    else:
        checks["pagespeed"] = {
            "status": "skipped",
            "notes": ["pagespeed disabled"],
            "evidence_ids": []
        }

    # Optional: Search Console (GSC)
    if ctx.gsc_enabled:
        if ctx.gsc_ok:
            checks["search_console"] = {
                "status": "done",
                "notes": ctx.notes.get("search_console", []),
                "evidence_ids": ctx.evidence_ids.get("search_console", [])
            }
        else:
            checks["search_console"] = {
                "status": "partial",
                "notes": ctx.notes.get("search_console", ["gsc auth/config issue"]),
                "evidence_ids": ctx.evidence_ids.get("search_console", [])
            }
    else:
        checks["search_console"] = {
            "status": "skipped",
            "notes": ["GSC not configured"],
            "evidence_ids": []
        }

    # Competitor diff (requires at least 1 competitor)
    if ctx.competitor_count >= 1:
        checks["competitor_diff"] = {
            "status": "done",
            "notes": ctx.notes.get("competitor_diff", []),
            "evidence_ids": ctx.evidence_ids.get("competitor_diff", [])
        }
    else:
        checks["competitor_diff"] = {
            "status": "skipped",
            "notes": ["no competitors"],
            "evidence_ids": []
        }

    # Extension placeholders (future features)
    extension_checks = [
        "backlinks",
        "serp_rank",
        "keyword_research",
        "site_crawl",
        "log_analysis",
        "duplicate_cannibalization"
    ]

    for code in extension_checks:
        checks[code] = {
            "status": "not_supported",
            "notes": ["planned"],
            "evidence_ids": []
        }

    return {
        "schema_version": "0.1",
        "checks": checks
    }


def infer_source_checks(todo: Dict[str, Any]) -> List[str]:
    """
    ToDoから関連する解析チェックを推定する

    Args:
        todo: ToDo辞書（category, key, evidence_refs等を含む）

    Returns:
        関連するチェックコードのリスト
    """
    category = (todo.get("category") or "").lower()
    key = (todo.get("key") or todo.get("title") or "").lower()
    evidence_refs = todo.get("evidence_refs") or todo.get("evidence") or []

    # Evidence prefix based inference (strongest signal)
    for ev in evidence_refs:
        ev_lower = ev.lower() if isinstance(ev, str) else ""
        if "pagespeed" in ev_lower or "performance" in ev_lower:
            return ["pagespeed"]
        if "gsc" in ev_lower or "search_console" in ev_lower:
            return ["search_console"]
        if "schema" in ev_lower or "structured" in ev_lower:
            return ["structured_data"]
        if "heading" in ev_lower or "h1" in ev_lower or "h2" in ev_lower:
            return ["headings"]
        if "image" in ev_lower or "alt" in ev_lower:
            return ["images_alt"]
        if "fetch" in ev_lower or "status" in ev_lower or "http" in ev_lower:
            return ["fetch"]
        if "link" in ev_lower:
            return ["links"]

    # Key/title based inference
    if "competitor" in key or "diff" in key or "比較" in key or "競合" in key:
        return ["competitor_diff"]
    if "intent" in key or "意図" in key or "カバー" in key:
        return ["intent_coverage"]
    if "pagespeed" in key or "speed" in key or "速度" in key or "performance" in key:
        return ["pagespeed"]
    if "gsc" in key or "search console" in key or "ctr" in key:
        return ["search_console"]
    if "schema" in key or "構造化" in key or "faq" in key or "organization" in key:
        return ["structured_data"]
    if "heading" in key or "見出し" in key or "h1" in key or "h2" in key:
        return ["headings"]
    if "image" in key or "画像" in key or "alt" in key:
        return ["images_alt"]
    if "text" in key or "テキスト" in key or "文字" in key:
        return ["text_stats"]
    if "link" in key or "リンク" in key:
        return ["links"]
    if "noindex" in key or "robots" in key or "index" in key:
        return ["html_basic"]
    if "http" in key or "status" in key or "ステータス" in key or "fetch" in key:
        return ["fetch"]

    # Category based fallback
    if category == "technical":
        # Check for specific technical issues
        if "noindex" in key or "meta" in key or "title" in key or "canonical" in key:
            return ["html_basic"]
        if "speed" in key or "core web" in key or "lcp" in key or "cls" in key:
            return ["pagespeed"]
        return ["fetch"]

    if category == "content":
        return ["intent_coverage"]

    if category == "ctr":
        return ["search_console"]

    # Default fallback
    return ["html_basic"]


def add_source_checks_to_todos(todos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    ToDoリストに source_checks を追加する

    Args:
        todos: ToDoリスト

    Returns:
        source_checks が追加されたToDoリスト
    """
    for todo in todos:
        if "source_checks" not in todo:
            todo["source_checks"] = infer_source_checks(todo)
    return todos


def build_context_from_job(
    job: Any,
    pages: List[Dict[str, Any]],
    pagespeed_results: Dict[str, bool],
    gsc_results: Dict[str, bool]
) -> AnalysisContext:
    """
    解析ジョブからコンテキストを構築する

    Args:
        job: AnalysisJob オブジェクト
        pages: 解析されたページリスト
        pagespeed_results: PageSpeed実行結果 {page_id: success}
        gsc_results: GSC実行結果 {page_id: success}

    Returns:
        AnalysisContext オブジェクト
    """
    # Count competitors
    competitor_count = sum(
        1 for p in pages
        if p.get("page_type") in ["competitor_page", "third_party_profile_page"]
    )

    # Check PageSpeed status
    pagespeed_enabled = getattr(job, "enable_pagespeed", False)
    pagespeed_ok = any(pagespeed_results.values()) if pagespeed_results else False

    # Check GSC status
    gsc_enabled = getattr(job, "enable_gsc", False) and getattr(job, "gsc_property", None)
    gsc_ok = any(gsc_results.values()) if gsc_results else False

    # Build evidence IDs based on pages
    evidence_ids: Dict[str, List[str]] = {}

    for page in pages:
        page_id = page.get("page_id", "unknown")
        page_type = page.get("page_type", "unknown")

        # Fetch evidence
        if "fetch" in page:
            evidence_ids.setdefault("fetch", []).append(f"ev_fetch_{page_id}")

        # HTML evidence
        if "html" in page:
            evidence_ids.setdefault("html_basic", []).append(f"ev_html_meta_{page_id}")
            evidence_ids.setdefault("headings", []).append(f"ev_headings_{page_id}")
            evidence_ids.setdefault("text_stats", []).append(f"ev_text_stats_{page_id}")
            evidence_ids.setdefault("links", []).append(f"ev_links_{page_id}")
            evidence_ids.setdefault("images_alt", []).append(f"ev_images_{page_id}")

            if page.get("html", {}).get("structured_data"):
                evidence_ids.setdefault("structured_data", []).append(f"ev_schema_{page_id}")

        # PageSpeed evidence
        if page.get("tech", {}).get("pagespeed", {}).get("available"):
            evidence_ids.setdefault("pagespeed", []).append(f"ev_pagespeed_{page_id}")

        # GSC evidence
        if page.get("search_console", {}).get("available"):
            evidence_ids.setdefault("search_console", []).append(f"ev_gsc_{page_id}")

        # Intent coverage evidence
        if "content" in page:
            evidence_ids.setdefault("intent_coverage", []).append(f"ev_intent_{page_id}")

    return AnalysisContext(
        pagespeed_enabled=pagespeed_enabled,
        pagespeed_ok=pagespeed_ok,
        gsc_enabled=gsc_enabled,
        gsc_ok=gsc_ok,
        competitor_count=competitor_count,
        evidence_ids=evidence_ids
    )
