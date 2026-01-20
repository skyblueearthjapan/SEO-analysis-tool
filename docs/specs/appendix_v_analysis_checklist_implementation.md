# Appendix V — AnalysisChecklist（UI + Backend + 生成ロジック + ToDo連動）実装仕様

Version: 0.2
目的:
- Result画面に「このRunで実行された解析一覧」をチェックリストで表示し、信頼性・拡張余地を明示する
- ToDo詳細Drawerでも「どの解析から出た指摘か」を可視化し、コンサル感を上げる

前提:
- Next.js(App Router) + FastAPI + Postgres(JSONB)
- analysis_result.json を analysis_results.raw_json に保存
- 既存ToDo: `evidence_refs` を持つ（または持たせる）

---

## 0) 実装方針（重要）

- 解析一覧は **analysis_checks** を結果JSONに保存（保存型）
- 各解析モジュールは `AnalyzerMeta` を返し、集約して `analysis_checks` を作る
- ToDoは `source_checks`（どの解析チェックに紐づくか）を持つ
- UIは
  - Result Overview に `AnalysisChecklistPanel`
  - TodoDetailDrawer に `TodoSourcesPanel` を追加

---

## 1) データ仕様（analysis_result.json 拡張）

### 1.1 enum

```json
{
  "AnalysisCheckStatus": ["done", "partial", "skipped", "not_supported"],
  "AnalysisCheckCode": [
    "fetch",
    "html_basic",
    "headings",
    "text_stats",
    "links",
    "images_alt",
    "structured_data",
    "pagespeed",
    "search_console",
    "intent_coverage",
    "competitor_diff",
    "backlinks",
    "serp_rank",
    "keyword_research",
    "site_crawl",
    "log_analysis",
    "duplicate_cannibalization"
  ]
}
```

### 1.2 analysis_checks（保存）

```json
{
  "analysis_checks": {
    "schema_version": "0.1",
    "checks": {
      "fetch": { "status": "done", "notes": [], "evidence_ids": ["ev_fetch_official"] },
      "html_basic": { "status": "done", "notes": [], "evidence_ids": ["ev_html_meta_official"] },
      "headings": { "status": "done", "notes": [], "evidence_ids": ["ev_headings_official"] },
      "text_stats": { "status": "done", "notes": [], "evidence_ids": ["ev_text_stats_official"] },
      "links": { "status": "done", "notes": [], "evidence_ids": ["ev_links_official"] },
      "images_alt": { "status": "done", "notes": [], "evidence_ids": ["ev_images_official"] },
      "structured_data": { "status": "done", "notes": [], "evidence_ids": ["ev_schema_official"] },
      "pagespeed": { "status": "partial", "notes": ["pagespeed disabled or timeout"], "evidence_ids": ["ev_pagespeed_official"] },
      "search_console": { "status": "skipped", "notes": ["GSC not configured"], "evidence_ids": [] },
      "intent_coverage": { "status": "done", "notes": [], "evidence_ids": ["ev_intent_official"] },
      "competitor_diff": { "status": "done", "notes": [], "evidence_ids": ["ev_comp_diff_1", "ev_comp_diff_2"] },

      "backlinks": { "status": "not_supported", "notes": ["planned"], "evidence_ids": [] },
      "serp_rank": { "status": "not_supported", "notes": ["planned"], "evidence_ids": [] },
      "keyword_research": { "status": "not_supported", "notes": ["planned"], "evidence_ids": [] },
      "site_crawl": { "status": "not_supported", "notes": ["planned"], "evidence_ids": [] },
      "log_analysis": { "status": "not_supported", "notes": ["planned"], "evidence_ids": [] },
      "duplicate_cannibalization": { "status": "not_supported", "notes": ["planned"], "evidence_ids": [] }
    }
  }
}
```

### 1.3 ToDo拡張：source_checks（推奨）

```json
{
  "todo_id": "todo_001",
  "title": "HTTPステータスコードの修正",
  "priority": "P0",
  "category": "technical",
  "impact": "high",
  "effort": "medium",
  "evidence_refs": ["ev_fetch_official"],
  "source_checks": ["fetch"]
}
```

> NOTE: `source_checks` が無い場合は、`evidence_refs` の種別から推定してもよいが、まずは生成時に埋める。

---

## 2) Backend 生成ロジック（Python）

### 2.1 解析モジュールのメタ返却（AnalyzerMeta）

