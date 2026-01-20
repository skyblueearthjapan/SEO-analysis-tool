# Appendix AL — キーワード設計・クラスタリング・カニバリ検出 設計仕様

Version: 0.1
目的:
- SEO会社が行う「キーワード設計」をアプリ上で再現する
- クエリ → 意図 → ページ → サイト全体 の整理を自動化する
- 取りこぼし・競合差分・カニバリを構造的に可視化する

---

## AL-0. 基本思想（最重要）

```md
SEOにおけるキーワード分析とは、
「どの検索クエリを、どのページで取りに行くか」
を決める設計作業である。

本機能は、単なるキーワード一覧ではなく、
検索意図とページ割当の"設計図"を作ることを目的とする。
```

---

## AL-1. 用語定義（UI・設計で共通）

| 用語 | 定義 |
|------|------|
| Query | 実際に検索されている検索クエリ |
| Intent | 検索者の目的（情報/比較/行動など） |
| Cluster | 同じ意図を持つクエリ群 |
| Target Page | そのクラスターを担当するページ |
| Orphan Query | どのページにも割り当てられていないクエリ |
| Cannibalization | 複数ページが同一クエリを奪い合っている状態 |

---

## AL-2. データ取得元（MVP前提）

### 必須

* Google Search Console
  * query
  * impressions
  * clicks
  * ctr
  * avg_position
  * page

### 補助（任意）

* 競合ページの title / h2 / FAQ
* キーワードツール（将来拡張）

---

## AL-3. 内部データモデル（論理）

```text
Search Query
  ↓（意味的に近い）
Keyword Cluster（Intent）
  ↓（1つに割り当てる）
Target Page
  ↓
Site
```

---

## AL-4. キーワードクラスタリング仕様

### 4.1 クラスタ単位（MVP）

* 同義語
* 語順違い
* 修飾語違い
* 意図が同じと判断できるもの

### 4.2 実装方法（段階）

* MVP:
  * 文字列類似度
  * 共通語幹
  * 同一ページ出現率
* 将来:
  * embedding / LLM

### 4.3 クラスタリングアルゴリズム（MVP）

```python
# app/services/analyzers/keyword_clustering.py
from typing import List, Dict, Any
from collections import defaultdict
import re

def tokenize_query(query: str) -> set:
    """Split query into tokens"""
    # 日本語対応: スペース区切り + 基本的な分割
    tokens = re.split(r'[\s　]+', query.lower())
    return set(t for t in tokens if len(t) > 1)

def calculate_similarity(q1: str, q2: str) -> float:
    """Calculate Jaccard similarity between queries"""
    tokens1 = tokenize_query(q1)
    tokens2 = tokenize_query(q2)

    if not tokens1 or not tokens2:
        return 0.0

    intersection = len(tokens1 & tokens2)
    union = len(tokens1 | tokens2)

    return intersection / union if union > 0 else 0.0

def cluster_queries(
    queries: List[Dict[str, Any]],
    similarity_threshold: float = 0.5
) -> List[Dict[str, Any]]:
    """
    Cluster queries by similarity

    Input: [{"query": "...", "impressions": N, "page": "..."}]
    Output: [{"cluster_name": "...", "queries": [...], "pages": [...]}]
    """
    clusters = []
    assigned = set()

    # Sort by impressions (descending)
    sorted_queries = sorted(queries, key=lambda x: x.get("impressions", 0), reverse=True)

    for q in sorted_queries:
        query_text = q["query"]

        if query_text in assigned:
            continue

        # Start new cluster
        cluster = {
            "cluster_name": query_text,  # Use highest-impression query as name
            "queries": [q],
            "pages": {q.get("page")} if q.get("page") else set()
        }
        assigned.add(query_text)

        # Find similar queries
        for other in sorted_queries:
            other_text = other["query"]
            if other_text in assigned:
                continue

            similarity = calculate_similarity(query_text, other_text)
            if similarity >= similarity_threshold:
                cluster["queries"].append(other)
                assigned.add(other_text)
                if other.get("page"):
                    cluster["pages"].add(other["page"])

        cluster["pages"] = list(cluster["pages"])
        clusters.append(cluster)

    return clusters
```

---

## AL-5. Intent分類仕様

### 5.1 意図カテゴリ

