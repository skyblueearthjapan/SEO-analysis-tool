# SEO Analysis Checklist (Page-Type Specific)
Version: 0.1 (MVP)
Scope: 公式ホームページ（自社） / 紹介記事ページ（第三者サイト内の自社紹介）

---

## 0. 共通方針（最重要）
- 本アプリは「診断結果（根拠データ）」を生成し、最終レポートはルールベース +（必要なら）AIで文章化する。
- ページタイプにより「改善できる主体」が異なるため、チェック項目・推奨アクションを分ける。
  - 公式HP: 自社で変更可能（修正ToDoを中心に）
  - 紹介記事: 原則は第三者管理（依頼ToDo + 自社側の代替策を中心に）
- 競合比較は「構造差」「SERP上の見え方（title/description）」「テクニカル差」を優先し、競合のSearch Consoleデータは前提にしない。

---

## 1. ページタイプ判定（入力時）
### 1.1 ページタイプ（page_type）
- `official_homepage`（自社公式サイト内のページ）
- `third_party_profile_page`（第三者サイト内の自社紹介/掲載ページ）

### 1.2 入力パラメータ（MVP）
- url: string (必須)
- page_type: enum (必須)
- locale: string (例: "ja-JP") (任意 / default "ja-JP")
- device: enum ("mobile" | "desktop") (任意 / default "mobile")
- target_country: string (例: "JP") (任意 / default "JP")

---

## 2. 共通データ取得（両タイプに適用）
### 2.1 HTML/構造の抽出
- title, meta description
- canonical, robots meta
- h1/h2/h3構造（テキスト、順序、数）
- 本文テキスト（可読テキスト抽出）
- internal links count（同一ドメインのみ）
- external links count（異なるドメイン）
- images count / images with alt / alt率
- structured data（JSON-LD等）の種類（FAQ/HowTo/Article等）

### 2.2 技術メタ（簡易）
- HTTP status code
- final URL（リダイレクト後URL）
- mobile-friendly簡易判定（viewport meta有無など）
- Core Web Vitals（可能なら PageSpeed Insights API）
  - LCP / INP / CLS / Performance score
  - ※MVPはscoreだけでも可

### 2.3 SERPスナップショット（可能なら / optional）
- 指定クエリ1〜3個で上位結果のtitle/descriptionを取得
  - 取得できない場合は "not_available" とし、比較ロジックは構造中心で実施
- SERP features（FAQ, Video, Local packなど）が確認できれば記録

---

## 3. 公式ホームページ用チェックリスト（official_homepage）
目的: 「自社で直せる」前提で、テクニカル/構造/CTR訴求/情報設計の改善ToDoを生成する。

### 3.1 検索パフォーマンス（自社のみ / Search Console連携がある場合）
#### 取得
- 対象URLのクエリ上位N（推奨: 20）
  - impressions, clicks, ctr, position（期間: 7日 / 28日）
- brand queries（劇団名/会社名など）の有無と傾向

#### チェック
- [ ] Brandクエリで「表示はあるがCTRが低い」(例: ctr < 0.5 * median_ctr_top10)
- [ ] Non-brandで「11〜20位停滞」(例: 11 <= position <= 20 が多い)
- [ ] 「表示多い×CTR低い」(impressions高、ctr低)
- [ ] 「急落」(7日平均順位が前7日より悪化、かつimpressions減)

#### 出力（例）
- opportunities: {type, query, metric_snapshot, suggested_action_bucket}

---

### 3.2 情報設計・コンテンツ構造（ホームページ最重要）
※ホームページは「記事」よりも "信頼" と "目的別導線" が重要。単なる文字数勝負にしない。