各サービスは（既存の返り値に加えて）以下を返すか、集約層が作る。

```python
from dataclasses import dataclass
from typing import List, Literal, Optional

CheckStatus = Literal["done","partial","skipped","not_supported"]

@dataclass
class AnalyzerMeta:
    code: str
    status: CheckStatus
    notes: List[str]
    evidence_ids: List[str]
```

### 2.2 集約関数：build_analysis_checks

作成場所: `app/services/checks.py`

```python
def build_analysis_checks(ctx) -> dict:
    """
    ctx: 実行コンテキスト（設定/ページ数/機能フラグ/タイムアウト等を含む）
    outputs: 各解析の実行可否と結果メタ
    """
    checks = {}

    # core (always)
    checks["fetch"] = {"status":"done","notes":[], "evidence_ids": ctx.evidence_ids.get("fetch", [])}
    checks["html_basic"] = {"status":"done","notes":[], "evidence_ids": ctx.evidence_ids.get("html_basic", [])}
    checks["headings"] = {"status":"done","notes":[], "evidence_ids": ctx.evidence_ids.get("headings", [])}
    checks["text_stats"] = {"status":"done","notes":[], "evidence_ids": ctx.evidence_ids.get("text_stats", [])}
    checks["links"] = {"status":"done","notes":[], "evidence_ids": ctx.evidence_ids.get("links", [])}
    checks["images_alt"] = {"status":"done","notes":[], "evidence_ids": ctx.evidence_ids.get("images_alt", [])}
    checks["structured_data"] = {"status":"done","notes":[], "evidence_ids": ctx.evidence_ids.get("structured_data", [])}
    checks["intent_coverage"] = {"status":"done","notes":[], "evidence_ids": ctx.evidence_ids.get("intent_coverage", [])}

    # optional tech
    if ctx.flags.pagespeed_enabled:
        # timeout or missing key => partial
        st = "done" if ctx.flags.pagespeed_ok else "partial"
        notes = [] if st == "done" else ["pagespeed disabled/timeout/key missing"]
        checks["pagespeed"] = {"status": st, "notes": notes, "evidence_ids": ctx.evidence_ids.get("pagespeed", [])}
    else:
        checks["pagespeed"] = {"status":"skipped","notes":["pagespeed disabled"], "evidence_ids":[]}

    # optional GSC
    if ctx.flags.gsc_enabled:
        st = "done" if ctx.flags.gsc_ok else "partial"
        notes = [] if st == "done" else ["gsc auth/config issue"]
        checks["search_console"] = {"status": st, "notes": notes, "evidence_ids": ctx.evidence_ids.get("search_console", [])}
    else:
        checks["search_console"] = {"status":"skipped","notes":["GSC not configured"], "evidence_ids":[]}

    # competitor diff only if competitors >= 1
    if ctx.competitor_count >= 1:
        checks["competitor_diff"] = {"status":"done","notes":[], "evidence_ids": ctx.evidence_ids.get("competitor_diff", [])}
    else:
        checks["competitor_diff"] = {"status":"skipped","notes":["no competitors"], "evidence_ids":[]}

    # extension placeholders
    for code in ["backlinks","serp_rank","keyword_research","site_crawl","log_analysis","duplicate_cannibalization"]:
        checks[code] = {"status":"not_supported","notes":["planned"], "evidence_ids":[]}

    return {"schema_version":"0.1", "checks": checks}
```

### 2.3 ToDoへ source_checks を付与する

場所: `rule_engine.py` の `create_todo()` または `generate_todos()`

ルール:
- technical系で fetch起因 → `["fetch"]`
- title/meta系 → `["html_basic"]`
- h2/h3構造 → `["headings"]`
- alt → `["images_alt"]`
- schema → `["structured_data"]`
- pagespeed → `["pagespeed"]`
- gsc/ctr → `["search_console"]`
- intent不足 → `["intent_coverage"]`
- competitor差分起因 → `["competitor_diff"]`

