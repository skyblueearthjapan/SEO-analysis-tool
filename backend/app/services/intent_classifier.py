"""
Intent Classifier - ページの意図カバー判定
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# 公式HP用の意図項目（10項目）
OFFICIAL_INTENT_ITEMS = [
    "overview",           # 何者か（概要）
    "activities",         # 活動内容
    "works_or_history",   # 公演/実績
    "media_gallery",      # 写真/メディア
    "cta_contact",        # 参加/問い合わせ導線
    "faq",                # よくある質問
    "region",             # 活動地域/所在地
    "team_or_operator",   # メンバー/運営情報
    "freshness",          # 最新情報/更新性
    "audience_branch"     # 観客/参加希望の導線分岐
]

# 紹介記事用の意図項目（6項目）
THIRD_PARTY_INTENT_ITEMS = [
    "brand_clear",        # 自社名が明確
    "description_depth",  # 説明文十分
    "unique_points",      # 特徴・差別化
    "region_or_genre",    # 地域/ジャンル
    "official_link",      # 公式HPリンク
    "cta_present"         # 参加/予約導線
]


@dataclass
class IntentCoverageResult:
    """Intent coverage analysis result"""
    intent_coverage: Dict[str, float] = field(default_factory=dict)
    missing_sections: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)


def compute_intent_coverage(
    page_type: str,
    title: str,
    h2_list: List[str],
    text: str,
    links: Dict[str, Any],
    brand_terms: Optional[List[str]] = None,
    cfg: Optional[Dict[str, Any]] = None
) -> IntentCoverageResult:
    """
    Compute intent coverage based on page type

    Args:
        page_type: "official_homepage", "competitor_page", or "third_party_profile_page"
        title: Page title
        h2_list: List of H2 headings
        text: Full page text
        links: Links info from HTML parser
        brand_terms: Brand-related terms for detection
        cfg: Configuration dictionary

    Returns:
        IntentCoverageResult with coverage scores and missing sections
    """
    if page_type == "official_homepage" or page_type == "competitor_page":
        items = OFFICIAL_INTENT_ITEMS
        coverage = _check_official_intent(title, h2_list, text, links)
    elif page_type == "third_party_profile_page":
        items = THIRD_PARTY_INTENT_ITEMS
        coverage = _check_third_party_intent(title, h2_list, text, links, brand_terms)
    else:
        # Default to official
        items = OFFICIAL_INTENT_ITEMS
        coverage = _check_official_intent(title, h2_list, text, links)

    # Find missing sections
    missing = [item for item in items if coverage.get(item, 0) == 0]

    return IntentCoverageResult(
        intent_coverage=coverage,
        missing_sections=missing,
        notes=[]
    )


def _check_official_intent(
    title: str,
    h2_list: List[str],
    text: str,
    links: Dict[str, Any]
) -> Dict[str, float]:
    """
    Check intent coverage for official/competitor pages

    Uses keyword matching against H2 headings and full text
    """
    coverage: Dict[str, float] = {}

    h2_text = " ".join(h2_list).lower()
    text_lower = text.lower()
    title_lower = title.lower()

    # Overview (概要)
    overview_keywords = ["概要", "について", "とは", "私たち", "who we are", "about"]
    coverage["overview"] = 1.0 if any(k in h2_text or k in title_lower for k in overview_keywords) else 0.0

    # Activities (活動内容)
    activities_keywords = ["活動", "事業", "サービス", "内容", "activities", "services", "what we do"]
    coverage["activities"] = 1.0 if any(k in h2_text for k in activities_keywords) else 0.0

    # Works/History (公演/実績)
    works_keywords = ["実績", "公演", "作品", "履歴", "歴史", "works", "portfolio", "history", "past"]
    coverage["works_or_history"] = 1.0 if any(k in h2_text or k in text_lower[:2000] for k in works_keywords) else 0.0

    # Media Gallery (写真/メディア)
    media_keywords = ["写真", "ギャラリー", "動画", "メディア", "photo", "gallery", "video", "media"]
    coverage["media_gallery"] = 1.0 if any(k in h2_text or k in text_lower for k in media_keywords) else 0.0

    # CTA/Contact (問い合わせ/参加導線)
    cta_keywords = ["お問い合わせ", "問い合わせ", "参加", "申込", "予約", "contact", "join", "apply", "book"]
    coverage["cta_contact"] = 1.0 if any(k in text_lower for k in cta_keywords) else 0.0

    # FAQ (よくある質問)
    faq_keywords = ["faq", "質問", "q&a", "よくある"]
    coverage["faq"] = 1.0 if any(k in h2_text or k in text_lower for k in faq_keywords) else 0.0

    # Region (活動地域/所在地)
    # Check for common Japanese prefecture/city names or address patterns
    region_keywords = ["東京", "大阪", "名古屋", "福岡", "札幌", "所在地", "住所", "アクセス", "location", "address"]
    coverage["region"] = 1.0 if any(k in text_lower for k in region_keywords) else 0.0

    # Team/Operator (メンバー/運営情報)
    team_keywords = ["メンバー", "運営", "代表", "チーム", "スタッフ", "team", "member", "staff", "founder"]
    coverage["team_or_operator"] = 1.0 if any(k in h2_text or k in text_lower for k in team_keywords) else 0.0

    # Freshness (最新情報/更新性)
    # Check for news/update sections or recent year mentions
    import datetime
    current_year = str(datetime.datetime.now().year)
    last_year = str(datetime.datetime.now().year - 1)
    freshness_keywords = ["最新", "ニュース", "お知らせ", "news", "update", current_year, last_year]
    coverage["freshness"] = 1.0 if any(k in h2_text or k in text_lower[:3000] for k in freshness_keywords) else 0.0

    # Audience Branch (観客/参加希望の導線分岐)
    audience_keywords = ["観客", "参加希望", "初めての方", "はじめて", "visitor", "first time", "for beginners"]
    coverage["audience_branch"] = 1.0 if any(k in text_lower for k in audience_keywords) else 0.0

    return coverage


def _check_third_party_intent(
    title: str,
    h2_list: List[str],
    text: str,
    links: Dict[str, Any],
    brand_terms: Optional[List[str]] = None
) -> Dict[str, float]:
    """
    Check intent coverage for third-party profile pages

    Uses keyword matching and brand term detection
    """
    coverage: Dict[str, float] = {}

    h2_text = " ".join(h2_list).lower()
    text_lower = text.lower()
    title_lower = title.lower()

    # Brand Clear (自社名が明確)
    brand_found = False
    if brand_terms:
        brand_terms_lower = [t.lower() for t in brand_terms]
        brand_found = any(term in title_lower or term in h2_text for term in brand_terms_lower)
    coverage["brand_clear"] = 1.0 if brand_found else 0.0

    # Description Depth (説明文十分 >= 200字)
    # Count text excluding common boilerplate
    meaningful_text = text_lower
    coverage["description_depth"] = 1.0 if len(meaningful_text) >= 200 else 0.0

    # Unique Points (特徴・差別化)
    unique_keywords = ["特徴", "強み", "魅力", "ユニーク", "違い", "こだわり", "feature", "unique", "specialty"]
    coverage["unique_points"] = 1.0 if any(k in h2_text or k in text_lower for k in unique_keywords) else 0.0

    # Region/Genre (地域/ジャンル)
    region_genre_keywords = ["東京", "大阪", "ジャンル", "種類", "カテゴリ", "演劇", "音楽", "ダンス"]
    coverage["region_or_genre"] = 1.0 if any(k in text_lower for k in region_genre_keywords) else 0.0

    # Official Link (公式HPリンク)
    official_link_keywords = ["公式", "オフィシャル", "official", "ホームページ", "website"]
    has_official_link = any(k in text_lower for k in official_link_keywords)
    has_external_links = links.get("external_count", 0) > 0
    coverage["official_link"] = 1.0 if (has_official_link or has_external_links) else 0.0

    # CTA Present (参加/予約導線)
    cta_keywords = ["参加", "予約", "申込", "チケット", "購入", "book", "reserve", "ticket", "buy"]
    coverage["cta_present"] = 1.0 if any(k in text_lower for k in cta_keywords) else 0.0

    return coverage


def compute_content_score(
    page_type: str,
    intent_coverage: Dict[str, float],
    cfg: Optional[Dict[str, Any]] = None
) -> str:
    """
    Compute content score grade (A/B/C/D) based on intent coverage

    Args:
        page_type: Page type
        intent_coverage: Intent coverage dictionary
        cfg: Configuration with grade thresholds

    Returns:
        Score grade: "A", "B", "C", or "D"
    """
    # Sum coverage points
    total_coverage = sum(intent_coverage.values())

    if page_type in ["official_homepage", "competitor_page"]:
        # 10 items max
        if cfg and "content" in cfg:
            grade_cfg = cfg["content"].get("official_grade", {})
            a_min = grade_cfg.get("A_min", 9)
            b_min = grade_cfg.get("B_min", 7)
            c_min = grade_cfg.get("C_min", 5)
        else:
            a_min, b_min, c_min = 9, 7, 5

        if total_coverage >= a_min:
            return "A"
        elif total_coverage >= b_min:
            return "B"
        elif total_coverage >= c_min:
            return "C"
        else:
            return "D"

    else:  # third_party
        # 6 items max
        if cfg and "content" in cfg:
            grade_cfg = cfg["content"].get("third_party_grade", {})
            a_min = grade_cfg.get("A_min", 6)
            b_min = grade_cfg.get("B_min", 5)
            c_min = grade_cfg.get("C_min", 3)
        else:
            a_min, b_min, c_min = 6, 5, 3

        if total_coverage >= a_min:
            return "A"
        elif total_coverage >= b_min:
            return "B"
        elif total_coverage >= c_min:
            return "C"
        else:
            return "D"
