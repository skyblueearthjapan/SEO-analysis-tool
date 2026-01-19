# spec.md — SEO Analysis & Recommendation App (MVP)
Version: 0.1
Target: Web App + Python backend
Scope (MVP): 自社公式HP 1URL + 競合 2URL（構造比較） + 紹介記事ページ（第三者掲載）も扱える設計
Output: `analysis_result.json`（機械可読） + AI生成の `report.md`（人間可読）

---

## 1. 全体アーキテクチャ概要（MVP）
### 1.1 処理フロー
1) URL登録（page_type指定）
2) Pythonがページを取得・解析（HTML/構造/リンク/構造化データ/速度）
3) （自社公式HPのみ）Search ConsoleでURL単位の検索パフォーマンスを取得（可能な場合）
4) 競合比較（公式HP vs 競合2URL）
5) ルールベースで
   - 改善タイプ推定（content / ctr / technical）
   - ToDoの優先度付け（P0/P1/P2）
6) `analysis_result.json` を保存
7) AIに `analysis_result.json` を渡して `report.md`（提案レポート）を生成

---

## 2. `analysis_result.json` 出力スキーマ
### 2.1 スキーマ（JSON Schema Draft 2020-12想定）
> 実装では厳密なJSON Schemaバリデーションを推奨（pydantic等）

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://example.com/schemas/analysis_result.schema.json",
  "title": "SEOAnalysisResult",
  "type": "object",
  "required": [
    "schema_version",
    "generated_at",
    "run_id",
    "inputs",
    "pages",
    "comparisons",
    "diagnosis",
    "todos",
    "ai_prompt_payload"
  ],
  "properties": {
    "schema_version": { "type": "string", "const": "0.1" },
    "generated_at": { "type": "string", "format": "date-time" },
    "run_id": { "type": "string" },

    "inputs": {
      "type": "object",
      "required": ["target_country", "locale", "device"],
      "properties": {
        "target_country": { "type": "string", "default": "JP" },
        "locale": { "type": "string", "default": "ja-JP" },
        "device": { "type": "string", "enum": ["mobile", "desktop"], "default": "mobile" },
        "time_windows_days": {
          "type": "object",
          "required": ["short", "long"],
          "properties": {
            "short": { "type": "integer", "default": 7 },
            "long": { "type": "integer", "default": 28 }
          }
        }
      }
    },

    "pages": {
      "type": "array",
      "minItems": 1,
      "items": { "$ref": "#/$defs/PageAnalysis" }
    },

    "comparisons": {
      "type": "array",
      "items": { "$ref": "#/$defs/Comparison" }
    },

    "diagnosis": { "$ref": "#/$defs/Diagnosis" },

    "todos": {
      "type": "array",
      "items": { "$ref": "#/$defs/Todo" }
    },

    "ai_prompt_payload": {
      "type": "object",
      "description": "AI生成に渡すための整形済みペイロード（report生成用）。pages/diagnosis/todosの要点を冗長になりすぎない形で再掲。",
      "required": ["report_language", "report_style", "constraints", "data"],
      "properties": {
        "report_language": { "type": "string", "default": "ja" },
        "report_style": {
          "type": "string",
          "enum": ["consultant", "concise", "technical"],
          "default": "consultant"
        },
        "constraints": {
          "type": "object",
          "required": ["must_cite_evidence", "no_guessing", "max_todos_per_priority"],
          "properties": {
            "must_cite_evidence": { "type": "boolean", "default": true },
            "no_guessing": { "type": "boolean", "default": true },
            "max_todos_per_priority": { "type": "integer", "default": 5 }
          }
        },
        "data": {
          "type": "object",
          "required": ["summary", "pages", "comparisons", "diagnosis", "todos"],
          "properties": {
            "summary": { "type": "string" },
            "pages": { "type": "array", "items": { "type": "object" } },
            "comparisons": { "type": "array", "items": { "type": "object" } },
            "diagnosis": { "type": "object" },
            "todos": { "type": "array", "items": { "type": "object" } }
          }
        }
      }
    }
  },

  "$defs": {
    "PageAnalysis": {
      "type": "object",
      "required": ["page_id", "url", "page_type", "fetch", "html", "tech", "content", "serp", "search_console"],
      "properties": {
        "page_id": { "type": "string" },
        "url": { "type": "string" },
        "page_type": { "type": "string", "enum": ["official_homepage", "third_party_profile_page", "competitor_page"] },

        "fetch": {
          "type": "object",
          "required": ["status_code", "final_url"],
          "properties": {
            "status_code": { "type": "integer" },
            "final_url": { "type": "string" },
            "redirect_chain": { "type": "array", "items": { "type": "string" } }
          }
        },

        "html": {
          "type": "object",
          "required": ["title", "meta_description", "canonical", "robots_meta", "headings"],
          "properties": {
            "title": { "type": "string" },
            "meta_description": { "type": "string" },
            "canonical": { "type": "string" },
            "robots_meta": { "type": "string" },
            "headings": {
              "type": "object",
              "required": ["h1", "h2", "h3"],
              "properties": {
                "h1": { "type": "array", "items": { "type": "string" } },
                "h2": { "type": "array", "items": { "type": "string" } },
                "h3": { "type": "array", "items": { "type": "string" } }
              }
            },
            "text_stats": {
              "type": "object",
              "properties": {
                "text_length_chars": { "type": "integer" },
                "text_length_words_est": { "type": "integer" }
              }
            },
            "links": {
              "type": "object",
              "properties": {
                "internal_count": { "type": "integer" },
                "external_count": { "type": "integer" },
                "external_domains": { "type": "array", "items": { "type": "string" } }
              }
            },
            "images": {
              "type": "object",
              "properties": {
                "count": { "type": "integer" },
                "with_alt": { "type": "integer" },
                "alt_ratio": { "type": "number" }
              }
            },
            "structured_data": {
              "type": "object",
              "properties": {
                "types": { "type": "array", "items": { "type": "string" } },
                "has_faq_schema": { "type": "boolean" },
                "has_organization_schema": { "type": "boolean" },
                "has_article_schema": { "type": "boolean" }
              }
            }
          }
        },

        "tech": {
          "type": "object",
          "required": ["mobile_friendly_hint", "pagespeed"],
          "properties": {
            "mobile_friendly_hint": { "type": "string", "enum": ["pass", "warn", "fail", "not_available"] },
            "pagespeed": {
              "type": "object",
              "required": ["available"],
              "properties": {
                "available": { "type": "boolean" },
                "performance_score": { "type": ["integer", "null"] },
                "lcp_ms": { "type": ["integer", "null"] },
                "inp_ms": { "type": ["integer", "null"] },
                "cls": { "type": ["number", "null"] }
              }
            }
          }
        },

        "content": {
          "type": "object",
          "required": ["intent_coverage", "missing_sections", "notes"],
          "properties": {
            "intent_coverage": {
              "type": "object",
              "description": "ホームページ/紹介記事に必要な意図項目のカバー状況（0/1または0-1）",
              "additionalProperties": { "type": "number" }
            },
            "missing_sections": { "type": "array", "items": { "type": "string" } },
            "notes": { "type": "array", "items": { "type": "string" } }
          }
        },

        "serp": {
          "type": "object",
          "required": ["available"],
          "properties": {
            "available": { "type": "boolean" },
            "queries_tested": { "type": "array", "items": { "type": "string" } },
            "serp_features": { "type": "array", "items": { "type": "string" } },
            "top_results": {
              "type": "array",
              "items": {
                "type": "object",
                "properties": {
                  "rank": { "type": "integer" },
                  "url": { "type": "string" },
                  "title": { "type": "string" },
                  "snippet": { "type": "string" }
                }
              }
            }
          }
        },

        "search_console": {
          "type": "object",
          "required": ["available"],
          "properties": {
            "available": { "type": "boolean" },
            "time_window_days": { "type": ["integer", "null"] },
            "top_queries": {
              "type": "array",
              "items": {
                "type": "object",
                "required": ["query", "impressions", "clicks", "ctr", "position"],
                "properties": {
                  "query": { "type": "string" },
                  "impressions": { "type": "integer" },
                  "clicks": { "type": "integer" },
                  "ctr": { "type": "number" },
                  "position": { "type": "number" },
                  "query_intent": { "type": "string", "enum": ["brand", "info", "compare", "price", "visit", "unknown"] }
                }
              }
            },
            "brand_query_summary": {
              "type": "object",
              "properties": {
                "brand_queries_present": { "type": "boolean" },
                "brand_impressions": { "type": "integer" },
                "brand_ctr": { "type": "number" }
              }
            }
          }
        }
      }
    },

    "Comparison": {
      "type": "object",
      "required": ["comparison_id", "kind", "source_page_id", "target_page_id", "diff"],
      "properties": {
        "comparison_id": { "type": "string" },
        "kind": { "type": "string", "enum": ["official_vs_competitor", "official_vs_third_party"] },
        "source_page_id": { "type": "string" },
        "target_page_id": { "type": "string" },
        "diff": {
          "type": "object",
          "required": ["structure", "tech", "serp"],
          "properties": {
            "structure": {
              "type": "object",
              "properties": {
                "h2_count_delta": { "type": "integer" },
                "missing_intent_items": { "type": "array", "items": { "type": "string" } },
                "faq_schema_delta": { "type": "integer" }
              }
            },
            "tech": {
              "type": "object",
              "properties": {
                "performance_score_delta": { "type": ["integer", "null"] },
                "mobile_hint_delta": { "type": "string" }
              }
            },
            "serp": {
              "type": "object",
              "properties": {
                "title_pattern_notes": { "type": "array", "items": { "type": "string" } },
                "snippet_pattern_notes": { "type": "array", "items": { "type": "string" } }
              }
            }
          }
        }
      }
    },

    "Diagnosis": {
      "type": "object",
      "required": ["main_cause", "cause_breakdown", "scores", "evidence"],
      "properties": {
        "main_cause": { "type": "string", "enum": ["content_quality", "ctr", "technical", "mixed", "unknown"] },
        "cause_breakdown": {
          "type": "object",
          "required": ["content_quality", "ctr", "technical"],
          "properties": {
            "content_quality": { "type": "integer", "minimum": 0, "maximum": 100 },
            "ctr": { "type": "integer", "minimum": 0, "maximum": 100 },
            "technical": { "type": "integer", "minimum": 0, "maximum": 100 }
          }
        },
        "scores": {
          "type": "object",
          "required": ["content", "technical", "ctr"],
          "properties": {
            "content": { "type": "string", "enum": ["A", "B", "C", "D"] },
            "technical": { "type": "string", "enum": ["A", "B", "C", "D"] },
            "ctr": { "type": "string", "enum": ["A", "B", "C", "D"] }
          }
        },
        "evidence": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["claim", "support"],
            "properties": {
              "claim": { "type": "string" },
              "support": { "type": "array", "items": { "type": "string" } }
            }
          }
        }
      }
    },

    "Todo": {
      "type": "object",
      "required": ["todo_id", "priority", "category", "title", "details", "evidence", "impact", "effort"],
      "properties": {
        "todo_id": { "type": "string" },
        "priority": { "type": "string", "enum": ["P0", "P1", "P2"] },
        "category": { "type": "string", "enum": ["content", "technical", "ctr", "outreach", "internal_linking"] },
        "title": { "type": "string" },
        "details": { "type": "string" },
        "evidence": { "type": "array", "items": { "type": "string" } },
        "impact": { "type": "string", "enum": ["high", "medium", "low"] },
        "effort": { "type": "string", "enum": ["small", "medium", "large"] },
        "examples": {
          "type": "object",
          "properties": {
            "title_variants": { "type": "array", "items": { "type": "string" } },
            "meta_description_variants": { "type": "array", "items": { "type": "string" } },
            "h2_outline": { "type": "array", "items": { "type": "string" } },
            "faq_questions": { "type": "array", "items": { "type": "string" } },
            "outreach_message_draft_jp": { "type": "string" }
          }
        }
      }
    }
  }
}
```

---

## 3. 判定ルール（閾値・優先度付け）

### 3.1 共通の前提
- **Search Consoleが利用できない場合：**
  - CTR系の判定は「unknown」扱いにし、構造/テクニカル中心で診断する。
- **PageSpeedが取れない場合：**
  - テクニカルは canonical/noindex/構造化データ等で評価し、速度は「not_available」。

### 3.2 スコアリング（A/B/C/D）

#### 3.2.1 Technical Score
- **D:**
  - status_code != 200 OR robots_metaにnoindex を含む
  - OR pagespeed.performance_score < 50（取得できる場合）
- **C:**
  - pagespeed.performance_score 50-69
  - OR canonicalが空/不自然（自己参照でない等）
  - OR mobile_friendly_hint == "fail"
- **B:**
  - pagespeed.performance_score 70-84
  - AND noindex/canonical重大問題なし
- **A:**
  - pagespeed.performance_score >= 85
  - AND 主要schema（公式HPならOrganization/WebSite、FAQがあるならFAQ）あり

#### 3.2.2 Content Score（公式HP向け）
意図カバー項目（MVP）を10点満点で評価（各1点）
- 概要（何者か）
- 活動内容
- 公演/実績
- 写真/メディア
- 参加/問い合わせ導線（CTA）
- よくある質問（FAQ）
- 活動地域/所在地
- メンバー/運営情報
- 最新情報（更新性の要素）
- 参加者/観客向け情報の分岐

**スコア → グレード**
- A: 9-10
- B: 7-8
- C: 5-6
- D: 0-4

（紹介記事ページは別基準：3.2.3）

#### 3.2.3 Content Score（紹介記事ページ向け）
意図カバー（MVP）を6点満点（各1点）
- 自社名が見出し/本文で明確
- 説明文が十分（>=200字）
- 特徴・差別化が具体
- 活動地域/ジャンルが明確
- 公式HPリンクがある
- 参加/予約など導線がある

**グレード**
- A: 6
- B: 5
- C: 3-4
- D: 0-2

#### 3.2.4 CTR Score（Search Consoleがある場合のみ）
対象URLの上位クエリ（推奨20）から「チャンス」比率で評価
- **チャンス定義（いずれか）**
  - (impressions >= 300) AND (position <= 10) AND (ctr <= 0.5 * median_ctr_of_top_queries)
  - (impressions >= 500) AND (position <= 5) AND (ctr < 0.03)

**グレード**
- A: チャンス比率 < 10%
- B: 10-20%
- C: 20-35%
- D: > 35% または majorキーワードで極端に低いCTRが存在

※median_ctr_of_top_queries はそのURL内クエリでの中央値（外部ベンチマークなしで成立させる）

---

### 3.3 main_cause（原因推定）ルール

cause_breakdown（%）をルールベースで作り、最大値を main_cause にする（差が小さければ mixed）。

#### 3.3.1 Technical寄り
- technical grade が C/D
- AND（pagespeed_score < 70 OR noindex/canonical問題 OR mobile fail）
→ technical = 50〜70
→ content/ctrは残りを配分（コンテンツ欠損が大きい場合はcontentも上げる）

#### 3.3.2 CTR寄り（Search Consoleあり）
- ctr grade が C/D
- AND position<=10 のクエリが一定数（例: 上位クエリ20中3件以上）
→ ctr = 50〜70

#### 3.3.3 Content寄り
- content grade が C/D
- AND 競合比較で missing_intent_items が多い（例: 3個以上）
- OR h2_count_delta が -5 以下（自社が少ない）
→ content = 50〜75

#### 3.3.4 mixed
- 上記が2つ同時に強い（例: content C/D かつ technical C/D）
→ mixed、配分は 40/40/20 など

---

### 3.4 ToDo生成ルール（カテゴリ別テンプレ + 優先度）

ToDoは最大15件（P0/P1/P2それぞれ最大5）。

#### 3.4.1 P0（今すぐ）
**発火条件（いずれか）**
- noindex / status!=200 / canonical重大問題 → technical P0
- Search Consoleで「表示多い×CTR低い×順位10以内」 → ctr P0
- 公式HPで「概要/CTA/実績」など中核セクション欠損（missing_sectionsに含まれる） → content P0
- 紹介記事で「公式HPリンクなし」または「リンクテキストが弱い」 → outreach P0

P0のimpactは原則 high、effortは small〜medium を選ぶ（最短で効くものを優先）

#### 3.4.2 P1（1〜2週間）
- FAQ追加（FAQ schema含む）
- 比較/料金/参加方法など "意図カバー拡張"
- 内部リンク設計（掲載実績ページ作成、関連ページへの導線）

#### 3.4.3 P2（継続）
- 体系的なコンテンツクラスター化（活動内容→公演→参加導線）
- 外部露出強化（掲載サイト追加、PR、SNS連携）
- 速度改善の深掘り（画像最適化/JS削減など）

---

## 4. AIに渡すプロンプト仕様（入力JSON → 出力Markdown）

### 4.1 基本思想（品質を上げるための制約）
- AIは **推測しない**。根拠は analysis_result.json の evidence を必ず引用。
- 断定は「根拠がある場合のみ」。不明な場合は「可能性」「要確認」とする。
- 出力は必ず以下のMarkdown構造に従う（固定）。
- 具体策は「作業レベル」で書く（h2案、title案、FAQ案、依頼文面など）。

### 4.2 AI入力（システム側で作る）
- そのまま analysis_result.json を渡すのではなく、`ai_prompt_payload` を渡す。
- 理由：冗長な生データを減らし、出力を安定させる。

### 4.3 出力Markdown仕様（report.md）

以下の見出し順を固定（必須）
1. `# SEO診断レポート`
2. `## 対象URL`
   - 自社公式HP
   - 競合（2URL）
   - 紹介記事（あれば）
