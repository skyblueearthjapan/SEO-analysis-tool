# Appendix AC — 成果トラッキング（Before / After）仕様

Version: 0.1
目的:
- 「やった結果どうなったか」を可視化
- SEOコンサル体験を完成させる
- 継続利用・改善ループを作る

---

## AC-1. 基本思想（重要）

SEOは「診断 → 改善 → 検証」の繰り返しです。このツールは、改善の成果を可視化し、次の判断につなげるためのものです。

---

## AC-2. トラッキング対象（MVP）

### 技術

- PageSpeed score
- LCP / INP / CLS

### 構造・品質

- 意図カバー率（missing_sections数）
- 構造化データ有無

### 検索（GSC連携時）

- Impressions
- CTR
- Average position

---

## AC-3. データモデル（MVP）

### 3.1 progress_snapshots テーブル

```sql
CREATE TABLE progress_snapshots (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  site_id UUID NOT NULL REFERENCES sites(site_id),
  page_id UUID REFERENCES pages(page_id),
  result_id UUID REFERENCES analysis_results(result_id),
  snapshot_type VARCHAR(20) DEFAULT 'auto',  -- auto, baseline, manual
  metrics JSONB NOT NULL,
  captured_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_progress_snapshots_site ON progress_snapshots(site_id);
CREATE INDEX idx_progress_snapshots_captured ON progress_snapshots(captured_at);
```

### 3.2 metrics JSON構造

```json
{
  "pagespeed": {
    "performance_score": 78,
    "lcp_ms": 2100,
    "inp_ms": 180,
    "cls": 0.05
  },
  "content": {
    "intent_missing_count": 1,
    "word_count": 2400,
    "h2_count": 8
  },
  "schema": {
    "has_faq": true,
    "has_organization": true
  },
  "gsc": {
    "impressions": 5400,
    "clicks": 168,
    "ctr": 0.031,
    "avg_position": 10.4
  }
}
```

### 3.3 比較用オブジェクト

```json
{
  "baseline": {
    "captured_at": "2026-01-01T00:00:00Z",
    "metrics": { ... }
  },
  "current": {
    "captured_at": "2026-01-28T00:00:00Z",
    "metrics": { ... }
  },
  "diff": {
    "pagespeed_score": +16,
    "intent_missing": -3,
    "ctr": +0.013,
    "avg_position": -3.8
  }
}
```

---

## AC-4. Backend実装

### AC-4.1 スナップショット保存

```python
# app/services/progress.py
from datetime import datetime
from typing import Dict, Any, Optional
from uuid import UUID

async def save_progress_snapshot(
    db,
    site_id: UUID,
    page_id: Optional[UUID],
    result_id: UUID,
    metrics: Dict[str, Any],
    snapshot_type: str = "auto"
):
    """Save a progress snapshot after analysis"""
    snapshot = ProgressSnapshot(
        site_id=site_id,
        page_id=page_id,
        result_id=result_id,
        snapshot_type=snapshot_type,
        metrics=metrics,
        captured_at=datetime.utcnow()
    )
    db.add(snapshot)
    await db.flush()
    return snapshot

def extract_metrics_from_result(analysis_json: Dict[str, Any]) -> Dict[str, Any]:
    """Extract trackable metrics from analysis result"""
    pages = analysis_json.get("pages", [])
    official = None
    for p in pages:
        if p.get("page_type") == "official_homepage":
            official = p
            break

    if not official:
        return {}

    tech = official.get("tech", {})
    content = official.get("content", {})
    html = official.get("html", {})
    gsc = official.get("search_console", {})
    pagespeed = tech.get("pagespeed", {})

    # Count missing intents
    intent_coverage = content.get("intent_coverage", {})
    missing_count = sum(1 for v in intent_coverage.values() if v == 0)

    return {
        "pagespeed": {
            "performance_score": pagespeed.get("performance_score"),
            "lcp_ms": pagespeed.get("lcp_ms"),
            "inp_ms": pagespeed.get("inp_ms"),
            "cls": pagespeed.get("cls")
        },
        "content": {
            "intent_missing_count": missing_count,
            "word_count": content.get("word_count", 0),
            "h2_count": len(html.get("h2", []))
        },
        "schema": {
            "has_faq": html.get("structured_data", {}).get("has_faq_schema", False),
            "has_organization": html.get("structured_data", {}).get("has_organization_schema", False)
        },
        "gsc": {
            "impressions": gsc.get("impressions"),
            "clicks": gsc.get("clicks"),
            "ctr": gsc.get("ctr"),
            "avg_position": gsc.get("avg_position")
        }
    }
```

