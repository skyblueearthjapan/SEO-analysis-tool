"use client";

import { cn } from "@/lib/utils";
import type { JobStatus } from "@/lib/api/types";
import { Loader2, CheckCircle, XCircle, Clock } from "lucide-react";

interface JobStatusBadgeProps {
  status: JobStatus;
  size?: "sm" | "md" | "lg";
}

const STATUS_CONFIG: Record<
  JobStatus,
  { label: string; color: string; icon: React.ComponentType<any> }
> = {
  queued: {
    label: "待機中",
    color: "bg-yellow-500/20 text-yellow-400",
    icon: Clock,
  },
  running: {
    label: "実行中",
    color: "bg-accent-cyan/20 text-accent-cyan",
    icon: Loader2,
  },
  done: {
    label: "完了",
    color: "bg-green-500/20 text-green-400",
    icon: CheckCircle,
  },
  failed: {
    label: "失敗",
    color: "bg-red-500/20 text-red-400",
    icon: XCircle,
  },
};

export function JobStatusBadge({ status, size = "md" }: JobStatusBadgeProps) {
  const config = STATUS_CONFIG[status];
  const Icon = config.icon;

  const sizeClasses = {
    sm: "px-2 py-0.5 text-xs",
    md: "px-3 py-1 text-sm",
    lg: "px-4 py-1.5 text-base",
  };

  const iconSizes = {
    sm: "h-3 w-3",
    md: "h-4 w-4",
    lg: "h-5 w-5",
  };

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full font-medium",
        config.color,
        sizeClasses[size]
      )}
    >
      <Icon
        className={cn(iconSizes[size], status === "running" && "animate-spin")}
      />
      <span>{config.label}</span>
    </span>
  );
}