3. `## 結論（最優先3点）`
   - 各点：理由（根拠データ引用）/期待効果/優先度
4. `## 原因推定（なぜ伸びないか・差があるか）`
   - main_cause と breakdown（%）
   - evidence（箇条書き）
5. `## 公式ホームページ 改善ToDo（P0/P1/P2）`
   - 各ToDo：手順 / 具体案 / 根拠 / 検証指標
6. `## 紹介記事ページ 改善依頼（依頼テンプレ付き）`
   - 依頼すべき修正（最大3点）
   - 依頼文面（丁寧な日本語）
   - 修正できない場合の代替策（自社側）
7. `## 競合との差分（構造・訴求・テクニカル）`
   - 差分テーブル（簡易）
   - 競合が持ち、自社が欠ける要素 → 追加ToDoへ紐付け
8. `## 検証計画（7日 / 28日）`
   - 何を、いつ、どの指標で見るか
   - 期待する変化（CTR→短期、順位→中期）

### 4.4 AIプロンプト（テンプレ）

実装では、下記を「1つのプロンプト文字列」として構成し、ai_prompt_payload を差し込む。

**Prompt Template (JP)**

```
あなたはSEOコンサルタントです。以下の入力データ（JSON）に基づき、Markdown形式の「SEO診断レポート」を作成してください。

【厳守ルール】
- 推測しない。根拠がない断定は禁止。根拠がない場合は「可能性」「要確認」と書く。
- すべての重要な指摘には、必ず入力JSON内の evidence（数値・差分・観測結果）を引用して根拠を示す。
- 出力は指定のMarkdown見出し構造を必ず守る。
- ToDoは P0/P1/P2 に分け、各ToDoに「手順」「具体案（例）」「根拠」「検証指標」を含める。
- 紹介記事ページは「修正依頼できること」と「自社側代替策」を分けて書く。
- 競合のSearch Consoleデータはない前提で、構造・訴求・テクニカル差から理由を述べる。

【出力構造（必須）】
# SEO診断レポート
## 対象URL
## 結論（最優先3点）
## 原因推定（なぜ伸びないか・差があるか）
## 公式ホームページ 改善ToDo（P0/P1/P2）
## 紹介記事ページ 改善依頼（依頼テンプレ付き）
## 競合との差分（構造・訴求・テクニカル）
## 検証計画（7日 / 28日）

【入力JSON】
{{AI_PROMPT_PAYLOAD_JSON}}
```

