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
} from "recharts";
import { GlassCard } from "@/components/layout/GlassCard";
import { TrendingDown, Info } from "lucide-react";

interface SerpDataPoint {
  date: string;
  avg_position: number | null;
}

interface SerpTrendChartProps {
  data: SerpDataPoint[];
  title?: string;
}

export function SerpTrendChart({ data, title = "平均掲載順位の推移" }: SerpTrendChartProps) {
  // Filter out null values for chart
  const chartData = data.filter((d) => d.avg_position !== null);

  if (chartData.length < 2) {
    return (
      <GlassCard>
        <div className="flex items-center gap-2 mb-4">
          <TrendingDown className="h-5 w-5 text-accent-cyan" />
          <h3 className="text-sm font-semibold">{title}</h3>
        </div>
        <div className="text-center py-8 text-text-muted">
          <p>データが不足しています</p>
          <p className="text-xs mt-2">複数日の解析を実行すると推移が表示されます</p>
        </div>
      </GlassCard>
    );
  }

  return (
    <GlassCard>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <TrendingDown className="h-5 w-5 text-accent-cyan" />
          <h3 className="text-sm font-semibold">{title}</h3>
        </div>
        <div className="flex items-center gap-1 text-xs text-text-muted">
          <Info className="h-3 w-3" />
          <span>低いほど良い</span>
        </div>
      </div>

      <div className="w-full h-64">
        <ResponsiveContainer>
          <LineChart data={chartData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
            <XAxis
              dataKey="date"
              tick={{ fill: "#94a3b8", fontSize: 11 }}
              tickFormatter={(val) => val.slice(5)} // MM-DD format
            />
            <YAxis
              reversed // Lower position = better, show at top
              tick={{ fill: "#94a3b8", fontSize: 11 }}
              domain={["auto", "auto"]}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "rgba(15, 23, 42, 0.95)",
                border: "1px solid rgba(6, 182, 212, 0.3)",
                borderRadius: "8px",
              }}
              labelStyle={{ color: "#94a3b8" }}
              formatter={(value: number) => [`${value.toFixed(1)}位`, "平均順位"]}
            />
            <Line
              type="monotone"
              dataKey="avg_position"
              stroke="#06b6d4"
              strokeWidth={2}
              dot={{ fill: "#06b6d4", r: 3 }}
              activeDot={{ r: 5, fill: "#22d3ee" }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <p className="mt-3 text-xs text-text-muted">
        ※ 平均掲載順位は「小さいほど良い」指標です。グラフが上に向かうと改善を示します。
      </p>
    </GlassCard>
  );
}
