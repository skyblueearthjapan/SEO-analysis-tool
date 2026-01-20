# Appendix AD — SERP順位の時系列（GSCベース）実装仕様

Version: 0.1
目的: 公式/競合（任意）について、GSCの掲載順位を「時系列で蓄積・可視化」し、改善効果をトレンドで判断できるようにする
優先度: 推奨順 #1（最短で効く）
前提: GSC連携（search_console）が既存で動作している / Appendix V（analysis_checks）実装済み

---

## AD-0. 重要な前提（誤解防止）

- 本Appendixの「SERP順位」は **GSCの average_position（平均掲載順位）** を使用する（実SERP順位とは異なる）
- 目的は「改善前後のトレンド把握」であり、順位の厳密計測は次フェーズ（外部SERP API）で行う

---

## AD-1. 収集対象（MVP決め打ち）

### 1.1 ページ対象

- 公式HP（必須）
- 競合2URL（任意・GSC権限が無い場合は取得不可 → skipped）

> 競合は通常GSCが取れないため、MVPは「公式のみ」で完結させる設計とする。

### 1.2 期間

- 原則: `last_28_days` を日次で取得し、当日分のスナップショットとして保存
- UIは日次粒度だが、必要なら週次集計も可能

### 1.3 クエリ粒度（MVP）

- "ページ全体（page filter）" の集計を優先
- クエリ別は上位20（`top_queries_limit=20`）まで（任意フラグ）

---

## AD-2. DB追加（推奨：時系列は別テーブル）

analysis_results.raw_json に毎回28日分を詰めると肥大化するため、時系列は別テーブルへ。

```sql
CREATE TABLE serp_time_series (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  site_id UUID NOT NULL REFERENCES sites(site_id),
  page_id UUID REFERENCES pages(page_id),
  url TEXT NOT NULL,
  source TEXT NOT NULL DEFAULT 'gsc',
  date DATE NOT NULL,
  range_days INT NOT NULL DEFAULT 28,
  clicks INT,
  impressions INT,
  ctr DOUBLE PRECISION,
  avg_position DOUBLE PRECISION,
  created_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(site_id, url, source, date)
);

CREATE INDEX idx_serp_time_series_site ON serp_time_series(site_id);
CREATE INDEX idx_serp_time_series_date ON serp_time_series(date);
```

---

## AD-3. Backend 実装（Analyzer）

### 3.1 ファイル

```
app/services/analyzers/serp_rank_gsc_timeseries.py
```

### 3.2 実装

