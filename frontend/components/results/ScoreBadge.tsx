"use client";

import { cn, getScoreBadgeClass } from "@/lib/utils";
import type { ScoreGrade } from "@/lib/api/types";

interface ScoreBadgeProps {
  grade: ScoreGrade;
  label?: string;
  size?: "sm" | "md" | "lg";
  showLabel?: boolean;
}

const sizeStyles = {
  sm: "w-8 h-8 text-sm",
  md: "w-12 h-12 text-lg",
  lg: "w-16 h-16 text-2xl",
};

export function ScoreBadge({
  grade,
  label,
  size = "md",
  showLabel = false,
}: ScoreBadgeProps) {
  return (
    <div className="flex flex-col items-center gap-1">
      <div
        className={cn(
          "score-badge",
          getScoreBadgeClass(grade),
          sizeStyles[size]
        )}
      >
        {grade}
      </div>
      {showLabel && label && (
        <span className="text-xs text-text-muted">{label}</span>
      )}
    </div>
  );
}