---

## 5. ai_prompt_payload の作り方（整形ルール）

### 5.1 要約の作成
- **summary:** 2〜4行で「現状」と「主因」を書く（ルールベース）
- **pages:** 各ページは以下だけ残す（冗長な原文HTMLは入れない）
  - url, page_type
  - title/meta
  - h2リスト（最大20、超える場合は上位20）
  - intent_coverage / missing_sections
  - pagespeed（scoreのみでも可）
  - search_console（top_queriesは最大20）
- **comparisons:** diffの要点のみ（h2_count_delta / missing_intent_items / faq_schema_delta / performance_score_delta）
- **diagnosis:** main_cause / breakdown / scores / evidence
- **todos:** P0/P1/P2各最大5件（detailsは短く、examplesは必要なら含める）

---

## 6. MVPの受け入れ基準（Acceptance Criteria）
- `analysis_result.json` がスキーマに準拠して生成される
- 公式HP（自社）について最低限以下が埋まる
  - title/meta、h2一覧、missing_sections、pagespeed(可能なら)、Search Console(可能なら)
- 競合2URLについて最低限以下が埋まる
  - title/meta、h2一覧、FAQ schema有無、pagespeed(可能なら)
- 比較結果として comparisons が2件（official_vs_competitor x2）生成される
- diagnosis.main_cause と cause_breakdown がルールで算出される
- todos が最大15件、P0/P1/P2で割り振られる
- AIに ai_prompt_payload を渡して report.md が生成され、指定の見出し構造を満たす

---

## 7. 実装メモ（コーディングエージェント向け）
- **Python側：**
  - HTML解析: BeautifulSoup / lxml
  - テキスト抽出: readability-lxml 等（MVPは簡易でOK）
  - PageSpeed: Google PageSpeed Insights API（任意）
  - Search Console API: URL単位で query data（可能なら）
  - Schema抽出: JSON-LD `<script type="application/ld+json">` をparse
  - ルールエンジン: しきい値は設定ファイル化（YAML推奨）
- **Web側：**
  - URL登録 + page_type選択
  - 実行ステータス表示
  - report.md を表示（Markdownレンダリング）
  - analysis_result.json のダウンロード

---

## 次のステップ（必要なら追記）
コーディングエージェントがそのまま着手できるように:
- `config/thresholds.yml`（閾値を外出しした設定例）
- `analysis_pipeline.py` の疑似コード（関数分割）
- `db_schema.sql`（MVPテーブル）
まで一気に追記可能。
