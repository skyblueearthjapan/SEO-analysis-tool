"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { GlassCard } from "@/components/layout/GlassCard";
import { listPages, createAnalysisJob, getJob } from "@/lib/api/queries";
import type { Page, DeviceType, AnalysisJob } from "@/lib/api/types";
import { Play, Loader2, CheckCircle, XCircle } from "lucide-react";
import { cn } from "@/lib/utils";

export default function RunPage({
  params,
}: {
  params: { siteId: string };
}) {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [pages, setPages] = useState<Page[]>([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [currentJob, setCurrentJob] = useState<AnalysisJob | null>(null);

  // Config state
  const [device, setDevice] = useState<DeviceType>("mobile");
  const [enablePagespeed, setEnablePagespeed] = useState(true);
  const [enableGsc, setEnableGsc] = useState(false);
  const [enableAiReport, setEnableAiReport] = useState(true);
  const [brandTerms, setBrandTerms] = useState<string[]>([]);
  const [newBrandTerm, setNewBrandTerm] = useState("");

  // Selected pages from URL params
  const officialId = searchParams.get("official");
  const competitorIds = searchParams.get("competitors")?.split(",").filter(Boolean) || [];
  const thirdPartyIds = searchParams.get("thirdParty")?.split(",").filter(Boolean) || [];

  useEffect(() => {
    loadPages();
  }, [params.siteId]);

  async function loadPages() {
    try {
      const data = await listPages(params.siteId);
      setPages(data.items);
    } catch (error) {
      console.error("Failed to load pages:", error);
    } finally {
      setLoading(false);
    }
  }

  async function handleRunAnalysis() {
    if (!officialId) {
      alert("公式HPを選択してください");
      return;
    }

    setRunning(true);

    try {
      const targets = [
        { page_id: officialId, role: "official" as const, sort_order: 0 },
        ...competitorIds.map((id, i) => ({
          page_id: id,
          role: "competitor" as const,
          sort_order: i + 1,
        })),
        ...thirdPartyIds.map((id, i) => ({
          page_id: id,
          role: "third_party" as const,
          sort_order: competitorIds.length + i + 1,
        })),
      ];

      const result = await createAnalysisJob(params.siteId, {
        device,
        locale: "ja-JP",
        target_country: "JP",
        enable_pagespeed: enablePagespeed,
        enable_gsc: enableGsc,
        enable_ai_report: enableAiReport,
        brand_terms: brandTerms.length > 0 ? brandTerms : undefined,
        targets,
      });

      // Poll job status
      const jobId = result.job_id;
      const pollInterval = setInterval(async () => {
        try {
          const job = await getJob(params.siteId, jobId);
          setCurrentJob(job);

          if (job.status === "done") {
            clearInterval(pollInterval);
            // Navigate to results
            setTimeout(() => {
              router.push(`/sites/${params.siteId}/results`);
            }, 1000);
          } else if (job.status === "failed") {
            clearInterval(pollInterval);
            setRunning(false);
          }
        } catch (error) {
          console.error("Failed to poll job:", error);
        }
      }, 2000);
    } catch (error) {
      console.error("Failed to create job:", error);
      setRunning(false);
    }
  }

  function addBrandTerm() {
    if (newBrandTerm.trim() && !brandTerms.includes(newBrandTerm.trim())) {
      setBrandTerms([...brandTerms, newBrandTerm.trim()]);
      setNewBrandTerm("");
    }
  }

  function removeBrandTerm(term: string) {
    setBrandTerms(brandTerms.filter((t) => t !== term));
  }

  const selectedPages = pages.filter(
    (p) =>
      p.page_id === officialId ||
      competitorIds.includes(p.page_id) ||
      thirdPartyIds.includes(p.page_id)
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-text-muted">読み込み中...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">RUN CONFIG</h1>
        <p className="text-text-secondary text-sm">
          解析設定を確認して実行
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Config Card */}
        <GlassCard>
          <h2 className="text-lg font-semibold mb-4">解析設定</h2>

          <div className="space-y-6">
            {/* Device */}
            <div>
              <label className="block text-sm text-text-secondary mb-2">
                デバイス
              </label>
              <div className="flex gap-2">
                {(["mobile", "desktop"] as const).map((d) => (
                  <button
                    key={d}
                    onClick={() => setDevice(d)}
                    className={cn(
                      "px-4 py-2 rounded-lg text-sm font-medium transition-colors",
                      device === d
                        ? "bg-accent-cyan/20 text-accent-cyan border border-accent-cyan/30"
                        : "bg-bg-surface text-text-secondary border border-transparent hover:border-accent-cyan/20"
                    )}
                  >
                    {d === "mobile" ? "モバイル" : "デスクトップ"}
                  </button>
                ))}
              </div>
            </div>

            {/* Options */}
            <div className="space-y-3">
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={enablePagespeed}
                  onChange={(e) => setEnablePagespeed(e.target.checked)}
                  className="h-4 w-4"
                />
                <span className="text-sm">PageSpeed Insights</span>
              </label>
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={enableGsc}
                  onChange={(e) => setEnableGsc(e.target.checked)}
                  className="h-4 w-4"
                />
                <span className="text-sm">Search Console（要設定）</span>
              </label>
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={enableAiReport}
                  onChange={(e) => setEnableAiReport(e.target.checked)}
                  className="h-4 w-4"
                />
                <span className="text-sm">AIレポート生成</span>
              </label>
            </div>

            {/* Brand Terms */}
            <div>
              <label className="block text-sm text-text-secondary mb-2">
                ブランドキーワード
              </label>
              <div className="flex gap-2 mb-2">
                <input
                  type="text"
                  value={newBrandTerm}
                  onChange={(e) => setNewBrandTerm(e.target.value)}
                  onKeyPress={(e) => e.key === "Enter" && addBrandTerm()}
                  placeholder="例: 会社名"
                  className="input-base flex-1"
                />
                <button onClick={addBrandTerm} className="btn-secondary">
                  追加
                </button>
              </div>
              {brandTerms.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {brandTerms.map((term) => (
                    <span
                      key={term}
                      className="inline-flex items-center gap-1 px-2 py-1 rounded bg-bg-surface text-sm"
                    >
                      {term}
                      <button
                        onClick={() => removeBrandTerm(term)}
                        className="text-text-muted hover:text-accent-red"
                      >
                        ×
                      </button>
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        </GlassCard>

        {/* Target Summary */}
        <GlassCard>
          <h2 className="text-lg font-semibold mb-4">解析対象</h2>

          {selectedPages.length > 0 ? (
            <div className="space-y-3">
              {selectedPages.map((page) => (
                <div
                  key={page.page_id}
                  className="p-3 rounded-lg bg-bg-surface"
                >
                  <div className="flex items-center gap-2 mb-1">
                    <span
                      className={cn(
                        "text-xs px-2 py-0.5 rounded",
                        page.page_type === "official_homepage"
                          ? "bg-accent-cyan/20 text-accent-cyan"
                          : page.page_type === "competitor_page"
                          ? "bg-accent-violet/20 text-accent-violet"
                          : "bg-accent-amber/20 text-accent-amber"
                      )}
                    >
                      {page.page_type === "official_homepage"
                        ? "公式"
                        : page.page_type === "competitor_page"
                        ? "競合"
                        : "紹介"}
                    </span>
                    <span className="font-medium text-sm">
                      {page.label || "ラベルなし"}
                    </span>
                  </div>
                  <p className="text-xs text-text-muted truncate">
                    {page.url}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-text-muted text-sm">
              解析対象が選択されていません
            </p>
          )}
        </GlassCard>
      </div>

      {/* Run Button / Status */}
      <GlassCard>
        {currentJob ? (
          <div className="flex items-center justify-center gap-4 py-4">
            {currentJob.status === "queued" && (
              <>
                <Loader2 className="h-6 w-6 text-accent-cyan animate-spin" />
                <span>待機中...</span>
              </>
            )}
            {currentJob.status === "running" && (
              <>
                <Loader2 className="h-6 w-6 text-accent-cyan animate-spin" />
                <span>解析実行中...</span>
              </>
            )}
            {currentJob.status === "done" && (
              <>
                <CheckCircle className="h-6 w-6 text-accent-green" />
                <span>完了！結果ページに移動します...</span>
              </>
            )}
            {currentJob.status === "failed" && (
              <>
                <XCircle className="h-6 w-6 text-accent-red" />
                <span>エラーが発生しました: {currentJob.error_message}</span>
              </>
            )}
          </div>
        ) : (
          <button
            onClick={handleRunAnalysis}
            disabled={running || !officialId}
            className={cn(
              "w-full py-4 rounded-xl font-semibold text-lg flex items-center justify-center gap-3 transition-all",
              "bg-accent-cyan/20 text-accent-cyan border border-accent-cyan/30",
              "hover:bg-accent-cyan/30 hover:shadow-glow-cyan",
              (running || !officialId) && "opacity-50 cursor-not-allowed"
            )}
          >
            {running ? (
              <Loader2 className="h-6 w-6 animate-spin" />
            ) : (
              <Play className="h-6 w-6" />
            )}
            <span>RUN DIAGNOSTIC</span>
          </button>
        )}
      </GlassCard>
    </div>
  );
}
