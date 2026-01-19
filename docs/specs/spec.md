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

## Appendix A — config/thresholds.yml（閾値設定例）

> Note: しきい値は運用で変える前提。まずはMVPの安全寄り設定。

```yaml
app:
  schema_version: "0.1"
  max_queries_per_url: 20
  max_todos_total: 15
  max_todos_per_priority: 5
  default_locale: "ja-JP"
  default_country: "JP"
  default_device: "mobile"
  time_windows_days:
    short: 7
    long: 28

technical:
  # Fetch/indexing
  require_status_code: 200
  noindex_keywords:
    - "noindex"
  canonical_must_exist: true

  # Mobile hint rules (simple heuristic)
  mobile_friendly:
    viewport_required: true

  # PageSpeed (if available)
  pagespeed:
    score:
      A_min: 85
      B_min: 70
      C_min: 50
      D_max: 49
    lcp_ms:
      good_max: 2500
      needs_improvement_max: 4000
    inp_ms:
      good_max: 200
      needs_improvement_max: 500
    cls:
      good_max: 0.1
      needs_improvement_max: 0.25

content:
  # Official homepage intent coverage items (10)
  official_intent_items:
    - "overview"           # 何者か（概要）
    - "activities"         # 活動内容
    - "works_or_history"   # 公演/実績
    - "media_gallery"      # 写真/メディア
    - "cta_contact"        # 参加/問い合わせ導線
    - "faq"                # よくある質問
    - "region"             # 活動地域/所在地
    - "team_or_operator"   # メンバー/運営情報
    - "freshness"          # 最新情報/更新性
    - "audience_branch"    # 観客/参加希望など導線の分岐

  official_grade:
    A_min: 9
    B_min: 7
    C_min: 5
    D_max: 4

  # Third party profile intent coverage items (6)
  third_party_intent_items:
    - "brand_clear"        # 自社名が明確
    - "description_depth"  # 説明文十分
    - "unique_points"      # 特徴・差別化
    - "region_or_genre"    # 地域/ジャンル
    - "official_link"      # 公式HPリンク
    - "cta_present"        # 参加/予約導線

  third_party_grade:
    A_min: 6
    B_min: 5
    C_min: 3
    D_max: 2

  text_rules:
    third_party_min_chars: 200  # 紹介文の目安（日本語は文字数でOK）
    alt_ratio_good_min: 0.70

ctr:
  # CTR判定は Search Console 取得時のみ
  opportunity:
    min_impressions_1: 300
    min_impressions_2: 500
    pos_max_1: 10
    pos_max_2: 5
    ctr_low_ratio_to_median: 0.5
    ctr_hard_low: 0.03

  grade:
    A_max_opportunity_ratio: 0.10
    B_max_opportunity_ratio: 0.20
    C_max_opportunity_ratio: 0.35
    D_min_opportunity_ratio: 0.35

comparisons:
  # 競合差分判定の閾値
  h2_delta_content_strong: -5
  missing_intent_items_strong_min: 3
  faq_schema_delta_strong: -1
  pagespeed_delta_strong: -15

todos:
  # 自動ToDo作成の優先度ルール
  P0:
    - "indexing_critical"
    - "ctr_high_opportunity"
    - "core_sections_missing"
    - "official_link_missing_on_third_party"
  P1:
    - "faq_addition"
    - "intent_expansion"
    - "schema_addition"
    - "internal_linking_plan"
  P2:
    - "content_cluster"
    - "deep_performance_optimization"
    - "ongoing_outreach"

ai:
  report_style: "consultant"
  language: "ja"
  must_cite_evidence: true
  no_guessing: true
```

---

## Appendix B — analysis_pipeline.py（疑似コード / 関数分割）

> 目的: コーディングエージェントがそのまま実装に着手できる粒度。
> 前提: Python + FastAPI（任意）+ Celery/RQ（任意） or cron/Cloud Scheduler。
> 入力: URL登録（page_type含む） → 実行 → analysis_result.json保存 → report.md生成

