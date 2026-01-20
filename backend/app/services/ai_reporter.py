"""
AI Reporter - LLMを使ったレポート生成
"""

import json
from typing import Any, Dict, List, Optional

# Prompt template for report generation
PROMPT_TEMPLATE = """あなたはSEOコンサルタントです。以下の入力データ（JSON）に基づき、Markdown形式の「SEO診断レポート」を作成してください。

【厳守ルール】
- 推測しない。根拠がない断定は禁止。根拠がない場合は「可能性」「要確認」と書く。
- すべての重要な指摘には、必ず入力JSON内の evidence（数値・差分・観測結果）を引用して根拠を示す。
- 出力は指定のMarkdown見出し構造を必ず守る。
- ToDoは P0/P1/P2 に分け、各ToDoに「手順」「具体案（例）」「根拠」「検証指標」を含める。
- 紹介記事ページは「修正依頼できること」と「自社側代替策」を分けて書く。
- 競合のSearch Consoleデータはない前提で、構造・訴求・テクニカル差から理由を述べる。

【出力構造（必須）】
# SEO診断レポート
## 対象URL
## 結論（最優先3点）
## 原因推定（なぜ伸びないか・差があるか）
## 公式ホームページ 改善ToDo（P0/P1/P2）
## 紹介記事ページ 改善依頼（依頼テンプレ付き）
## 競合との差分（構造・訴求・テクニカル）
## 検証計画（7日 / 28日）

【入力JSON】
{AI_PROMPT_PAYLOAD_JSON}
"""


async def generate_report_md(
    ai_payload: Dict[str, Any],
    cfg: Optional[Dict[str, Any]] = None
) -> str:
    """
    Generate markdown report using LLM

    Args:
        ai_payload: AI prompt payload with analysis data
        cfg: Configuration dictionary

    Returns:
        Generated markdown report
    """
    # Build prompt
    payload_json = json.dumps(ai_payload, ensure_ascii=False, indent=2)
    prompt = PROMPT_TEMPLATE.replace("{AI_PROMPT_PAYLOAD_JSON}", payload_json)

    # Try OpenAI first, then Anthropic
    md = await _try_openai(prompt, cfg)
    if md is None:
        md = await _try_anthropic(prompt, cfg)

    if md is None:
        # Fallback to template-based report
        md = _generate_fallback_report(ai_payload)

    # Validate and repair if needed
    if not validate_report_markdown(md):
        md = _repair_report(ai_payload, md)

    return md


async def _try_openai(prompt: str, cfg: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """Try generating report with OpenAI"""
    try:
        from openai import AsyncOpenAI
        from app.config import get_settings

        settings = get_settings()
        if not settings.openai_api_key:
            return None

        client = AsyncOpenAI(api_key=settings.openai_api_key)

        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=4000
        )

        return response.choices[0].message.content

    except ImportError:
        return None
    except Exception as e:
        print(f"OpenAI error: {e}")
        return None


async def _try_anthropic(prompt: str, cfg: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """Try generating report with Anthropic"""
    try:
        from anthropic import AsyncAnthropic
        from app.config import get_settings

        settings = get_settings()
        if not settings.anthropic_api_key:
            return None

        client = AsyncAnthropic(api_key=settings.anthropic_api_key)

        response = await client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}]
        )

        return response.content[0].text

    except ImportError:
        return None
    except Exception as e:
        print(f"Anthropic error: {e}")
        return None


def validate_report_markdown(md: str) -> bool:
    """
    Validate that report contains required headings

    Args:
        md: Markdown content

    Returns:
        True if valid, False otherwise
    """
    required_headings = [
        "# SEO診断レポート",
        "## 対象URL",
        "## 結論",
        "## 原因推定",
        "## 公式ホームページ",
        "## 競合との差分",
        "## 検証計画"
    ]

    md_lower = md.lower()
    for heading in required_headings:
        # Check for heading (case-insensitive for some parts)
        if heading.lower() not in md_lower and heading not in md:
            return False

    return True


