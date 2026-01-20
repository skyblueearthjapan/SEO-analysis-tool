# Appendix AE — クロールエラー推移（サイトクロール由来）実装仕様

Version: 0.1
目的: サイト全体クロールの結果から「4xx/5xx/タイムアウト等のエラー推移」を時系列で蓄積し、技術改善効果を可視化する
優先度: 推奨順 #2
前提: Appendix Y（site_crawl）を実装済み or 先に実装する（クロールが無いと作れない）

---

## AE-0. スコープ（MVP）

- "クロール実行ごと" にエラーサマリを保存
- 日次は必須ではなく、Run実行タイミングでも可（週次運用でも成立）

---

## AE-1. DB（サマリテーブル追加）

crawl_pages から都度集計でも可能だが、表示を高速化するためサマリを保存。

```sql
CREATE TABLE crawl_error_time_series (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  site_id UUID NOT NULL REFERENCES sites(site_id),
  run_id UUID NOT NULL REFERENCES crawl_runs(id),
  date DATE NOT NULL,
  pages_crawled INT NOT NULL DEFAULT 0,
  errors_4xx INT NOT NULL DEFAULT 0,
  errors_5xx INT NOT NULL DEFAULT 0,
  timeouts INT NOT NULL DEFAULT 0,
  other_errors INT NOT NULL DEFAULT 0,
  orphan_count INT DEFAULT 0,
  created_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(site_id, date, run_id)
);

CREATE INDEX idx_crawl_error_ts_site ON crawl_error_time_series(site_id);
CREATE INDEX idx_crawl_error_ts_date ON crawl_error_time_series(date);
```

---

## AE-2. Backend（集計ジョブ）

### 2.1 集計タイミング

- crawl_run 完了後に集計して保存（最推奨）

### 2.2 実装

```python
# app/services/analyzers/crawl_error_timeseries.py
from dataclasses import dataclass
from typing import List, Dict, Any
from datetime import date
from uuid import UUID
from sqlalchemy import select, func

async def save_crawl_error_snapshot(
    db,
    site_id: UUID,
    run_id: UUID,
    crawl_pages: List[Dict[str, Any]]
):
    """
    Save crawl error summary after crawl completion
    """
    today = date.today()

    pages_crawled = len(crawl_pages)
    errors_4xx = sum(1 for p in crawl_pages if 400 <= (p.get("status_code") or 0) < 500)
    errors_5xx = sum(1 for p in crawl_pages if (p.get("status_code") or 0) >= 500)
    timeouts = sum(1 for p in crawl_pages if p.get("timeout", False))
    other_errors = sum(1 for p in crawl_pages if p.get("error") and not p.get("timeout"))

    # Orphan count (pages with 0 inlinks except start page)
    orphan_count = sum(1 for p in crawl_pages if p.get("inlinks", 0) == 0 and p.get("depth", 0) > 0)

    from sqlalchemy import text
    await db.execute(
        text("""
            INSERT INTO crawl_error_time_series
            (id, site_id, run_id, date, pages_crawled, errors_4xx, errors_5xx, timeouts, other_errors, orphan_count)
            VALUES (gen_random_uuid(), :site_id, :run_id, :date, :pages_crawled, :errors_4xx, :errors_5xx, :timeouts, :other_errors, :orphan_count)
            ON CONFLICT (site_id, date, run_id)
            DO UPDATE SET
                pages_crawled = EXCLUDED.pages_crawled,
                errors_4xx = EXCLUDED.errors_4xx,
                errors_5xx = EXCLUDED.errors_5xx,
                timeouts = EXCLUDED.timeouts,
                other_errors = EXCLUDED.other_errors,
                orphan_count = EXCLUDED.orphan_count
        """),
        {
            "site_id": site_id,
            "run_id": run_id,
            "date": today,
            "pages_crawled": pages_crawled,
            "errors_4xx": errors_4xx,
            "errors_5xx": errors_5xx,
            "timeouts": timeouts,
            "other_errors": other_errors,
            "orphan_count": orphan_count
        }
    )

    return {
        "date": today.isoformat(),
        "pages_crawled": pages_crawled,
        "errors_4xx": errors_4xx,
        "errors_5xx": errors_5xx,
        "timeouts": timeouts,
        "orphan_count": orphan_count
    }
```

