# Appendix AM — コンテンツ設計自動生成 & ページ分割シミュレーション仕様

Version: 0.1
目的:
- キーワードクラスタ（Appendix AL）を起点に、
  実際に「どういうページ構成にすべきか」まで落とし込む
- SEO会社のコンテンツ設計業務を自動化する
- 作る／直す／分ける の判断をシミュレーションできるようにする

---

## AM-0. 全体フロー（最重要）

```text
Keyword Cluster
  ↓
検索意図の明文化
  ↓
コンテンツアウトライン生成
  ↓
H2構成案生成
  ↓
FAQ案生成
  ↓
ページ分割 / 統合シミュレーション
```

---

## AM-1. 入力（前提）

### 必須

* keyword_cluster（Appendix AL）
  * cluster_name
  * intent
  * queries[]
  * impressions / clicks
  * assigned_page
  * competitor_outline（任意）

### 補助

* 既存ページ構造
* 競合ページ見出し

---

## AM-2. コンテンツ設計ユニット（Concept）

```json
{
  "cluster": "社会人演劇 参加",
  "intent": "行動（参加・申込）",
  "primary_goal": "参加申込",
  "secondary_goals": ["不安解消", "流れ理解"]
}
```

---

## AM-3. コンテンツアウトライン自動生成

### 目的

* ページ全体で **何を伝えるべきか** を先に固める

### 出力（例）

```md
このページでは以下を伝える必要があります。

1. 社会人演劇とは何か
2. 参加するメリット
3. 初心者でも参加できる理由
4. 実際の参加の流れ
5. よくある不安への回答
6. 参加・問い合わせ方法
```

---

## AM-4. H2構成案 自動生成

### ルール

* 1 intent = 1 H2 群
* クエリの言い換えを自然に含める
* キーワード詰め込み禁止

### 出力（例）

```md
## 社会人演劇とは？
## 社会人演劇に参加するメリット
## 初心者でも参加できる理由
## 参加までの流れ
## よくある不安・質問
## 参加・お問い合わせ方法
```

---

## AM-5. FAQ案 自動生成

### 入力ソース

* クエリの疑問形
* 競合FAQ
* GSCの低CTRクエリ

### 出力（例）

```md
### Q. 演劇未経験でも参加できますか？
A. 多くの社会人演劇では未経験者の参加を歓迎しています。

### Q. どのくらいの頻度で活動しますか？
A. 劇団によって異なりますが、週1〜2回が一般的です。
```

---

## AM-6. コンテンツ過不足評価

### 評価指標

| 指標 | 判定 |
|------|------|
| クエリ数 > 10 | 情報量多 |
| intent多様 | 分割候補 |
| 競合が専用ページ | 分割候補 |
| CV目的明確 | 専用化推奨 |

---

## AM-7. ページ分割 / 統合シミュレーション（核心）

### シミュレーション結果タイプ

#### ① 現状維持

```md
現在の1ページ構成で問題ありません。
情報量・意図ともに適切です。
```

#### ② セクション追加

```md
現在のページに以下のセクションを追加してください。
- 初心者向けQ&A
- 参加の流れ詳細
```

#### ③ ページ分割（重要）

```md
以下の理由から、専用ページの作成を推奨します。

理由:
- クエリ数が多い
- 行動系 intent が強い
- 競合が専用ページを持っている

推奨構成:
- /join （参加専用ページ）
- /about （概要ページ）
```

#### ④ ページ統合（カニバリ解消）

```md
2ページが同一意図を扱っています。
どちらかに統合することで評価集中が期待できます。
```

---

## AM-8. 出力データ構造（Backend）