```python
# app/services/analyzers/serp_rank_gsc_timeseries.py
from dataclasses import dataclass
from typing import List, Dict, Any, Literal, Optional
from datetime import date, datetime
from uuid import UUID

CheckStatus = Literal["done", "partial", "skipped", "not_supported"]

@dataclass
class AnalyzerOutput:
    check_code: str
    status: CheckStatus
    notes: List[str]
    evidence: List[Dict[str, Any]]
    todo_candidates: List[Dict[str, Any]]

async def analyze_serp_rank_gsc(
    db,
    site_id: UUID,
    page_id: Optional[UUID],
    url: str,
    gsc_data: Optional[Dict[str, Any]]
) -> AnalyzerOutput:
    """
    Analyze SERP rank using GSC data and save to time series
    """
    if not gsc_data:
        return AnalyzerOutput(
            check_code="serp_rank",
            status="skipped",
            notes=["GSC not configured or no data available"],
            evidence=[],
            todo_candidates=[]
        )

    try:
        today = date.today()
        clicks = gsc_data.get("clicks", 0)
        impressions = gsc_data.get("impressions", 0)
        ctr = gsc_data.get("ctr", 0)
        avg_position = gsc_data.get("avg_position")

        # Save to time series (UPSERT)
        await save_serp_snapshot(
            db,
            site_id=site_id,
            page_id=page_id,
            url=url,
            source="gsc",
            snapshot_date=today,
            range_days=28,
            clicks=clicks,
            impressions=impressions,
            ctr=ctr,
            avg_position=avg_position
        )

        evidence = [{
            "id": "ev_serp_rank_gsc_today_official",
            "kind": "serp",
            "title": "GSC平均掲載順位（公式・本日スナップショット）",
            "severity": "info",
            "data": {
                "url": url,
                "date": today.isoformat(),
                "range_days": 28,
                "clicks": clicks,
                "impressions": impressions,
                "ctr": ctr,
                "avg_position": avg_position
            }
        }]

        # Generate todos
        todo_candidates = []

        if avg_position and avg_position <= 10 and ctr and ctr < 0.03:
            todo_candidates.append({
                "title": "CTR改善（タイトル/ディスクリプション見直し）",
                "priority": "P1",
                "category": "ctr",
                "details": f"平均順位 {avg_position:.1f} でCTRが {ctr*100:.1f}% と低い。タイトルやmeta descriptionの改善を検討",
                "source_checks": ["serp_rank", "search_console"]
            })

        if avg_position and 11 <= avg_position <= 20 and impressions and impressions > 1000:
            todo_candidates.append({
                "title": "コンテンツ拡充による順位改善",
                "priority": "P1",
                "category": "content",
                "details": f"平均順位 {avg_position:.1f} で表示回数が多い。コンテンツ拡充で上位進出の余地あり",
                "source_checks": ["serp_rank", "search_console"]
            })

        return AnalyzerOutput(
            check_code="serp_rank",
            status="done",
            notes=[],
            evidence=evidence,
            todo_candidates=todo_candidates
        )

    except Exception as e:
        return AnalyzerOutput(
            check_code="serp_rank",
            status="partial",
            notes=[f"Error: {str(e)}"],
            evidence=[],
            todo_candidates=[]
        )


async def save_serp_snapshot(
    db,
    site_id: UUID,
    page_id: Optional[UUID],
    url: str,
    source: str,
    snapshot_date: date,
    range_days: int,
    clicks: int,
    impressions: int,
    ctr: float,
    avg_position: Optional[float]
):
    """Save SERP snapshot with UPSERT"""
    from sqlalchemy import text

    await db.execute(
        text("""
            INSERT INTO serp_time_series
            (id, site_id, page_id, url, source, date, range_days, clicks, impressions, ctr, avg_position)
            VALUES (gen_random_uuid(), :site_id, :page_id, :url, :source, :date, :range_days, :clicks, :impressions, :ctr, :avg_position)
            ON CONFLICT (site_id, url, source, date)
            DO UPDATE SET
                clicks = EXCLUDED.clicks,
                impressions = EXCLUDED.impressions,
                ctr = EXCLUDED.ctr,
                avg_position = EXCLUDED.avg_position
        """),
        {
            "site_id": site_id,
            "page_id": page_id,
            "url": url,
            "source": source,
            "date": snapshot_date,
            "range_days": range_days,
            "clicks": clicks,
            "impressions": impressions,
            "ctr": ctr,
            "avg_position": avg_position
        }
    )
```

### 3.3 status ルール

| 条件 | status |
|------|--------|
| GSC enabled & fetch success | done |
| GSC enabled but partial data/timeout | partial |
| GSC not configured | skipped |

---

## AD-4. API（取得）

### 4.1 エンドポイント

```python
# app/routers/metrics.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from datetime import date

router = APIRouter()

@router.get("/{site_id}/metrics/serp")
async def get_serp_timeseries(
    site_id: UUID,
    url: str = Query(...),
    from_date: date = Query(alias="from"),
    to_date: date = Query(alias="to"),
    db: AsyncSession = Depends(get_db)
):
    """Get SERP time series data"""
    result = await db.execute(
        select(SerpTimeSeries)
        .where(
            SerpTimeSeries.site_id == site_id,
            SerpTimeSeries.url == url,
            SerpTimeSeries.date >= from_date,
            SerpTimeSeries.date <= to_date
        )
        .order_by(SerpTimeSeries.date.asc())
    )
    rows = result.scalars().all()

    return {
        "url": url,
        "source": "gsc",
        "points": [
            {
                "date": r.date.isoformat(),
                "avg_position": r.avg_position,
                "ctr": r.ctr,
                "impressions": r.impressions,
                "clicks": r.clicks
            }
            for r in rows
        ]
    }
```

### 4.2 レスポンス例

```json
{
  "url": "https://example.com",
  "source": "gsc",
  "points": [
    {"date":"2026-01-01","avg_position":14.2,"ctr":0.018,"impressions":4100,"clicks":74},
    {"date":"2026-01-02","avg_position":13.9,"ctr":0.019,"impressions":4200,"clicks":80}
  ]
}
```

---

## AD-5. Frontend（UI）

### 5.1 表示場所

- Result 詳細ページに `Progress` タブ追加（または ACセクション内）

### 5.2 コンポーネント

