"use client";

import * as React from "react";
import { useEffect, useState } from "react";
import { GlassCard } from "@/components/layout/GlassCard";
import { TrendingUp, TrendingDown, Minus, Calendar, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ProgressComparison } from "@/lib/api/types";
import { apiFetch, routes } from "@/lib/api/client";

interface MetricDisplayProps {
  label: string;
  baseline: number | string | null | undefined;
  current: number | string | null | undefined;
  diff: number | null | undefined;
  unit?: string;
  lowerIsBetter?: boolean;
}

function MetricDisplay({ label, baseline, current, diff, unit = "", lowerIsBetter = false }: MetricDisplayProps) {
  if (baseline === null || baseline === undefined || current === null || current === undefined) return null;

  const numDiff = diff ?? 0;
  const isImproved = lowerIsBetter ? numDiff < 0 : numDiff > 0;
  const isDeclined = lowerIsBetter ? numDiff > 0 : numDiff < 0;

  const formatValue = (v: number | string) => {
    if (typeof v === "number") {
      return v % 1 === 0 ? v : v.toFixed(1);
    }
    return v;
  };

  return (
    <div className="p-4 bg-bg-surface rounded-lg border border-border-subtle">
      <div className="text-xs text-text-muted mb-2">{label}</div>
      <div className="flex items-end justify-between">
        <div className="flex items-baseline gap-2">
          <span className="text-text-muted text-sm">{formatValue(baseline)}{unit}</span>
          <span className="text-text-muted">→</span>
          <span className="text-lg font-semibold text-text-primary">{formatValue(current)}{unit}</span>
        </div>
        {diff !== null && diff !== undefined && (
          <span className={cn(
            "flex items-center gap-1 text-sm font-medium px-2 py-0.5 rounded",
            isImproved && "text-green-400 bg-green-400/10",
            isDeclined && "text-red-400 bg-red-400/10",
            !isImproved && !isDeclined && "text-text-muted bg-bg-elevated"
          )}>
            {isImproved && <TrendingUp className="h-3 w-3" />}
            {isDeclined && <TrendingDown className="h-3 w-3" />}
            {!isImproved && !isDeclined && <Minus className="h-3 w-3" />}
            {diff > 0 && "+"}{typeof diff === "number" ? diff.toFixed(diff % 1 === 0 ? 0 : 1) : diff}{unit}
          </span>
        )}
      </div>
    </div>
  );
}

interface ProgressPanelProps {
  siteId: string;
}

export function ProgressPanel({ siteId }: ProgressPanelProps) {
  const [data, setData] = useState<ProgressComparison | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadProgress() {
      try {
        setLoading(true);
        setError(null);
        const res = await apiFetch<ProgressComparison>(`${routes.sites}/${siteId}/progress`);
        if (res.baseline && res.current) {
          setData(res);
        } else {
          setData(null);
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load progress data");
      } finally {
        setLoading(false);
      }
    }
    loadProgress();
  }, [siteId]);

  if (loading) {
    return (
      <GlassCard>
        <div className="flex items-center justify-center gap-2 text-text-muted py-8">
          <Loader2 className="h-4 w-4 animate-spin" />
          <span>読み込み中...</span>
        </div>
      </GlassCard>
    );
  }

  if (error) {
    return (
      <GlassCard>
        <div className="text-center py-8">
          <p className="text-red-400 mb-2">エラーが発生しました</p>
          <p className="text-xs text-text-muted">{error}</p>
        </div>
      </GlassCard>
    );
  }

  if (!data || !data.baseline || !data.current) {
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

  // Generate summary message
  const getSummaryMessage = () => {
    const psImproved = (diff?.pagespeed_score ?? 0) > 0;
    const intentImproved = (diff?.intent_missing ?? 0) < 0;

    if (psImproved && intentImproved) {
      return "ページの技術的評価とコンテンツの網羅性が改善されています。";
    }
    if (psImproved && !intentImproved) {
      return "PageSpeedが改善されました。コンテンツ面の改善も検討してください。";
    }
    if (!psImproved && intentImproved) {
      return "コンテンツの網羅性が改善されました。";
    }
    return "大きな変化は見られません。ToDoを確認してください。";
  };

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
          {getSummaryMessage()}
        </p>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-2 gap-3">
        <MetricDisplay
          label="PageSpeed スコア"
          baseline={baseline.metrics.pagespeed?.performance_score}
          current={current.metrics.pagespeed?.performance_score}
          diff={diff?.pagespeed_score}
        />
        <MetricDisplay
          label="意図欠損数"
          baseline={baseline.metrics.content?.intent_missing_count}
          current={current.metrics.content?.intent_missing_count}
          diff={diff?.intent_missing}
          lowerIsBetter
        />
        <MetricDisplay
          label="CTR"
          baseline={baseline.metrics.gsc?.ctr != null ? (baseline.metrics.gsc.ctr * 100) : null}
          current={current.metrics.gsc?.ctr != null ? (current.metrics.gsc.ctr * 100) : null}
          diff={diff?.ctr != null ? (diff.ctr * 100) : null}
          unit="%"
        />
        <MetricDisplay
          label="平均順位"
          baseline={baseline.metrics.gsc?.avg_position}
          current={current.metrics.gsc?.avg_position}
          diff={diff?.avg_position}
          lowerIsBetter
        />
      </div>
    </GlassCard>
  );
}