```json
{
  "cluster_id": "cl_001",
  "content_outline": [
    "社会人演劇とは何か",
    "参加するメリット",
    "初心者でも参加できる理由",
    "実際の参加の流れ",
    "よくある不安への回答",
    "参加・問い合わせ方法"
  ],
  "h2_proposals": [
    {"text": "社会人演劇とは？", "intent": "informational"},
    {"text": "社会人演劇に参加するメリット", "intent": "informational"},
    {"text": "初心者でも参加できる理由", "intent": "commercial"},
    {"text": "参加までの流れ", "intent": "transactional"},
    {"text": "よくある不安・質問", "intent": "commercial"},
    {"text": "参加・お問い合わせ方法", "intent": "transactional"}
  ],
  "faq_proposals": [
    {"question": "演劇未経験でも参加できますか？", "answer_hint": "未経験歓迎の旨を説明"},
    {"question": "どのくらいの頻度で活動しますか？", "answer_hint": "週1〜2回が一般的"},
    {"question": "費用はどのくらいかかりますか？", "answer_hint": "月会費・公演費用の目安"}
  ],
  "page_strategy": {
    "type": "split",
    "recommended_pages": [
      {"path": "/join", "purpose": "参加申込専用"},
      {"path": "/about", "purpose": "概要・紹介"}
    ],
    "reasons": [
      "intent_overload",
      "competitor_structure",
      "high_query_volume"
    ],
    "explanation": "クエリ数が多く、行動系intentが強いため、専用ページの作成を推奨します。"
  }
}
```

---

## AM-9. Backend 実装

### 9.1 ファイル構成

```
app/services/
├─ content_designer.py
├─ outline_generator.py
├─ faq_generator.py
└─ page_strategy_simulator.py
```

### 9.2 メインサービス

```python
# app/services/content_designer.py
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from uuid import UUID

@dataclass
class ContentDesign:
    cluster_id: str
    content_outline: List[str]
    h2_proposals: List[Dict[str, str]]
    faq_proposals: List[Dict[str, str]]
    page_strategy: Dict[str, Any]

async def design_content(
    cluster: Dict[str, Any],
    existing_page_structure: Optional[Dict] = None,
    competitor_outlines: Optional[List[Dict]] = None,
    use_llm: bool = True
) -> ContentDesign:
    """
    Generate content design from keyword cluster

    Args:
        cluster: Keyword cluster data from AL
        existing_page_structure: Current page's h1/h2/h3 structure
        competitor_outlines: Competitor page structures
        use_llm: Whether to use LLM for generation
    """

    # 1. Generate content outline
    outline = await generate_outline(
        cluster=cluster,
        competitor_outlines=competitor_outlines,
        use_llm=use_llm
    )

    # 2. Generate H2 proposals
    h2_proposals = await generate_h2_structure(
        outline=outline,
        cluster=cluster,
        use_llm=use_llm
    )

    # 3. Generate FAQ proposals
    faq_proposals = await generate_faq_proposals(
        cluster=cluster,
        competitor_outlines=competitor_outlines,
        use_llm=use_llm
    )

    # 4. Simulate page strategy
    page_strategy = simulate_page_strategy(
        cluster=cluster,
        existing_structure=existing_page_structure,
        competitor_outlines=competitor_outlines
    )

    return ContentDesign(
        cluster_id=cluster["id"],
        content_outline=outline,
        h2_proposals=h2_proposals,
        faq_proposals=faq_proposals,
        page_strategy=page_strategy
    )
```

### 9.3 アウトライン生成