```python
INTENT_CATEGORIES = {
    "informational": {
        "label": "情報収集",
        "description": "知識を得たい",
        "indicators": ["とは", "方法", "やり方", "仕組み", "意味", "違い"]
    },
    "commercial": {
        "label": "比較・検討",
        "description": "選択肢を比較したい",
        "indicators": ["おすすめ", "比較", "ランキング", "評判", "口コミ", "レビュー"]
    },
    "transactional": {
        "label": "行動・購入",
        "description": "行動を起こしたい",
        "indicators": ["購入", "申込", "予約", "参加", "入会", "登録", "料金"]
    },
    "navigational": {
        "label": "ナビゲーション",
        "description": "特定サイトに行きたい",
        "indicators": ["公式", "ログイン", "アクセス", "サイト"]
    }
}

def classify_intent(query: str) -> str:
    """Classify query intent"""
    query_lower = query.lower()

    for intent_type, config in INTENT_CATEGORIES.items():
        for indicator in config["indicators"]:
            if indicator in query_lower:
                return intent_type

    return "informational"  # Default
```

---

## AL-6. DB設計

### 6.1 テーブル

```sql
-- クラスタ定義
CREATE TABLE keyword_clusters (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  site_id UUID NOT NULL REFERENCES sites(site_id),
  cluster_name TEXT NOT NULL,
  intent TEXT DEFAULT 'informational',
  target_page TEXT,
  status VARCHAR(20) DEFAULT 'unassigned',  -- unassigned, partial, assigned
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- クラスタに含まれるクエリ
CREATE TABLE cluster_queries (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  cluster_id UUID NOT NULL REFERENCES keyword_clusters(id) ON DELETE CASCADE,
  query TEXT NOT NULL,
  impressions INT,
  clicks INT,
  ctr DOUBLE PRECISION,
  avg_position DOUBLE PRECISION,
  page TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);

-- カニバリ検出結果
CREATE TABLE cannibalization_issues (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  site_id UUID NOT NULL REFERENCES sites(site_id),
  query TEXT NOT NULL,
  pages JSONB NOT NULL,  -- [{"page": "...", "position": N}]
  severity VARCHAR(20) DEFAULT 'warning',
  status VARCHAR(20) DEFAULT 'open',  -- open, resolved, ignored
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_keyword_clusters_site ON keyword_clusters(site_id);
CREATE INDEX idx_cluster_queries_cluster ON cluster_queries(cluster_id);
CREATE INDEX idx_cannibalization_site ON cannibalization_issues(site_id);
```

---

## AL-7. Backend Analyzer

### 7.1 ファイル構成

```
app/services/analyzers/
├─ keyword_architecture.py
├─ keyword_clustering.py
└─ cannibalization_detector.py
```

### 7.2 メインAnalyzer