def _repair_report(ai_payload: Dict[str, Any], md: str) -> str:
    """
    Repair report by adding missing sections

    Args:
        ai_payload: Original AI payload
        md: Incomplete markdown

    Returns:
        Repaired markdown
    """
    # If completely invalid, generate fallback
    if "SEO診断レポート" not in md and "対象URL" not in md:
        return _generate_fallback_report(ai_payload)

    # Add missing sections
    sections = {
        "## 対象URL": _generate_target_urls_section(ai_payload),
        "## 結論（最優先3点）": _generate_conclusion_section(ai_payload),
        "## 原因推定（なぜ伸びないか・差があるか）": _generate_cause_section(ai_payload),
        "## 公式ホームページ 改善ToDo（P0/P1/P2）": _generate_todos_section(ai_payload),
        "## 紹介記事ページ 改善依頼（依頼テンプレ付き）": _generate_third_party_section(ai_payload),
        "## 競合との差分（構造・訴求・テクニカル）": _generate_diff_section(ai_payload),
        "## 検証計画（7日 / 28日）": _generate_verification_section(ai_payload)
    }

    for heading, content in sections.items():
        if heading not in md:
            md += f"\n\n{heading}\n\n{content}"

    return md


def _generate_fallback_report(ai_payload: Dict[str, Any]) -> str:
    """Generate a template-based fallback report"""
    data = ai_payload.get("data", {})

    report = "# SEO診断レポート\n\n"
    report += _generate_target_urls_section(ai_payload)
    report += "\n\n## 結論（最優先3点）\n\n"
    report += _generate_conclusion_section(ai_payload)
    report += "\n\n## 原因推定（なぜ伸びないか・差があるか）\n\n"
    report += _generate_cause_section(ai_payload)
    report += "\n\n## 公式ホームページ 改善ToDo（P0/P1/P2）\n\n"
    report += _generate_todos_section(ai_payload)
    report += "\n\n## 紹介記事ページ 改善依頼（依頼テンプレ付き）\n\n"
    report += _generate_third_party_section(ai_payload)
    report += "\n\n## 競合との差分（構造・訴求・テクニカル）\n\n"
    report += _generate_diff_section(ai_payload)
    report += "\n\n## 検証計画（7日 / 28日）\n\n"
    report += _generate_verification_section(ai_payload)

    return report


def _generate_target_urls_section(ai_payload: Dict[str, Any]) -> str:
    """Generate target URLs section"""
    data = ai_payload.get("data", {})
    pages = data.get("pages", [])

    section = "## 対象URL\n\n"

    for page in pages:
        page_type = page.get("page_type", "")
        url = page.get("url", "")
        label = ""

        if page_type == "official_homepage":
            label = "**公式HP**: "
        elif page_type == "competitor_page":
            label = "**競合**: "
        elif page_type == "third_party_profile_page":
            label = "**紹介記事**: "

        section += f"- {label}{url}\n"

    return section


def _generate_conclusion_section(ai_payload: Dict[str, Any]) -> str:
    """Generate conclusion section"""
    data = ai_payload.get("data", {})
    diagnosis = data.get("diagnosis", {})
    todos = data.get("todos", [])

    section = ""
    p0_todos = [t for t in todos if t.get("priority") == "P0"]

    for i, todo in enumerate(p0_todos[:3], 1):
        section += f"### {i}. {todo.get('title', '改善項目')}\n\n"
        section += f"- **内容**: {todo.get('details', '')}\n"
        section += f"- **根拠**: {', '.join(todo.get('evidence', []))}\n"
        section += f"- **優先度**: {todo.get('priority', 'P0')}\n\n"

    if not p0_todos:
        section += "現時点で致命的な問題は検出されませんでした。P1/P2の改善に取り組むことを推奨します。\n"

    return section


