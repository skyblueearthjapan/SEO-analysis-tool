"""
Rule Engine - スコアリング + 原因推定 + ToDo生成
"""

from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4


def compute_technical_score(
    pagespeed_score: Optional[int],
    robots_meta: str,
    status_code: int,
    mobile_hint: str,
    has_organization_schema: bool = False,
    has_faq_schema: bool = False,
    cfg: Optional[Dict[str, Any]] = None
) -> str:
    """
    Compute technical score (A/B/C/D)

    Args:
        pagespeed_score: PageSpeed performance score (0-100)
        robots_meta: Robots meta tag content
        status_code: HTTP status code
        mobile_hint: Mobile-friendly hint
        has_organization_schema: Has Organization schema
        has_faq_schema: Has FAQ schema
        cfg: Configuration dictionary

    Returns:
        Score grade: "A", "B", "C", or "D"
    """
    # Get thresholds from config
    if cfg and "technical" in cfg:
        ps_cfg = cfg["technical"].get("pagespeed", {}).get("score", {})
        a_min = ps_cfg.get("A_min", 85)
        b_min = ps_cfg.get("B_min", 70)
        c_min = ps_cfg.get("C_min", 50)
    else:
        a_min, b_min, c_min = 85, 70, 50

    # D: Critical issues
    if status_code != 200:
        return "D"
    if "noindex" in robots_meta.lower():
        return "D"
    if pagespeed_score is not None and pagespeed_score < c_min:
        return "D"

    # C: Needs improvement
    if pagespeed_score is not None and c_min <= pagespeed_score < b_min:
        return "C"
    if mobile_hint == "fail":
        return "C"

    # B: Good
    if pagespeed_score is not None and b_min <= pagespeed_score < a_min:
        return "B"

    # A: Excellent
    if pagespeed_score is not None and pagespeed_score >= a_min:
        # Bonus check for schemas
        if has_organization_schema or has_faq_schema:
            return "A"
        return "A"

    # Default to B if no pagespeed data but no critical issues
    return "B"


def compute_content_score(
    intent_coverage: Dict[str, float],
    page_type: str,
    cfg: Optional[Dict[str, Any]] = None
) -> str:
    """
    Compute content score (A/B/C/D) based on intent coverage

    Args:
        intent_coverage: Intent coverage dictionary
        page_type: Page type
        cfg: Configuration dictionary

    Returns:
        Score grade: "A", "B", "C", or "D"
    """
    total = sum(intent_coverage.values())

    if page_type in ["official_homepage", "competitor_page"]:
        # 10 items max
        if cfg and "content" in cfg:
            grade_cfg = cfg["content"].get("official_grade", {})
            a_min = grade_cfg.get("A_min", 9)
            b_min = grade_cfg.get("B_min", 7)
            c_min = grade_cfg.get("C_min", 5)
        else:
            a_min, b_min, c_min = 9, 7, 5
    else:
        # 6 items max
        if cfg and "content" in cfg:
            grade_cfg = cfg["content"].get("third_party_grade", {})
            a_min = grade_cfg.get("A_min", 6)
            b_min = grade_cfg.get("B_min", 5)
            c_min = grade_cfg.get("C_min", 3)
        else:
            a_min, b_min, c_min = 6, 5, 3

    if total >= a_min:
        return "A"
    elif total >= b_min:
        return "B"
    elif total >= c_min:
        return "C"
    else:
        return "D"


