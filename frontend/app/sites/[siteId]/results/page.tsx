"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { GlassCard } from "@/components/layout/GlassCard";
import { listResults } from "@/lib/api/queries";
import type { AnalysisResultListItem } from "@/lib/api/types";
import { formatDate, getCauseBadgeClass, translateCause, cn } from "@/lib/utils";
import { BarChart3, ArrowRight } from "lucide-react";

export default function ResultsPage({
  params,
}: {
  params: { siteId: string };
}) {
  const [results, setResults] = useState<AnalysisResultListItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadResults();
  }, [params.siteId]);

  async function loadResults() {
    try {
      const data = await listResults(params.siteId, 50);
      setResults(data.items);
    } catch (error) {
      console.error("Failed to load results:", error);
    } finally {
      setLoading(false);
    }
  }

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
        <h1 className="text-2xl font-bold">RESULTS</h1>
        <p className="text-text-secondary text-sm">
          解析結果の履歴
        </p>
      </div>

      <GlassCard>
        {results.length > 0 ? (
          <div className="space-y-2">
            {results.map((result) => (
              <Link
                key={result.result_id}
                href={`/sites/${params.siteId}/results/${result.result_id}`}
                className="flex items-center justify-between p-4 rounded-lg bg-bg-surface hover:bg-bg-elevated transition-colors"
              >
                <div className="flex items-center gap-4">
                  <BarChart3 className="h-8 w-8 text-accent-cyan" />
                  <div>
                    <div className="font-medium">
                      {formatDate(result.generated_at)}
                    </div>
                    <span
                      className={cn(
                        "cause-badge text-xs mt-1",
                        getCauseBadgeClass(
                          result.diagnosis_main_cause || "unknown"
                        )
                      )}
                    >
                      {translateCause(result.diagnosis_main_cause || "unknown")}
                    </span>
                  </div>
                </div>
                <ArrowRight className="h-5 w-5 text-text-muted" />
              </Link>
            ))}
          </div>
        ) : (
          <div className="text-center py-12">
            <BarChart3 className="h-12 w-12 text-text-muted mx-auto mb-4" />
            <p className="text-text-muted">
              まだ解析結果がありません
            </p>
            <Link
              href={`/sites/${params.siteId}/pages`}
              className="btn-primary inline-flex mt-4"
            >
              URL管理へ
            </Link>
          </div>
        )}
      </GlassCard>
    </div>
  );
}