### AC-4.2 比較取得

```python
async def get_progress_comparison(
    db,
    site_id: UUID,
    page_id: Optional[UUID] = None
) -> Dict[str, Any]:
    """Get baseline vs current comparison"""
    from sqlalchemy import select

    # Get baseline (first snapshot or marked as baseline)
    baseline_query = (
        select(ProgressSnapshot)
        .where(ProgressSnapshot.site_id == site_id)
        .order_by(ProgressSnapshot.captured_at.asc())
        .limit(1)
    )
    if page_id:
        baseline_query = baseline_query.where(ProgressSnapshot.page_id == page_id)

    baseline_result = await db.execute(baseline_query)
    baseline = baseline_result.scalar_one_or_none()

    # Get current (latest snapshot)
    current_query = (
        select(ProgressSnapshot)
        .where(ProgressSnapshot.site_id == site_id)
        .order_by(ProgressSnapshot.captured_at.desc())
        .limit(1)
    )
    if page_id:
        current_query = current_query.where(ProgressSnapshot.page_id == page_id)

    current_result = await db.execute(current_query)
    current = current_result.scalar_one_or_none()

    if not baseline or not current:
        return None

    # Calculate diff
    diff = calculate_diff(baseline.metrics, current.metrics)

    return {
        "baseline": {
            "captured_at": baseline.captured_at.isoformat(),
            "metrics": baseline.metrics
        },
        "current": {
            "captured_at": current.captured_at.isoformat(),
            "metrics": current.metrics
        },
        "diff": diff
    }

def calculate_diff(baseline: Dict, current: Dict) -> Dict[str, Any]:
    """Calculate metric differences"""
    diff = {}

    # PageSpeed
    b_ps = baseline.get("pagespeed", {}).get("performance_score")
    c_ps = current.get("pagespeed", {}).get("performance_score")
    if b_ps is not None and c_ps is not None:
        diff["pagespeed_score"] = c_ps - b_ps

    # Intent missing
    b_im = baseline.get("content", {}).get("intent_missing_count", 0)
    c_im = current.get("content", {}).get("intent_missing_count", 0)
    diff["intent_missing"] = c_im - b_im

    # CTR
    b_ctr = baseline.get("gsc", {}).get("ctr")
    c_ctr = current.get("gsc", {}).get("ctr")
    if b_ctr is not None and c_ctr is not None:
        diff["ctr"] = round(c_ctr - b_ctr, 4)

    # Avg Position (lower is better, so negative diff is good)
    b_pos = baseline.get("gsc", {}).get("avg_position")
    c_pos = current.get("gsc", {}).get("avg_position")
    if b_pos is not None and c_pos is not None:
        diff["avg_position"] = round(c_pos - b_pos, 1)

    return diff
```

### AC-4.3 API エンドポイント

```python
# app/routers/progress.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

router = APIRouter()

@router.get("/{site_id}/progress")
async def get_site_progress(
    site_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get progress comparison for a site"""
    from app.services.progress import get_progress_comparison

    comparison = await get_progress_comparison(db, site_id)
    if not comparison:
        return {"message": "Not enough data for comparison"}

    return comparison

@router.post("/{site_id}/progress/baseline")
async def set_baseline(
    site_id: UUID,
    result_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Manually set a result as baseline"""
    # Implementation: mark specific snapshot as baseline
    pass
```