def _generate_cause_section(ai_payload: Dict[str, Any]) -> str:
    """Generate cause analysis section"""
    data = ai_payload.get("data", {})
    diagnosis = data.get("diagnosis", {})

    main_cause = diagnosis.get("main_cause", "unknown")
    breakdown = diagnosis.get("cause_breakdown", {})
    evidence = diagnosis.get("evidence", [])

    section = f"**主因**: {main_cause}\n\n"
    section += "**内訳**:\n"
    section += f"- コンテンツ品質: {breakdown.get('content_quality', 0)}%\n"
    section += f"- CTR: {breakdown.get('ctr', 0)}%\n"
    section += f"- テクニカル: {breakdown.get('technical', 0)}%\n\n"

    if evidence:
        section += "**根拠**:\n"
        for e in evidence:
            section += f"- {e.get('claim', '')}\n"
            for s in e.get("support", []):
                section += f"  - {s}\n"

    return section


def _generate_todos_section(ai_payload: Dict[str, Any]) -> str:
    """Generate todos section"""
    data = ai_payload.get("data", {})
    todos = data.get("todos", [])

    section = ""

    for priority in ["P0", "P1", "P2"]:
        priority_todos = [t for t in todos if t.get("priority") == priority]
        if not priority_todos:
            continue

        section += f"### {priority}（{'今すぐ' if priority == 'P0' else '1-2週間' if priority == 'P1' else '継続'}）\n\n"

        for todo in priority_todos:
            section += f"#### {todo.get('title', '')}\n\n"
            section += f"- **詳細**: {todo.get('details', '')}\n"
            section += f"- **影響度**: {todo.get('impact', 'medium')}\n"
            section += f"- **工数**: {todo.get('effort', 'medium')}\n"

            examples = todo.get("examples", {})
            if examples:
                if examples.get("faq_questions"):
                    section += "- **FAQ案**:\n"
                    for q in examples["faq_questions"]:
                        section += f"  - {q}\n"
            section += "\n"

    return section


def _generate_third_party_section(ai_payload: Dict[str, Any]) -> str:
    """Generate third-party section"""
    data = ai_payload.get("data", {})
    pages = data.get("pages", [])

    third_party = [p for p in pages if p.get("page_type") == "third_party_profile_page"]

    if not third_party:
        return "紹介記事ページは対象に含まれていません。\n"

    section = ""
    for page in third_party:
        url = page.get("url", "")
        missing = page.get("missing_sections", [])

        section += f"### {url}\n\n"

        if missing:
            section += "**改善依頼項目**:\n"
            for item in missing:
                section += f"- {item}\n"

        section += "\n**依頼テンプレート**:\n\n"
        section += "```\n"
        section += "お世話になっております。\n"
        section += "掲載いただいている紹介ページについて、以下の点の追記をお願いできますでしょうか。\n\n"
        section += "1. 公式ホームページへのリンク追加\n"
        section += "2. 活動地域の明記\n"
        section += "3. 参加方法の案内\n\n"
        section += "ご検討いただけますと幸いです。\n"
        section += "```\n\n"

    return section


def _generate_diff_section(ai_payload: Dict[str, Any]) -> str:
    """Generate competitor diff section"""
    data = ai_payload.get("data", {})
    comparisons = data.get("comparisons", [])

    if not comparisons:
        return "競合比較データはありません。\n"

    section = "| 項目 | 自社 | 競合 | 差分 |\n"
    section += "|------|------|------|------|\n"

    for comp in comparisons:
        diff = comp.get("diff", {})
        structure = diff.get("structure", {})
        tech = diff.get("tech", {})

        h2_delta = structure.get("h2_count_delta", 0)
        faq_delta = structure.get("faq_schema_delta", 0)
        perf_delta = tech.get("performance_score_delta")

        section += f"| H2見出し数 | - | - | {h2_delta:+d} |\n"
        section += f"| FAQ schema | {'あり' if faq_delta >= 0 else 'なし'} | {'あり' if faq_delta <= 0 else 'なし'} | {faq_delta:+d} |\n"

        if perf_delta is not None:
            section += f"| PageSpeed | - | - | {perf_delta:+d} |\n"

        missing_items = structure.get("missing_intent_items", [])
        if missing_items:
            section += f"\n**競合にあり自社にない要素**: {', '.join(missing_items)}\n"

    return section