```python
def infer_source_checks(todo: dict) -> list[str]:
    t = (todo.get("type") or todo.get("category") or "").lower()
    key = (todo.get("key") or "").lower()
    ev = todo.get("evidence_refs", [])

    # strongest by evidence prefix
    if any("pagespeed" in e for e in ev): return ["pagespeed"]
    if any("gsc" in e or "search_console" in e for e in ev): return ["search_console"]
    if any("schema" in e for e in ev): return ["structured_data"]
    if any("heading" in e for e in ev): return ["headings"]
    if any("image" in e or "alt" in e for e in ev): return ["images_alt"]
    if any("fetch" in e or "status" in e for e in ev): return ["fetch"]
    if "competitor" in key or "diff" in key: return ["competitor_diff"]
    if "intent" in key or t == "content": return ["intent_coverage"]
    return ["html_basic"]
```

生成時に:

```python
todo["source_checks"] = infer_source_checks(todo)
```

### 2.4 analysis_result.json に反映

ジョブ完了時（保存直前）に:

- `analysis_result["analysis_checks"] = build_analysis_checks(ctx)`
- すべての `todo` に `source_checks` を付与

---

## 3) Backend API（FastAPI）

### 3.1 既存結果取得に含める（推奨）

`GET /api/v1/sites/{site_id}/analysis-results/{result_id}` のレスポンスに
- `analysis_checks` を含める（すでに raw_json を返しているなら自動）

### 3.2 追加APIは不要（MVP）

UIが result 全体を取得できるならチェックリスト表示だけなら足りる。

> TodoDetailDrawer で詳細を別API取得している場合でも、analysis_checks は result JSON から参照可能。

---

## 4) Frontend 型定義

### 4.1 lib/analysisChecks/types.ts

```ts
export type AnalysisCheckStatus = "done" | "partial" | "skipped" | "not_supported";

export type AnalysisCheckCode =
  | "fetch"
  | "html_basic"
  | "headings"
  | "text_stats"
  | "links"
  | "images_alt"
  | "structured_data"
  | "pagespeed"
  | "search_console"
  | "intent_coverage"
  | "competitor_diff"
  | "backlinks"
  | "serp_rank"
  | "keyword_research"
  | "site_crawl"
  | "log_analysis"
  | "duplicate_cannibalization";

export interface AnalysisCheckItem {
  status: AnalysisCheckStatus;
  notes: string[];
  evidence_ids: string[];
}

export interface AnalysisChecks {
  schema_version: string;
  checks: Record<AnalysisCheckCode, AnalysisCheckItem>;
}
```

---

## 5) Frontend UI（Result Overview）

### 5.1 components/results/AnalysisChecklistPanel.tsx

要件:
- セクションごとに表示
- statusに応じてアイコン/色/バッジ
- notesはホバー or "詳細" で展開
- not_supported は "Planned" バッジ

