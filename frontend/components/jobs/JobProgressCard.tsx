"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { GlassCard } from "@/components/layout/GlassCard";
import { JobStatusBadge } from "./JobStatusBadge";
import { getJob } from "@/lib/api/queries";
import type { JobDetail } from "@/lib/api/types";
import { formatDate } from "@/lib/utils";
import { ArrowRight, RefreshCw } from "lucide-react";

interface JobProgressCardProps {
  siteId: string;
  jobId: string;
  onComplete?: (resultId: string) => void;
}

export function JobProgressCard({
  siteId,
  jobId,
  onComplete,
}: JobProgressCardProps) {
  const router = useRouter();
  const [job, setJob] = useState<JobDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [polling, setPolling] = useState(true);

  useEffect(() => {
    loadJob();
  }, [jobId]);

  useEffect(() => {
    if (!polling) return;

    const interval = setInterval(async () => {
      try {
        const data = await getJob(siteId, jobId);
        setJob(data);

        if (data.status === "done" || data.status === "failed") {
          setPolling(false);
          if (data.status === "done" && onComplete) {
            // Get result ID from the completed job
            // Note: In real implementation, this would come from the API
            onComplete(jobId);
          }
        }
      } catch (error) {
        console.error("Failed to poll job:", error);
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [jobId, polling]);

  async function loadJob() {
    try {
      const data = await getJob(siteId, jobId);
      setJob(data);
      if (data.status === "done" || data.status === "failed") {
        setPolling(false);
      }
    } catch (error) {
      console.error("Failed to load job:", error);
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <GlassCard>
        <div className="flex items-center justify-center py-8">
          <RefreshCw className="h-6 w-6 text-accent-cyan animate-spin" />
        </div>
      </GlassCard>
    );
  }

  if (!job) {
    return (
      <GlassCard>
        <div className="text-center py-8 text-text-muted">
          ジョブが見つかりません
        </div>
      </GlassCard>
    );
  }

  return (
    <GlassCard>
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold">解析ジョブ</h3>
        <JobStatusBadge status={job.status} />
      </div>

      <div className="space-y-3 text-sm">
        <div className="flex justify-between">
          <span className="text-text-muted">作成日時</span>
          <span>{formatDate(job.created_at)}</span>
        </div>
        {job.started_at && (
          <div className="flex justify-between">
            <span className="text-text-muted">開始日時</span>
            <span>{formatDate(job.started_at)}</span>
          </div>
        )}
        {job.finished_at && (
          <div className="flex justify-between">
            <span className="text-text-muted">完了日時</span>
            <span>{formatDate(job.finished_at)}</span>
          </div>
        )}
        <div className="flex justify-between">
          <span className="text-text-muted">デバイス</span>
          <span>{job.device === "mobile" ? "モバイル" : "デスクトップ"}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-text-muted">対象ページ数</span>
          <span>{job.targets?.length || 0}</span>
        </div>
      </div>

      {job.status === "failed" && job.error_message && (
        <div className="mt-4 p-3 bg-red-500/10 border border-red-500/30 rounded-lg">
          <div className="text-sm text-red-400">{job.error_message}</div>
        </div>
      )}

      {job.status === "done" && (
        <button
          onClick={() => router.push(`/sites/${siteId}/results`)}
          className="mt-4 w-full btn-primary flex items-center justify-center gap-2"
        >
          <span>結果を見る</span>
          <ArrowRight className="h-4 w-4" />
        </button>
      )}

      {(job.status === "queued" || job.status === "running") && (
        <div className="mt-4">
          <div className="h-2 bg-bg-surface rounded-full overflow-hidden">
            <div
              className="h-full bg-accent-cyan rounded-full animate-pulse"
              style={{
                width: job.status === "running" ? "60%" : "20%",
              }}
            />
          </div>
          <div className="text-xs text-text-muted mt-2 text-center">
            {job.status === "queued"
              ? "解析を待機しています..."
              : "解析を実行中です..."}
          </div>
        </div>
      )}
    </GlassCard>
  );
}