```python
# app/services/analyzers/keyword_architecture.py
from dataclasses import dataclass
from typing import List, Dict, Any, Literal
from uuid import UUID

from .keyword_clustering import cluster_queries, classify_intent
from .cannibalization_detector import detect_cannibalization

CheckStatus = Literal["done", "partial", "skipped", "not_supported"]

@dataclass
class AnalyzerOutput:
    check_code: str
    status: CheckStatus
    notes: List[str]
    evidence: List[Dict[str, Any]]
    todo_candidates: List[Dict[str, Any]]

async def analyze_keyword_architecture(
    db,
    site_id: UUID,
    gsc_queries: List[Dict[str, Any]],
    competitor_terms: List[str] = None
) -> AnalyzerOutput:
    """
    Analyze keyword architecture

    Args:
        gsc_queries: GSC query data [{query, impressions, clicks, ctr, position, page}]
        competitor_terms: Terms found in competitor pages
    """

    if not gsc_queries:
        return AnalyzerOutput(
            check_code="keyword_architecture",
            status="skipped",
            notes=["GSCデータがありません"],
            evidence=[],
            todo_candidates=[]
        )

    # 1. Cluster queries
    clusters = cluster_queries(gsc_queries)

    # 2. Classify intent for each cluster
    for cluster in clusters:
        cluster["intent"] = classify_intent(cluster["cluster_name"])

    # 3. Detect orphan queries (high impressions but low position)
    orphan_queries = []
    for cluster in clusters:
        if not cluster["pages"]:
            orphan_queries.extend(cluster["queries"])

    # 4. Detect cannibalization
    cannibal_issues = detect_cannibalization(gsc_queries)

    # 5. Find competitor gaps
    competitor_gaps = []
    if competitor_terms:
        our_terms = set()
        for q in gsc_queries:
            our_terms.update(q["query"].lower().split())

        for term in competitor_terms:
            if term.lower() not in our_terms:
                competitor_gaps.append(term)

    # Build evidence
    evidence = []

    # Cluster summary
    evidence.append({
        "id": "ev_keyword_clusters",
        "kind": "keyword",
        "title": "キーワードクラスタ",
        "severity": "info",
        "data": {
            "total_clusters": len(clusters),
            "clusters": [
                {
                    "name": c["cluster_name"],
                    "intent": c["intent"],
                    "query_count": len(c["queries"]),
                    "pages": c["pages"],
                    "total_impressions": sum(q.get("impressions", 0) for q in c["queries"])
                }
                for c in clusters[:20]  # Top 20
            ]
        }
    })

    # Orphan queries
    if orphan_queries:
        evidence.append({
            "id": "ev_orphan_queries",
            "kind": "keyword",
            "title": "取りこぼしクエリ",
            "severity": "warning",
            "data": {
                "count": len(orphan_queries),
                "queries": [
                    {"query": q["query"], "impressions": q.get("impressions", 0)}
                    for q in orphan_queries[:10]
                ]
            }
        })

    # Cannibalization
    if cannibal_issues:
        evidence.append({
            "id": "ev_cannibalization",
            "kind": "keyword",
            "title": "カニバリゼーション検出",
            "severity": "warning",
            "data": {
                "count": len(cannibal_issues),
                "issues": cannibal_issues[:10]
            }
        })

    # Competitor gaps
    if competitor_gaps:
        evidence.append({
            "id": "ev_competitor_gaps",
            "kind": "keyword",
            "title": "競合差分キーワード",
            "severity": "info",
            "data": {
                "count": len(competitor_gaps),
                "terms": competitor_gaps[:20]
            }
        })

    # Generate todos
    todo_candidates = []

    if orphan_queries:
        todo_candidates.append({
            "title": "取りこぼしクエリへの対応",
            "priority": "P1",
            "category": "content",
            "details": f"{len(orphan_queries)}件のクエリがページに割り当てられていません",
            "source_checks": ["keyword_architecture"]
        })

    if cannibal_issues:
        todo_candidates.append({
            "title": "カニバリゼーションの解消",
            "priority": "P1",
            "category": "structure",
            "details": f"{len(cannibal_issues)}件のクエリで複数ページが競合しています",
            "source_checks": ["keyword_architecture"]
        })

    if competitor_gaps:
        todo_candidates.append({
            "title": "競合が扱うトピックの追加検討",
            "priority": "P2",
            "category": "content",
            "details": f"競合ページで扱われている{len(competitor_gaps)}件のトピックが未対応です",
            "source_checks": ["keyword_architecture"]
        })

    return AnalyzerOutput(
        check_code="keyword_architecture",
        status="done",
        notes=[],
        evidence=evidence,
        todo_candidates=todo_candidates
    )
```

### 7.3 カニバリ検出

```python
# app/services/analyzers/cannibalization_detector.py
from typing import List, Dict, Any
from collections import defaultdict

def detect_cannibalization(
    gsc_queries: List[Dict[str, Any]],
    position_threshold: float = 20.0
) -> List[Dict[str, Any]]:
    """
    Detect cannibalization issues

    Condition: Same query appears on multiple pages, both with mid-range positions
    """

    # Group by query
    query_pages = defaultdict(list)

    for q in gsc_queries:
        query_text = q["query"]
        page = q.get("page")
        position = q.get("avg_position", 100)

        if page and position <= position_threshold:
            query_pages[query_text].append({
                "page": page,
                "position": position,
                "impressions": q.get("impressions", 0)
            })

    # Find queries with multiple pages
    issues = []

    for query, pages in query_pages.items():
        if len(pages) >= 2:
            # Sort by position
            pages_sorted = sorted(pages, key=lambda x: x["position"])

            # Check if positions are close (both in mid-range = problem)
            if all(8 <= p["position"] <= 20 for p in pages_sorted[:2]):
                issues.append({
                    "query": query,
                    "pages": pages_sorted,
                    "severity": "warning"
                })
            elif len(pages) >= 2:
                issues.append({
                    "query": query,
                    "pages": pages_sorted,
                    "severity": "info"
                })

    # Sort by total impressions
    issues.sort(key=lambda x: sum(p["impressions"] for p in x["pages"]), reverse=True)

    return issues
```

