"use client";

import Link from "next/link";
import { Activity } from "lucide-react";

interface TopNavProps {
  title?: string;
  rightSlot?: React.ReactNode;
}

export function TopNav({ title, rightSlot }: TopNavProps) {
  return (
    <header className="sticky top-0 z-50 w-full border-b border-[rgba(148,163,184,0.15)] bg-bg-base/80 backdrop-blur-xl">
      <div className="container flex h-16 items-center justify-between px-6">
        <div className="flex items-center gap-4">
          <Link href="/" className="flex items-center gap-2">
            <Activity className="h-6 w-6 text-accent-cyan" />
            <span className="text-lg font-bold tracking-tight">
              SEO<span className="text-accent-cyan">Diagnostic</span>
            </span>
          </Link>
          {title && (
            <>
              <span className="text-text-muted">/</span>
              <span className="text-text-secondary">{title}</span>
            </>
          )}
        </div>
        <div className="flex items-center gap-4">
          {rightSlot}
        </div>
      </div>
    </header>
  );
}
