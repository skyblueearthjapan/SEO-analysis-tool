"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { GlassCard } from "@/components/layout/GlassCard";
import { ResultHeader } from "@/components/results/ResultHeader";
import { TodoBoard } from "@/components/results/TodoBoard";
import { ReportMarkdown } from "@/components/results/ReportMarkdown";
import { TodoDetailDrawer } from "@/components/todos/TodoDetailDrawer";
import { getResult, getReport } from "@/lib/api/queries";
import type { AnalysisResultDetail, AIReportItem, Todo } from "@/lib/api/types";
import { cn, getCauseBadgeClass, translateCause } from "@/lib/utils";
import {
  ChevronDown,
  ChevronRight,
  Download,
  FileJson,
  TrendingUp,
  TrendingDown,
  Minus,
  AlertTriangle,
  CheckCircle,
  XCircle,
} from "lucide-react";

export default function ResultDetailPage() {
  const params = useParams();
  const siteId = params.siteId as string;
  const resultId = params.resultId as string;

  const [result, setResult] = useState<AnalysisResultDetail | null>(null);
  const [report, setReport] = useState<AIReportItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"overview" | "todos" | "compare" | "report">("overview");
  const [expandedEvidence, setExpandedEvidence] = useState<string | null>(null);
  const [selectedTodo, setSelectedTodo] = useState<Todo | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);

  useEffect(() => {
    loadData();
  }, [siteId, resultId]);

  async function loadData() {
    try {
      const [resultData, reportData] = await Promise.all([
        getResult(siteId, resultId),
        getReport(siteId, resultId).catch(() => null),
      ]);
      setResult(resultData);
      setReport(reportData);
    } catch (error) {
      console.error("Failed to load result:", error);
    } finally {
      setLoading(false);
    }
  }

  function downloadJson() {
    if (!result) return;
    const blob = new Blob([JSON.stringify(result.analysis_json, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `analysis_${resultId}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  function handleSelectTodo(todo: Todo) {
    setSelectedTodo(todo);
    setDrawerOpen(true);
  }

  function handleCloseDrawer() {
    setDrawerOpen(false);
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-text-muted">読み込み中...</div>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-text-muted">結果が見つかりません</div>
      </div>
    );
  }

  const analysis = result.analysis_json;
  const diagnosis = analysis.diagnosis;
  const todos = analysis.todos || [];
  const comparisons = analysis.comparisons || {};
  const pages = analysis.pages || [];

  // Find official page
  const officialPage = pages.find((p: any) => p.page_type === "official_homepage");
  const competitorPages = pages.filter((p: any) => p.page_type === "competitor_page");

  return (
    <div className="space-y-6">
      {/* Header */}
      <ResultHeader
        result={result}
        diagnosis={diagnosis}
        onDownload={downloadJson}
      />

      {/* Tab Navigation */}
      <div className="flex gap-2 border-b border-border-subtle pb-2">
        {[
          { key: "overview", label: "概要" },
          { key: "todos", label: "ToDo" },
          { key: "compare", label: "競合比較" },
          { key: "report", label: "AIレポート" },
        ].map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key as any)}
            className={cn(
              "px-4 py-2 rounded-t-lg transition-colors",
              activeTab === tab.key
                ? "bg-bg-elevated text-text-primary border-b-2 border-accent-cyan"
                : "text-text-muted hover:text-text-secondary"
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === "overview" && (
        <div className="space-y-6">
          {/* Insight Summary */}
          <GlassCard>
            <h2 className="text-lg font-semibold mb-4">診断サマリー</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="p-4 bg-bg-surface rounded-lg">
                <div className="text-sm text-text-muted mb-1">主要因</div>
                <span className={cn("cause-badge", getCauseBadgeClass(diagnosis.main_cause))}>
                  {translateCause(diagnosis.main_cause)}
                </span>
              </div>
              <div className="p-4 bg-bg-surface rounded-lg">
                <div className="text-sm text-text-muted mb-1">総合スコア</div>
                <div className="text-2xl font-bold">
                  {diagnosis.overall_score?.toFixed(1) || "-"}
                </div>
              </div>
              <div className="p-4 bg-bg-surface rounded-lg">
                <div className="text-sm text-text-muted mb-1">グレード</div>
                <div className={cn(
                  "text-2xl font-bold",
                  diagnosis.grade === "A" && "text-green-400",
                  diagnosis.grade === "B" && "text-accent-cyan",
                  diagnosis.grade === "C" && "text-yellow-400",
                  diagnosis.grade === "D" && "text-red-400"
                )}>
                  {diagnosis.grade || "-"}
                </div>
              </div>
            </div>

            {/* Breakdown Scores */}
            <div className="mt-6">
              <h3 className="text-sm font-medium text-text-muted mb-3">スコア内訳</h3>
              <div className="grid grid-cols-3 gap-4">
                {Object.entries(diagnosis.scores || {}).map(([key, value]) => (
                  <div key={key} className="p-3 bg-bg-surface rounded-lg">
                    <div className="text-xs text-text-muted mb-1">
                      {key === "content" && "コンテンツ"}
                      {key === "technical" && "技術面"}
                      {key === "ctr" && "CTR"}
                    </div>
                    <div className={cn(
                      "text-lg font-semibold",
                      value === "A" && "text-green-400",
                      value === "B" && "text-accent-cyan",
                      value === "C" && "text-yellow-400",
                      value === "D" && "text-red-400"
                    )}>
                      {value || "-"}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </GlassCard>

          {/* Official Page Summary */}
          {officialPage && (
            <GlassCard>
              <h2 className="text-lg font-semibold mb-4">公式ページ分析</h2>
              <div className="space-y-4">
                <div className="p-4 bg-bg-surface rounded-lg">
                  <div className="text-sm text-text-muted mb-2">URL</div>
                  <a
                    href={officialPage.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-accent-cyan hover:underline break-all"
                  >
                    {officialPage.url}
                  </a>
                </div>

                {/* HTML Analysis */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="p-4 bg-bg-surface rounded-lg">
                    <div className="text-sm text-text-muted mb-2">タイトル</div>
                    <div className="font-medium">{officialPage.html?.title || "-"}</div>
                    <div className="text-xs text-text-muted mt-1">
                      {officialPage.html?.title?.length || 0} 文字
                    </div>
                  </div>
                  <div className="p-4 bg-bg-surface rounded-lg">
                    <div className="text-sm text-text-muted mb-2">メタディスクリプション</div>
                    <div className="text-sm">{officialPage.html?.meta_description || "-"}</div>
                    <div className="text-xs text-text-muted mt-1">
                      {officialPage.html?.meta_description?.length || 0} 文字
                    </div>
                  </div>
                </div>

                {/* Tech Stats */}
                {officialPage.tech?.pagespeed?.available && (
                  <div className="p-4 bg-bg-surface rounded-lg">
                    <div className="text-sm text-text-muted mb-3">PageSpeed Insights</div>
                    <div className="grid grid-cols-4 gap-4">
                      <div>
                        <div className="text-xs text-text-muted">Performance</div>
                        <div className="text-lg font-semibold">
                          {officialPage.tech.pagespeed.performance_score || "-"}
                        </div>
                      </div>
                      <div>
                        <div className="text-xs text-text-muted">LCP</div>
                        <div className="text-lg font-semibold">
                          {officialPage.tech.pagespeed.lcp_ms
                            ? `${(officialPage.tech.pagespeed.lcp_ms / 1000).toFixed(1)}s`
                            : "-"}
                        </div>
                      </div>
                      <div>
                        <div className="text-xs text-text-muted">INP</div>
                        <div className="text-lg font-semibold">
                          {officialPage.tech.pagespeed.inp_ms
                            ? `${officialPage.tech.pagespeed.inp_ms}ms`
                            : "-"}
                        </div>
                      </div>
                      <div>
                        <div className="text-xs text-text-muted">CLS</div>
                        <div className="text-lg font-semibold">
                          {officialPage.tech.pagespeed.cls?.toFixed(3) || "-"}
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* Intent Coverage */}
                {officialPage.content?.intent_coverage && (
                  <div className="p-4 bg-bg-surface rounded-lg">
                    <div className="text-sm text-text-muted mb-3">意図カバレッジ</div>
                    <div className="flex items-center gap-4">
                      <div className="text-2xl font-bold">
                        {(officialPage.content.intent_coverage * 100).toFixed(0)}%
                      </div>
                      {officialPage.content.missing_sections?.length > 0 && (
                        <div className="text-sm text-text-muted">
                          不足: {officialPage.content.missing_sections.join(", ")}
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </GlassCard>
          )}
        </div>
      )}

      {activeTab === "todos" && (
        <TodoBoard todos={todos} onSelectTodo={handleSelectTodo} />
      )}

      {activeTab === "compare" && (
        <div className="space-y-6">
          {/* Diff Summary */}
          {comparisons.diff_summary && (
            <GlassCard>
              <h2 className="text-lg font-semibold mb-4">競合との差分サマリー</h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <DiffCard
                  label="タイトル長"
                  value={comparisons.diff_summary.title_length_diff}
                  unit="文字"
                />
                <DiffCard
                  label="見出し数"
                  value={comparisons.diff_summary.heading_count_diff}
                  unit="個"
                />
                <DiffCard
                  label="本文量"
                  value={comparisons.diff_summary.word_count_diff}
                  unit="文字"
                />
              </div>
            </GlassCard>
          )}

          {/* Competitor Details */}
          {competitorPages.length > 0 && (
            <GlassCard>
              <h2 className="text-lg font-semibold mb-4">競合ページ詳細</h2>
              <div className="space-y-4">
                {competitorPages.map((comp: any, idx: number) => (
                  <div key={idx} className="p-4 bg-bg-surface rounded-lg">
                    <div className="flex items-start justify-between mb-3">
                      <div>
                        <div className="text-sm text-text-muted">競合 {idx + 1}</div>
                        <a
                          href={comp.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-accent-cyan hover:underline text-sm break-all"
                        >
                          {comp.url}
                        </a>
                      </div>
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                      <div>
                        <div className="text-text-muted">タイトル長</div>
                        <div>{comp.html?.title?.length || 0} 文字</div>
                      </div>
                      <div>
                        <div className="text-text-muted">H2数</div>
                        <div>{comp.html?.headings?.h2?.length || 0} 個</div>
                      </div>
                      <div>
                        <div className="text-text-muted">本文量</div>
                        <div>{comp.html?.text_stats?.word_count || 0} 文字</div>
                      </div>
                      <div>
                        <div className="text-text-muted">内部リンク</div>
                        <div>{comp.html?.links?.internal_count || 0} 件</div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </GlassCard>
          )}

          {/* Structure Comparison */}
          {comparisons.structure_comparison && (
            <GlassCard>
              <h2 className="text-lg font-semibold mb-4">構造比較</h2>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border-subtle">
                      <th className="text-left py-2 px-3">項目</th>
                      <th className="text-right py-2 px-3">公式</th>
                      <th className="text-right py-2 px-3">競合平均</th>
                      <th className="text-right py-2 px-3">差分</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(comparisons.structure_comparison).map(([key, data]: [string, any]) => (
                      <tr key={key} className="border-b border-border-subtle/50">
                        <td className="py-2 px-3 text-text-muted">{key}</td>
                        <td className="text-right py-2 px-3">{data.official ?? "-"}</td>
                        <td className="text-right py-2 px-3">{data.competitor_avg?.toFixed(1) ?? "-"}</td>
                        <td className="text-right py-2 px-3">
                          <DiffIndicator value={data.diff} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </GlassCard>
          )}
        </div>
      )}

      {activeTab === "report" && (
        <GlassCard>
          {report ? (
            <ReportMarkdown markdown={report.report_markdown} />
          ) : (
            <div className="text-center py-12">
              <div className="text-text-muted">AIレポートがありません</div>
            </div>
          )}
        </GlassCard>
      )}

      {/* JSON Download FAB */}
      <button
        onClick={downloadJson}
        className="fixed bottom-6 right-6 p-4 bg-accent-cyan text-bg-base rounded-full shadow-lg hover:bg-accent-cyan/80 transition-colors"
        title="JSONダウンロード"
      >
        <FileJson className="h-6 w-6" />
      </button>

      {/* Todo Detail Drawer */}
      <TodoDetailDrawer
        todo={selectedTodo}
        open={drawerOpen}
        onClose={handleCloseDrawer}
        allTodos={todos}
        onSelectTodo={handleSelectTodo}
      />
    </div>
  );
}

function DiffCard({
  label,
  value,
  unit,
}: {
  label: string;
  value?: number;
  unit: string;
}) {
  if (value === undefined || value === null) {
    return (
      <div className="p-4 bg-bg-surface rounded-lg">
        <div className="text-sm text-text-muted mb-1">{label}</div>
        <div className="text-lg font-semibold text-text-muted">-</div>
      </div>
    );
  }

  const isPositive = value > 0;
  const isNegative = value < 0;

  return (
    <div className="p-4 bg-bg-surface rounded-lg">
      <div className="text-sm text-text-muted mb-1">{label}</div>
      <div className="flex items-center gap-2">
        {isPositive && <TrendingUp className="h-5 w-5 text-green-400" />}
        {isNegative && <TrendingDown className="h-5 w-5 text-red-400" />}
        {!isPositive && !isNegative && <Minus className="h-5 w-5 text-text-muted" />}
        <span
          className={cn(
            "text-lg font-semibold",
            isPositive && "text-green-400",
            isNegative && "text-red-400"
          )}
        >
          {isPositive && "+"}
          {value} {unit}
        </span>
      </div>
    </div>
  );
}

function DiffIndicator({ value }: { value?: number }) {
  if (value === undefined || value === null) {
    return <span className="text-text-muted">-</span>;
  }

  const isPositive = value > 0;
  const isNegative = value < 0;

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1",
        isPositive && "text-green-400",
        isNegative && "text-red-400",
        !isPositive && !isNegative && "text-text-muted"
      )}
    >
      {isPositive && <TrendingUp className="h-4 w-4" />}
      {isNegative && <TrendingDown className="h-4 w-4" />}
      {isPositive && "+"}
      {value}
    </span>
  );
}