---

## AC-5. Frontend実装

### AC-5.1 ProgressPanel コンポーネント

```tsx
// components/progress/ProgressPanel.tsx
"use client";

import { useEffect, useState } from "react";
import { GlassCard } from "@/components/layout/GlassCard";
import { TrendingUp, TrendingDown, Minus, Calendar } from "lucide-react";
import { cn } from "@/lib/utils";

interface ProgressData {
  baseline: {
    captured_at: string;
    metrics: Record<string, any>;
  };
  current: {
    captured_at: string;
    metrics: Record<string, any>;
  };
  diff: Record<string, number>;
}

interface MetricDisplayProps {
  label: string;
  baseline: number | null;
  current: number | null;
  diff: number | null;
  unit?: string;
  lowerIsBetter?: boolean;
}

function MetricDisplay({ label, baseline, current, diff, unit = "", lowerIsBetter = false }: MetricDisplayProps) {
  if (baseline === null || current === null) return null;

  const isImproved = lowerIsBetter ? (diff ?? 0) < 0 : (diff ?? 0) > 0;
  const isDeclined = lowerIsBetter ? (diff ?? 0) > 0 : (diff ?? 0) < 0;

  return (
    <div className="p-4 bg-bg-surface rounded-lg border border-border-subtle">
      <div className="text-xs text-text-muted mb-2">{label}</div>
      <div className="flex items-end justify-between">
        <div className="flex items-baseline gap-2">
          <span className="text-text-muted text-sm">{baseline}{unit}</span>
          <span className="text-text-muted">→</span>
          <span className="text-lg font-semibold text-text-primary">{current}{unit}</span>
        </div>
        {diff !== null && (
          <span className={cn(
            "flex items-center gap-1 text-sm font-medium px-2 py-0.5 rounded",
            isImproved && "text-green-400 bg-green-400/10",
            isDeclined && "text-red-400 bg-red-400/10",
            !isImproved && !isDeclined && "text-text-muted bg-bg-elevated"
          )}>
            {isImproved && <TrendingUp className="h-3 w-3" />}
            {isDeclined && <TrendingDown className="h-3 w-3" />}
            {!isImproved && !isDeclined && <Minus className="h-3 w-3" />}
            {diff > 0 && "+"}{diff}{unit}
          </span>
        )}
      </div>
    </div>
  );
}

export function ProgressPanel({ siteId }: { siteId: string }) {
  const [data, setData] = useState<ProgressData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadProgress() {
      try {
        const res = await fetch(`/api/v1/sites/${siteId}/progress`);
        if (res.ok) {
          const json = await res.json();
          if (json.baseline && json.current) {
            setData(json);
          }
        }
      } finally {
        setLoading(false);
      }
    }
    loadProgress();
  }, [siteId]);

  if (loading) {
    return (
      <GlassCard>
        <div className="text-center text-text-muted py-8">読み込み中...</div>
      </GlassCard>
    );
  }

  if (!data) {
    return (
      <GlassCard>
        <div className="text-center py-8">
          <p className="text-text-muted mb-2">まだ比較データがありません</p>
          <p className="text-xs text-text-muted">複数回の解析を実行すると、改善の推移が表示されます</p>
        </div>
      </GlassCard>
    );
  }

  const { baseline, current, diff } = data;
  const baselineDate = new Date(baseline.captured_at).toLocaleDateString("ja-JP");
  const currentDate = new Date(current.captured_at).toLocaleDateString("ja-JP");

  return (
    <GlassCard>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold">改善の推移</h3>
        <div className="flex items-center gap-2 text-xs text-text-muted">
          <Calendar className="h-3 w-3" />
          <span>{baselineDate} → {currentDate}</span>
        </div>
      </div>

      {/* Summary Message */}
      <div className="p-4 bg-bg-elevated rounded-lg mb-4">
        <p className="text-sm text-text-secondary">
          {diff.pagespeed_score > 0 && diff.intent_missing < 0 && (
            <>ページの技術的評価とコンテンツの網羅性が改善されています。</>
          )}
          {diff.pagespeed_score > 0 && diff.intent_missing >= 0 && (
            <>PageSpeedが改善されました。コンテンツ面の改善も検討してください。</>
          )}
          {diff.pagespeed_score <= 0 && diff.intent_missing < 0 && (
            <>コンテンツの網羅性が改善されました。</>
          )}
          {diff.pagespeed_score <= 0 && diff.intent_missing >= 0 && (
            <>大きな変化は見られません。ToDoを確認してください。</>
          )}
        </p>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-2 gap-3">
        <MetricDisplay
          label="PageSpeed スコア"
          baseline={baseline.metrics.pagespeed?.performance_score}
          current={current.metrics.pagespeed?.performance_score}
          diff={diff.pagespeed_score}
        />
        <MetricDisplay
          label="意図欠損数"
          baseline={baseline.metrics.content?.intent_missing_count}
          current={current.metrics.content?.intent_missing_count}
          diff={diff.intent_missing}
          lowerIsBetter
        />
        <MetricDisplay
          label="CTR"
          baseline={baseline.metrics.gsc?.ctr ? (baseline.metrics.gsc.ctr * 100).toFixed(1) : null}
          current={current.metrics.gsc?.ctr ? (current.metrics.gsc.ctr * 100).toFixed(1) : null}
          diff={diff.ctr ? (diff.ctr * 100) : null}
          unit="%"
        />
        <MetricDisplay
          label="平均順位"
          baseline={baseline.metrics.gsc?.avg_position}
          current={current.metrics.gsc?.avg_position}
          diff={diff.avg_position}
          lowerIsBetter
        />
      </div>
    </GlassCard>
  );
}
```