```python
"""
analysis_pipeline.py (pseudo)

Modules (suggested):
- config.py            # thresholds.yml loader
- fetcher.py           # HTTP fetch + redirect chain
- parser_html.py       # title/meta/headings/text/images/links
- parser_schema.py     # JSON-LD schema types extraction
- pagespeed_client.py  # PageSpeed Insights API client
- gsc_client.py        # Search Console API client
- intent_classifier.py # intent coverage + query intent
- comparator.py        # diff official vs competitors
- rule_engine.py       # scoring, main_cause, todo generation
- ai_reporter.py       # prompt build + LLM call + markdown validation
- storage.py           # DB access + file (json/md) persistence
"""

from datetime import datetime
from typing import List, Dict, Any

def run_analysis_job(job_id: str) -> Dict[str, Any]:
    """
    Entry point for background job.
    Loads job config from DB: target urls (official + competitors + third-party pages).
    Produces analysis_result.json, stores it, optionally triggers AI report generation.
    """
    cfg = load_thresholds("config/thresholds.yml")
    job = db_get_job(job_id)

    # 1) Analyze each page independently
    pages = []
    for page in job.pages:  # list of {page_id,url,page_type}
        pages.append(analyze_single_page(page, cfg, job))

    # 2) Build comparisons (official vs competitors / official vs third-party)
    comparisons = build_comparisons(pages, cfg, job)

    # 3) Run rule engine (scores, cause, todos)
    diagnosis, todos = run_rule_engine(pages, comparisons, cfg, job)

    # 4) Build AI prompt payload
    ai_payload = build_ai_prompt_payload(pages, comparisons, diagnosis, todos, cfg, job)

    # 5) Assemble final analysis_result object
    result = {
        "schema_version": cfg["app"]["schema_version"],
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "run_id": job_id,
        "inputs": build_inputs(job, cfg),
        "pages": pages,
        "comparisons": comparisons,
        "diagnosis": diagnosis,
        "todos": todos,
        "ai_prompt_payload": ai_payload
    }

    # 6) Persist JSON
    storage_save_analysis_result(job_id, result)  # DB + object storage/file

    # 7) Generate report.md via AI (optional but MVP includes)
    if job.enable_ai_report:
        report_md = generate_report_md(ai_payload, cfg)
        storage_save_report(job_id, report_md)

    # 8) Update job status
    db_mark_job_done(job_id, success=True)
    return result


def analyze_single_page(page: Dict[str, Any], cfg: Dict[str, Any], job: Any) -> Dict[str, Any]:
    """
    Fetch + parse + enrich (pagespeed, gsc if official) + intent coverage.
    """
    fetch = http_fetch(page["url"], user_agent=job.user_agent)

    html_doc = parse_html(fetch.html)
    schema = extract_structured_data(fetch.html)

    # Minimal mobile-friendly hint heuristic
    mobile_hint = compute_mobile_hint(fetch.html, cfg)

    # PageSpeed optional
    pagespeed = {"available": False, "performance_score": None, "lcp_ms": None, "inp_ms": None, "cls": None}
    if job.enable_pagespeed:
        pagespeed = pagespeed_fetch(page["url"], device=job.device)

    # Search Console only for official_homepage pages (and only if configured)
    gsc = {"available": False, "time_window_days": None, "top_queries": [], "brand_query_summary": {}}
    if page["page_type"] == "official_homepage" and job.enable_gsc:
        gsc = gsc_fetch_url_metrics(
            site_property=job.gsc_property,
            url=fetch.final_url,
            days=cfg["app"]["time_windows_days"]["long"],
            max_queries=cfg["app"]["max_queries_per_url"]
        )
        # Query intent classification (brand/info/compare/price/visit/unknown)
        gsc["top_queries"] = classify_query_intents(gsc["top_queries"], brand_terms=job.brand_terms)

    # Intent coverage by page type (official vs third party)
    content = compute_intent_coverage(
        page_type=page["page_type"],
        title=html_doc["title"],
        h2=html_doc["headings"]["h2"],
        text=html_doc.get("text", ""),
        links=html_doc.get("links", {}),
        cfg=cfg,
        brand_terms=job.brand_terms
    )

    return {
        "page_id": page["page_id"],
        "url": page["url"],
        "page_type": page["page_type"],
        "fetch": {
            "status_code": fetch.status_code,
            "final_url": fetch.final_url,
            "redirect_chain": fetch.redirect_chain
        },
        "html": {
            "title": html_doc["title"],
            "meta_description": html_doc.get("meta_description", ""),
            "canonical": html_doc.get("canonical", ""),
            "robots_meta": html_doc.get("robots_meta", ""),
            "headings": html_doc["headings"],
            "text_stats": html_doc.get("text_stats", {}),
            "links": html_doc.get("links", {}),
            "images": html_doc.get("images", {}),
            "structured_data": schema
        },
        "tech": {
            "mobile_friendly_hint": mobile_hint,
            "pagespeed": pagespeed
        },
        "content": content,
        "serp": build_serp_snapshot_if_enabled(page, job, cfg),
        "search_console": gsc
    }


def build_comparisons(pages: List[Dict[str, Any]], cfg: Dict[str, Any], job: Any) -> List[Dict[str, Any]]:
    """
    Create diff objects:
    - official_vs_competitor for each competitor
    - official_vs_third_party for each third_party_profile_page (optional)
    """
    official = find_page(pages, page_type="official_homepage")
    competitors = [p for p in pages if p["page_type"] == "competitor_page"]
    third_parties = [p for p in pages if p["page_type"] == "third_party_profile_page"]

    comparisons = []
    for comp in competitors:
        comparisons.append(diff_pages(official, comp, kind="official_vs_competitor", cfg=cfg))
    for tp in third_parties:
        comparisons.append(diff_pages(official, tp, kind="official_vs_third_party", cfg=cfg))

    return comparisons


def diff_pages(source: Dict[str, Any], target: Dict[str, Any], kind: str, cfg: Dict[str, Any]) -> Dict[str, Any]:
    """
    Core diff used for both competitor and third-party.
    """
    h2_delta = len(source["html"]["headings"]["h2"]) - len(target["html"]["headings"]["h2"])
    missing_intent_items = compute_missing_intent_items(source["content"]["intent_coverage"], target["content"]["intent_coverage"])
    faq_delta = int(source["html"]["structured_data"].get("has_faq_schema", False)) - int(target["html"]["structured_data"].get("has_faq_schema", False))

    ps_source = source["tech"]["pagespeed"].get("performance_score")
    ps_target = target["tech"]["pagespeed"].get("performance_score")
    ps_delta = None if (ps_source is None or ps_target is None) else (ps_source - ps_target)

    return {
        "comparison_id": new_id(),
        "kind": kind,
        "source_page_id": source["page_id"],
        "target_page_id": target["page_id"],
        "diff": {
            "structure": {
                "h2_count_delta": h2_delta,
                "missing_intent_items": missing_intent_items,
                "faq_schema_delta": faq_delta
            },
            "tech": {
                "performance_score_delta": ps_delta,
                "mobile_hint_delta": f'{source["tech"]["mobile_friendly_hint"]}->{target["tech"]["mobile_friendly_hint"]}'
            },
            "serp": {
                "title_pattern_notes": extract_title_pattern_notes(source, target),
                "snippet_pattern_notes": extract_snippet_pattern_notes(source, target)
            }
        }
    }


def run_rule_engine(pages, comparisons, cfg, job):
    """
    Produces:
    - scores (A/B/C/D)
    - cause_breakdown (content/ctr/technical %)
    - main_cause (content_quality/ctr/technical/mixed)
    - todos list (<= 15)
    """
    official = find_page(pages, "official_homepage")

    scores = compute_scores(pages, cfg)
    cause = compute_main_cause(official, comparisons, scores, cfg)
    evidence = build_evidence(official, comparisons, scores, cause, cfg)

    diagnosis = {
        "main_cause": cause["main_cause"],
        "cause_breakdown": cause["breakdown"],
        "scores": scores,
        "evidence": evidence
    }

    todos = generate_todos(pages, comparisons, diagnosis, cfg, job)
    todos = enforce_todo_limits(todos, cfg)

    return diagnosis, todos


def build_ai_prompt_payload(pages, comparisons, diagnosis, todos, cfg, job):
    """
    Produce compact payload for AI report generation.
    """
    summary = build_summary_text(diagnosis, todos)
    slim_pages = slim_pages_for_ai(pages, cfg)
    slim_comparisons = slim_comparisons_for_ai(comparisons)
    slim_todos = slim_todos_for_ai(todos, cfg)

    return {
        "report_language": cfg["ai"]["language"],
        "report_style": cfg["ai"]["report_style"],
        "constraints": {
            "must_cite_evidence": cfg["ai"]["must_cite_evidence"],
            "no_guessing": cfg["ai"]["no_guessing"],
            "max_todos_per_priority": cfg["app"]["max_todos_per_priority"]
        },
        "data": {
            "summary": summary,
            "pages": slim_pages,
            "comparisons": slim_comparisons,
            "diagnosis": diagnosis,
            "todos": slim_todos
        }
    }


def generate_report_md(ai_payload, cfg):
    """
    Call LLM with prompt template; validate markdown headings; fallback if invalid.
    """
    prompt = build_prompt_from_template(ai_payload)
    md = llm_call(prompt)

    if not validate_report_markdown(md):
        md = llm_call(build_repair_prompt(ai_payload, md))

    return md
```