```tsx
// components/metrics/SerpTrendChart.tsx
"use client";

import { useEffect, useState } from "react";
import { GlassCard } from "@/components/layout/GlassCard";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import { cn } from "@/lib/utils";

interface SerpPoint {
  date: string;
  avg_position: number | null;
  ctr: number | null;
  impressions: number | null;
  clicks: number | null;
}

interface SerpTrendChartProps {
  siteId: string;
  url: string;
}

export function SerpTrendChart({ siteId, url }: SerpTrendChartProps) {
  const [data, setData] = useState<SerpPoint[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      const to = new Date().toISOString().split("T")[0];
      const from = new Date(Date.now() - 28 * 24 * 60 * 60 * 1000).toISOString().split("T")[0];

      try {
        const res = await fetch(
          `/api/v1/sites/${siteId}/metrics/serp?url=${encodeURIComponent(url)}&from=${from}&to=${to}`
        );
        if (res.ok) {
          const json = await res.json();
          setData(json.points || []);
        }
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [siteId, url]);

  if (loading) {
    return <GlassCard><div className="text-center py-8 text-text-muted">読み込み中...</div></GlassCard>;
  }

  if (data.length === 0) {
    return (
      <GlassCard>
        <div className="text-center py-8">
          <p className="text-text-muted">SERP順位データがありません</p>
          <p className="text-xs text-text-muted mt-1">GSC連携と複数回の解析が必要です</p>
        </div>
      </GlassCard>
    );
  }

  const latest = data[data.length - 1];
  const oldest = data[0];
  const positionDiff = latest.avg_position && oldest.avg_position
    ? latest.avg_position - oldest.avg_position
    : null;

  return (
    <GlassCard>
      <h3 className="text-lg font-semibold mb-4">SERP順位推移（GSC）</h3>

      {/* KPI Row */}
      <div className="grid grid-cols-4 gap-4 mb-4">
        <div className="p-3 bg-bg-surface rounded-lg">
          <div className="text-xs text-text-muted mb-1">現在の順位</div>
          <div className="text-xl font-semibold">{latest.avg_position?.toFixed(1) ?? "-"}</div>
        </div>
        <div className="p-3 bg-bg-surface rounded-lg">
          <div className="text-xs text-text-muted mb-1">変化</div>
          <div className={cn(
            "text-xl font-semibold flex items-center gap-1",
            positionDiff && positionDiff < 0 && "text-green-400",
            positionDiff && positionDiff > 0 && "text-red-400"
          )}>
            {positionDiff && positionDiff < 0 && <TrendingUp className="h-4 w-4" />}
            {positionDiff && positionDiff > 0 && <TrendingDown className="h-4 w-4" />}
            {positionDiff !== null ? positionDiff.toFixed(1) : "-"}
          </div>
        </div>
        <div className="p-3 bg-bg-surface rounded-lg">
          <div className="text-xs text-text-muted mb-1">CTR</div>
          <div className="text-xl font-semibold">
            {latest.ctr ? (latest.ctr * 100).toFixed(1) + "%" : "-"}
          </div>
        </div>
        <div className="p-3 bg-bg-surface rounded-lg">
          <div className="text-xs text-text-muted mb-1">表示回数</div>
          <div className="text-xl font-semibold">{latest.impressions?.toLocaleString() ?? "-"}</div>
        </div>
      </div>

      {/* Simple Chart (bars) */}
      <div className="h-32 flex items-end gap-1">
        {data.slice(-14).map((point, i) => {
          const maxPos = Math.max(...data.map(d => d.avg_position || 0));
          const height = point.avg_position ? ((maxPos - point.avg_position + 1) / maxPos) * 100 : 0;
          return (
            <div
              key={i}
              className="flex-1 bg-accent-cyan/60 rounded-t"
              style={{ height: `${Math.max(height, 5)}%` }}
              title={`${point.date}: ${point.avg_position?.toFixed(1)}`}
            />
          );
        })}
      </div>
      <p className="text-xs text-text-muted mt-2 text-center">過去14日間（低いほど上位）</p>
    </GlassCard>
  );
}
```

---

## AD-6. ToDo連動（任意）

- avg_position が改善せず、impressionsが十分 → title/meta見直し ToDo
- CTRが低い → CTR改善 ToDo

source_checks は `["serp_rank","search_console"]` を許可（複数）

---

## AD-7. analysis_checks 連動

- `analysis_checks.checks.serp_rank` を追加・更新
- Checklist UI（拡張予定 → done/partial/skippedに変化）

---

## AD-8. 受け入れ基準

- [ ] 日次スナップショットがDBに保存される
- [ ] from/to 指定で時系列が取れる
- [ ] UIにトレンドが表示される
- [ ] 順位改善（下がる）が緑、悪化（上がる）が赤で表示
- [ ] GSC無しの場合は skipped 表示で落ちない