```python
# app/services/outline_generator.py
from typing import List, Dict, Any, Optional

# Intent-based outline templates
OUTLINE_TEMPLATES = {
    "informational": [
        "{topic}とは",
        "{topic}の特徴・メリット",
        "{topic}の種類・選び方",
        "まとめ"
    ],
    "commercial": [
        "{topic}を選ぶポイント",
        "{topic}の比較",
        "おすすめの{topic}",
        "よくある質問"
    ],
    "transactional": [
        "{topic}の方法・流れ",
        "{topic}に必要なもの",
        "{topic}の注意点",
        "{topic}の申込・問い合わせ"
    ]
}

async def generate_outline(
    cluster: Dict[str, Any],
    competitor_outlines: Optional[List[Dict]] = None,
    use_llm: bool = True
) -> List[str]:
    """Generate content outline"""

    intent = cluster.get("intent", "informational")
    topic = cluster.get("cluster_name", "")

    if use_llm:
        return await generate_outline_with_llm(cluster, competitor_outlines)

    # Template-based fallback
    template = OUTLINE_TEMPLATES.get(intent, OUTLINE_TEMPLATES["informational"])
    return [item.format(topic=topic) for item in template]


async def generate_outline_with_llm(
    cluster: Dict[str, Any],
    competitor_outlines: Optional[List[Dict]] = None
) -> List[str]:
    """Generate outline using LLM"""

    queries = [q["query"] for q in cluster.get("queries", [])[:10]]
    intent = cluster.get("intent", "informational")
    topic = cluster.get("cluster_name", "")

    competitor_context = ""
    if competitor_outlines:
        competitor_context = "競合ページの構成:\n" + "\n".join(
            f"- {c.get('title', '')}: {', '.join(c.get('h2s', []))}"
            for c in competitor_outlines[:3]
        )

    prompt = f"""
あなたはSEOコンテンツ設計者です。
以下のキーワードクラスターに基づき、ページのコンテンツアウトライン（伝えるべき内容の順序）を生成してください。

トピック: {topic}
検索意図: {intent}
含まれるクエリ: {', '.join(queries)}

{competitor_context}

条件:
- 検索意図を満たすことを最優先
- ユーザーが知りたい順序で並べる
- 5〜8項目程度
- 箇条書きで出力

出力形式:
- 項目1
- 項目2
...
"""

    # Call LLM API
    response = await call_llm(prompt, temperature=0.3)

    # Parse response into list
    lines = response.strip().split("\n")
    return [line.lstrip("- ").strip() for line in lines if line.strip()]
```

### 9.4 H2構成生成

```python
# app/services/h2_generator.py
from typing import List, Dict, Any

async def generate_h2_structure(
    outline: List[str],
    cluster: Dict[str, Any],
    use_llm: bool = True
) -> List[Dict[str, str]]:
    """Generate H2 heading proposals"""

    if use_llm:
        return await generate_h2_with_llm(outline, cluster)

    # Simple mapping from outline
    intent = cluster.get("intent", "informational")
    return [
        {"text": item, "intent": intent}
        for item in outline
    ]


async def generate_h2_with_llm(
    outline: List[str],
    cluster: Dict[str, Any]
) -> List[Dict[str, str]]:
    """Generate H2 using LLM"""

    queries = [q["query"] for q in cluster.get("queries", [])[:10]]
    topic = cluster.get("cluster_name", "")

    prompt = f"""
以下のコンテンツアウトラインを、SEOに適したH2見出しに変換してください。

トピック: {topic}
関連クエリ: {', '.join(queries)}

アウトライン:
{chr(10).join(f'- {item}' for item in outline)}

条件:
- キーワードを不自然に繰り返さない
- ユーザーにとって分かりやすい表現
- 疑問形も活用可能
- 各見出しの検索意図（informational/commercial/transactional）も付記

出力形式（JSON配列）:
[{{"text": "見出し文", "intent": "意図"}}]
"""

    response = await call_llm(prompt, temperature=0.3)

    import json
    try:
        return json.loads(response)
    except:
        # Fallback
        return [{"text": item, "intent": "informational"} for item in outline]
```

### 9.5 FAQ生成

