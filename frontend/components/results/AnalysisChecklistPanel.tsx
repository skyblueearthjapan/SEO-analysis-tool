"use client";

import * as React from "react";
import type { AnalysisChecks, AnalysisCheckCode, AnalysisCheckStatus } from "@/lib/api/types";
import { GlassCard } from "@/components/layout/GlassCard";
import { cn } from "@/lib/utils";
import { Check, Minus, AlertTriangle, Clock, Info } from "lucide-react";

const statusIcon = (st: AnalysisCheckStatus) => {
  if (st === "done") return <Check className="h-4 w-4 text-accent-cyan" />;
  if (st === "partial") return <AlertTriangle className="h-4 w-4 text-amber-400" />;
  if (st === "skipped") return <Minus className="h-4 w-4 text-text-muted" />;
  return <Clock className="h-4 w-4 text-violet-400" />; // not_supported/planned
};

const statusLabel: Record<AnalysisCheckStatus, string> = {
  done: "実行済み",
  partial: "一部実行",
  skipped: "スキップ",
  not_supported: "拡張予定",
};

const statusColor: Record<AnalysisCheckStatus, string> = {
  done: "text-accent-cyan border-accent-cyan/30 bg-accent-cyan/10",
  partial: "text-amber-400 border-amber-400/30 bg-amber-400/10",
  skipped: "text-text-muted border-border-subtle bg-bg-surface",
  not_supported: "text-violet-400 border-violet-400/30 bg-violet-400/10",
};

interface CheckItemConfig {
  code: AnalysisCheckCode;
  label: string;
  desc: string;
}

interface CheckGroup {
  title: string;
  items: CheckItemConfig[];
}

const groups: CheckGroup[] = [
  {
    title: "基本取得 / HTML",
    items: [
      { code: "fetch", label: "HTTP取得・ステータス確認", desc: "status/final_url/redirect/主要ヘッダー" },
      { code: "html_basic", label: "title / meta / canonical / robots", desc: "基本メタ要素の抽出" },
      { code: "headings", label: "見出し構造（h1/h2/h3）", desc: "見出し一覧と構造差分に利用" },
      { code: "text_stats", label: "テキスト量", desc: "文字数などの簡易指標" },
      { code: "links", label: "リンク集計", desc: "内部/外部リンク数の集計" },
      { code: "images_alt", label: "画像 alt", desc: "alt付与率の算出" },
      { code: "structured_data", label: "構造化データ（JSON-LD）", desc: "FAQ/Organization/Article 等" },
    ],
  },
  {
    title: "テクニカル",
    items: [
      { code: "pagespeed", label: "PageSpeed / Core Web Vitals", desc: "PSスコア, LCP, INP, CLS" },
    ],
  },
  {
    title: "検索パフォーマンス",
    items: [
      { code: "search_console", label: "Search Console", desc: "Clicks/Impr/CTR/Pos（連携時）" },
    ],
  },
  {
    title: "品質・比較",
    items: [
      { code: "intent_coverage", label: "意図カバー率", desc: "公式/紹介ページの必須項目カバー" },
      { code: "competitor_diff", label: "競合差分", desc: "構造/意図/テクニカルの差分" },
    ],
  },
  {
    title: "拡張（予定）",
    items: [
      { code: "backlinks", label: "被リンク分析", desc: "外部API連携（Ahrefs等）" },
      { code: "serp_rank", label: "SERP順位計測", desc: "定点観測/外部SERP API" },
      { code: "keyword_research", label: "キーワード大量調査", desc: "サジェスト/関連検索など" },
      { code: "site_crawl", label: "サイト全体クロール", desc: "内部リンクグラフ/Orphan検出" },
      { code: "log_analysis", label: "ログ解析", desc: "bot到達/クロール頻度（上級）" },
      { code: "duplicate_cannibalization", label: "重複・カニバリ", desc: "類似度/同一クエリ競合" },
    ],
  },
];

interface AnalysisChecklistPanelProps {
  analysisChecks?: AnalysisChecks | null;
}

export function AnalysisChecklistPanel({ analysisChecks }: AnalysisChecklistPanelProps) {
  return (
    <GlassCard>
      <div className="flex items-start justify-between gap-3 mb-4">
        <div>
          <h3 className="text-sm font-semibold">解析チェックリスト</h3>
          <p className="mt-1 text-xs text-text-muted">
            このRunで実行した解析内容
          </p>
        </div>
        <div className="flex items-center gap-1 text-xs text-text-muted">
          <Info className="h-3 w-3" />
          <span>Hoverで詳細</span>
        </div>
      </div>

      <div className="space-y-4">
        {groups.map((g) => (
          <div key={g.title}>
            <div className="text-xs font-medium text-text-muted mb-2">{g.title}</div>
            <div className="space-y-1.5">
              {g.items.map((it) => {
                const item = analysisChecks?.checks?.[it.code];
                const st: AnalysisCheckStatus = item?.status ?? "not_supported";
                const notes = item?.notes ?? (st === "not_supported" ? ["planned"] : []);
                return (
                  <div
                    key={it.code}
                    className="group flex items-center justify-between gap-3 rounded-lg border border-border-subtle bg-bg-surface px-3 py-2 hover:bg-bg-elevated transition-colors"
                    title={[it.desc, ...notes].join(" / ")}
                  >
                    <div className="flex items-center gap-3">
                      <div className="flex-shrink-0">
                        {statusIcon(st)}
                      </div>
                      <div>
                        <div className="text-xs font-medium text-text-primary">{it.label}</div>
                        <div className="text-[11px] text-text-muted opacity-0 group-hover:opacity-100 transition-opacity">
                          {it.desc}
                        </div>
                      </div>
                    </div>

                    <span className={cn(
                      "text-[10px] font-medium px-2 py-0.5 rounded-full border",
                      statusColor[st]
                    )}>
                      {statusLabel[st]}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </GlassCard>
  );
}