### 2.3 集計ロジック

- 4xx: 400–499
- 5xx: 500–599
- timeout: timeoutフラグまたは status_code=0 等（実装で統一）

---

## AE-3. evidence（analysis_result.json に入れるのは当日分のみ）

```json
{
  "id": "ev_crawl_errors_today",
  "kind": "crawl",
  "title": "クロールエラーサマリ（今回）",
  "severity": "info",
  "data": {
    "date": "2026-01-20",
    "pages_crawled": 84,
    "errors_4xx": 3,
    "errors_5xx": 1,
    "timeouts": 0,
    "orphan_count": 5
  }
}
```

---

## AE-4. API（取得）

### 4.1 エンドポイント

```python
# app/routers/metrics.py
@router.get("/{site_id}/metrics/crawl-errors")
async def get_crawl_error_timeseries(
    site_id: UUID,
    from_date: date = Query(alias="from"),
    to_date: date = Query(alias="to"),
    db: AsyncSession = Depends(get_db)
):
    """Get crawl error time series data"""
    result = await db.execute(
        select(CrawlErrorTimeSeries)
        .where(
            CrawlErrorTimeSeries.site_id == site_id,
            CrawlErrorTimeSeries.date >= from_date,
            CrawlErrorTimeSeries.date <= to_date
        )
        .order_by(CrawlErrorTimeSeries.date.asc())
    )
    rows = result.scalars().all()

    return {
        "points": [
            {
                "date": r.date.isoformat(),
                "pages_crawled": r.pages_crawled,
                "errors_4xx": r.errors_4xx,
                "errors_5xx": r.errors_5xx,
                "timeouts": r.timeouts,
                "orphan_count": r.orphan_count
            }
            for r in rows
        ]
    }
```

### 4.2 レスポンス例

```json
{
  "points": [
    {"date":"2026-01-01","errors_4xx":15,"errors_5xx":4,"timeouts":1,"pages_crawled":80,"orphan_count":8},
    {"date":"2026-01-08","errors_4xx":3,"errors_5xx":1,"timeouts":0,"pages_crawled":90,"orphan_count":5}
  ]
}
```

---

## AE-5. Frontend（UI）

### 5.1 表示場所

- `Progress` タブ（ACの成果トラッキングの中に並べる）

### 5.2 コンポーネント