### AC-5.2 Result画面への組み込み

```tsx
// Result Overview タブに追加
{activeTab === "overview" && (
  <div className="space-y-6">
    {/* Progress Panel */}
    <ProgressPanel siteId={siteId} />

    {/* 既存のDiagnosis Card等 */}
    ...
  </div>
)}
```

---

## AC-6. 完了ToDoとの紐付け

### AC-6.1 改善に寄与した可能性のあるToDo

Result間の差分から、完了したToDoを推定表示：

```tsx
// components/progress/CompletedTodosPanel.tsx
export function CompletedTodosPanel({
  baselineTodos,
  currentTodos
}: {
  baselineTodos: Todo[];
  currentTodos: Todo[];
}) {
  // baseline にあって current にないToDo = 改善された可能性
  const completedIds = new Set(currentTodos.map(t => t.todo_id));
  const potentiallyCompleted = baselineTodos.filter(t => !completedIds.has(t.todo_id));

  if (potentiallyCompleted.length === 0) return null;

  return (
    <div className="mt-4">
      <div className="text-xs font-medium text-text-muted mb-2">
        改善に寄与した可能性のあるToDo
      </div>
      <div className="space-y-2">
        {potentiallyCompleted.slice(0, 5).map(todo => (
          <div key={todo.todo_id} className="flex items-center gap-2 text-sm">
            <span className="text-green-400">✓</span>
            <span className="text-text-secondary">{todo.title}</span>
          </div>
        ))}
      </div>
      <p className="mt-2 text-xs text-text-muted">
        ※因果関係は断定できません。参考情報としてご覧ください。
      </p>
    </div>
  );
}
```

---

## AC-7. 受け入れ基準

- [ ] 改善の有無が一目で分かる
- [ ] 数値は「差分」で表示される
- [ ] 上昇/下降が色分けされる
- [ ] baseline vs current の日付が表示される
- [ ] ToDoと成果が紐づいて見える
- [ ] 過度な断定表現が無い（「可能性がある」等）
- [ ] データが少ない場合のフォールバック表示がある

---

## AC-8. 将来拡張（予告）

- SERP順位の時系列グラフ
- 被リンク数推移
- クロールエラー推移
- 週次/月次レポートメール
- PDF出力
