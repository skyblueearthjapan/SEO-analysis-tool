# Appendix AG — Progress Dashboard（時系列統合ダッシュボード）設計仕様

Version: 0.1
目的:
- SEO改善の「経過」と「成果」を1画面で可視化する
- 診断 → 実行 → 成果確認 → 次の判断、の循環を完成させる
- コンサルツールとしての説得力を最大化する

対象:
- Next.js（Result配下）
- Appendix AD / AE / AF 実装済み前提

---

## AG-0. ダッシュボードの思想（重要）

```md
SEOの成果は「単発の数値」ではなく「流れ」で見るものです。

Progress Dashboard は
- 何を改善したか
- その後、どう変化したか
- 今は良い流れか、止まっているか
を直感的に判断するための画面です。
```

---

## AG-1. 表示場所・導線

### 推奨配置

* Result詳細ページ内
  タブ構成:

  ```
  Overview | Todos | Progress | Report
  ```

* **Progress タブ = 本Appendixの画面**

---

## AG-2. 画面全体レイアウト（上 → 下）

```text
[ Progress Summary ]
[ SERP Rank Trend ]
[ Crawl Health Trend ]
[ Authority / Backlinks Trend ]
[ Improvement & Todo Correlation ]
```

---

## AG-3. Progress Summary（最上部サマリ）

### 内容

* 対象期間（例：過去28日）
* 全体評価（上向き / 横ばい / 注意）
* 主要指標の差分

### UI例

```text
Progress (Last 28 days)

▲ SERP Position     14.2 → 10.4
▲ CTR               1.8% → 3.1%
▲ PageSpeed         62 → 78
▼ Crawl Errors      19 → 4
```

### 判定ルール（簡易）

* 2指標以上が改善 → `Upward`
* 改善/悪化が混在 → `Mixed`
* 悪化が目立つ → `Attention`

---

## AG-4. SERP Rank Trend セクション

### 参照

* Appendix AD（serp_time_series）

### コンポーネント

* `SerpTrendChart`
* `SerpKpiRow`

### 表示内容

* 折れ線グラフ（avg_position）
* 直近値 / 7日前比 / 28日前比

### UI注意

* Y軸は「小さいほど良い」ことを説明文で補足
* GSC未連携時は

  ```md
  SERP順位データはSearch Console連携が必要です
  ```

---

## AG-5. Crawl Health Trend（クロール健全性）

### 参照

* Appendix AE（crawl_error_time_series）

### 表示内容

* errors_4xx / errors_5xx の推移
* pages_crawled との対比（任意）

### UI表現

* 赤系: 5xx
* 黄系: 4xx
* 0件の場合は `Healthy` バッジ

### 解釈文言（例）

```md
クロールエラーは大きく減少しています。
検索エンジンがページを取得しやすい状態に改善されています。
```

---

## AG-6. Authority / Backlinks Trend

### 参照

* Appendix AF（backlink_time_series）

### 表示内容

* 参照ドメイン数（主）
* Authority（副）

### UI表現

* 月次 or 週次スナップショット
* 数値は緩やかな変化を前提に表示

### 注意文

```md
被リンク指標は変化に時間がかかるため、
短期的な上下で判断しないことが重要です。
```

---

## AG-7. Improvement & Todo Correlation（改善との関係）

### 目的

「何をやったから、こうなった可能性がある」
を **断定せず** に示す

---

### 表示内容

#### 1) 完了ToDo一覧（期間内）

```text
✔ CTA導線の追加
✔ FAQセクション追加
✔ 画像alt修正
```

#### 2) その後の変化（自動要約）

```md
これらの改善後、以下の変化が確認されています。

- CTRの上昇
- 意図カバー欠損数の減少
```

※ 因果関係は断定しない（必須）

---

## AG-8. Backend データ集約（API）

### 推奨API

* `GET /api/v1/sites/{site_id}/progress?from=YYYY-MM-DD&to=YYYY-MM-DD`

### レスポンス例（集約）

```json
{
  "range": {"from":"2026-01-01","to":"2026-01-28"},
  "summary": {
    "serp": {"before":14.2,"after":10.4},
    "ctr": {"before":0.018,"after":0.031},
    "pagespeed": {"before":62,"after":78},
    "crawl_errors": {"before":19,"after":4}
  },
  "serp_series": [...],
  "crawl_series": [...],
  "backlink_series": [...],
  "completed_todos": ["todo_001","todo_004"]
}
```

---

## AG-9. Frontend コンポーネント構成

```
components/progress/
├─ ProgressDashboard.tsx
├─ ProgressSummary.tsx
├─ SerpTrendSection.tsx
├─ CrawlHealthSection.tsx
├─ BacklinkTrendSection.tsx
├─ TodoImpactSection.tsx
```

---

## AG-10. UX・トーン（重要）

* 数値は **評価材料** であり、結論ではない
* 「改善傾向」「可能性がある」という表現を徹底
* ユーザーが "安心して次の一手を考えられる" UI

---

## AG-11. 受け入れ基準（Definition of Done）

- [ ] Progressタブが存在する
- [ ] SERP / Crawl / Backlinks の推移が表示される
- [ ] 改善サマリが一目で分かる
- [ ] 完了ToDoとの関係が説明される
- [ ] データが無い場合も説明付きで表示される

---

## AG-12. この画面が完成すると何が起きるか

```md
・「改善しているか？」がすぐ分かる
・ツールの継続利用理由が明確になる
・SEOコンサルと同じ視点で判断できる
```
