"use client";

import {
  cn,
  formatDate,
  getCauseBadgeClass,
  translateCause,
} from "@/lib/utils";
import type { AnalysisResultDetail, MainCause, ScoreGrade } from "@/lib/api/types";
import { ScoreBadge } from "./ScoreBadge";
import { Download, Calendar } from "lucide-react";

interface ResultHeaderProps {
  result: AnalysisResultDetail;
  diagnosis: any;
  onDownload: () => void;
}

export function ResultHeader({
  result,
  diagnosis,
  onDownload,
}: ResultHeaderProps) {
  const mainCause = diagnosis?.main_cause || "unknown";
  const grade = diagnosis?.grade || "-";
  const overallScore = diagnosis?.overall_score;

  return (
    <div className="glass-card p-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-2">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold">解析結果</h1>
            <span className={cn("cause-badge", getCauseBadgeClass(mainCause))}>
              {translateCause(mainCause)}
            </span>
          </div>
          <div className="flex items-center gap-2 text-text-secondary text-sm">
            <Calendar className="h-4 w-4" />
            <span>{formatDate(result.generated_at)}</span>
          </div>
        </div>

        <div className="flex items-center gap-6">
          {/* Overall Grade */}
          <div className="flex items-center gap-4">
            <div className="text-center">
              <div className="text-xs text-text-muted mb-1">総合グレード</div>
              <div className={cn(
                "text-3xl font-bold",
                grade === "A" && "text-green-400",
                grade === "B" && "text-accent-cyan",
                grade === "C" && "text-yellow-400",
                grade === "D" && "text-red-400"
              )}>
                {grade}
              </div>
            </div>
            {overallScore !== undefined && (
              <div className="text-center">
                <div className="text-xs text-text-muted mb-1">スコア</div>
                <div className="text-2xl font-semibold">
                  {overallScore.toFixed(1)}
                </div>
              </div>
            )}
          </div>

          {/* Download Button */}
          <button
            onClick={onDownload}
            className="btn-primary flex items-center gap-2"
          >
            <Download className="h-4 w-4" />
            <span>JSON</span>
          </button>
        </div>
      </div>
    </div>
  );
}