```python
# app/services/faq_generator.py
from typing import List, Dict, Any, Optional

async def generate_faq_proposals(
    cluster: Dict[str, Any],
    competitor_outlines: Optional[List[Dict]] = None,
    use_llm: bool = True
) -> List[Dict[str, str]]:
    """Generate FAQ proposals"""

    queries = cluster.get("queries", [])
    topic = cluster.get("cluster_name", "")

    # Extract question-like queries
    question_queries = [
        q for q in queries
        if any(kw in q["query"] for kw in ["とは", "方法", "やり方", "できる", "いくら", "どこ", "いつ", "なぜ"])
    ]

    # Extract competitor FAQs
    competitor_faqs = []
    if competitor_outlines:
        for c in competitor_outlines:
            competitor_faqs.extend(c.get("faqs", []))

    if use_llm:
        return await generate_faq_with_llm(topic, question_queries, competitor_faqs)

    # Simple extraction
    return [
        {"question": q["query"] + "？", "answer_hint": ""}
        for q in question_queries[:5]
    ]


async def generate_faq_with_llm(
    topic: str,
    question_queries: List[Dict],
    competitor_faqs: List[str]
) -> List[Dict[str, str]]:
    """Generate FAQ using LLM"""

    query_texts = [q["query"] for q in question_queries[:10]]

    prompt = f"""
以下のトピックについて、よくある質問（FAQ）を5〜7件生成してください。

トピック: {topic}

参考クエリ: {', '.join(query_texts)}

競合サイトのFAQ例: {', '.join(competitor_faqs[:5]) if competitor_faqs else 'なし'}

条件:
- 検索ユーザーが本当に知りたいことを優先
- 具体的で実用的な質問
- 回答のヒントも付記

出力形式（JSON配列）:
[{{"question": "質問文？", "answer_hint": "回答のポイント"}}]
"""

    response = await call_llm(prompt, temperature=0.4)

    import json
    try:
        return json.loads(response)
    except:
        return []
```

### 9.6 ページ戦略シミュレーション

```python
# app/services/page_strategy_simulator.py
from typing import Dict, Any, List, Optional

def simulate_page_strategy(
    cluster: Dict[str, Any],
    existing_structure: Optional[Dict] = None,
    competitor_outlines: Optional[List[Dict]] = None
) -> Dict[str, Any]:
    """
    Simulate page strategy (maintain / add sections / split / merge)
    """

    queries = cluster.get("queries", [])
    intent = cluster.get("intent", "informational")
    pages = cluster.get("pages", [])

    total_impressions = sum(q.get("impressions", 0) for q in queries)
    query_count = len(queries)

    # Check for cannibalization
    has_cannibalization = len(pages) > 1

    # Check competitor structure
    competitor_has_dedicated = False
    if competitor_outlines:
        # If competitor has dedicated page for this intent
        competitor_has_dedicated = any(
            c.get("is_dedicated", False) for c in competitor_outlines
        )

    # Decision logic
    reasons = []
    strategy_type = "maintain"
    recommended_pages = []
    explanation = ""

    # Rule 1: Cannibalization → Merge
    if has_cannibalization:
        strategy_type = "merge"
        reasons.append("cannibalization_detected")
        explanation = "複数ページが同じ検索意図で競合しています。どちらかに統合することを推奨します。"

    # Rule 2: High volume transactional → Split
    elif intent == "transactional" and query_count >= 5 and total_impressions >= 500:
        strategy_type = "split"
        reasons.append("high_query_volume")
        reasons.append("transactional_intent")
        recommended_pages = [
            {"path": "/dedicated-page", "purpose": "行動系クエリ専用"}
        ]
        explanation = "行動系の検索意図が強く、クエリ数も多いため、専用ページの作成を推奨します。"

    # Rule 3: Competitor has dedicated page
    elif competitor_has_dedicated and query_count >= 3:
        strategy_type = "split"
        reasons.append("competitor_structure")
        recommended_pages = [
            {"path": "/dedicated-page", "purpose": "競合対抗"}
        ]
        explanation = "競合サイトが専用ページを持っています。同様の構成を検討してください。"

    # Rule 4: Missing sections
    elif existing_structure:
        # Check if current page is missing key sections
        existing_h2s = existing_structure.get("h2s", [])
        if len(existing_h2s) < 3 and query_count >= 5:
            strategy_type = "add_sections"
            reasons.append("insufficient_coverage")
            explanation = "現在のページに追加セクションを設けることで、より多くの検索意図をカバーできます。"

    # Default: Maintain
    else:
        strategy_type = "maintain"
        explanation = "現在の構成で問題ありません。"

    return {
        "type": strategy_type,
        "recommended_pages": recommended_pages,
        "reasons": reasons,
        "explanation": explanation,
        "metrics": {
            "query_count": query_count,
            "total_impressions": total_impressions,
            "page_count": len(pages),
            "intent": intent
        }
    }
```