```tsx
// components/metrics/CrawlErrorTrendChart.tsx
"use client";

import { useEffect, useState } from "react";
import { GlassCard } from "@/components/layout/GlassCard";
import { AlertTriangle, CheckCircle, TrendingDown } from "lucide-react";
import { cn } from "@/lib/utils";

interface CrawlErrorPoint {
  date: string;
  pages_crawled: number;
  errors_4xx: number;
  errors_5xx: number;
  timeouts: number;
  orphan_count: number;
}

interface CrawlErrorTrendChartProps {
  siteId: string;
}

export function CrawlErrorTrendChart({ siteId }: CrawlErrorTrendChartProps) {
  const [data, setData] = useState<CrawlErrorPoint[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      const to = new Date().toISOString().split("T")[0];
      const from = new Date(Date.now() - 90 * 24 * 60 * 60 * 1000).toISOString().split("T")[0];

      try {
        const res = await fetch(
          `/api/v1/sites/${siteId}/metrics/crawl-errors?from=${from}&to=${to}`
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
  }, [siteId]);

  if (loading) {
    return <GlassCard><div className="text-center py-8 text-text-muted">読み込み中...</div></GlassCard>;
  }

  if (data.length === 0) {
    return (
      <GlassCard>
        <div className="text-center py-8">
          <p className="text-text-muted">クロールエラーデータがありません</p>
          <p className="text-xs text-text-muted mt-1">サイトクロールを実行してください</p>
        </div>
      </GlassCard>
    );
  }

  const latest = data[data.length - 1];
  const oldest = data[0];
  const errorDiff4xx = latest.errors_4xx - oldest.errors_4xx;
  const errorDiff5xx = latest.errors_5xx - oldest.errors_5xx;
  const totalErrors = latest.errors_4xx + latest.errors_5xx + latest.timeouts;
  const isHealthy = totalErrors === 0;

  return (
    <GlassCard>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold">クロールエラー推移</h3>
        {isHealthy ? (
          <span className="flex items-center gap-1 text-green-400 text-sm">
            <CheckCircle className="h-4 w-4" />
            Healthy
          </span>
        ) : (
          <span className="flex items-center gap-1 text-amber-400 text-sm">
            <AlertTriangle className="h-4 w-4" />
            {totalErrors} errors
          </span>
        )}
      </div>

      {/* KPI Row */}
      <div className="grid grid-cols-4 gap-4 mb-4">
        <div className="p-3 bg-bg-surface rounded-lg">
          <div className="text-xs text-text-muted mb-1">4xx エラー</div>
          <div className="flex items-center gap-2">
            <span className={cn(
              "text-xl font-semibold",
              latest.errors_4xx > 0 && "text-amber-400"
            )}>
              {latest.errors_4xx}
            </span>
            {errorDiff4xx < 0 && (
              <span className="text-xs text-green-400 flex items-center">
                <TrendingDown className="h-3 w-3" />
                {errorDiff4xx}
              </span>
            )}
          </div>
        </div>
        <div className="p-3 bg-bg-surface rounded-lg">
          <div className="text-xs text-text-muted mb-1">5xx エラー</div>
          <div className="flex items-center gap-2">
            <span className={cn(
              "text-xl font-semibold",
              latest.errors_5xx > 0 && "text-red-400"
            )}>
              {latest.errors_5xx}
            </span>
            {errorDiff5xx < 0 && (
              <span className="text-xs text-green-400 flex items-center">
                <TrendingDown className="h-3 w-3" />
                {errorDiff5xx}
              </span>
            )}
          </div>
        </div>
        <div className="p-3 bg-bg-surface rounded-lg">
          <div className="text-xs text-text-muted mb-1">Orphan</div>
          <div className="text-xl font-semibold">{latest.orphan_count}</div>
        </div>
        <div className="p-3 bg-bg-surface rounded-lg">
          <div className="text-xs text-text-muted mb-1">総ページ</div>
          <div className="text-xl font-semibold">{latest.pages_crawled}</div>
        </div>
      </div>

      {/* Timeline */}
      <div className="space-y-2">
        {data.slice(-5).map((point, i) => (
          <div key={i} className="flex items-center gap-4 text-sm">
            <span className="text-text-muted w-24">{point.date}</span>
            <div className="flex-1 flex items-center gap-2">
              <span className={cn(
                "px-2 py-0.5 rounded text-xs",
                point.errors_4xx > 0 ? "bg-amber-400/10 text-amber-400" : "bg-bg-elevated text-text-muted"
              )}>
                4xx: {point.errors_4xx}
              </span>
              <span className={cn(
                "px-2 py-0.5 rounded text-xs",
                point.errors_5xx > 0 ? "bg-red-400/10 text-red-400" : "bg-bg-elevated text-text-muted"
              )}>
                5xx: {point.errors_5xx}
              </span>
            </div>
          </div>
        ))}
      </div>
    </GlassCard>
  );
}
```

---

## AE-6. ToDo連動

- errors_5xx > 0 → P0 サーバエラー修正（source_checks=["site_crawl"]）
- errors_4xx が多い → P1 URL修正 / リダイレクト整備（source_checks=["site_crawl"]）
- orphan増 → P1 内部リンク改善（source_checks=["site_crawl"]）

---

## AE-7. analysis_checks

- `site_crawl` が done のときのみ `crawl-errors` 表示を濃くする
- 無い場合は "No crawl data" 表示

---

## AE-8. 受け入れ基準

- [ ] crawl完了ごとにサマリ保存される
- [ ] from/to で推移取得できる
- [ ] UIに推移が表示される
- [ ] エラー0件で "Healthy" バッジが表示される
- [ ] エラー減少時に緑で表示される
- [ ] クロール未実行でもUIが壊れず説明表示
