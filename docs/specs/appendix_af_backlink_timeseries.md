# Appendix AF — 被リンク推移（Backlinks Timeseries）実装仕様

Version: 0.1
目的: 被リンク（参照ドメイン数・リンク数・オーソリティ）の推移を時系列で保存し、外部評価の成長を可視化する
優先度: 推奨順 #3
前提: Appendix X（backlinks provider）を実装済み

---

## AF-0. MVPポリシー（決め打ち）

- 取得頻度は **週次 or 月次** を推奨（毎日だとコストが上がりがち）
- "スナップショット"として保存し、グラフ化
- 競合も取れるなら同様に保存（provider次第）

---

## AF-1. DB（時系列テーブル）

```sql
CREATE TABLE backlink_time_series (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  site_id UUID NOT NULL REFERENCES sites(site_id),
  url TEXT NOT NULL,
  provider TEXT NOT NULL DEFAULT 'moz',
  date DATE NOT NULL,
  ref_domains INT,
  backlinks_total INT,
  dofollow_ratio DOUBLE PRECISION,
  authority DOUBLE PRECISION,
  created_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(site_id, url, provider, date)
);

CREATE INDEX idx_backlink_ts_site ON backlink_time_series(site_id);
CREATE INDEX idx_backlink_ts_date ON backlink_time_series(date);
```

---

## AF-2. Backend（Analyzer拡張）

### 2.1 既存 `backlinks` Analyzer に追加実装

取得に成功したら `backlink_time_series` に UPSERT。
analysis_result.json には当日分サマリevidenceのみ入れる。

### 2.2 実装

```python
# app/services/analyzers/backlinks_timeseries.py
from datetime import date
from uuid import UUID
from typing import Dict, Any, Optional

async def save_backlink_snapshot(
    db,
    site_id: UUID,
    url: str,
    provider: str,
    metrics: Dict[str, Any]
):
    """
    Save backlink snapshot with UPSERT
    """
    today = date.today()

    from sqlalchemy import text
    await db.execute(
        text("""
            INSERT INTO backlink_time_series
            (id, site_id, url, provider, date, ref_domains, backlinks_total, dofollow_ratio, authority)
            VALUES (gen_random_uuid(), :site_id, :url, :provider, :date, :ref_domains, :backlinks_total, :dofollow_ratio, :authority)
            ON CONFLICT (site_id, url, provider, date)
            DO UPDATE SET
                ref_domains = EXCLUDED.ref_domains,
                backlinks_total = EXCLUDED.backlinks_total,
                dofollow_ratio = EXCLUDED.dofollow_ratio,
                authority = EXCLUDED.authority
        """),
        {
            "site_id": site_id,
            "url": url,
            "provider": provider,
            "date": today,
            "ref_domains": metrics.get("ref_domains"),
            "backlinks_total": metrics.get("backlinks_total"),
            "dofollow_ratio": metrics.get("dofollow_ratio"),
            "authority": metrics.get("domain_authority") or metrics.get("authority")
        }
    )

    return {
        "date": today.isoformat(),
        "provider": provider,
        **metrics
    }
```

### 2.3 Analyzer統合

```python
# backlinks_moz.py に追加
async def analyze_backlinks(
    db,
    site_id: UUID,
    official_url: str,
    competitor_urls: List[str]
) -> AnalyzerOutput:
    # ... 既存の取得ロジック ...

    if official_metrics:
        # Save to time series
        await save_backlink_snapshot(
            db,
            site_id=site_id,
            url=official_url,
            provider="moz",
            metrics=official_metrics
        )

        evidence.append({
            "id": "ev_backlinks_today_official",
            "kind": "backlinks",
            "title": "被リンク推移（本日スナップショット）",
            "severity": "info",
            "data": {
                "date": date.today().isoformat(),
                "provider": "moz",
                "url": official_url,
                **official_metrics
            }
        })

    # ... 残りの処理 ...
```

---

## AF-3. evidence例

