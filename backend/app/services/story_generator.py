"""
Improvement Story Generator - 改善ストーリー自動生成 (Appendix AI)

改善の流れを自然な文章で説明し、「何をやって、どう変わったか」を自動要約する。
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional
from uuid import UUID


@dataclass
class MetricPair:
    """Before/After metric pair"""
    before: Optional[float] = None
    after: Optional[float] = None


@dataclass
class StoryInput:
    """Input data for story generation"""
    # Period
    range_from: str
    range_to: str

    # Before/After metrics
    serp_position: MetricPair = field(default_factory=MetricPair)
    ctr: MetricPair = field(default_factory=MetricPair)
    pagespeed: MetricPair = field(default_factory=MetricPair)
    crawl_errors: MetricPair = field(default_factory=MetricPair)
    ref_domains: MetricPair = field(default_factory=MetricPair)

    # Completed todos
    completed_todos: List[Dict[str, str]] = field(default_factory=list)

    # Site info
    site_name: str = ""
    url: str = ""


def generate_improvement_story(input_data: StoryInput) -> str:
    """
    Generate improvement story from metrics and completed todos

    Args:
        input_data: Story input data

    Returns:
        Generated story in Markdown format
    """
    # Group todos by category
    todo_by_category: Dict[str, List[str]] = {}
    for todo in input_data.completed_todos:
        cat = todo.get("category", "other")
        if cat not in todo_by_category:
            todo_by_category[cat] = []
        todo_by_category[cat].append(todo.get("title", ""))

    # Analyze metric changes
    changes: List[tuple] = []

    # SERP position (lower is better)
    if input_data.serp_position.before and input_data.serp_position.after:
        diff = input_data.serp_position.before - input_data.serp_position.after
        if diff > 0:
            changes.append((
                "平均掲載順位",
                "改善",
                f"{input_data.serp_position.before:.1f}位 → {input_data.serp_position.after:.1f}位"
            ))
        elif diff < -1:
            changes.append((
                "平均掲載順位",
                "低下",
                f"{input_data.serp_position.before:.1f}位 → {input_data.serp_position.after:.1f}位"
            ))

    # CTR (higher is better)
    if input_data.ctr.before is not None and input_data.ctr.after is not None:
        diff = input_data.ctr.after - input_data.ctr.before
        if diff > 0.001:
            changes.append((
                "CTR",
                "改善",
                f"{input_data.ctr.before * 100:.1f}% → {input_data.ctr.after * 100:.1f}%"
            ))
        elif diff < -0.005:
            changes.append((
                "CTR",
                "低下",
                f"{input_data.ctr.before * 100:.1f}% → {input_data.ctr.after * 100:.1f}%"
            ))

    # PageSpeed (higher is better)
    if input_data.pagespeed.before and input_data.pagespeed.after:
        diff = input_data.pagespeed.after - input_data.pagespeed.before
        if diff > 5:
            changes.append((
                "PageSpeed",
                "改善",
                f"{int(input_data.pagespeed.before)} → {int(input_data.pagespeed.after)}"
            ))
        elif diff < -5:
            changes.append((
                "PageSpeed",
                "低下",
                f"{int(input_data.pagespeed.before)} → {int(input_data.pagespeed.after)}"
            ))

    # Crawl errors (lower is better)
    if input_data.crawl_errors.before and input_data.crawl_errors.after:
        diff = input_data.crawl_errors.before - input_data.crawl_errors.after
        if diff > 0:
            changes.append((
                "クロールエラー",
                "減少",
                f"{int(input_data.crawl_errors.before)}件 → {int(input_data.crawl_errors.after)}件"
            ))
        elif diff < -2:
            changes.append((
                "クロールエラー",
                "増加",
                f"{int(input_data.crawl_errors.before)}件 → {int(input_data.crawl_errors.after)}件"
            ))

    # Referring domains (higher is better)
    if input_data.ref_domains.before and input_data.ref_domains.after:
        diff = input_data.ref_domains.after - input_data.ref_domains.before
        if diff > 0:
            changes.append((
                "参照ドメイン数",
                "増加",
                f"{int(input_data.ref_domains.before)} → {int(input_data.ref_domains.after)}"
            ))

    # Build story
    story = f"""## 改善レポート

