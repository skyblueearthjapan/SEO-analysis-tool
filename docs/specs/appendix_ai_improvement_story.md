# Appendix AI — 改善ストーリー自動生成仕様

Version: 0.1
目的:
- 改善の流れを自然な文章で説明する
- 「何をやって、どう変わったか」を自動要約する
- PDFや画面でそのまま使える

---

## AI-1. 生成タイミング

- Progress画面表示時
- PDF生成時
- 手動リクエスト時

---

## AI-2. 入力データ

```typescript
interface StoryInput {
  // 期間
  range: {
    from: string;  // YYYY-MM-DD
    to: string;
  };

  // Before / After 指標
  metrics: {
    serp_position: { before: number | null; after: number | null };
    ctr: { before: number | null; after: number | null };
    pagespeed: { before: number | null; after: number | null };
    crawl_errors: { before: number | null; after: number | null };
    ref_domains: { before: number | null; after: number | null };
  };

  // 完了ToDo
  completed_todos: Array<{
    title: string;
    category: string;
    completed_at: string;
  }>;

  // サイト情報
  site_name: string;
  url: string;
}
```

---

## AI-3. 出力（例）

```md
## 改善レポート

対象サイト: example.com
期間: 2025年12月1日 〜 2026年1月15日

### 実施した改善

この期間中、以下の改善を実施しました。

- 問い合わせ導線の明確化（CTA改善）
- FAQセクションの追加
- ページ表示速度の改善
- 画像alt属性の追加

### 観測された変化

改善実施後、以下の変化が確認されています。

| 指標 | 改善前 | 改善後 | 変化 |
|------|--------|--------|------|
| 平均掲載順位 | 14.2位 | 10.4位 | ▲改善 |
| CTR | 1.8% | 3.1% | ▲改善 |
| PageSpeed | 62 | 78 | ▲改善 |
| クロールエラー | 19件 | 4件 | ▲改善 |

### 考察

これらの改善が、検索パフォーマンスの向上に寄与している可能性があります。

特に、CTRの上昇は検索結果での見え方の改善（title/description）が、
掲載順位の改善はコンテンツの充実が影響していると考えられます。

※ 因果関係を断定するものではありません。
```

---

## AI-4. 生成ロジック

### パターンA: テンプレートベース（推奨・MVP）

```python
# app/services/story_generator.py

def generate_improvement_story(input: StoryInput) -> str:
    """Generate improvement story from metrics and todos"""

    # 完了ToDo をカテゴリ別に整理
    todo_by_category = {}
    for todo in input.completed_todos:
        cat = todo["category"]
        if cat not in todo_by_category:
            todo_by_category[cat] = []
        todo_by_category[cat].append(todo["title"])

    # 指標の変化を判定
    changes = []
    metrics = input.metrics

    if metrics["serp_position"]["before"] and metrics["serp_position"]["after"]:
        diff = metrics["serp_position"]["before"] - metrics["serp_position"]["after"]
        if diff > 0:
            changes.append(("平均掲載順位", "改善", f"{metrics['serp_position']['before']:.1f}位 → {metrics['serp_position']['after']:.1f}位"))

    if metrics["ctr"]["before"] and metrics["ctr"]["after"]:
        diff = metrics["ctr"]["after"] - metrics["ctr"]["before"]
        if diff > 0:
            changes.append(("CTR", "改善", f"{metrics['ctr']['before']*100:.1f}% → {metrics['ctr']['after']*100:.1f}%"))

    if metrics["pagespeed"]["before"] and metrics["pagespeed"]["after"]:
        diff = metrics["pagespeed"]["after"] - metrics["pagespeed"]["before"]
        if diff > 0:
            changes.append(("PageSpeed", "改善", f"{metrics['pagespeed']['before']} → {metrics['pagespeed']['after']}"))

    if metrics["crawl_errors"]["before"] and metrics["crawl_errors"]["after"]:
        diff = metrics["crawl_errors"]["before"] - metrics["crawl_errors"]["after"]
        if diff > 0:
            changes.append(("クロールエラー", "減少", f"{metrics['crawl_errors']['before']}件 → {metrics['crawl_errors']['after']}件"))

    # ストーリー生成
    story = f"""## 改善レポート

対象サイト: {input.site_name}
期間: {input.range['from']} 〜 {input.range['to']}

### 実施した改善

この期間中、以下の改善を実施しました。

"""

    for todo in input.completed_todos[:10]:
        story += f"- {todo['title']}\n"

    story += """
### 観測された変化

改善実施後、以下の変化が確認されています。

"""

    if changes:
        for metric, status, detail in changes:
            story += f"- {metric}: {detail}（{status}）\n"
    else:
        story += "※ 有意な変化は確認されていません。\n"

    story += """
### 考察

"""

    if len(changes) >= 2:
        story += "これらの改善が、検索パフォーマンスの向上に寄与している可能性があります。\n"
    elif len(changes) == 1:
        story += "一部の指標に改善が見られます。継続的な観測が必要です。\n"
    else:
        story += "改善の効果が現れるまでには時間がかかることがあります。引き続き観測を続けてください。\n"

    story += "\n※ 因果関係を断定するものではありません。\n"

    return story
```

