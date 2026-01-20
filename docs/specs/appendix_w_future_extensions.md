# Appendix W — 将来拡張（被リンク / SERP順位 / キーワード調査 / 全体クロール / ログ解析 / 重複カニバリ）実装ガイド

Version: 0.1
目的: "拡張解析"を段階的に追加しつつ、既存の `analysis_checks` / `evidence` / `todos` / Drawer UI と自然に統合する
対象: コーディングエージェント（AI/人間）
前提: Appendix V の `analysis_checks` + `source_checks` が既に実装済み

---

## 0) 拡張実装の共通ルール（最重要）

拡張解析はすべて **Analyzerモジュール**として追加する。

### 0.1 Analyzerインターフェース（共通）

どの拡張でも必ず返す:
- `check_code`
- `status`
- `notes`
- `evidence[]`（0件でもよい）
- `todo_candidates[]`（任意）

```python
# app/services/analyzers/base.py
from dataclasses import dataclass
from typing import Literal, List, Dict, Any

CheckStatus = Literal["done","partial","skipped","not_supported"]

@dataclass
class AnalyzerOutput:
    check_code: str
    status: CheckStatus
    notes: List[str]
    evidence: List[Dict[str, Any]]     # evidence objects (id/kind/title/data/...)
    todo_candidates: List[Dict[str, Any]]  # optional; later merged into rule_engine
```

### 0.2 evidence 仕様（共通）

evidenceは **ToDoの根拠**として機械的に参照できる形で統一。

- `id`: `ev_<check>_<page|site>_<suffix>`（重複禁止）
- `kind`: `fetch|html|pagespeed|gsc|serp|backlinks|crawl|logs|similarity|...`
- `title`: 人間が見てわかる短い名前
- `severity`: `critical|warning|info`
- `data`: 生データ（必要最小限）

### 0.3 analysis_checks への反映

- 各Analyzerは `AnalyzerOutput` を返す
- 集約が `analysis_checks.checks[code] = {status, notes, evidence_ids}` を構築する
- ToDoは `source_checks=[check_code]` を必ず入れる

---

## 1) 実装の優先順位（推奨ロードマップ）

運用価値 / 難易度 / 外部API依存 を総合して順番を決め打ち。

### Phase X-1（最初に足すのが強い・コスパ良）

1. **SERP順位（GSCベース）**：`serp_rank`（partial→doneへ）
2. **キーワード大量調査（GSC + 抽出）**：`keyword_research`

### Phase X-2（外部API or 追加インフラが必要）

3. **被リンク分析**：`backlinks`（外部API）
4. **重複/カニバリ（オンページ類似）**：`duplicate_cannibalization`（内部計算）

### Phase Y（中〜大型機能）

5. **サイト全体クロール**：`site_crawl`（キュー/レート制御/robots考慮）

### Phase Z（最上級・導入難）

6. **ログ解析**：`log_analysis`（ログ入手・処理設計が必要）

---

## 2) SERP順位計測（serp_rank）

### 2.1 MVP方針（最初はGSCで代替）

- GSCが有効なら `average_position` を「順位代替」として保存（正確な"SERP順位"ではないが、トレンドには十分）
- GSC無効なら `not_supported` または `skipped`

### 2.2 Analyzer

ファイル: `app/services/analyzers/serp_rank_gsc.py`

入力:
- site_id, official_url, competitor_urls
- gsc（query別 or page別）

出力（evidence例）:

```json
{
  "id": "ev_serp_rank_gsc_official",
  "kind": "serp",
  "title": "GSC平均掲載順位（公式）",
  "severity": "info",
  "data": {
    "page": "https://...",
    "avg_position": 12.3,
    "clicks": 120,
    "impressions": 5400,
    "ctr": 0.022,
    "range": "last_28_days"
  }
}
```

analysis_checks:
- GSC enabled & OK → `done`
- GSC enabled but limited → `partial`
- not configured → `skipped`

ToDo候補:
- `avg_position <= 10` でCTR低い → CTR改善ToDo（title/description）
- `avg_position 11-20` & impressions多 → コンテンツ拡張ToDo

### 2.3 将来（本格SERP）

- 外部SERP API（合法性/利用規約を確認）
- 取得の最小設計:
  - キーワード数を絞る（上位10〜30）
  - 週次計測（毎日だと費用/ブロック増）

---

## 3) キーワード大量調査（keyword_research）

### 3.1 MVP方針（無料・低コスト）

- GSCクエリ（上位N）を取得
- HTML（title/h1/h2）からキーフレーズ抽出（簡易）
- 競合との "クエリ集合差分" を出す