```tsx
"use client";

import * as React from "react";
import type { AnalysisChecks, AnalysisCheckCode, AnalysisCheckStatus } from "@/lib/analysisChecks/types";
import { GlassCard } from "@/components/layout/GlassCard";
import { cn } from "@/lib/utils";
import { Check, Minus, AlertTriangle, Clock, Info } from "lucide-react";

const statusIcon = (st: AnalysisCheckStatus) => {
  if (st === "done") return <Check className="h-4 w-4 text-accent-cyan" />;
  if (st === "partial") return <AlertTriangle className="h-4 w-4 text-amber-400" />;
  if (st === "skipped") return <Minus className="h-4 w-4 text-text-muted" />;
  return <Clock className="h-4 w-4 text-violet-400" />; // not_supported/planned
};

const statusLabel: Record<AnalysisCheckStatus, string> = {
  done: "実行済み",
  partial: "一部実行",
  skipped: "スキップ",
  not_supported: "拡張予定",
};

const statusColor: Record<AnalysisCheckStatus, string> = {
  done: "text-accent-cyan border-accent-cyan/30 bg-accent-cyan/10",
  partial: "text-amber-400 border-amber-400/30 bg-amber-400/10",
  skipped: "text-text-muted border-border-subtle bg-bg-surface",
  not_supported: "text-violet-400 border-violet-400/30 bg-violet-400/10",
};

const groups: { title: string; items: { code: AnalysisCheckCode; label: string; desc: string }[] }[] = [
  {
    title: "基本取得 / HTML",
    items: [
      { code: "fetch", label: "HTTP取得・ステータス確認", desc: "status/final_url/redirect/主要ヘッダー" },
      { code: "html_basic", label: "title / meta / canonical / robots", desc: "基本メタ要素の抽出" },
      { code: "headings", label: "見出し構造（h1/h2/h3）", desc: "見出し一覧と構造差分に利用" },
      { code: "text_stats", label: "テキスト量", desc: "文字数などの簡易指標" },
      { code: "links", label: "リンク集計", desc: "内部/外部リンク数の集計" },
      { code: "images_alt", label: "画像 alt", desc: "alt付与率の算出" },
      { code: "structured_data", label: "構造化データ（JSON-LD）", desc: "FAQ/Organization/Article 等" },
    ],
  },
  {
    title: "テクニカル",
    items: [
      { code: "pagespeed", label: "PageSpeed / Core Web Vitals", desc: "PSスコア, LCP, INP, CLS" },
    ],
  },
  {
    title: "検索パフォーマンス",
    items: [
      { code: "search_console", label: "Search Console", desc: "Clicks/Impr/CTR/Pos（連携時）" },
    ],
  },
  {
    title: "品質・比較",
    items: [
      { code: "intent_coverage", label: "意図カバー率", desc: "公式/紹介ページの必須項目カバー" },
      { code: "competitor_diff", label: "競合差分", desc: "構造/意図/テクニカルの差分" },
    ],
  },
  {
    title: "拡張（予定）",
    items: [
      { code: "backlinks", label: "被リンク分析", desc: "外部API連携（Ahrefs等）" },
      { code: "serp_rank", label: "SERP順位計測", desc: "定点観測/外部SERP API" },
      { code: "keyword_research", label: "キーワード大量調査", desc: "サジェスト/関連検索など" },
      { code: "site_crawl", label: "サイト全体クロール", desc: "内部リンクグラフ/Orphan検出" },
      { code: "log_analysis", label: "ログ解析", desc: "bot到達/クロール頻度（上級）" },
      { code: "duplicate_cannibalization", label: "重複・カニバリ", desc: "類似度/同一クエリ競合" },
    ],
  },
];

export function AnalysisChecklistPanel({ analysisChecks }: { analysisChecks?: AnalysisChecks | null }) {
  return (
    <GlassCard>
      <div className="flex items-start justify-between gap-3 mb-4">
        <div>
          <h3 className="text-sm font-semibold">解析チェックリスト</h3>
          <p className="mt-1 text-xs text-text-muted">
            このRunで実行した解析内容
          </p>
        </div>
        <div className="flex items-center gap-1 text-xs text-text-muted">
          <Info className="h-3 w-3" />
          <span>Hoverで詳細</span>
        </div>
      </div>

      <div className="space-y-4">
        {groups.map((g) => (
          <div key={g.title}>
            <div className="text-xs font-medium text-text-muted mb-2">{g.title}</div>
            <div className="space-y-1.5">
              {g.items.map((it) => {
                const item = analysisChecks?.checks?.[it.code];
                const st: AnalysisCheckStatus = item?.status ?? "not_supported";
                const notes = item?.notes ?? (st === "not_supported" ? ["planned"] : []);
                return (
                  <div
                    key={it.code}
                    className="group flex items-center justify-between gap-3 rounded-lg border border-border-subtle bg-bg-surface px-3 py-2 hover:bg-bg-elevated transition-colors"
                    title={[it.desc, ...notes].join(" / ")}
                  >
                    <div className="flex items-center gap-3">
                      <div className="flex-shrink-0">
                        {statusIcon(st)}
                      </div>
                      <div>
                        <div className="text-xs font-medium text-text-primary">{it.label}</div>
                        <div className="text-[11px] text-text-muted opacity-0 group-hover:opacity-100 transition-opacity">
                          {it.desc}
                        </div>
                      </div>
                    </div>

                    <span className={cn(
                      "text-[10px] font-medium px-2 py-0.5 rounded-full border",
                      statusColor[st]
                    )}>
                      {statusLabel[st]}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </GlassCard>
  );
}
```

### 5.2 Result Overview への組込み

`/results/[resultId]/page.tsx` の Overview 上部に:

```tsx
<AnalysisChecklistPanel analysisChecks={result.analysis_checks} />
```

---

## 6) ToDo詳細Drawerへの連動（source_checks表示）

### 6.1 Todo型に source_checks を追加

`lib/api/types.ts`（既存に追記）

```ts
import type { AnalysisCheckCode } from "@/lib/analysisChecks/types";

export interface Todo {
  todo_id: string;
  title: string;
  priority: "P0" | "P1" | "P2";
  category: string;
  impact: "high" | "medium" | "low";
  effort: "small" | "medium" | "large";
  evidence_refs?: string[];
  source_checks?: AnalysisCheckCode[];
  detail?: TodoDetail;
}
```