#### チェック（構造）
- [ ] h1が1つだけで、ページ内容を説明している
- [ ] titleに「固有名（劇団名/会社名）」が含まれる
- [ ] titleに補助語（カテゴリ/地域/提供価値）が含まれる（例: 社会人演劇/東京/公演情報）
- [ ] meta descriptionが空でない（80〜140字程度が望ましい）
- [ ] 主要セクションが存在する（ホームページ向け）
  - [ ] 何者か（概要）
  - [ ] 活動内容（何をしているか）
  - [ ] 実績/公演履歴（信頼）
  - [ ] 写真/メディア（体験）
  - [ ] 参加/問い合わせ導線（CTA）
  - [ ] FAQ or よくある質問（任意だが強い）

#### チェック（文章/信頼要素）
- [ ] 固有情報（所在地/活動地域/連絡先/運営者情報）がどこかにある
- [ ] 公演履歴・受賞・メディア掲載などの実績がある（なければ「今後追加推奨」として出す）
- [ ] 画像にaltが一定割合付いている（例: alt率 >= 70%）

#### 出力（ホームページの改善ToDo）
- content_todos:
  - missing_sections: [ ... ]
  - rewrite_suggestions:
    - hero_copy_suggestion (例: 1文で何者か)
    - CTA improvement
  - title_candidates: [3案]
  - meta_description_candidates: [2案]
  - h2_outline_candidates: [10案（必要なら）]

---

### 3.3 テクニカルSEO（ホームページ）
#### チェック（indexing/基本）
- [ ] status code == 200
- [ ] robots metaが noindex でない
- [ ] canonicalが自己参照/適切
- [ ] OGP/Twitterカード（任意、SNS流入にも影響）

#### チェック（CWV/速度）
- [ ] Performance score < 60（要改善） / 60-80（改善余地） / 80+（良）
- [ ] LCPが遅い（例: LCP > 2.5s）

#### チェック（構造化データ）
- [ ] Organization / WebSite schema（あれば強い）
- [ ] FAQ schema（FAQがある場合）

#### 出力（テクニカルToDo）
- technical_todos:
  - indexing_issue: {present, reason}
  - speed_issue: {score, likely_causes_bucket}
  - schema_missing: [ ... ]
  - priority_fix_list: [P0/P1]

---

### 3.4 CTR訴求（検索結果で"選ばれる"）
#### チェック（Search Consoleがある場合に強い）
- [ ] position <= 10 かつ ctr が低い（優先度高）
- [ ] titleに数字/年版/ベネフィット/具体が少ない

#### 出力（CTR改善案）
- ctr_todos:
  - title_variants: [ ... ]
  - description_variants: [ ... ]
  - snippets_to_add: [例: 実績数、写真、FAQ]

---

## 4. 紹介記事ページ用チェックリスト（third_party_profile_page）
目的: 「自社で直接直せない」前提で、掲載価値の評価と、掲載元への修正依頼テンプレ＆自社側の代替策を生成する。

### 4.1 掲載価値（露出/ブランド/導線）
#### チェック
- [ ] 自社名（劇団名/会社名）がtitleまたはh1/h2に含まれる
- [ ] 自社の説明文量が十分（例: 200字以上）※短い場合「拡充依頼」
- [ ] 自社HPへのリンクがある
- [ ] リンクがnofollow/sponsoredでない（取得できるなら）
- [ ] 画像・ロゴがある（任意）

#### 出力
- listing_value:
  - brand_visibility: High/Med/Low
  - description_depth: Adequate/Thin
  - link_to_official: Present/Absent (+ rel)
  - suggested_next_action: request_update / leverage_on_official_site

---

### 4.2 掲載内容の品質（"差別化"と"文脈"）
#### チェック（内容）
- [ ] 自社の特徴（作風/活動地域/参加条件/公演頻度など）が具体的に書かれている
- [ ] 他団体と区別できる要素がある（独自性）
- [ ] 検索意図に沿う語が含まれる（例: 社会人演劇, 地域名, 劇団, 公演, 参加 など）

#### チェック（構造）
- [ ] 見出しに自社名が入っている（理想）
- [ ] 連絡導線（公式HP/問い合わせ/予約）が明確

