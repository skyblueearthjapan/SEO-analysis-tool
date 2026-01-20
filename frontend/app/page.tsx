"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { GlassCard } from "@/components/layout/GlassCard";
import { listSites, createSite, listResults } from "@/lib/api/queries";
import type { Site, AnalysisResultListItem } from "@/lib/api/types";
import { formatDate, getCauseBadgeClass, translateCause, cn } from "@/lib/utils";
import { Plus, Play, BarChart3, Globe, ArrowRight } from "lucide-react";

export default function DashboardPage() {
  const [sites, setSites] = useState<Site[]>([]);
  const [results, setResults] = useState<AnalysisResultListItem[]>([]);
  const [selectedSite, setSelectedSite] = useState<Site | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [newSiteName, setNewSiteName] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadSites();
  }, []);

  useEffect(() => {
    if (selectedSite) {
      loadResults(selectedSite.site_id);
    }
  }, [selectedSite]);

  async function loadSites() {
    try {
      const data = await listSites();
      setSites(data.items);
      if (data.items.length > 0) {
        setSelectedSite(data.items[0]);
      }
    } catch (error) {
      console.error("Failed to load sites:", error);
    } finally {
      setLoading(false);
    }
  }

  async function loadResults(siteId: string) {
    try {
      const data = await listResults(siteId, 10);
      setResults(data.items);
    } catch (error) {
      console.error("Failed to load results:", error);
    }
  }

  async function handleCreateSite() {
    if (!newSiteName.trim()) return;
    try {
      const site = await createSite({ name: newSiteName });
      setSites([site, ...sites]);
      setSelectedSite(site);
      setNewSiteName("");
      setIsCreating(false);
    } catch (error) {
      console.error("Failed to create site:", error);
    }
  }

  if (loading) {
    return (
      <div className="container px-6 py-12">
        <div className="flex items-center justify-center h-64">
          <div className="text-text-muted">読み込み中...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="container px-6 py-12">
      {/* Hero Section */}
      <div className="mb-12">
        <h1 className="text-4xl font-bold mb-4">
          SEO <span className="text-accent-cyan">DIAGNOSTIC</span>
        </h1>
        <p className="text-text-secondary text-lg max-w-2xl">
          公式HP + 競合2URLの差分から、次の一手を提示。
          改善ToDoを優先度付きで自動生成します。
        </p>
      </div>

      {/* Site Selector */}
      <div className="flex items-center gap-4 mb-8">
        <select
          value={selectedSite?.site_id || ""}
          onChange={(e) => {
            const site = sites.find((s) => s.site_id === e.target.value);
            if (site) setSelectedSite(site);
          }}
          className="input-base max-w-xs"
        >
          {sites.map((site) => (
            <option key={site.site_id} value={site.site_id}>
              {site.name}
            </option>
          ))}
        </select>
        <button
          onClick={() => setIsCreating(true)}
          className="btn-secondary flex items-center gap-2"
        >
          <Plus className="h-4 w-4" />
          <span>新規プロジェクト</span>
        </button>
      </div>

      {/* Create Site Modal */}
      {isCreating && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <GlassCard className="w-full max-w-md">
            <h2 className="text-xl font-semibold mb-4">新規プロジェクト作成</h2>
            <input
              type="text"
              value={newSiteName}
              onChange={(e) => setNewSiteName(e.target.value)}
              placeholder="プロジェクト名"
              className="input-base mb-4"
              autoFocus
            />
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setIsCreating(false)}
                className="btn-secondary"
              >
                キャンセル
              </button>
              <button onClick={handleCreateSite} className="btn-primary">
                作成
              </button>
            </div>
          </GlassCard>
        </div>
      )}

      {selectedSite && (
        <div className="grid gap-6 lg:grid-cols-3">
          {/* Quick Actions */}
          <GlassCard className="lg:col-span-2">
            <h2 className="text-lg font-semibold mb-4">クイックアクション</h2>
            <div className="grid gap-4 sm:grid-cols-3">
              <Link
                href={`/sites/${selectedSite.site_id}/pages`}
                className="flex flex-col items-center gap-3 p-4 rounded-xl bg-bg-surface hover:bg-bg-elevated transition-colors"
              >
                <Globe className="h-8 w-8 text-accent-cyan" />
                <span className="font-medium">URL管理</span>
              </Link>
              <Link
                href={`/sites/${selectedSite.site_id}/run`}
                className="flex flex-col items-center gap-3 p-4 rounded-xl bg-bg-surface hover:bg-bg-elevated transition-colors"
              >
                <Play className="h-8 w-8 text-accent-green" />
                <span className="font-medium">解析実行</span>
              </Link>
              <Link
                href={`/sites/${selectedSite.site_id}/results`}
                className="flex flex-col items-center gap-3 p-4 rounded-xl bg-bg-surface hover:bg-bg-elevated transition-colors"
              >
                <BarChart3 className="h-8 w-8 text-accent-violet" />
                <span className="font-medium">結果一覧</span>
              </Link>
            </div>
          </GlassCard>

          {/* Latest Result */}
          <GlassCard>
            <h2 className="text-lg font-semibold mb-4">最新の解析結果</h2>
            {results.length > 0 ? (
              <Link
                href={`/sites/${selectedSite.site_id}/results/${results[0].result_id}`}
                className="block p-4 rounded-xl bg-bg-surface hover:bg-bg-elevated transition-colors"
              >
                <div className="flex items-center justify-between mb-2">
                  <span
                    className={cn(
                      "cause-badge text-xs",
                      getCauseBadgeClass(results[0].diagnosis_main_cause || "unknown")
                    )}
                  >
                    {translateCause(results[0].diagnosis_main_cause || "unknown")}
                  </span>
                  <ArrowRight className="h-4 w-4 text-text-muted" />
                </div>
                <p className="text-sm text-text-secondary">
                  {formatDate(results[0].generated_at)}
                </p>
              </Link>
            ) : (
              <p className="text-text-muted text-sm">
                まだ解析結果がありません
              </p>
            )}
          </GlassCard>

          {/* Recent Results */}
          <GlassCard className="lg:col-span-3">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">解析履歴</h2>
              <Link
                href={`/sites/${selectedSite.site_id}/results`}
                className="text-sm text-accent-cyan hover:underline"
              >
                すべて見る
              </Link>
            </div>
            {results.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="text-left text-text-muted text-sm border-b border-[rgba(148,163,184,0.15)]">
                      <th className="pb-2 font-medium">日時</th>
                      <th className="pb-2 font-medium">主因</th>
                      <th className="pb-2 font-medium">アクション</th>
                    </tr>
                  </thead>
                  <tbody>
                    {results.slice(0, 5).map((result) => (
                      <tr
                        key={result.result_id}
                        className="border-b border-[rgba(148,163,184,0.1)]"
                      >
                        <td className="py-3 text-text-secondary">
                          {formatDate(result.generated_at)}
                        </td>
                        <td className="py-3">
                          <span
                            className={cn(
                              "cause-badge text-xs",
                              getCauseBadgeClass(
                                result.diagnosis_main_cause || "unknown"
                              )
                            )}
                          >
                            {translateCause(
                              result.diagnosis_main_cause || "unknown"
                            )}
                          </span>
                        </td>
                        <td className="py-3">
                          <Link
                            href={`/sites/${selectedSite.site_id}/results/${result.result_id}`}
                            className="text-accent-cyan hover:underline text-sm"
                          >
                            詳細を見る
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-text-muted text-sm text-center py-8">
                解析履歴がありません。URLを登録して解析を実行してください。
              </p>
            )}
          </GlassCard>
        </div>
      )}

      {sites.length === 0 && (
        <GlassCard className="text-center py-12">
          <h2 className="text-xl font-semibold mb-4">
            はじめに、プロジェクトを作成しましょう
          </h2>
          <p className="text-text-secondary mb-6">
            プロジェクトを作成して、解析対象のURLを登録します。
          </p>
          <button
            onClick={() => setIsCreating(true)}
            className="btn-primary inline-flex items-center gap-2"
          >
            <Plus className="h-4 w-4" />
            <span>プロジェクトを作成</span>
          </button>
        </GlassCard>
      )}
    </div>
  );
}