### 6.2 components/todos/TodoSourcesPanel.tsx（新規）

```tsx
"use client";

import * as React from "react";
import type { AnalysisChecks, AnalysisCheckCode, AnalysisCheckStatus } from "@/lib/analysisChecks/types";
import { cn } from "@/lib/utils";

const mapLabel: Record<AnalysisCheckCode, string> = {
  fetch: "HTTP取得",
  html_basic: "メタ要素",
  headings: "見出し",
  text_stats: "テキスト量",
  links: "リンク",
  images_alt: "画像alt",
  structured_data: "構造化データ",
  pagespeed: "PageSpeed",
  search_console: "GSC",
  intent_coverage: "意図カバー",
  competitor_diff: "競合差分",
  backlinks: "被リンク",
  serp_rank: "順位計測",
  keyword_research: "KW調査",
  site_crawl: "全体クロール",
  log_analysis: "ログ解析",
  duplicate_cannibalization: "重複/カニバリ",
};

const statusColor: Record<AnalysisCheckStatus, string> = {
  done: "text-accent-cyan border-accent-cyan/30 bg-accent-cyan/10",
  partial: "text-amber-400 border-amber-400/30 bg-amber-400/10",
  skipped: "text-text-muted border-border-subtle bg-bg-surface",
  not_supported: "text-violet-400 border-violet-400/30 bg-violet-400/10",
};

export function TodoSourcesPanel({
  sourceChecks,
  analysisChecks,
}: {
  sourceChecks?: AnalysisCheckCode[];
  analysisChecks?: AnalysisChecks | null;
}) {
  if (!sourceChecks?.length) return null;

  return (
    <div className="mt-3">
      <div className="text-xs font-medium text-text-muted mb-2">この指摘の根拠となった解析</div>
      <div className="flex flex-wrap gap-2">
        {sourceChecks.map((c) => {
          const st = analysisChecks?.checks?.[c]?.status ?? "not_supported";
          return (
            <span
              key={c}
              className={cn(
                "text-[11px] font-medium px-2 py-1 rounded-full border",
                statusColor[st]
              )}
              title={analysisChecks?.checks?.[c]?.notes?.join(" / ") || ""}
            >
              {mapLabel[c]}
            </span>
          );
        })}
      </div>
    </div>
  );
}
```

### 6.3 Drawerに組込み

`TodoDetailDrawer` 内（header直下など）に追加:

```tsx
<TodoSourcesPanel sourceChecks={todo.source_checks} analysisChecks={result?.analysis_checks} />
```

---

## 7) Backend 受け入れ条件（生成が正しいこと）

- pagespeed_enabled=false → pagespeed=skipped
- pagespeed_enabled=true だが timeout/key欠如 → pagespeed=partial + notes
- GSC未設定 → search_console=skipped
- 競合0件 → competitor_diff=skipped
- 拡張系は全て not_supported（planned）

---

## 8) フロント受け入れ基準

- [ ] Result Overview にチェックリストが表示される
- [ ] Done/Partial/Skipped/Planned が明確に色分けされる
- [ ] Hoverで説明/notesが見える
- [ ] TodoDetailDrawer に「根拠となった解析」がチップで表示される
- [ ] analysis_checks が無い古い結果でもUIが壊れない（not_supported扱い）

---

## 9) 実装順（推奨）

1. Backend: `build_analysis_checks(ctx)` を追加し、保存時に `analysis_result["analysis_checks"]` を埋める
2. Backend: `todo["source_checks"]=infer_source_checks(todo)` を追加
3. Frontend: types追加（AnalysisChecks / Todo source_checks）
4. Frontend: `AnalysisChecklistPanel` を Result Overview に追加
5. Frontend: `TodoSourcesPanel` を TodoDetailDrawer に追加
6. E2E確認（旧resultでも落ちない/notes表示）

---

## 10) 将来拡張の約束（この設計が効くポイント）

被リンク/順位/クロール等を追加したら:
- analyzerが evidence_ids を吐く
- checksに `done` が立つ
- ToDoが `source_checks` で紐づく
- UIは自動的に "実行済み" として表示される

→ 機能追加が「差分実装」で済むようになる