### パターンB: LLM API（将来拡張）

```python
# LLMを使った自然な文章生成（低温度）
async def generate_story_with_llm(input: StoryInput) -> str:
    prompt = f"""
以下のデータをもとに、SEO改善レポートの「改善ストーリー」セクションを生成してください。

【ルール】
- 因果関係は断定しない（「可能性があります」「考えられます」を使う）
- 客観的で読みやすい文章
- 専門用語は必要最小限

【データ】
期間: {input.range['from']} 〜 {input.range['to']}
完了ToDo: {[t['title'] for t in input.completed_todos]}
指標変化: {input.metrics}
"""

    # LLM API呼び出し（temperature=0.3）
    response = await call_llm(prompt, temperature=0.3)
    return response
```

---

## AI-5. API

### エンドポイント

```python
# app/routers/reports.py

@router.get("/{site_id}/story")
async def get_improvement_story(
    site_id: UUID,
    from_date: date = Query(alias="from"),
    to_date: date = Query(alias="to"),
    db: AsyncSession = Depends(get_db)
):
    """Generate improvement story for the period"""

    # 1. 指標データを取得
    metrics = await get_metrics_for_period(db, site_id, from_date, to_date)

    # 2. 完了ToDoを取得
    todos = await get_completed_todos_for_period(db, site_id, from_date, to_date)

    # 3. サイト情報を取得
    site = await get_site(db, site_id)

    # 4. ストーリー生成
    input_data = StoryInput(
        range={"from": from_date.isoformat(), "to": to_date.isoformat()},
        metrics=metrics,
        completed_todos=todos,
        site_name=site.name,
        url=site.official_url
    )

    story = generate_improvement_story(input_data)

    return {
        "site_id": str(site_id),
        "range": {"from": from_date.isoformat(), "to": to_date.isoformat()},
        "story_markdown": story
    }
```

---

## AI-6. Frontend実装

```tsx
// components/progress/ImprovementStory.tsx
"use client";

import { useEffect, useState } from "react";
import { GlassCard } from "@/components/layout/GlassCard";
import { FileText, RefreshCw } from "lucide-react";
import ReactMarkdown from "react-markdown";

interface ImprovementStoryProps {
  siteId: string;
  from: string;
  to: string;
}

export function ImprovementStory({ siteId, from, to }: ImprovementStoryProps) {
  const [story, setStory] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  async function loadStory() {
    setLoading(true);
    try {
      const res = await fetch(
        `/api/v1/sites/${siteId}/story?from=${from}&to=${to}`
      );
      if (res.ok) {
        const data = await res.json();
        setStory(data.story_markdown);
      }
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadStory();
  }, [siteId, from, to]);

  if (loading) {
    return (
      <GlassCard>
        <div className="flex items-center justify-center py-8 text-text-muted">
          <RefreshCw className="h-5 w-5 animate-spin mr-2" />
          ストーリーを生成中...
        </div>
      </GlassCard>
    );
  }

  if (!story) {
    return (
      <GlassCard>
        <div className="text-center py-8 text-text-muted">
          改善ストーリーを生成できませんでした
        </div>
      </GlassCard>
    );
  }

  return (
    <GlassCard>
      <div className="flex items-center gap-2 mb-4">
        <FileText className="h-5 w-5 text-accent-cyan" />
        <h3 className="text-lg font-semibold">改善ストーリー</h3>
      </div>

      <div className="prose prose-invert prose-sm max-w-none">
        <ReactMarkdown>{story}</ReactMarkdown>
      </div>
    </GlassCard>
  );
}
```

---

## AI-7. トーン・表現ルール（重要）

### 使ってよい表現

- 「〜の可能性があります」
- 「〜と考えられます」
- 「〜が寄与していると推測されます」
- 「〜が観測されています」

### 使ってはいけない表現

- 「〜したおかげで」（因果断定）
- 「〜が原因で」（因果断定）
- 「必ず〜」「確実に〜」（過度な保証）

---

## AI-8. 受け入れ基準

- [ ] 読みやすい日本語で出力される
- [ ] 因果関係を断定していない
- [ ] 第三者に説明できる文章になっている
- [ ] データがない場合も適切にハンドリングされる
- [ ] Progress画面・PDF両方で使える