### 3.2 Analyzer

ファイル: `app/services/analyzers/keyword_research.py`

evidence例:

```json
{
  "id": "ev_kw_top_queries_official",
  "kind": "keywords",
  "title": "GSC上位クエリ（公式）",
  "severity": "info",
  "data": {
    "top_queries": [
      {"query": "社会人演劇", "clicks": 20, "impressions": 600, "ctr": 0.033, "pos": 8.4},
      {"query": "劇団 参加", "clicks": 5, "impressions": 400, "ctr": 0.012, "pos": 14.1}
    ],
    "range": "last_28_days"
  }
}
```

差分evidence:

```json
{
  "id": "ev_kw_gap_official_vs_comp1",
  "kind": "keywords",
  "title": "クエリ差分（公式 vs 競合1）",
  "severity": "info",
  "data": {
    "missing_on_official": ["...", "..."],
    "unique_on_official": ["..."],
    "overlap": ["..."]
  }
}
```

ToDo候補:
- "競合で強いが自社に無いクエリ" → セクション追加案（h2案/FAQ案）
- "impressions多いがCTR低いクエリ" → title/description案（AI補助）

---

## 4) 被リンク分析（backlinks）

### 4.1 注意（先に決めること）

被リンクは **外部データソース依存**。まずは Provider を1つ決める。

候補: Ahrefs / Majestic / Moz / SEMrush など

MVP要件: 「ドメイン参照数」「総リンク数」「上位リンク元」「競合比較」

> 実装前に「どのAPIを使うか」「APIキー課金」「利用規約」を確定する。
> 未確定なら `status=not_supported` のままにしておく。

### 4.2 Analyzer

ファイル: `app/services/analyzers/backlinks_<provider>.py`

evidence例（共通フォーマット）:

```json
{
  "id": "ev_backlinks_summary_official",
  "kind": "backlinks",
  "title": "被リンクサマリ（公式）",
  "severity": "info",
  "data": {
    "ref_domains": 42,
    "backlinks_total": 1200,
    "dofollow_ratio": 0.71,
    "top_ref_domains": ["example.com", "foo.jp"],
    "timestamp": "2026-01-20T12:00:00Z"
  }
}
```

analysis_checks:
- provider key configured → `done`（API成功）
- key configured but limit/timeout → `partial`
- 未設定 → `skipped`（または `not_supported`）

ToDo候補:
- 競合比でref_domainsが極端に少ない → 外部露出/紹介依頼ToDo
- 低品質ドメイン比率が高い → disavow検討（※高難度。MVPでは"注意喚起"まで）

---

## 5) 重複・カニバリ精密判定（duplicate_cannibalization）

### 5.1 MVP方針（オンページ類似 + クエリ競合）

サイト全体クロールが無くても、まずは **登録ページ集合**で判定できる。

- 文章類似（簡易）: Jaccard / cosine（TF-IDF）
- 見出し類似: h2集合の重なり
- GSCがあれば: 同一クエリで複数URLに表示がある → カニバリ疑い

### 5.2 Analyzer

ファイル: `app/services/analyzers/duplicate_cannibalization.py`

evidence例:

```json
{
  "id": "ev_dup_similarity_matrix",
  "kind": "similarity",
  "title": "類似度マトリクス（登録ページ）",
  "severity": "info",
  "data": {
    "pairs": [
      {"a_page_id": "p1", "b_page_id": "p2", "text_cosine": 0.86, "h2_jaccard": 0.52}
    ],
    "thresholds": {"text_cosine": 0.80, "h2_jaccard": 0.45}
  }
}
```

ToDo候補:
- 類似度が閾値超え → "統合/差別化" ToDo（どちらを主にするか提案）
- 同一クエリで2URL表示 → canonical/内部リンク/セクション整理提案

---

## 6) サイト全体クロール（site_crawl）

### 6.1 MVP設計（安全な最小）

目的: 1URL解析から "サイト全体" へ拡張し、構造問題を検出する。

#### 6.1.1 クロールポリシー（必須）

- robots.txt 尊重（MVPでも最低限）
- 同一ホストのみ
- 最大ページ数 `MAX_PAGES`（例: 100）
- 最大深さ `MAX_DEPTH`（例: 3）
- レート制限（例: 1 req/sec）
- 重複URL正規化（末尾スラッシュ・クエリ除外ルール）

#### 6.1.2 データ

- CrawlRun: site_id, start_url, started_at, finished_at
- CrawledPage: url, status, title, canonical, depth, inlinks_count, outlinks_count