---

## Appendix C — db_schema.sql（MVPテーブル）

> 目的: URL登録、実行ジョブ、ページ解析結果(JSON)、AIレポート(MD)を保存し、後から履歴が見られる。
> DB: PostgreSQL想定（JSONBを活用）

```sql
BEGIN;

-- 1) Sites (プロジェクト単位: 例「日本社会人演劇チームSEO」)
CREATE TABLE IF NOT EXISTS sites (
  site_id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name               TEXT NOT NULL,
  owner_user_id      UUID NULL,
  created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 2) Pages (分析対象URL: 公式/競合/紹介記事)
CREATE TABLE IF NOT EXISTS pages (
  page_id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  site_id            UUID NOT NULL REFERENCES sites(site_id) ON DELETE CASCADE,
  url                TEXT NOT NULL,
  page_type          TEXT NOT NULL CHECK (page_type IN ('official_homepage', 'competitor_page', 'third_party_profile_page')),
  label              TEXT NULL,              -- 任意: "公式トップ", "競合A", "紹介記事(掲載元X)"
  created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(site_id, url)
);

-- 3) Analysis Jobs (1回の実行単位)
CREATE TABLE IF NOT EXISTS analysis_jobs (
  job_id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  site_id            UUID NOT NULL REFERENCES sites(site_id) ON DELETE CASCADE,

  -- 実行パラメータ
  device             TEXT NOT NULL DEFAULT 'mobile' CHECK (device IN ('mobile','desktop')),
  locale             TEXT NOT NULL DEFAULT 'ja-JP',
  target_country     TEXT NOT NULL DEFAULT 'JP',
  enable_pagespeed   BOOLEAN NOT NULL DEFAULT TRUE,
  enable_gsc         BOOLEAN NOT NULL DEFAULT FALSE,
  enable_ai_report   BOOLEAN NOT NULL DEFAULT TRUE,

  -- Search Console property等（必要に応じて）
  gsc_property       TEXT NULL,
  brand_terms        TEXT[] NULL,

  status             TEXT NOT NULL DEFAULT 'queued' CHECK (status IN ('queued','running','done','failed')),
  error_message      TEXT NULL,

  created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
  started_at         TIMESTAMPTZ NULL,
  finished_at        TIMESTAMPTZ NULL
);

-- 4) Job Targets (ジョブごとの対象ページ: 公式1 + 競合2 +（任意で紹介記事…）)
CREATE TABLE IF NOT EXISTS analysis_job_targets (
  job_id             UUID NOT NULL REFERENCES analysis_jobs(job_id) ON DELETE CASCADE,
  page_id            UUID NOT NULL REFERENCES pages(page_id) ON DELETE CASCADE,
  role               TEXT NOT NULL CHECK (role IN ('official','competitor','third_party')),
  sort_order         INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (job_id, page_id)
);

-- 5) Analysis Results (analysis_result.json本体)
CREATE TABLE IF NOT EXISTS analysis_results (
  result_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id             UUID NOT NULL REFERENCES analysis_jobs(job_id) ON DELETE CASCADE,
  site_id            UUID NOT NULL REFERENCES sites(site_id) ON DELETE CASCADE,

  schema_version     TEXT NOT NULL,
  generated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),

  analysis_json       JSONB NOT NULL,          -- analysis_result.json相当
  diagnosis_main_cause TEXT NULL,              -- クエリ用に冗長保存（任意）
  created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_analysis_results_site_time
  ON analysis_results(site_id, generated_at DESC);

CREATE INDEX IF NOT EXISTS idx_analysis_results_json_gin
  ON analysis_results USING GIN (analysis_json);

-- 6) AI Reports (report.md)
CREATE TABLE IF NOT EXISTS ai_reports (
  report_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  result_id          UUID NOT NULL REFERENCES analysis_results(result_id) ON DELETE CASCADE,
  job_id             UUID NOT NULL REFERENCES analysis_jobs(job_id) ON DELETE CASCADE,

  report_markdown    TEXT NOT NULL,
  model_name         TEXT NULL,
  prompt_version     TEXT NULL,

  created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 7) Daily Metrics（将来: 日次のGSC結果や順位を蓄積するための器。MVPではoptional）
CREATE TABLE IF NOT EXISTS daily_metrics (
  metric_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  page_id            UUID NOT NULL REFERENCES pages(page_id) ON DELETE CASCADE,
  date              DATE NOT NULL,

  source             TEXT NOT NULL DEFAULT 'gsc' CHECK (source IN ('gsc','serp','manual')),
  metrics_json       JSONB NOT NULL,   -- impressions/clicks/ctr/positionなど

  created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(page_id, date, source)
);

COMMIT;
```

---

## Appendix D — 最小の運用設計（コーディングエージェント向け）

### バッチ実行
- `analysis_jobs` を `queued` で作成 → workerが拾って `running` → `analysis_results` 作成 → `ai_reports` 作成 → `done`

### Web UI
- Site作成 → Pages登録（公式/競合/紹介記事）→ "解析実行"ボタンで job作成
- 最新の `analysis_results` と `ai_reports` を表示

### 将来拡張
- `daily_metrics` を毎日更新し、時系列（7/28/90日）での改善検証を可能にする

---

## 次のステップ（必要なら追記）
コーディングエージェントがそのまま着手できるように:
- FastAPIのエンドポイント設計（routes）
- フロントの画面コンポーネント（URL登録〜レポート表示）
まで追記可能。
