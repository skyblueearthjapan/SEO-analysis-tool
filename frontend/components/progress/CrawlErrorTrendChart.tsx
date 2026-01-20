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
import { AlertTriangle, Info } from "lucide-react";

interface CrawlErrorDataPoint {
  date: string;
  error_type: string;
  count: number;
}

interface CrawlErrorTrendChartProps {
  data: CrawlErrorDataPoint[];
  title?: string;
}

export function CrawlErrorTrendChart({
  data,
  title = "クロールエラーの推移",
}: CrawlErrorTrendChartProps) {
  // Transform data: group by date, aggregate by error type
  const byDate: Record<string, Record<string, number>> = {};

  for (const row of data) {
    if (!byDate[row.date]) {
      byDate[row.date] = { date: row.date } as any;
    }
    byDate[row.date][row.error_type] = row.count;
  }

  const chartData = Object.values(byDate).sort((a: any, b: any) =>
    a.date.localeCompare(b.date)
  );

  // Calculate total errors for display
  const errorTypes = new Set(data.map((d) => d.error_type));

  if (chartData.length < 2) {
    return (
      <GlassCard>
        <div className="flex items-center gap-2 mb-4">
          <AlertTriangle className="h-5 w-5 text-amber-400" />
          <h3 className="text-sm font-semibold">{title}</h3>
        </div>
        <div className="text-center py-8 text-text-muted">
          <p>データが不足しています</p>
          <p className="text-xs mt-2">複数日の解析を実行すると推移が表示されます</p>
        </div>
      </GlassCard>
    );
  }

  const errorColors: Record<string, string> = {
    "http_404": "#f87171",
    "http_500": "#fb923c",
    "http_503": "#fbbf24",
    "redirect_chain_long": "#a78bfa",
    "noindex": "#60a5fa",
    "4xx": "#f87171",
    "5xx": "#fb923c",
    "other": "#94a3b8",
  };

  return (
    <GlassCard>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <AlertTriangle className="h-5 w-5 text-amber-400" />
          <h3 className="text-sm font-semibold">{title}</h3>
        </div>
        <div className="flex items-center gap-1 text-xs text-text-muted">
          <Info className="h-3 w-3" />
          <span>少ないほど良い</span>
        </div>
      </div>

      <div className="w-full h-64">
        <ResponsiveContainer>
          <LineChart data={chartData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
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
                border: "1px solid rgba(251, 191, 36, 0.3)",
                borderRadius: "8px",
              }}
              labelStyle={{ color: "#94a3b8" }}
            />
            <Legend
              wrapperStyle={{ fontSize: 11 }}
              formatter={(value) => <span style={{ color: "#94a3b8" }}>{value}</span>}
            />
            {Array.from(errorTypes).map((errorType) => (
              <Line
                key={errorType}
                type="monotone"
                dataKey={errorType}
                stroke={errorColors[errorType] || "#94a3b8"}
                strokeWidth={2}
                dot={{ fill: errorColors[errorType] || "#94a3b8", r: 3 }}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>

      <p className="mt-3 text-xs text-text-muted">
        ※ エラー数が0に近づくほど健全な状態です。
      </p>
    </GlassCard>
  );
}