### 6.2 アーキテクチャ

- RQジョブとして実行（長時間化するため）
- 途中経過を `daily_metrics` または新テーブル `crawl_pages` に保存（推奨）
- 結果は `analysis_result.json` に "サマリだけ" 入れる（巨大化防止）

### 6.3 evidence例（サマリ）

```json
{
  "id": "ev_crawl_summary",
  "kind": "crawl",
  "title": "サイトクロールサマリ",
  "severity": "info",
  "data": {
    "pages_crawled": 84,
    "errors_4xx": 3,
    "errors_5xx": 1,
    "orphan_candidates": 5,
    "max_depth": 4,
    "top_depth_urls": ["..."]
  }
}
```

ToDo候補:
- 4xx/5xx多数 → 修正ToDo（P0/P1）
- Orphan疑い → 内部リンク改善ToDo
- 深すぎる導線 → ナビ改善/カテゴリ構造提案

---

## 7) ログ解析（log_analysis）

### 7.1 事前条件（これが無いと始まらない）

- ログの入手経路（CloudFront/NGINX/Apache/GA4/サーバ）
- 個人情報/取り扱いポリシー
- 保存先（S3等）と保持期間

### 7.2 MVPの最小アウトプット

- Googlebot等のクロール頻度
- 404/500の発生箇所
- 重いURL（response time）

evidence例:

```json
{
  "id": "ev_logs_bot_crawl",
  "kind": "logs",
  "title": "Botクロール概要（過去7日）",
  "severity": "info",
  "data": {
    "googlebot_hits": 1200,
    "bingbot_hits": 90,
    "top_crawled_urls": [{"url":"...","hits":120}],
    "errors": {"4xx": 30, "5xx": 3}
  }
}
```

> ログ解析は Phase Z。MVPでは `not_supported` 維持でOK。

---

## 8) UI/UX 連動（Checklist + Drawer）

### 8.1 Checklist（既存）

- 追加したAnalyzerが `analysis_checks.checks[code].status=done` を返せば、UIは自動で "Done" になる

### 8.2 TodoDetailDrawer

- ToDoに `source_checks=["keyword_research"]` 等が入れば、自動でチップ表示される
- 拡張に伴って新しい ToDo種類が増えたら、Drawerの `templates` を活用
  - 例: 「外部露出依頼文」「記事構成案」「FAQ案」など

---

## 9) API / DB 追加指針（どこまで増やすか）

### 9.1 原則

- 解析結果は `analysis_results.raw_json` に保存（まずはここ）
- 大量データ（クロールページ一覧、ログ明細、SERP全件）は **別テーブル**へ

### 9.2 推奨の追加テーブル（必要になった時だけ）

- `crawl_runs` / `crawl_pages`
- `serp_snapshots`（本格SERPをやる場合）
- `backlink_snapshots`（providerレスポンスの保存）
- `log_ingests` / `log_events`（ログ解析）

---

## 10) 拡張実装の「コーディングエージェントへの指示」テンプレ

各拡張は以下の手順で追加する。

### 手順テンプレ

1. `AnalysisCheckCode` にコード追加（既にenumにある場合は不要）
2. `app/services/analyzers/<feature>.py` を新規作成（AnalyzerOutputを返す）
3. 集約層で Analyzer を呼び出し、`analysis_checks` と `evidence` に統合
4. `rule_engine` で ToDo生成:
   - `evidence_refs` + `source_checks=[<feature>]` を必ず付与
5. Frontend:
   - Checklist UIは自動（statusが変わるだけ）
   - TodoDetailDrawerに evidence/templates/verification を表示（既存流用）
6. E2E:
   - feature無効時: status=skipped or not_supported
   - feature有効時: status=done/partial、ToDoが出る

---

## 11) 最初に実装する拡張（指示：これで着手）

### 11.1 まずはこれ（最小追加で効果が大）

- `keyword_research`（GSC + 抽出）
- `serp_rank`（GSC average position）

**理由**:
- 外部課金なし（GSCがある前提）
- 競合差分とToDoに直結しやすい
- UI（Checklist/Drawer）が即"賢く"見える

---

## 12) Definition of Done（拡張共通の完了条件）

- [ ] `analysis_checks.<code>` が `done/partial/skipped` を正しく返す
- [ ] `evidence` が作られ、ToDoの `evidence_refs` で参照できる
- [ ] ToDoに `source_checks` が付く
- [ ] Drawerで根拠→手順→検証が見える
- [ ] 機能OFFでもUIが壊れず "Skipped/Planned" になる