---

## AL-8. API

### 8.1 エンドポイント

```python
# app/routers/keywords.py
from fastapi import APIRouter, Depends, Query
from uuid import UUID

router = APIRouter(prefix="/api/v1/sites/{site_id}/keywords", tags=["keywords"])

@router.get("/clusters")
async def get_keyword_clusters(
    site_id: UUID,
    intent: str = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get keyword clusters for site"""
    query = select(KeywordCluster).where(KeywordCluster.site_id == site_id)

    if intent:
        query = query.where(KeywordCluster.intent == intent)

    result = await db.execute(query.order_by(KeywordCluster.created_at.desc()))
    clusters = result.scalars().all()

    return {
        "clusters": [
            {
                "id": str(c.id),
                "cluster_name": c.cluster_name,
                "intent": c.intent,
                "target_page": c.target_page,
                "status": c.status,
                "query_count": len(c.queries) if hasattr(c, 'queries') else 0
            }
            for c in clusters
        ]
    }

@router.get("/clusters/{cluster_id}")
async def get_cluster_detail(
    site_id: UUID,
    cluster_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get cluster detail with queries"""
    cluster = await db.get(KeywordCluster, cluster_id)
    if not cluster or cluster.site_id != site_id:
        raise HTTPException(404, "Cluster not found")

    queries = await db.execute(
        select(ClusterQuery)
        .where(ClusterQuery.cluster_id == cluster_id)
        .order_by(ClusterQuery.impressions.desc())
    )

    return {
        "cluster": {
            "id": str(cluster.id),
            "cluster_name": cluster.cluster_name,
            "intent": cluster.intent,
            "target_page": cluster.target_page,
            "status": cluster.status
        },
        "queries": [
            {
                "query": q.query,
                "impressions": q.impressions,
                "clicks": q.clicks,
                "ctr": q.ctr,
                "avg_position": q.avg_position,
                "page": q.page
            }
            for q in queries.scalars().all()
        ]
    }

@router.get("/cannibalization")
async def get_cannibalization_issues(
    site_id: UUID,
    status: str = Query("open"),
    db: AsyncSession = Depends(get_db)
):
    """Get cannibalization issues"""
    result = await db.execute(
        select(CannibalizationIssue)
        .where(
            CannibalizationIssue.site_id == site_id,
            CannibalizationIssue.status == status
        )
        .order_by(CannibalizationIssue.created_at.desc())
    )

    return {
        "issues": [
            {
                "id": str(i.id),
                "query": i.query,
                "pages": i.pages,
                "severity": i.severity,
                "status": i.status
            }
            for i in result.scalars().all()
        ]
    }

@router.patch("/clusters/{cluster_id}/assign")
async def assign_cluster_page(
    site_id: UUID,
    cluster_id: UUID,
    target_page: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """Assign target page to cluster"""
    cluster = await db.get(KeywordCluster, cluster_id)
    if not cluster or cluster.site_id != site_id:
        raise HTTPException(404, "Cluster not found")

    cluster.target_page = target_page
    cluster.status = "assigned"
    cluster.updated_at = datetime.utcnow()

    await db.commit()

    return {"success": True, "cluster_id": str(cluster_id)}
```

---

## AL-9. Frontend UI

### 9.1 コンポーネント構成

```
components/keywords/
├─ KeywordArchitecturePage.tsx
├─ ClusterList.tsx
├─ ClusterDetail.tsx
├─ CannibalizationPanel.tsx
├─ OrphanQueriesPanel.tsx
└─ PageAssignmentModal.tsx
```

### 9.2 ClusterList.tsx