---

## AM-10. API

### エンドポイント

```python
# app/routers/content_design.py
from fastapi import APIRouter, Depends
from uuid import UUID

router = APIRouter(prefix="/api/v1/sites/{site_id}/content-design", tags=["content-design"])

@router.post("/clusters/{cluster_id}/generate")
async def generate_content_design(
    site_id: UUID,
    cluster_id: UUID,
    use_llm: bool = True,
    db: AsyncSession = Depends(get_db)
):
    """Generate content design for a cluster"""

    # Get cluster
    cluster = await get_cluster_with_queries(db, cluster_id)
    if not cluster:
        raise HTTPException(404, "Cluster not found")

    # Get existing page structure if assigned
    existing_structure = None
    if cluster.target_page:
        existing_structure = await get_page_structure(db, site_id, cluster.target_page)

    # Get competitor outlines
    competitor_outlines = await get_competitor_outlines(db, site_id)

    # Generate design
    design = await design_content(
        cluster=cluster.to_dict(),
        existing_page_structure=existing_structure,
        competitor_outlines=competitor_outlines,
        use_llm=use_llm
    )

    return {
        "cluster_id": str(cluster_id),
        "content_outline": design.content_outline,
        "h2_proposals": design.h2_proposals,
        "faq_proposals": design.faq_proposals,
        "page_strategy": design.page_strategy
    }

@router.post("/clusters/{cluster_id}/create-todos")
async def create_todos_from_design(
    site_id: UUID,
    cluster_id: UUID,
    design_type: str,  # "add_sections" | "split" | "merge"
    db: AsyncSession = Depends(get_db)
):
    """Create todos from content design recommendation"""

    todos = []

    if design_type == "add_sections":
        todos.append({
            "title": "H2セクションの追加",
            "priority": "P1",
            "category": "content",
            "details": "コンテンツ設計に基づきセクションを追加してください",
            "source_checks": ["content_design"]
        })
        todos.append({
            "title": "FAQセクションの追加",
            "priority": "P2",
            "category": "content",
            "details": "生成されたFAQ案を参考に追加してください",
            "source_checks": ["content_design"]
        })

    elif design_type == "split":
        todos.append({
            "title": "専用ページの作成",
            "priority": "P1",
            "category": "structure",
            "details": "検索意図に合わせた専用ページを作成してください",
            "source_checks": ["content_design"]
        })

    elif design_type == "merge":
        todos.append({
            "title": "ページの統合",
            "priority": "P1",
            "category": "structure",
            "details": "カニバリ解消のためページを統合してください",
            "source_checks": ["content_design"]
        })

    # Save todos
    for todo_data in todos:
        await create_todo(db, site_id, todo_data)

    return {"created_todos": len(todos)}
```

---

## AM-11. Frontend UI

### 11.1 コンポーネント構成

```
components/content-design/
├─ ContentDesignPanel.tsx
├─ OutlineSection.tsx
├─ H2ProposalsSection.tsx
├─ FaqProposalsSection.tsx
├─ PageStrategySection.tsx
└─ CreateTodosButton.tsx
```

### 11.2 ContentDesignPanel.tsx

