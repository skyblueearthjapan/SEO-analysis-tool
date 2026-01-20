"use client";

import * as React from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Legend,
} from "recharts";
import { GlassCard } from "@/components/layout/GlassCard";
import { Link2, Info } from "lucide-react";

interface BacklinkDataPoint {
  date: string;
  referring_domains?: number | null;
  backlinks_count?: number | null;
  total_backlinks?: number | null;
}

interface BacklinkTrendChartProps {
  data: BacklinkDataPoint[];
  title?: string;
}

export function BacklinkTrendChart({
  data,
  title = "被リンクの推移",
}: BacklinkTrendChartProps) {
  // Normalize data - handle both total_backlinks and backlinks_count
  const chartData = data.map((d) => ({
    date: d.date,
    referring_domains: d.referring_domains ?? null,
    backlinks_count: d.backlinks_count ?? d.total_backlinks ?? null,
  }));

  const validData = chartData.filter(
    (d) => d.referring_domains !== null || d.backlinks_count !== null
  );

  if (validData.length < 2) {
    return (
      <GlassCard>
        <div className="flex items-center gap-2 mb-4">
          <Link2 className="h-5 w-5 text-violet-400" />
          <h3 className="text-sm font-semibold">{title}</h3>
        </div>
        <div className="text-center py-8 text-text-muted">
          <p>データが不足しています</p>
          <p className="text-xs mt-2">被リンクデータは外部API連携で取得されます</p>
        </div>
      </GlassCard>
    );
  }

  return (
    <GlassCard>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Link2 className="h-5 w-5 text-violet-400" />
          <h3 className="text-sm font-semibold">{title}</h3>
        </div>
        <div className="flex items-center gap-1 text-xs text-text-muted">
          <Info className="h-3 w-3" />
          <span>多いほど良い（一般的に）</span>
        </div>
      </div>

      <div className="w-full h-64">
        <ResponsiveContainer>
          <LineChart data={validData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
            <XAxis
              dataKey="date"
              tick={{ fill: "#94a3b8", fontSize: 11 }}
              tickFormatter={(val) => val.slice(5)}
            />
            <YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} />
            <Tooltip
              contentStyle={{
                backgroundColor: "rgba(15, 23, 42, 0.95)",
                border: "1px solid rgba(167, 139, 250, 0.3)",
                borderRadius: "8px",
              }}
              labelStyle={{ color: "#94a3b8" }}
            />
            <Legend
              wrapperStyle={{ fontSize: 11 }}
              formatter={(value) => {
                const labels: Record<string, string> = {
                  referring_domains: "参照ドメイン数",
                  backlinks_count: "被リンク数",
                };
                return <span style={{ color: "#94a3b8" }}>{labels[value] || value}</span>;
              }}
            />
            <Line
              type="monotone"
              dataKey="referring_domains"
              stroke="#a78bfa"
              strokeWidth={2}
              dot={{ fill: "#a78bfa", r: 3 }}
              name="referring_domains"
            />
            <Line
              type="monotone"
              dataKey="backlinks_count"
              stroke="#c4b5fd"
              strokeWidth={2}
              dot={{ fill: "#c4b5fd", r: 3 }}
              name="backlinks_count"
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <p className="mt-3 text-xs text-text-muted">
        ※ 被リンク指標は変化が緩やかなため、短期の上下で判断しないことを推奨します。
      </p>
    </GlassCard>
  );
}