```tsx
"use client";

import { useEffect, useState } from "react";
import { GlassCard } from "@/components/layout/GlassCard";
import { Layers, AlertTriangle, CheckCircle, HelpCircle } from "lucide-react";
import { cn } from "@/lib/utils";

interface Cluster {
  id: string;
  cluster_name: string;
  intent: string;
  target_page: string | null;
  status: string;
  query_count: number;
}

const INTENT_LABELS: Record<string, { label: string; color: string }> = {
  informational: { label: "情報収集", color: "text-blue-400" },
  commercial: { label: "比較・検討", color: "text-yellow-400" },
  transactional: { label: "行動", color: "text-green-400" },
  navigational: { label: "ナビ", color: "text-purple-400" }
};

const STATUS_ICONS: Record<string, React.ReactNode> = {
  assigned: <CheckCircle className="h-4 w-4 text-green-400" />,
  partial: <AlertTriangle className="h-4 w-4 text-yellow-400" />,
  unassigned: <HelpCircle className="h-4 w-4 text-text-muted" />
};

interface ClusterListProps {
  siteId: string;
  onSelectCluster: (clusterId: string) => void;
}

export function ClusterList({ siteId, onSelectCluster }: ClusterListProps) {
  const [clusters, setClusters] = useState<Cluster[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      const url = filter
        ? `/api/v1/sites/${siteId}/keywords/clusters?intent=${filter}`
        : `/api/v1/sites/${siteId}/keywords/clusters`;

      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        setClusters(data.clusters || []);
      }
      setLoading(false);
    }
    load();
  }, [siteId, filter]);

  if (loading) {
    return <div className="text-center py-8 text-text-muted">読み込み中...</div>;
  }

  return (
    <div className="space-y-4">
      {/* Intent Filter */}
      <div className="flex gap-2 flex-wrap">
        <button
          onClick={() => setFilter(null)}
          className={cn(
            "px-3 py-1 text-xs rounded-full border transition-colors",
            !filter
              ? "bg-accent-cyan/20 border-accent-cyan text-accent-cyan"
              : "border-border-subtle text-text-muted hover:bg-bg-elevated"
          )}
        >
          すべて
        </button>
        {Object.entries(INTENT_LABELS).map(([key, { label }]) => (
          <button
            key={key}
            onClick={() => setFilter(key)}
            className={cn(
              "px-3 py-1 text-xs rounded-full border transition-colors",
              filter === key
                ? "bg-accent-cyan/20 border-accent-cyan text-accent-cyan"
                : "border-border-subtle text-text-muted hover:bg-bg-elevated"
            )}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Cluster List */}
      <div className="space-y-2">
        {clusters.map((cluster) => {
          const intent = INTENT_LABELS[cluster.intent] || INTENT_LABELS.informational;

          return (
            <GlassCard
              key={cluster.id}
              className="cursor-pointer hover:border-accent-cyan/50 transition-colors"
              onClick={() => onSelectCluster(cluster.id)}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Layers className="h-5 w-5 text-accent-cyan" />
                  <div>
                    <div className="font-medium text-text-primary">
                      {cluster.cluster_name}
                    </div>
                    <div className="flex items-center gap-2 mt-1 text-xs">
                      <span className={intent.color}>{intent.label}</span>
                      <span className="text-text-muted">
                        {cluster.query_count} クエリ
                      </span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  {STATUS_ICONS[cluster.status]}
                  {cluster.target_page && (
                    <span className="text-xs text-text-muted truncate max-w-[150px]">
                      {cluster.target_page}
                    </span>
                  )}
                </div>
              </div>
            </GlassCard>
          );
        })}
      </div>

      {clusters.length === 0 && (
        <div className="text-center py-8 text-text-muted">
          クラスタがありません
        </div>
      )}
    </div>
  );
}
```

### 9.3 CannibalizationPanel.tsx