```json
{
  "id": "ev_backlinks_today_official",
  "kind": "backlinks",
  "title": "被リンク推移（本日スナップショット）",
  "severity": "info",
  "data": {
    "date": "2026-01-20",
    "provider": "moz",
    "url": "https://example.com",
    "ref_domains": 42,
    "backlinks_total": 1200,
    "dofollow_ratio": 0.71,
    "authority": 18
  }
}
```

---

## AF-4. API（取得）

### 4.1 エンドポイント

```python
# app/routers/metrics.py
@router.get("/{site_id}/metrics/backlinks")
async def get_backlink_timeseries(
    site_id: UUID,
    url: str = Query(...),
    from_date: date = Query(alias="from"),
    to_date: date = Query(alias="to"),
    db: AsyncSession = Depends(get_db)
):
    """Get backlink time series data"""
    result = await db.execute(
        select(BacklinkTimeSeries)
        .where(
            BacklinkTimeSeries.site_id == site_id,
            BacklinkTimeSeries.url == url,
            BacklinkTimeSeries.date >= from_date,
            BacklinkTimeSeries.date <= to_date
        )
        .order_by(BacklinkTimeSeries.date.asc())
    )
    rows = result.scalars().all()

    if not rows:
        return {"url": url, "provider": None, "points": []}

    return {
        "url": url,
        "provider": rows[0].provider if rows else None,
        "points": [
            {
                "date": r.date.isoformat(),
                "ref_domains": r.ref_domains,
                "backlinks_total": r.backlinks_total,
                "dofollow_ratio": r.dofollow_ratio,
                "authority": r.authority
            }
            for r in rows
        ]
    }
```

### 4.2 レスポンス例

```json
{
  "url": "example.com",
  "provider": "moz",
  "points": [
    {"date":"2025-11-01","ref_domains":18,"authority":12,"backlinks_total":320,"dofollow_ratio":0.65},
    {"date":"2025-12-01","ref_domains":22,"authority":14,"backlinks_total":450,"dofollow_ratio":0.68},
    {"date":"2026-01-01","ref_domains":26,"authority":15,"backlinks_total":520,"dofollow_ratio":0.70}
  ]
}
```

---

## AF-5. Frontend（UI）

### 5.1 表示場所

- `Progress` タブ（外部評価の成長セクション）

### 5.2 コンポーネント