```tsx
"use client";

import { useState } from "react";
import { GlassCard } from "@/components/layout/GlassCard";
import { Wand2, FileText, List, HelpCircle, GitBranch, Loader2 } from "lucide-react";
import { OutlineSection } from "./OutlineSection";
import { H2ProposalsSection } from "./H2ProposalsSection";
import { FaqProposalsSection } from "./FaqProposalsSection";
import { PageStrategySection } from "./PageStrategySection";

interface ContentDesign {
  content_outline: string[];
  h2_proposals: Array<{ text: string; intent: string }>;
  faq_proposals: Array<{ question: string; answer_hint: string }>;
  page_strategy: {
    type: string;
    recommended_pages: Array<{ path: string; purpose: string }>;
    reasons: string[];
    explanation: string;
  };
}

interface ContentDesignPanelProps {
  siteId: string;
  clusterId: string;
  clusterName: string;
}

export function ContentDesignPanel({ siteId, clusterId, clusterName }: ContentDesignPanelProps) {
  const [design, setDesign] = useState<ContentDesign | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function generateDesign() {
    setLoading(true);
    setError(null);

    try {
      const res = await fetch(
        `/api/v1/sites/${siteId}/content-design/clusters/${clusterId}/generate`,
        { method: "POST" }
      );

      if (res.ok) {
        const data = await res.json();
        setDesign(data);
      } else {
        setError("生成に失敗しました");
      }
    } catch (e) {
      setError("エラーが発生しました");
    } finally {
      setLoading(false);
    }
  }

  if (!design) {
    return (
      <GlassCard>
        <div className="text-center py-8">
          <Wand2 className="h-12 w-12 text-accent-cyan mx-auto mb-4" />
          <h3 className="text-lg font-semibold mb-2">コンテンツ設計を生成</h3>
          <p className="text-text-muted text-sm mb-4">
            「{clusterName}」クラスターに基づいて<br />
            アウトライン・H2構成・FAQ案を自動生成します
          </p>
          <button
            onClick={generateDesign}
            disabled={loading}
            className="px-6 py-2 bg-accent-cyan text-bg-base rounded-lg font-medium hover:bg-accent-cyan/90 transition-colors disabled:opacity-50"
          >
            {loading ? (
              <span className="flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin" />
                生成中...
              </span>
            ) : (
              "生成する"
            )}
          </button>
          {error && <p className="text-red-400 text-sm mt-2">{error}</p>}
        </div>
      </GlassCard>
    );
  }

  return (
    <div className="space-y-6">
      {/* Page Strategy (Top) */}
      <PageStrategySection
        strategy={design.page_strategy}
        siteId={siteId}
        clusterId={clusterId}
      />

      {/* Content Outline */}
      <OutlineSection outline={design.content_outline} />

      {/* H2 Proposals */}
      <H2ProposalsSection proposals={design.h2_proposals} />

      {/* FAQ Proposals */}
      <FaqProposalsSection proposals={design.faq_proposals} />

      {/* Regenerate Button */}
      <div className="text-center">
        <button
          onClick={generateDesign}
          disabled={loading}
          className="text-sm text-text-muted hover:text-accent-cyan transition-colors"
        >
          再生成する
        </button>
      </div>
    </div>
  );
}
```

### 11.3 PageStrategySection.tsx