```tsx
"use client";

import { useEffect, useState } from "react";
import { GlassCard } from "@/components/layout/GlassCard";
import { AlertTriangle, ExternalLink } from "lucide-react";

interface CannibalizationIssue {
  id: string;
  query: string;
  pages: Array<{
    page: string;
    position: number;
    impressions: number;
  }>;
  severity: string;
}

interface CannibalizationPanelProps {
  siteId: string;
}

export function CannibalizationPanel({ siteId }: CannibalizationPanelProps) {
  const [issues, setIssues] = useState<CannibalizationIssue[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      const res = await fetch(`/api/v1/sites/${siteId}/keywords/cannibalization`);
      if (res.ok) {
        const data = await res.json();
        setIssues(data.issues || []);
      }
      setLoading(false);
    }
    load();
  }, [siteId]);

  if (loading) {
    return <div className="text-center py-4 text-text-muted">読み込み中...</div>;
  }

  if (issues.length === 0) {
    return (
      <GlassCard>
        <div className="text-center py-6">
          <p className="text-green-400 font-medium">カニバリは検出されていません</p>
          <p className="text-xs text-text-muted mt-1">
            各クエリが適切にページに割り当てられています
          </p>
        </div>
      </GlassCard>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 text-yellow-400">
        <AlertTriangle className="h-5 w-5" />
        <span className="font-semibold">{issues.length}件のカニバリを検出</span>
      </div>

      {issues.map((issue) => (
        <GlassCard key={issue.id}>
          <div className="mb-3">
            <span className="text-sm font-medium text-text-primary">
              「{issue.query}」
            </span>
          </div>

          <div className="space-y-2">
            {issue.pages.map((p, i) => (
              <div
                key={i}
                className="flex items-center justify-between text-xs bg-bg-surface rounded p-2"
              >
                <div className="flex items-center gap-2">
                  <ExternalLink className="h-3 w-3 text-text-muted" />
                  <span className="text-text-secondary truncate max-w-[200px]">
                    {p.page}
                  </span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-text-muted">順位: {p.position.toFixed(1)}</span>
                  <span className="text-text-muted">表示: {p.impressions}</span>
                </div>
              </div>
            ))}
          </div>

          <p className="mt-3 text-xs text-text-muted">
            どちらか一方のページに集約するか、役割を明確に分離することを検討してください。
          </p>
        </GlassCard>
      ))}
    </div>
  );
}
```

---

## AL-10. ToDo連動

### ToDo詳細テンプレート

```python
TODO_DETAIL_TEMPLATES["keyword_orphan"] = {
    "why": "表示されているのにどのページでも十分に扱われていないクエリは、専用のセクションやページを作ることで順位・クリック率の改善が期待できます。",
    "root_causes": [
        {"label": "既存ページで触れていない", "likelihood": "high", "notes": ""},
        {"label": "触れているが薄い", "likelihood": "medium", "notes": ""},
        {"label": "専用ページが必要", "likelihood": "medium", "notes": ""}
    ],
    "steps": [
        {"text": "取りこぼしクエリの一覧を確認する", "done": False},
        {"text": "既存ページで扱えるか判断する", "done": False},
        {"text": "h2/FAQセクションを追加する or 専用ページを作成する", "done": False}
    ],
    "verification": [
        {"metric": "該当クエリの順位", "target": "10位以内", "how_to_check": "GSCで確認"}
    ]
}

TODO_DETAIL_TEMPLATES["keyword_cannibalization"] = {
    "why": "同じクエリで複数ページが競合すると、Googleがどちらを表示すべきか迷い、両方の順位が中途半端になります。",
    "root_causes": [
        {"label": "似たコンテンツが複数ページにある", "likelihood": "high", "notes": ""},
        {"label": "ページの役割が不明確", "likelihood": "high", "notes": ""},
        {"label": "内部リンクが分散している", "likelihood": "medium", "notes": ""}
    ],
    "steps": [
        {"text": "競合しているページを確認する", "done": False},
        {"text": "どちらを主軸にするか決める", "done": False},
        {"text": "片方に統合する or 役割を明確に分ける", "done": False},
        {"text": "必要に応じてリダイレクト設定", "done": False}
    ],
    "verification": [
        {"metric": "該当クエリの順位", "target": "主軸ページが上位に", "how_to_check": "GSCで確認"}
    ]
}
```

---

## AL-11. 画面配置

### Result詳細ページ タブ構成

```
Overview | Todos | Keywords | Progress | Report
                    ↑
            本Appendixの画面
```

---

## AL-12. 受け入れ基準

- [ ] クラスタが自動生成される
- [ ] Intent（意図）が分類される
- [ ] ページ割当状況が見える
- [ ] 取りこぼしクエリが検出される
- [ ] カニバリゼーションが検出される
- [ ] 競合差分キーワードが表示される
- [ ] ToDoに直結する
- [ ] クラスタへのページ割当ができる

---

## AL-13. この機能が完成すると

```md
・SEO会社が作る「キーワード設計表」が自動生成される
・どのページを直すべきかが構造で分かる
・感覚ではなく設計でSEOができる
・カニバリや取りこぼしが可視化される
```

---

## AL-14. 将来拡張

- クラスタ → コンテンツアウトライン自動生成
- h2構成案 / FAQ案自動生成
- ページ分割・統合シミュレーション
- LLM/embeddingによる高精度クラスタリング