対象サイト: {input_data.site_name or input_data.url or '(サイト名未設定)'}
期間: {input_data.range_from} 〜 {input_data.range_to}

### 実施した改善

"""

    if input_data.completed_todos:
        story += "この期間中、以下の改善を実施しました。\n\n"
        for todo in input_data.completed_todos[:10]:
            story += f"- {todo.get('title', '')}\n"
    else:
        story += "この期間中に完了したToDoはありません。\n"

    story += """
### 観測された変化

改善実施後、以下の変化が確認されています。

"""

    if changes:
        story += "| 指標 | 変化 | 詳細 |\n"
        story += "|------|------|------|\n"
        for metric, status, detail in changes:
            arrow = "▲" if status in ["改善", "増加", "減少"] else "▼"
            story += f"| {metric} | {arrow}{status} | {detail} |\n"
    else:
        story += "※ 有意な変化は確認されていません。\n"

    story += """
### 考察

"""

    # Generate analysis
    improvement_changes = [c for c in changes if c[1] in ["改善", "増加", "減少"]]
    decline_changes = [c for c in changes if c[1] in ["低下"]]

    if len(improvement_changes) >= 2:
        story += "複数の指標で改善が確認されています。"
        story += "これらの改善が、検索パフォーマンスの向上に寄与している可能性があります。\n\n"

        # Add specific analysis
        if any(c[0] == "CTR" for c in improvement_changes):
            story += "特に、CTRの上昇は検索結果での見え方の改善（title/descriptionの最適化）が影響していると考えられます。\n"
        if any(c[0] == "平均掲載順位" for c in improvement_changes):
            story += "掲載順位の改善はコンテンツの充実や技術的な改善が影響していると考えられます。\n"
        if any(c[0] == "PageSpeed" for c in improvement_changes):
            story += "PageSpeedの改善はユーザー体験の向上に繋がります。\n"

    elif len(improvement_changes) == 1:
        metric = improvement_changes[0][0]
        story += f"{metric}に改善が見られます。継続的な観測が必要です。\n"

    elif decline_changes:
        story += "一部の指標に低下が見られます。原因を調査し、対策を検討することを推奨します。\n"

    else:
        story += "改善の効果が現れるまでには時間がかかることがあります。引き続き観測を続けてください。\n"

    story += "\n※ 因果関係を断定するものではありません。参考情報としてご覧ください。\n"

    return story


def build_story_input_from_progress(
    baseline: Optional[Dict[str, Any]],
    current: Optional[Dict[str, Any]],
    completed_todos: List[Dict[str, Any]],
    site_name: str = "",
    url: str = "",
) -> StoryInput:
    """
    Build StoryInput from progress comparison data

    Args:
        baseline: Baseline progress snapshot
        current: Current progress snapshot
        completed_todos: List of completed todos
        site_name: Site name
        url: Site URL

    Returns:
        StoryInput instance
    """
    input_data = StoryInput(
        range_from=baseline.get("captured_at", "")[:10] if baseline else "",
        range_to=current.get("captured_at", "")[:10] if current else "",
        site_name=site_name,
        url=url,
        completed_todos=completed_todos,
    )

    if baseline and current:
        baseline_metrics = baseline.get("metrics", {})
        current_metrics = current.get("metrics", {})

        # SERP position
        b_pos = baseline_metrics.get("gsc", {}).get("avg_position")
        c_pos = current_metrics.get("gsc", {}).get("avg_position")
        input_data.serp_position = MetricPair(before=b_pos, after=c_pos)

        # CTR
        b_ctr = baseline_metrics.get("gsc", {}).get("ctr")
        c_ctr = current_metrics.get("gsc", {}).get("ctr")
        input_data.ctr = MetricPair(before=b_ctr, after=c_ctr)

        # PageSpeed
        b_ps = baseline_metrics.get("pagespeed", {}).get("performance_score")
        c_ps = current_metrics.get("pagespeed", {}).get("performance_score")
        input_data.pagespeed = MetricPair(before=b_ps, after=c_ps)

    return input_data
