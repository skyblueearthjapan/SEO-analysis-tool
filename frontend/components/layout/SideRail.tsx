"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Home, Globe, Play, BarChart3 } from "lucide-react";
import { cn } from "@/lib/utils";
import type { UUID } from "@/lib/api/types";

interface SideRailProps {
  siteId: UUID;
}

export function SideRail({ siteId }: SideRailProps) {
  const pathname = usePathname();

  const navItems = [
    {
      href: `/`,
      icon: Home,
      label: "Dashboard",
      active: pathname === "/",
    },
    {
      href: `/sites/${siteId}/pages`,
      icon: Globe,
      label: "URLs",
      active: pathname?.includes("/pages"),
    },
    {
      href: `/sites/${siteId}/run`,
      icon: Play,
      label: "Run",
      active: pathname?.includes("/run"),
    },
    {
      href: `/sites/${siteId}/results`,
      icon: BarChart3,
      label: "Results",
      active: pathname?.includes("/results"),
    },
  ];

  return (
    <aside className="fixed left-0 top-16 z-40 h-[calc(100vh-4rem)] w-[72px] border-r border-[rgba(148,163,184,0.15)] bg-bg-base/50 backdrop-blur-xl">
      <nav className="flex flex-col items-center gap-2 py-4">
        {navItems.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={cn(
              "flex h-12 w-12 items-center justify-center rounded-xl transition-all",
              item.active
                ? "bg-accent-cyan/20 text-accent-cyan shadow-glow-cyan"
                : "text-text-muted hover:bg-bg-elevated hover:text-text-primary"
            )}
            title={item.label}
          >
            <item.icon className="h-5 w-5" />
          </Link>
        ))}
      </nav>
    </aside>
  );
}