```tsx
"use client";

import { useState } from "react";
import { GlassCard } from "@/components/layout/GlassCard";
import { GitBranch, GitMerge, Plus, Check, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

const STRATEGY_CONFIG = {
  maintain: {
    icon: Check,
    color: "text-green-400",
    bgColor: "bg-green-400/10",
    label: "現状維持"
  },
  add_sections: {
    icon: Plus,
    color: "text-blue-400",
    bgColor: "bg-blue-400/10",
    label: "セクション追加"
  },
  split: {
    icon: GitBranch,
    color: "text-yellow-400",
    bgColor: "bg-yellow-400/10",
    label: "ページ分割"
  },
  merge: {
    icon: GitMerge,
    color: "text-purple-400",
    bgColor: "bg-purple-400/10",
    label: "ページ統合"
  }
};

interface PageStrategySectionProps {
  strategy: {
    type: string;
    recommended_pages: Array<{ path: string; purpose: string }>;
    reasons: string[];
    explanation: string;
  };
  siteId: string;
  clusterId: string;
}

export function PageStrategySection({ strategy, siteId, clusterId }: PageStrategySectionProps) {
  const [creating, setCreating] = useState(false);
  const [created, setCreated] = useState(false);

  const config = STRATEGY_CONFIG[strategy.type as keyof typeof STRATEGY_CONFIG] || STRATEGY_CONFIG.maintain;
  const Icon = config.icon;

  async function createTodos() {
    setCreating(true);
    try {
      const res = await fetch(
        `/api/v1/sites/${siteId}/content-design/clusters/${clusterId}/create-todos?design_type=${strategy.type}`,
        { method: "POST" }
      );
      if (res.ok) {
        setCreated(true);
      }
    } finally {
      setCreating(false);
    }
  }

  return (
    <GlassCard className={config.bgColor}>
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-3">
          <Icon className={cn("h-6 w-6 mt-1", config.color)} />
          <div>
            <h3 className={cn("text-lg font-semibold", config.color)}>
              {config.label}
            </h3>
            <p className="text-text-secondary text-sm mt-1">
              {strategy.explanation}
            </p>

            {strategy.recommended_pages.length > 0 && (
              <div className="mt-3 space-y-1">
                <p className="text-xs text-text-muted">推奨構成:</p>
                {strategy.recommended_pages.map((page, i) => (
                  <div key={i} className="text-sm">
                    <code className="text-accent-cyan">{page.path}</code>
                    <span className="text-text-muted ml-2">- {page.purpose}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {strategy.type !== "maintain" && (
          <button
            onClick={createTodos}
            disabled={creating || created}
            className={cn(
              "px-4 py-2 rounded-lg text-sm font-medium transition-colors",
              created
                ? "bg-green-400/20 text-green-400"
                : "bg-accent-cyan/20 text-accent-cyan hover:bg-accent-cyan/30"
            )}
          >
            {creating ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : created ? (
              "ToDo作成済み"
            ) : (
              "ToDoを作成"
            )}
          </button>
        )}
      </div>
    </GlassCard>
  );
}
```

---

## AM-12. LLMプロンプト指針（重要）

### 基本原則

```md
あなたはSEOコンテンツ設計者です。
以下のキーワードクラスターと検索意図に基づき、
コンテンツ設計を行ってください。

条件:
- キーワードを不自然に繰り返さない
- 検索意図を満たすことを最優先
- SEO目的だがユーザー視点で書く
- 競合との差別化を意識する
```

### 温度設定

| タスク | temperature |
|--------|-------------|
| アウトライン | 0.3 |
| H2生成 | 0.3 |
| FAQ生成 | 0.4 |

---

## AM-13. ToDo連動

| 戦略 | ToDo |
|------|------|
| セクション追加 | H2追加, FAQ追加 |
| ページ分割 | 新規ページ作成 |
| ページ統合 | ページ統合・リダイレクト |

source_checks=["keyword_architecture", "content_design"]

---

## AM-14. Progress連動

* 分割・改善後
* SERP / CTR / カニバリ改善を Progress Dashboard で追跡

---

## AM-15. 受け入れ基準

- [ ] アウトラインが生成される
- [ ] H2構成が具体的で実用的
- [ ] FAQが検索意図に基づいている
- [ ] ページ戦略に理由がある
- [ ] コピー可能なUI
- [ ] ToDoに直結する
- [ ] LLM未使用時もテンプレートで動作する

---

## AM-16. このAppendixが完成すると

```md
・SEO会社の設計業務（2〜5日）が自動化される
・「何を書くか」で迷わなくなる
・ページ構成の失敗が減る
・コンテンツ戦略が可視化される
```

---

## AM-17. 将来拡張

- 本文ドラフト生成
- CMS連携（下書き作成）
- 競合構成との差分ハイライト
- A/Bテスト構成提案
