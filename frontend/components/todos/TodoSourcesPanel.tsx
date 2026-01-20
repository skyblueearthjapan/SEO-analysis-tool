"use client";

import * as React from "react";
import type { AnalysisChecks, AnalysisCheckCode, AnalysisCheckStatus } from "@/lib/api/types";
import { cn } from "@/lib/utils";

const mapLabel: Record<AnalysisCheckCode, string> = {
  fetch: "HTTP取得",
  html_basic: "メタ要素",
  headings: "見出し",
  text_stats: "テキスト量",
  links: "リンク",
  images_alt: "画像alt",
  structured_data: "構造化データ",
  pagespeed: "PageSpeed",
  search_console: "GSC",
  intent_coverage: "意図カバー",
  competitor_diff: "競合差分",
  backlinks: "被リンク",
  serp_rank: "順位計測",
  keyword_research: "KW調査",
  site_crawl: "全体クロール",
  log_analysis: "ログ解析",
  duplicate_cannibalization: "重複/カニバリ",
};

const statusColor: Record<AnalysisCheckStatus, string> = {
  done: "text-accent-cyan border-accent-cyan/30 bg-accent-cyan/10",
  partial: "text-amber-400 border-amber-400/30 bg-amber-400/10",
  skipped: "text-text-muted border-border-subtle bg-bg-surface",
  not_supported: "text-violet-400 border-violet-400/30 bg-violet-400/10",
};

interface TodoSourcesPanelProps {
  sourceChecks?: AnalysisCheckCode[];
  analysisChecks?: AnalysisChecks | null;
}

export function TodoSourcesPanel({
  sourceChecks,
  analysisChecks,
}: TodoSourcesPanelProps) {
  if (!sourceChecks?.length) return null;

  return (
    <div className="mt-3">
      <div className="text-xs font-medium text-text-muted mb-2">この指摘の根拠となった解析</div>
      <div className="flex flex-wrap gap-2">
        {sourceChecks.map((c) => {
          const st = analysisChecks?.checks?.[c]?.status ?? "not_supported";
          return (
            <span
              key={c}
              className={cn(
                "text-[11px] font-medium px-2 py-1 rounded-full border",
                statusColor[st]
              )}
              title={analysisChecks?.checks?.[c]?.notes?.join(" / ") || ""}
            >
              {mapLabel[c]}
            </span>
          );
        })}
      </div>
    </div>
  );
}