#### 出力
- content_quality:
  - uniqueness_score: 0-100（ルールベース）
  - missing_angles: [例: 地域, 参加方法, 作風, 公演実績]
  - proposed_profile_copy: 150-250字の改善文案（生成）

---

### 4.3 リンク最適化（外部→公式への橋渡し）
#### チェック
- [ ] リンクテキストが具体的（例: "〇〇劇団 公式サイト"）
  - "こちら/公式HP"だけの場合、改善依頼
- [ ] 公式サイトへのリンクが1つ以上ある
- [ ] 可能なら、公式サイト内の関連ページ（公演情報/参加方法）へもリンクできる余地

#### 出力（依頼テンプレ）
- outreach_request_template:
  - requested_changes:
    - link_text_change: from "こちら" to "〇〇劇団（社会人演劇・地域）公式サイト"
    - add_more_context: add region/genre keywords in description
    - add CTA: reservation/participation link
  - message_draft_jp: |
      掲載ありがとうございます。SEO/ユーザー導線の観点で、以下の微修正をご相談できますでしょうか…
      （箇条書きで3点まで）

---

### 4.4 自社側の代替策（修正できない場合）
#### チェック
- [ ] 紹介記事URLを自社HP側で紹介し、内部リンクを張れるか（「掲載実績」ページ等）
- [ ] 自社HPに同等の情報を補完できるか（プロフィール/参加方法/FAQ）

#### 出力
- fallback_actions:
  - add_reference_page_on_official: true/false
  - internal_link_plan: [どこからどこへリンクするか案]
  - content_to_add_on_official: [不足セクション案]

---

## 5. 競合比較（自社公式 vs 競合2URL） ※MVP想定
### 5.1 比較対象
- 自社: official_homepage（1URL）
- 競合: 同じ検索意図のページ（2URL）

### 5.2 比較項目（優先）
- 構造:
  - h2/h3数
  - セクション構成（意図カバー）
  - FAQ有無
- SERP訴求:
  - title/descriptionパターン差分（可能なら）
- テクニカル:
  - speed score
  - schema有無

### 5.3 差分原因推定（ルール）
- 競合が「意図カバー項目」を複数持ち、自社が欠ける → 主因: コンテンツ品質
- 自社がposition <=10 で ctr 低（自社データ）→ 主因: CTR訴求
- 自社のCWVが悪く、競合が良い → 主因: テクニカル（補足/主因判定は閾値次第）

### 5.4 出力
- diff_summary:
  - main_cause: content_quality / ctr / technical
  - confidence: 0-1
  - evidence: [差分の根拠箇条書き]
- prioritized_todos:
  - P0/P1/P2 で最大10件
  - 各ToDoに (impact_estimate, effort_estimate, evidence_link)

---

## 6. 最終レポート（AI使用時の前提）
- AIは「文章化・優先順位・具体案生成」を担当し、判断根拠は必ず本チェック結果から引用させる。
- AI出力は以下のセクション固定：
  1) 結論（最優先3点）
  2) 公式HPの改善ToDo（P0/P1/P2）
  3) 紹介記事の改善依頼案（テンプレ付き）
  4) 競合との差分と理由（根拠付き）
  5) 検証計画（7日/28日で見る指標）

---

## 7. MVPで"必須"のチェック項目（実装優先度）
### Must-have (P0)
- title/meta/hタグ抽出
- セクション構成（h2一覧）
- FAQ有無（schema or content）
- 公式HP: Search Console クエリ上位取得（可能なら）
- 紹介記事: 公式HPリンク有無 + リンクテキスト
- 競合比較: h2数 + FAQ有無 + title差分

### Should-have (P1)
- PageSpeedスコア
- structured data種類抽出（FAQ/Organization/Article等）
- alt率、内部/外部リンク数

### Nice-to-have (P2)
- SERP feature検知
- より高度な意図分類（比較/料金/事例など）