def compute_ctr_score(
    top_queries: List[Dict[str, Any]],
    cfg: Optional[Dict[str, Any]] = None
) -> str:
    """
    Compute CTR score (A/B/C/D) based on opportunity ratio

    Args:
        top_queries: List of query data from Search Console
        cfg: Configuration dictionary

    Returns:
        Score grade: "A", "B", "C", or "D"
    """
    if not top_queries:
        return "B"  # Default if no data

    # Get thresholds
    if cfg and "ctr" in cfg:
        opp_cfg = cfg["ctr"].get("opportunity", {})
        min_imp_1 = opp_cfg.get("min_impressions_1", 300)
        min_imp_2 = opp_cfg.get("min_impressions_2", 500)
        pos_max_1 = opp_cfg.get("pos_max_1", 10)
        pos_max_2 = opp_cfg.get("pos_max_2", 5)
        ctr_low_ratio = opp_cfg.get("ctr_low_ratio_to_median", 0.5)
        ctr_hard_low = opp_cfg.get("ctr_hard_low", 0.03)

        grade_cfg = cfg["ctr"].get("grade", {})
        a_max = grade_cfg.get("A_max_opportunity_ratio", 0.10)
        b_max = grade_cfg.get("B_max_opportunity_ratio", 0.20)
        c_max = grade_cfg.get("C_max_opportunity_ratio", 0.35)
    else:
        min_imp_1, min_imp_2 = 300, 500
        pos_max_1, pos_max_2 = 10, 5
        ctr_low_ratio, ctr_hard_low = 0.5, 0.03
        a_max, b_max, c_max = 0.10, 0.20, 0.35

    # Calculate median CTR
    ctrs = [q.get("ctr", 0) for q in top_queries if q.get("ctr") is not None]
    if not ctrs:
        return "B"
    median_ctr = sorted(ctrs)[len(ctrs) // 2]

    # Count opportunities
    opportunities = 0
    for q in top_queries:
        impressions = q.get("impressions", 0)
        position = q.get("position", 100)
        ctr = q.get("ctr", 0)

        # Opportunity condition 1
        if impressions >= min_imp_1 and position <= pos_max_1 and ctr <= ctr_low_ratio * median_ctr:
            opportunities += 1
        # Opportunity condition 2
        elif impressions >= min_imp_2 and position <= pos_max_2 and ctr < ctr_hard_low:
            opportunities += 1

    # Calculate ratio
    opportunity_ratio = opportunities / len(top_queries) if top_queries else 0

    if opportunity_ratio <= a_max:
        return "A"
    elif opportunity_ratio <= b_max:
        return "B"
    elif opportunity_ratio <= c_max:
        return "C"
    else:
        return "D"


def compute_scores(
    pages: List[Dict[str, Any]],
    cfg: Optional[Dict[str, Any]] = None
) -> Dict[str, str]:
    """
    Compute all scores for the analysis

    Args:
        pages: List of page analysis objects
        cfg: Configuration dictionary

    Returns:
        Dictionary with content, technical, ctr scores
    """
    # Find official page
    official = None
    for page in pages:
        if page.get("page_type") == "official_homepage":
            official = page
            break

    if not official:
        return {"content": "D", "technical": "D", "ctr": "D"}

    # Technical score
    tech = official.get("tech", {})
    pagespeed = tech.get("pagespeed", {})
    html = official.get("html", {})
    fetch = official.get("fetch", {})
    structured_data = html.get("structured_data", {})

    technical_score = compute_technical_score(
        pagespeed_score=pagespeed.get("performance_score"),
        robots_meta=html.get("robots_meta", ""),
        status_code=fetch.get("status_code", 0),
        mobile_hint=tech.get("mobile_friendly_hint", "not_available"),
        has_organization_schema=structured_data.get("has_organization_schema", False),
        has_faq_schema=structured_data.get("has_faq_schema", False),
        cfg=cfg
    )

    # Content score
    content = official.get("content", {})
    content_score = compute_content_score(
        intent_coverage=content.get("intent_coverage", {}),
        page_type=official.get("page_type", "official_homepage"),
        cfg=cfg
    )

    # CTR score
    gsc = official.get("search_console", {})
    top_queries = gsc.get("top_queries", [])
    ctr_score = compute_ctr_score(top_queries, cfg)

    return {
        "content": content_score,
        "technical": technical_score,
        "ctr": ctr_score
    }


def compute_main_cause(
    scores: Dict[str, str],
    comparisons: List[Dict[str, Any]],
    cfg: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Compute main cause and breakdown

    Args:
        scores: Dictionary with content, technical, ctr scores
        comparisons: List of comparison objects
        cfg: Configuration dictionary

    Returns:
        Dictionary with main_cause and breakdown
    """
    breakdown = {"content_quality": 0, "ctr": 0, "technical": 0}

    # Technical (priority)
    if scores.get("technical") in ["C", "D"]:
        breakdown["technical"] = 50

    # Content
    if scores.get("content") in ["C", "D"]:
        breakdown["content_quality"] = 40

    # Check comparison data
    for comp in comparisons:
        diff = comp.get("diff", {})
        structure = diff.get("structure", {})

        # Missing many intent items
        missing = len(structure.get("missing_intent_items", []))
        if missing >= 3:
            breakdown["content_quality"] += 10

        # H2 count significantly lower
        h2_delta = structure.get("h2_count_delta", 0)
        if h2_delta <= -5:
            breakdown["content_quality"] += 10

    # CTR
    if scores.get("ctr") in ["C", "D"]:
        breakdown["ctr"] = 30

    # Normalize to 100%
    total = sum(breakdown.values()) or 1
    breakdown = {k: int(v / total * 100) for k, v in breakdown.items()}

    # Determine main cause
    max_key = max(breakdown, key=breakdown.get)
    max_val = breakdown[max_key]

    if max_val < 45:
        main_cause = "mixed"
    else:
        main_cause = max_key

    return {"main_cause": main_cause, "breakdown": breakdown}


def build_evidence(
    official: Dict[str, Any],
    comparisons: List[Dict[str, Any]],
    scores: Dict[str, str],
    cause: Dict[str, Any],
    cfg: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Build evidence list for diagnosis

    Args:
        official: Official page analysis
        comparisons: List of comparison objects
        scores: Score dictionary
        cause: Main cause and breakdown
        cfg: Configuration dictionary

    Returns:
        List of evidence objects with claim and support
    """
    evidence = []

    # Technical evidence
    tech = official.get("tech", {})
    pagespeed = tech.get("pagespeed", {})

    if scores.get("technical") in ["C", "D"]:
        support = []
        perf_score = pagespeed.get("performance_score")
        if perf_score is not None and perf_score < 70:
            support.append(f"PageSpeed Performance Score: {perf_score}")

        fetch = official.get("fetch", {})
        if fetch.get("status_code") != 200:
            support.append(f"HTTP Status: {fetch.get('status_code')}")

        html = official.get("html", {})
        if "noindex" in html.get("robots_meta", "").lower():
            support.append("robots metaにnoindexが設定されている")

        if support:
            evidence.append({
                "claim": "テクニカル面に課題がある",
                "support": support
            })

    # Content evidence
    if scores.get("content") in ["C", "D"]:
        content = official.get("content", {})
        missing = content.get("missing_sections", [])

        if missing:
            evidence.append({
                "claim": "コンテンツで意図カバーが不足している",
                "support": [f"不足セクション: {', '.join(missing[:5])}"]
            })

    # Comparison evidence
    for comp in comparisons:
        diff = comp.get("diff", {})
        structure = diff.get("structure", {})

        missing_items = structure.get("missing_intent_items", [])
        if missing_items:
            evidence.append({
                "claim": "競合に比べて欠けている要素がある",
                "support": [f"競合にあり自社にない: {', '.join(missing_items[:5])}"]
            })
            break  # One comparison is enough

    return evidence


def generate_todos(
    pages: List[Dict[str, Any]],
    comparisons: List[Dict[str, Any]],
    diagnosis: Dict[str, Any],
    cfg: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Generate ToDo list based on analysis

    Args:
        pages: List of page analysis objects
        comparisons: List of comparison objects
        diagnosis: Diagnosis object with scores and cause
        cfg: Configuration dictionary

    Returns:
        List of ToDo objects
    """
    todos = []

    # Find official page
    official = None
    for page in pages:
        if page.get("page_type") == "official_homepage":
            official = page
            break

    if not official:
        return todos

    fetch = official.get("fetch", {})
    html = official.get("html", {})
    content = official.get("content", {})
    tech = official.get("tech", {})
    gsc = official.get("search_console", {})
    structured_data = html.get("structured_data", {})

    # P0: Critical issues
    # HTTP status not 200
    if fetch.get("status_code") != 200:
        detail = _get_detail_for_todo("http_status", {
            "evidence_data": [{
                "id": "ev_http_status",
                "title": "HTTP取得結果",
                "kind": "fetch",
                "severity": "critical",
                "data": {
                    "url": official.get("url"),
                    "status_code": fetch.get("status_code"),
                    "final_url": fetch.get("final_url")
                }
            }]
        })
        todos.append(_create_todo(
            "P0", "technical",
            "HTTPステータスコードの修正",
            f"ステータスコード {fetch.get('status_code')} を 200 に修正する",
            ["indexing_critical"],
            "high", "medium",
            detail=detail
        ))

    # noindex
    if "noindex" in html.get("robots_meta", "").lower():
        detail = _get_detail_for_todo("noindex", {
            "evidence_data": [{
                "id": "ev_noindex",
                "title": "robots meta設定",
                "kind": "html",
                "severity": "critical",
                "data": {
                    "robots_meta": html.get("robots_meta")
                }
            }]
        })
        todos.append(_create_todo(
            "P0", "technical",
            "noindexタグの削除",
            "robots metaからnoindexを削除してインデックス可能にする",
            ["indexing_critical"],
            "high", "small",
            detail=detail
        ))

    # CTA missing
    if content.get("intent_coverage", {}).get("cta_contact", 0) == 0:
        detail = _get_detail_for_todo("cta_missing", {
            "evidence_data": [{
                "id": "ev_cta_missing",
                "title": "意図カバレッジ分析",
                "kind": "content",
                "severity": "warning",
                "data": {
                    "cta_contact_score": content.get("intent_coverage", {}).get("cta_contact", 0)
                }
            }]
        })
        todos.append(_create_todo(
            "P0", "content",
            "問い合わせ/参加導線（CTA）の追加",
            "ユーザーが次のアクションを取れるCTAボタンやセクションを追加",
            ["core_sections_missing"],
            "high", "small",
            detail=detail
        ))

    # Overview missing
    if content.get("intent_coverage", {}).get("overview", 0) == 0:
        detail = _get_detail_for_todo("overview_missing", {
            "evidence_data": [{
                "id": "ev_overview_missing",
                "title": "意図カバレッジ分析",
                "kind": "content",
                "severity": "warning",
                "data": {
                    "overview_score": content.get("intent_coverage", {}).get("overview", 0),
                    "missing_sections": content.get("missing_sections", [])
                }
            }]
        })
        todos.append(_create_todo(
            "P0", "content",
            "概要セクションの追加",
            "「私たちについて」「何者か」を説明するセクションを追加",
            ["core_sections_missing"],
            "high", "medium",
            detail=detail
        ))

    # P1: 1-2 weeks
    # FAQ section
    if not structured_data.get("has_faq_schema"):
        faq_questions = [
            "どのような活動をしていますか？",
            "参加方法を教えてください",
            "料金はいくらですか？",
            "初心者でも参加できますか？"
        ]
        detail = _get_detail_for_todo("faq_missing", {
            "evidence_data": [{
                "id": "ev_faq_missing",
                "title": "構造化データ分析",
                "kind": "schema",
                "severity": "info",
                "data": {
                    "has_faq_schema": False,
                    "schema_types": structured_data.get("types", [])
                }
            }]
        })
        todos.append(_create_todo(
            "P1", "content",
            "FAQセクションと構造化データの追加",
            "よくある質問セクションを追加し、FAQPage schemaをマークアップ",
            ["faq_addition"],
            "medium", "medium",
            examples={"faq_questions": faq_questions},
            detail=detail
        ))

    # Activities missing
    if content.get("intent_coverage", {}).get("activities", 0) == 0:
        detail = _get_detail_for_todo("activities_missing", {
            "evidence_data": [{
                "id": "ev_activities_missing",
                "title": "意図カバレッジ分析",
                "kind": "content",
                "severity": "warning",
                "data": {
                    "activities_score": content.get("intent_coverage", {}).get("activities", 0)
                }
            }]
        })
        todos.append(_create_todo(
            "P1", "content",
            "活動内容セクションの追加",
            "具体的な活動内容やサービス内容を説明するセクションを追加",
            ["intent_expansion"],
            "medium", "medium",
            detail=detail
        ))

    # Works/History missing
    if content.get("intent_coverage", {}).get("works_or_history", 0) == 0:
        todos.append(_create_todo(
            "P1", "content",
            "実績・履歴セクションの追加",
            "過去の公演や実績を紹介するセクションを追加",
            ["intent_expansion"],
            "medium", "medium"
        ))

    # Organization schema
    if not structured_data.get("has_organization_schema"):
        detail = _get_detail_for_todo("organization_schema", {
            "evidence_data": [{
                "id": "ev_org_schema_missing",
                "title": "構造化データ分析",
                "kind": "schema",
                "severity": "info",
                "data": {
                    "has_organization_schema": False,
                    "schema_types": structured_data.get("types", [])
                }
            }]
        })
        todos.append(_create_todo(
            "P1", "technical",
            "Organization構造化データの追加",
            "組織情報をschema.orgのOrganizationでマークアップ",
            ["schema_addition"],
            "medium", "small",
            detail=detail
        ))

    # PageSpeed improvement
    pagespeed = tech.get("pagespeed", {})
    perf_score = pagespeed.get("performance_score")
    if perf_score is not None and perf_score < 70:
        detail = _get_detail_for_todo("pagespeed", {
            "evidence_data": [{
                "id": "ev_pagespeed",
                "title": "PageSpeed分析",
                "kind": "tech",
                "severity": "warning",
                "data": {
                    "performance_score": perf_score,
                    "lcp_ms": pagespeed.get("lcp_ms"),
                    "cls": pagespeed.get("cls"),
                    "inp_ms": pagespeed.get("inp_ms")
                }
            }]
        })
        todos.append(_create_todo(
            "P1", "technical",
            "ページ速度の改善",
            f"現在のスコア {perf_score} を70以上に改善（画像最適化、JS削減等）",
            ["performance_improvement"],
            "medium", "large",
            detail=detail
        ))

    # P2: Ongoing
    # Content cluster
    detail_cluster = _get_detail_for_todo("content_cluster")
    todos.append(_create_todo(
        "P2", "content",
        "コンテンツクラスター化の検討",
        "関連コンテンツを体系化し、内部リンクで構造化",
        ["content_cluster"],
        "low", "large",
        detail=detail_cluster
    ))

    # External outreach
    detail_outreach = _get_detail_for_todo("outreach")
    todos.append(_create_todo(
        "P2", "outreach",
        "外部露出の強化",
        "紹介記事の追加依頼、SNS連携、PR活動の検討",
        ["ongoing_outreach"],
        "low", "large",
        detail=detail_outreach
    ))

    # Check comparisons for additional todos
    for comp in comparisons:
        diff = comp.get("diff", {})
        structure = diff.get("structure", {})

        # Competitor has FAQ but we don't
        if structure.get("faq_schema_delta", 0) < 0:
            if not any(t.get("title", "").startswith("FAQ") for t in todos):
                todos.append(_create_todo(
                    "P1", "content",
                    "競合にあるFAQの追加",
                    "競合サイトにあるFAQセクションを参考に自社にも追加",
                    ["competitor_advantage"],
                    "medium", "medium"
                ))
            break

    # Enforce limits
    return _enforce_limits(todos, cfg)


def _create_todo(
    priority: str,
    category: str,
    title: str,
    details: str,
    evidence: List[str],
    impact: str,
    effort: str,
    examples: Optional[Dict[str, Any]] = None,
    detail: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Create a ToDo object"""
    todo = {
        "todo_id": str(uuid4()),
        "priority": priority,
        "category": category,
        "title": title,
        "details": details,
        "evidence": evidence,
        "impact": impact,
        "effort": effort
    }
    if examples:
        todo["examples"] = examples
    if detail:
        todo["detail"] = detail
    return todo


# Todo Detail Templates - ルールベースで詳細情報を生成
TODO_DETAIL_TEMPLATES = {
    "http_status": {
        "why": "検索エンジンがページを正しく取得できず、インデックスや評価が進まない可能性があります。",
        "root_causes": [
            {"label": "サーバ側でエラーが発生している", "likelihood": "high", "notes": "500系エラーの場合"},
            {"label": "ページが削除または移動された", "likelihood": "medium", "notes": "404エラーの場合"},
            {"label": "WAF/認証でBotがブロックされている", "likelihood": "low", "notes": "特定のUser-Agentでのみ発生"}
        ],
        "steps": [
            {"text": "ブラウザとcurlでURLにアクセスし、実際のステータスコードを確認する", "done": False},
            {"text": "サーバログを確認してエラーの原因を特定する", "done": False},
            {"text": "必要に応じてリダイレクトまたはコンテンツを復旧する", "done": False},
            {"text": "Search ConsoleのURL検査で再クロールを依頼する", "done": False}
        ],
        "verification": [
            {"metric": "HTTPステータス", "target": "200", "how_to_check": "curl -I URL / ブラウザのDevTools"},
            {"metric": "インデックス状態", "target": "有効", "how_to_check": "GSC URL検査"}
        ]
    },
    "noindex": {
        "why": "noindexが設定されているため、検索エンジンにインデックスされず、検索結果に表示されません。",
        "root_causes": [
            {"label": "開発時の設定が残っている", "likelihood": "high", "notes": "テスト環境からの移行時によくある"},
            {"label": "CMSの設定ミス", "likelihood": "medium", "notes": "WordPressなどの設定"},
            {"label": "意図的に設定されたが不要になった", "likelihood": "low", "notes": ""}
        ],
        "steps": [
            {"text": "HTMLのmeta robotsタグを確認する", "done": False},
            {"text": "X-Robots-Tagヘッダーを確認する", "done": False},
            {"text": "noindexを削除または適切な値に変更する", "done": False},
            {"text": "変更をデプロイして再クロールを依頼する", "done": False}
        ],
        "verification": [
            {"metric": "robots meta", "target": "noindex無し", "how_to_check": "ページソースを確認"},
            {"metric": "インデックス状態", "target": "有効", "how_to_check": "GSC URL検査"}
        ]
    },
    "cta_missing": {
        "why": "CTAがないと、ユーザーが次のアクション（問い合わせ、申込など）を取りにくく、コンバージョンが低下します。",
        "root_causes": [
            {"label": "CTAの設計・配置が未実装", "likelihood": "high", "notes": ""},
            {"label": "CTAはあるが目立たない", "likelihood": "medium", "notes": "デザイン上の問題"},
        ],
        "steps": [
            {"text": "ページ上部（ファーストビュー内）にCTAボタンを配置する", "done": False},
            {"text": "ページ下部にもCTAセクションを追加する", "done": False},
            {"text": "ボタンの文言を行動を促すものにする（例：「お問い合わせ」「無料相談」）", "done": False}
        ],
        "templates": [
            {
                "title": "CTAボタン例",
                "type": "bullets",
                "content": "• お問い合わせはこちら\n• 無料相談を予約する\n• 資料をダウンロード\n• 今すぐ申し込む"
            }
        ],
        "verification": [
            {"metric": "CTAの存在", "target": "ファーストビュー内に1つ以上", "how_to_check": "目視確認"},
            {"metric": "クリック率", "target": "計測開始", "how_to_check": "GA4イベント設定"}
        ]
    },
    "overview_missing": {
        "why": "「私たちは何者か」が分からないと、ユーザーの信頼を得られず離脱率が高まります。",
        "root_causes": [
            {"label": "About/概要セクションが未作成", "likelihood": "high", "notes": ""},
            {"label": "情報が分散して分かりにくい", "likelihood": "medium", "notes": ""}
        ],
        "steps": [
            {"text": "「私たちについて」「会社概要」セクションを追加する", "done": False},
            {"text": "事業内容、設立年、実績などの基本情報を含める", "done": False},
            {"text": "代表者メッセージや理念があれば追加する", "done": False}
        ],
        "templates": [
            {
                "title": "概要セクション構成案",
                "type": "bullets",
                "content": "• 会社/団体名と設立年\n• 事業内容・サービス概要\n• ミッション・ビジョン\n• 所在地・連絡先"
            }
        ],
        "verification": [
            {"metric": "概要セクション", "target": "存在する", "how_to_check": "目視確認"},
            {"metric": "情報の充実度", "target": "基本情報が網羅されている", "how_to_check": "チェックリストで確認"}
        ]
    },
    "faq_missing": {
        "why": "FAQは検索結果でリッチスニペット表示される可能性があり、CTRの向上が期待できます。",
        "root_causes": [
            {"label": "FAQコンテンツが未作成", "likelihood": "high", "notes": ""},
            {"label": "FAQはあるが構造化データがない", "likelihood": "medium", "notes": ""}
        ],
        "steps": [
            {"text": "よくある質問を5-10個リストアップする", "done": False},
            {"text": "各質問に対する回答を作成する", "done": False},
            {"text": "FAQPage構造化データをマークアップする", "done": False},
            {"text": "リッチリザルトテストで確認する", "done": False}
        ],
        "templates": [
            {
                "title": "FAQPage JSON-LD 雛形",
                "type": "code",
                "language": "json",
                "content": '{\n  "@context": "https://schema.org",\n  "@type": "FAQPage",\n  "mainEntity": [\n    {\n      "@type": "Question",\n      "name": "質問をここに記載",\n      "acceptedAnswer": {\n        "@type": "Answer",\n        "text": "回答をここに記載"\n      }\n    }\n  ]\n}'
            }
        ],
        "verification": [
            {"metric": "FAQセクション", "target": "5問以上", "how_to_check": "目視確認"},
            {"metric": "構造化データ", "target": "有効", "how_to_check": "リッチリザルトテスト"}
        ]
    },
    "activities_missing": {
        "why": "具体的な活動内容がないと、ユーザーが何を期待できるか分からず離脱につながります。",
        "root_causes": [
            {"label": "活動内容ページが未作成", "likelihood": "high", "notes": ""},
            {"label": "情報が古い/不十分", "likelihood": "medium", "notes": ""}
        ],
        "steps": [
            {"text": "主要なサービス・活動を3-5個リストアップする", "done": False},
            {"text": "各活動の詳細説明を追加する", "done": False},
            {"text": "写真や実績を添えて説得力を高める", "done": False}
        ],
        "verification": [
            {"metric": "活動内容セクション", "target": "存在する", "how_to_check": "目視確認"}
        ]
    },
    "organization_schema": {
        "why": "Organization構造化データにより、検索結果でのブランド表示が強化される可能性があります。",
        "root_causes": [
            {"label": "構造化データが未実装", "likelihood": "high", "notes": ""}
        ],
        "steps": [
            {"text": "Organization JSON-LDを作成する", "done": False},
            {"text": "ロゴ、所在地、連絡先などを含める", "done": False},
            {"text": "headタグ内に埋め込む", "done": False},
            {"text": "リッチリザルトテストで確認する", "done": False}
        ],
        "templates": [
            {
                "title": "Organization JSON-LD 雛形",
                "type": "code",
                "language": "json",
                "content": '{\n  "@context": "https://schema.org",\n  "@type": "Organization",\n  "name": "組織名",\n  "url": "https://example.com",\n  "logo": "https://example.com/logo.png",\n  "address": {\n    "@type": "PostalAddress",\n    "addressCountry": "JP"\n  }\n}'
            }
        ],
        "verification": [
            {"metric": "構造化データ", "target": "有効", "how_to_check": "リッチリザルトテスト"}
        ]
    },
    "pagespeed": {
        "why": "ページ速度はCore Web Vitalsの一部であり、検索ランキングとユーザー体験に影響します。",
        "root_causes": [
            {"label": "画像が最適化されていない", "likelihood": "high", "notes": "WebP変換、圧縮"},
            {"label": "JavaScriptが重い", "likelihood": "medium", "notes": "バンドルサイズ、遅延読み込み"},
            {"label": "サーバー応答が遅い", "likelihood": "medium", "notes": "TTFB"}
        ],
        "steps": [
            {"text": "PageSpeed Insightsで詳細な診断を確認する", "done": False},
            {"text": "画像をWebP形式に変換し圧縮する", "done": False},
            {"text": "不要なJavaScriptを削除または遅延読み込みにする", "done": False},
            {"text": "キャッシュ設定を最適化する", "done": False}
        ],
        "verification": [
            {"metric": "PageSpeed Score", "target": "70以上", "how_to_check": "PageSpeed Insights"},
            {"metric": "LCP", "target": "2.5秒以下", "how_to_check": "PageSpeed Insights"}
        ]
    },
    "content_cluster": {
        "why": "関連コンテンツを体系化することで、サイト全体のトピック権威性が向上します。",
        "root_causes": [
            {"label": "コンテンツが散在している", "likelihood": "high", "notes": ""},
            {"label": "内部リンクが不足", "likelihood": "medium", "notes": ""}
        ],
        "steps": [
            {"text": "主要トピックを特定する", "done": False},
            {"text": "ピラーページ（まとめページ）を作成する", "done": False},
            {"text": "関連記事からピラーページへリンクする", "done": False},
            {"text": "ピラーページから各記事へリンクする", "done": False}
        ],
        "verification": [
            {"metric": "内部リンク", "target": "主要ページ間で相互リンク", "how_to_check": "サイトクローラー"}
        ]
    },
    "outreach": {
        "why": "外部からの言及やリンクは、サイトの信頼性と権威性を高めます。",
        "root_causes": [
            {"label": "PR活動が不足", "likelihood": "high", "notes": ""},
            {"label": "SNS連携がない", "likelihood": "medium", "notes": ""}
        ],
        "steps": [
            {"text": "関連メディアへのプレスリリースを検討する", "done": False},
            {"text": "業界団体や協会への登録を検討する", "done": False},
            {"text": "SNSアカウントを開設・運用する", "done": False},
            {"text": "イベントや活動を積極的に発信する", "done": False}
        ],
        "verification": [
            {"metric": "外部リンク", "target": "増加傾向", "how_to_check": "GSC / Ahrefs等"}
        ]
    }
}


def _get_detail_for_todo(todo_type: str, context: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """Get detail template for a todo type"""
    template = TODO_DETAIL_TEMPLATES.get(todo_type)
    if not template:
        return None

    detail = {
        "why": template.get("why", ""),
        "root_causes": template.get("root_causes", []),
        "evidence": [],  # Will be populated from context
        "steps": template.get("steps", []),
        "templates": template.get("templates", []),
        "verification": template.get("verification", []),
        "related_todo_ids": []
    }

    # Add evidence from context if provided
    if context:
        if context.get("evidence_data"):
            detail["evidence"] = context["evidence_data"]

    return detail


def _enforce_limits(
    todos: List[Dict[str, Any]],
    cfg: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Enforce todo limits (max 15 total, max 5 per priority)

    Args:
        todos: List of todos
        cfg: Configuration dictionary

    Returns:
        Limited list of todos
    """
    if cfg and "app" in cfg:
        max_total = cfg["app"].get("max_todos_total", 15)
        max_per_priority = cfg["app"].get("max_todos_per_priority", 5)
    else:
        max_total = 15
        max_per_priority = 5

    # Group by priority
    by_priority = {"P0": [], "P1": [], "P2": []}
    for todo in todos:
        p = todo.get("priority", "P2")
        if p in by_priority:
            by_priority[p].append(todo)

    # Limit per priority
    for p in by_priority:
        by_priority[p] = by_priority[p][:max_per_priority]

    # Combine and limit total
    result = by_priority["P0"] + by_priority["P1"] + by_priority["P2"]
    return result[:max_total]


def compute_overall_score_and_grade(scores: Dict[str, str]) -> Tuple[float, str]:
    """
    Compute overall score (0-100) and grade (A/B/C/D) from individual scores

    Args:
        scores: Dictionary with content, technical, ctr scores (A/B/C/D)

    Returns:
        Tuple of (overall_score, grade)
    """
    # Convert grades to numeric values
    grade_to_value = {"A": 90, "B": 75, "C": 55, "D": 30}

    content_val = grade_to_value.get(scores.get("content", "D"), 30)
    technical_val = grade_to_value.get(scores.get("technical", "D"), 30)
    ctr_val = grade_to_value.get(scores.get("ctr", "D"), 30)

    # Weighted average: content 50%, technical 30%, ctr 20%
    overall_score = content_val * 0.5 + technical_val * 0.3 + ctr_val * 0.2

    # Determine overall grade
    if overall_score >= 85:
        grade = "A"
    elif overall_score >= 70:
        grade = "B"
    elif overall_score >= 50:
        grade = "C"
    else:
        grade = "D"

    return round(overall_score, 1), grade


def run_rule_engine(
    pages: List[Dict[str, Any]],
    comparisons: List[Dict[str, Any]],
    cfg: Optional[Dict[str, Any]] = None
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Run the full rule engine

    Args:
        pages: List of page analysis objects
        comparisons: List of comparison objects
        cfg: Configuration dictionary

    Returns:
        Tuple of (diagnosis, todos)
    """
    # Find official page
    official = None
    for page in pages:
        if page.get("page_type") == "official_homepage":
            official = page
            break

    # Compute scores
    scores = compute_scores(pages, cfg)

    # Compute overall score and grade
    overall_score, grade = compute_overall_score_and_grade(scores)

    # Compute main cause
    cause = compute_main_cause(scores, comparisons, cfg)

    # Build evidence
    evidence = build_evidence(official, comparisons, scores, cause, cfg) if official else []

    # Build diagnosis
    diagnosis = {
        "main_cause": cause["main_cause"],
        "cause_breakdown": cause["breakdown"],
        "scores": scores,
        "overall_score": overall_score,
        "grade": grade,
        "evidence": evidence
    }

    # Generate todos
    todos = generate_todos(pages, comparisons, diagnosis, cfg)

    return diagnosis, todos
