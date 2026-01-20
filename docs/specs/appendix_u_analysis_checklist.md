# Appendix U — AnalysisChecklist（解析一覧チェックリスト）

Version: 0.1
目的: 実行した解析内容を可視化し、信頼性と拡張余地を示す
表示場所: Result画面 Overview タブ（最上部 or ResultHeader直下）

---

## 1) UI要件

### 1.1 表示形式
- チェックリスト形式（✓ / ⚠ / —）
- カテゴリ別セクション
- 各項目に「簡易説明 + 拡張予定ラベル」を付与

### 1.2 ステータス定義

| status | 意味 |
|--------|------|
| done | 今回のRunで実行済み |
| partial | 一部のみ/限定条件で実行 |
| skipped | 機能はあるが今回は未実行 |
| not_supported | 未実装（拡張予定） |

---

## 2) データ仕様（analysis_result.json 拡張）

### 2.1 analysis_checks オブジェクト

```json
{
  "analysis_checks": {
    "fetch": "done",
    "html_basic": "done",
    "headings": "done",
    "images_alt": "done",
    "structured_data": "done",
    "pagespeed": "done",
    "search_console": "partial",
    "intent_coverage": "done",
    "competitor_diff": "done",

    "backlinks": "not_supported",
    "serp_rank": "not_supported",
    "keyword_research": "not_supported",
    "site_crawl": "not_supported",
    "log_analysis": "not_supported",
    "duplicate_cannibalization": "not_supported"
  }
}
```

> ※ このオブジェクトは **ルールエンジン前**で確定させる
> → 後続の ToDo / AI レポートの「根拠メタ情報」にも流用可能

---

## 3) チェック項目一覧（初期）

### 3.1 基本取得

- ✓ HTTP取得・リダイレクト確認
- ✓ ステータスコード / robots / canonical

### 3.2 HTML・構造

- ✓ title / meta description
- ✓ 見出し構造（h1/h2/h3）
- ✓ テキスト量
- ✓ 内部リンク / 外部リンク
- ✓ 画像 alt 属性

### 3.3 構造化・技術

- ✓ FAQ / Organization / Article 構造化データ
- ✓ PageSpeed / Core Web Vitals

### 3.4 検索パフォーマンス

- ⚠ Search Console（連携時のみ）

### 3.5 コンテンツ品質

- ✓ 意図カバー率（公式 / 紹介記事）

### 3.6 競合比較

- ✓ 見出し構造差分
- ✓ 意図カバー差分
- ✓ 技術指標差分

---

## 4) フロントエンドUI

### 4.1 コンポーネント

- `AnalysisChecklistPanel`
- `AnalysisCheckRow`

### 4.2 表示例（文言）

```
✔ HTTP取得・ステータス確認
✔ title / meta description
✔ 構造化データ（FAQ / Organization）
✔ PageSpeed / Core Web Vitals
⚠ Search Console（未連携のため一部のみ）
— 被リンク分析（拡張予定）
— SERP順位計測（拡張予定）
```

### 4.3 UX小ワザ

- hoverで「何を見ているか」説明
- `not_supported` には「今後追加予定」バッジ
- ToDoと紐づくチェックはハイライト

---

## 5) チェック項目詳細定義

### 5.1 CheckItem 型定義

```typescript
interface CheckItem {
  id: string;
  label: string;
  description: string;
  category: "fetch" | "html" | "tech" | "search" | "content" | "compare" | "future";
  status: "done" | "partial" | "skipped" | "not_supported";
  relatedTodoIds?: string[];
  futureLabel?: string;  // not_supported時の表示
}
```

### 5.2 カテゴリ定義

| category | 日本語 | 説明 |
|----------|--------|------|
| fetch | 基本取得 | HTTP取得、リダイレクト |
| html | HTML・構造 | title, meta, 見出し等 |
| tech | 技術・構造化 | schema, PageSpeed |
| search | 検索パフォーマンス | GSC連携 |
| content | コンテンツ品質 | 意図カバー |
| compare | 競合比較 | diff分析 |
| future | 拡張予定 | 未実装機能 |

---

## 6) Backend実装

### 6.1 analysis_checks生成タイミング

```
analysis_pipeline.py
  └─> run_analysis()
       ├─> fetch_page() → checks["fetch"] = "done"
       ├─> parse_html() → checks["html_basic"] = "done"
       ├─> get_pagespeed() → checks["pagespeed"] = status
       ├─> get_gsc_data() → checks["search_console"] = status
       └─> finalize_checks() → 未実装項目を "not_supported" で埋める
```

### 6.2 ヘルパー関数

```python
def build_analysis_checks(
    fetch_result: dict,
    html_result: dict,
    pagespeed_result: dict,
    gsc_result: dict,
    comparisons: list
) -> dict:
    """
    各解析結果からanalysis_checksオブジェクトを生成
    """
    checks = {}

    # Fetch
    checks["fetch"] = "done" if fetch_result.get("status_code") else "skipped"

    # HTML Basic
    checks["html_basic"] = "done" if html_result.get("title") else "skipped"
    checks["headings"] = "done" if html_result.get("h1") else "partial"
    checks["images_alt"] = "done"  # パース時に常に実行

    # Structured Data
    sd = html_result.get("structured_data", {})
    checks["structured_data"] = "done" if sd.get("types") else "partial"

    # PageSpeed
    ps = pagespeed_result or {}
    if ps.get("available"):
        checks["pagespeed"] = "done"
    elif ps.get("error"):
        checks["pagespeed"] = "skipped"
    else:
        checks["pagespeed"] = "partial"

    # GSC
    if gsc_result and gsc_result.get("clicks") is not None:
        checks["search_console"] = "done"
    elif gsc_result:
        checks["search_console"] = "partial"
    else:
        checks["search_console"] = "skipped"

    # Intent Coverage
    checks["intent_coverage"] = "done"

    # Competitor Diff
    checks["competitor_diff"] = "done" if comparisons else "skipped"

    # Future features (always not_supported for now)
    checks["backlinks"] = "not_supported"
    checks["serp_rank"] = "not_supported"
    checks["keyword_research"] = "not_supported"
    checks["site_crawl"] = "not_supported"
    checks["log_analysis"] = "not_supported"
    checks["duplicate_cannibalization"] = "not_supported"

    return checks
```

---

## 7) 拡張ロードマップ

### Phase X-1: 被リンク分析
- 外部API: Ahrefs / Majestic / Moz
- 表示: 総リンク数、ドメイン数、競合比較

### Phase X-2: SERP順位計測
- GSC平均順位（まず）
- Custom Search API（本格）

### Phase X-3: キーワード調査
- title/h2からの自動抽出
- サジェストAPI連携

### Phase Y: サイト全体クロール
- 内部リンクグラフ
- orphan page検出
- depth分析

### Phase Z: ログ解析（エンタープライズ）
- Bot到達頻度
- クロール効率

---

## 8) 受け入れ基準

- [ ] Result画面で解析一覧が見える
- [ ] 実行/未実行/未対応が明確に区別できる
- [ ] ユーザーが「どこまで見ているツールか」を理解できる
- [ ] hover時に各項目の説明が表示される
- [ ] not_supported項目に「拡張予定」ラベルが表示される
