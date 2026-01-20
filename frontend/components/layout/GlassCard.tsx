"use client";

import { cn } from "@/lib/utils";
import { ReactNode } from "react";

interface GlassCardProps {
  children: ReactNode;
  className?: string;
  hover?: boolean;
  glow?: "cyan" | "violet" | "none";
}

export function GlassCard({
  children,
  className,
  hover = true,
  glow = "cyan",
}: GlassCardProps) {
  return (
    <div
      className={cn(
        "rounded-2xl p-6",
        "bg-[rgba(26,39,68,0.6)]",
        "border border-[rgba(53,212,255,0.2)]",
        "backdrop-blur-xl",
        hover && "transition-all duration-300",
        hover && "hover:border-cyan-400/40 hover:shadow-[0_0_30px_rgba(53,212,255,0.2)]",
        glow === "cyan" && "shadow-glow-cyan",
        glow === "violet" && "shadow-glow-violet",
        className
      )}
    >
      {children}
    </div>
  );
}