```tsx
// components/metrics/BacklinkTrendChart.tsx
"use client";

import { useEffect, useState } from "react";
import { GlassCard } from "@/components/layout/GlassCard";
import { TrendingUp, TrendingDown, Minus, Link2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface BacklinkPoint {
  date: string;
  ref_domains: number | null;
  backlinks_total: number | null;
  dofollow_ratio: number | null;
  authority: number | null;
}

interface BacklinkTrendChartProps {
  siteId: string;
  url: string;
}

export function BacklinkTrendChart({ siteId, url }: BacklinkTrendChartProps) {
  const [data, setData] = useState<BacklinkPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [metric, setMetric] = useState<"ref_domains" | "authority">("ref_domains");

  useEffect(() => {
    async function loadData() {
      const to = new Date().toISOString().split("T")[0];
      const from = new Date(Date.now() - 180 * 24 * 60 * 60 * 1000).toISOString().split("T")[0];

      try {
        const res = await fetch(
          `/api/v1/sites/${siteId}/metrics/backlinks?url=${encodeURIComponent(url)}&from=${from}&to=${to}`
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
          <p className="text-text-muted">被リンクデータがありません</p>
          <p className="text-xs text-text-muted mt-1">被リンク分析（Moz等）を有効にしてください</p>
        </div>
      </GlassCard>
    );
  }

  const latest = data[data.length - 1];
  const oldest = data[0];
  const refDomainsDiff = (latest.ref_domains ?? 0) - (oldest.ref_domains ?? 0);
  const authorityDiff = (latest.authority ?? 0) - (oldest.authority ?? 0);

  return (
    <GlassCard>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold flex items-center gap-2">
          <Link2 className="h-5 w-5 text-accent-cyan" />
          被リンク推移
        </h3>
        <div className="flex gap-2">
          <button
            onClick={() => setMetric("ref_domains")}
            className={cn(
              "px-3 py-1 text-xs rounded-full border transition-colors",
              metric === "ref_domains"
                ? "bg-accent-cyan/20 border-accent-cyan text-accent-cyan"
                : "border-border-subtle text-text-muted hover:bg-bg-elevated"
            )}
          >
            参照ドメイン
          </button>
          <button
            onClick={() => setMetric("authority")}
            className={cn(
              "px-3 py-1 text-xs rounded-full border transition-colors",
              metric === "authority"
                ? "bg-accent-cyan/20 border-accent-cyan text-accent-cyan"
                : "border-border-subtle text-text-muted hover:bg-bg-elevated"
            )}
          >
            DA
          </button>
        </div>
      </div>

      {/* KPI Row */}
      <div className="grid grid-cols-4 gap-4 mb-4">
        <div className="p-3 bg-bg-surface rounded-lg">
          <div className="text-xs text-text-muted mb-1">参照ドメイン</div>
          <div className="flex items-center gap-2">
            <span className="text-xl font-semibold">{latest.ref_domains ?? "-"}</span>
            {refDomainsDiff !== 0 && (
              <span className={cn(
                "text-xs flex items-center",
                refDomainsDiff > 0 ? "text-green-400" : "text-red-400"
              )}>
                {refDomainsDiff > 0 ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
                {refDomainsDiff > 0 && "+"}{refDomainsDiff}
              </span>
            )}
          </div>
        </div>
        <div className="p-3 bg-bg-surface rounded-lg">
          <div className="text-xs text-text-muted mb-1">DA</div>
          <div className="flex items-center gap-2">
            <span className="text-xl font-semibold">{latest.authority ?? "-"}</span>
            {authorityDiff !== 0 && (
              <span className={cn(
                "text-xs flex items-center",
                authorityDiff > 0 ? "text-green-400" : "text-red-400"
              )}>
                {authorityDiff > 0 ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
                {authorityDiff > 0 && "+"}{authorityDiff}
              </span>
            )}
          </div>
        </div>
        <div className="p-3 bg-bg-surface rounded-lg">
          <div className="text-xs text-text-muted mb-1">総リンク数</div>
          <div className="text-xl font-semibold">{latest.backlinks_total?.toLocaleString() ?? "-"}</div>
        </div>
        <div className="p-3 bg-bg-surface rounded-lg">
          <div className="text-xs text-text-muted mb-1">dofollow率</div>
          <div className="text-xl font-semibold">
            {latest.dofollow_ratio ? (latest.dofollow_ratio * 100).toFixed(0) + "%" : "-"}
          </div>
        </div>
      </div>

      {/* Chart */}
      <div className="h-32 flex items-end gap-2">
        {data.map((point, i) => {
          const value = metric === "ref_domains" ? point.ref_domains : point.authority;
          const maxValue = Math.max(...data.map(d => (metric === "ref_domains" ? d.ref_domains : d.authority) || 0));
          const height = value && maxValue ? (value / maxValue) * 100 : 0;
          return (
            <div
              key={i}
              className="flex-1 bg-accent-cyan/60 rounded-t transition-all"
              style={{ height: `${Math.max(height, 5)}%` }}
              title={`${point.date}: ${value}`}
            />
          );
        })}
      </div>
      <p className="text-xs text-text-muted mt-2 text-center">
        {metric === "ref_domains" ? "参照ドメイン数" : "ドメインオーソリティ"}の推移
      </p>
    </GlassCard>
  );
}
```

---

## AF-6. ToDo連動（任意）

- ref_domains が長期で増えない → P2 外部露出計画
- 競合とのギャップが大 → P1 露出強化

source_checks=["backlinks"]

---

## AF-7. 受け入れ基準

- [ ] スナップショット保存（週次/月次）
- [ ] from/to で推移取得
- [ ] UIで推移が見える
- [ ] ref_domains / DA の切替表示ができる
- [ ] 増加が緑、減少が赤で表示される
- [ ] provider未設定時は skipped で落ちない

---

## AF-8. 将来拡張

- 競合との比較グラフ
- 新規獲得ドメイン一覧
- 失った被リンク検出