def _generate_verification_section(ai_payload: Dict[str, Any]) -> str:
    """Generate verification plan section"""
    section = "### 7日後\n\n"
    section += "- [ ] P0タスクの完了確認\n"
    section += "- [ ] インデックス状況の確認\n"
    section += "- [ ] CTRの変化確認（Search Console）\n\n"

    section += "### 28日後\n\n"
    section += "- [ ] 検索順位の変化確認\n"
    section += "- [ ] オーガニックトラフィックの変化確認\n"
    section += "- [ ] P1タスクの進捗確認\n"
    section += "- [ ] 競合との差分の再評価\n"

    return section


def build_ai_prompt_payload(
    pages: List[Dict[str, Any]],
    comparisons: List[Dict[str, Any]],
    diagnosis: Dict[str, Any],
    todos: List[Dict[str, Any]],
    cfg: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Build AI prompt payload from analysis results

    Args:
        pages: List of page analysis objects
        comparisons: List of comparison objects
        diagnosis: Diagnosis object
        todos: List of todo objects
        cfg: Configuration dictionary

    Returns:
        AI prompt payload dictionary
    """
    # Build summary
    main_cause = diagnosis.get("main_cause", "unknown")
    scores = diagnosis.get("scores", {})
    summary = f"主因: {main_cause}。"
    summary += f"スコア - コンテンツ: {scores.get('content', 'D')}, "
    summary += f"テクニカル: {scores.get('technical', 'D')}, "
    summary += f"CTR: {scores.get('ctr', 'D')}"

    # Slim pages for AI
    slim_pages = []
    for page in pages:
        slim_page = {
            "url": page.get("url", ""),
            "page_type": page.get("page_type", ""),
            "title": page.get("html", {}).get("title", ""),
            "meta_description": page.get("html", {}).get("meta_description", ""),
            "h2_list": page.get("html", {}).get("headings", {}).get("h2", [])[:20],
            "intent_coverage": page.get("content", {}).get("intent_coverage", {}),
            "missing_sections": page.get("content", {}).get("missing_sections", []),
            "pagespeed_score": page.get("tech", {}).get("pagespeed", {}).get("performance_score")
        }
        slim_pages.append(slim_page)

    # Slim comparisons
    slim_comparisons = []
    for comp in comparisons:
        diff = comp.get("diff", {})
        slim_comp = {
            "kind": comp.get("kind", ""),
            "h2_count_delta": diff.get("structure", {}).get("h2_count_delta", 0),
            "missing_intent_items": diff.get("structure", {}).get("missing_intent_items", []),
            "faq_schema_delta": diff.get("structure", {}).get("faq_schema_delta", 0),
            "performance_score_delta": diff.get("tech", {}).get("performance_score_delta")
        }
        slim_comparisons.append(slim_comp)

    # Slim todos
    slim_todos = []
    for todo in todos:
        slim_todo = {
            "priority": todo.get("priority", "P2"),
            "category": todo.get("category", "content"),
            "title": todo.get("title", ""),
            "details": todo.get("details", ""),
            "evidence": todo.get("evidence", []),
            "impact": todo.get("impact", "medium"),
            "effort": todo.get("effort", "medium")
        }
        if todo.get("examples"):
            slim_todo["examples"] = todo["examples"]
        slim_todos.append(slim_todo)

    # Get config values
    ai_cfg = cfg.get("ai", {}) if cfg else {}
    app_cfg = cfg.get("app", {}) if cfg else {}

    return {
        "report_language": ai_cfg.get("language", "ja"),
        "report_style": ai_cfg.get("report_style", "consultant"),
        "constraints": {
            "must_cite_evidence": ai_cfg.get("must_cite_evidence", True),
            "no_guessing": ai_cfg.get("no_guessing", True),
            "max_todos_per_priority": app_cfg.get("max_todos_per_priority", 5)
        },
        "data": {
            "summary": summary,
            "pages": slim_pages,
            "comparisons": slim_comparisons,
            "diagnosis": diagnosis,
            "todos": slim_todos
        }
    }
