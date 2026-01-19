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

## Appendix E — FastAPI Routes Design (MVP)

> Base URL: `/api/v1`
> Auth (MVP): optional (token-based). If skipping auth, keep user_id nullable.

### 0. Conventions
- All responses JSON
- IDs are UUID strings
- Pagination: `{items:[], next_cursor?:string}` (MVP can omit)
- Job processing: async worker updates status (queued/running/done/failed)

### 1. Health

```
GET /health
```
Response:
```json
{"status":"ok", "time":"..."}
```

---

### 2. Sites

```
POST /sites
```
Create a project/site.

Request:
```json
{
  "name": "日本社会人演劇チームSEO"
}
```

Response:
```json
{
  "site_id": "...",
  "name": "...",
  "created_at": "..."
}
```

```
GET /sites
```
Response:
```json
{ "items": [ { "site_id":"...", "name":"...", "created_at":"..." } ] }
```

```
GET /sites/{site_id}
```
Response:
```json
{ "site_id":"...", "name":"...", "created_at":"..." }
```

---

### 3. Pages (URLs)

```
POST /sites/{site_id}/pages
```
Register URL with page_type.

Request:
```json
{
  "url": "https://example.com",
  "page_type": "official_homepage|competitor_page|third_party_profile_page",
  "label": "公式トップ"
}
```

Response:
```json
{
  "page_id":"...",
  "site_id":"...",
  "url":"...",
  "page_type":"...",
  "label":"...",
  "created_at":"..."
}
```

```
GET /sites/{site_id}/pages
```
Response:
```json
{
  "items": [
    {"page_id":"...","url":"...","page_type":"...","label":"...","created_at":"..."}
  ]
}
```

```
PATCH /sites/{site_id}/pages/{page_id}
```
Request (partial):
```json
{
  "label": "競合A",
  "page_type": "competitor_page"
}
```
Response: updated page object

```
DELETE /sites/{site_id}/pages/{page_id}
```
Response:
```json
{ "deleted": true }
```

---

### 4. Analysis Jobs

```
POST /sites/{site_id}/analysis-jobs
```
Create an analysis run for selected pages.

Request:
```json
{
  "device": "mobile|desktop",
  "locale": "ja-JP",
  "target_country": "JP",
  "enable_pagespeed": true,
  "enable_gsc": false,
  "enable_ai_report": true,

  "gsc_property": "sc-domain:example.com",
  "brand_terms": ["劇団名","日本社会人演劇"],

  "targets": [
    {"page_id":"...", "role":"official", "sort_order":0},
    {"page_id":"...", "role":"competitor", "sort_order":1},
    {"page_id":"...", "role":"competitor", "sort_order":2},
    {"page_id":"...", "role":"third_party", "sort_order":3}
  ]
}
```

Response:
```json
{
  "job_id":"...",
  "status":"queued",
  "created_at":"..."
}
```

```
GET /sites/{site_id}/analysis-jobs
```
Response:
```json
{
  "items":[
    {"job_id":"...","status":"done","created_at":"...","finished_at":"..."}
  ]
}
```

```
GET /sites/{site_id}/analysis-jobs/{job_id}
```
Response:
```json
{
  "job_id":"...",
  "status":"queued|running|done|failed",
  "error_message": null,
  "created_at":"...",
  "started_at": "...",
  "finished_at":"...",
  "targets":[{"page_id":"...","role":"official","sort_order":0}, ...]
}
```

```
POST /sites/{site_id}/analysis-jobs/{job_id}/run
```
Optional: trigger execution if jobs are created without auto-run.

Response:
```json
{ "ok": true }
```

---

### 5. Results & Reports

```
GET /sites/{site_id}/analysis-results?limit=20
```
Response:
```json
{
  "items":[
    {
      "result_id":"...",
      "job_id":"...",
      "generated_at":"...",
      "diagnosis_main_cause":"content_quality"
    }
  ]
}
```

```
GET /sites/{site_id}/analysis-results/{result_id}
```
Response:
```json
{
  "result_id":"...",
  "job_id":"...",
  "generated_at":"...",
  "analysis_json": { ...analysis_result.json... }
}
```

```
GET /sites/{site_id}/analysis-results/{result_id}/report
```
Response:
```json
{
  "result_id":"...",
  "report_markdown":"# SEO診断レポート\n..."
}
```

```
POST /sites/{site_id}/analysis-results/{result_id}/report/regenerate
```
Re-run AI report generation with same ai_prompt_payload.

Request (optional):
```json
{
  "report_style": "consultant|concise|technical"
}
```

Response:
```json
{ "ok": true, "report_id":"..." }
```

---

### 6. UX Helpers (Optional but recommended)

```
GET /sites/{site_id}/recommended-targets
```
Auto-pick best 1 official + 2 competitors if user has many pages registered.

Response:
```json
{
  "targets":[{"page_id":"...","role":"official"}, ...]
}
```

```
GET /sites/{site_id}/presets
```
Return UI presets (themes, report styles).

Response:
```json
{
  "themes": ["midnight-neon","graphite","light-minimal"],
  "report_styles": ["consultant","concise","technical"]
}
```

---

## Appendix F — Frontend UI Component Spec (Next.js App Router / TypeScript)

### 0. UI Direction (カッコいい / 洗練 / "男の子が喜ぶ")

**Theme: "Midnight Neon"**
- Base: deep navy/graphite
- Accent: electric cyan + violet (控えめに)
- Surfaces: glassmorphism (blur + subtle border)
- Motion: fast, snappy, but上品（hoverで僅かに発光/浮く）
- Typography: bold headings + clean mono for metrics
- Data viz: line chart for trends, badge chips for scores

**Recommended stack:**
- Next.js + Tailwind CSS
- UI: shadcn/ui (Radix基盤) + lucide icons
- Chart: recharts (or nivo) — minimal aesthetic
- Markdown: react-markdown + remark-gfm

---

### 1. Pages (Routes)

#### 1.1 `/` (Dashboard)

**Purpose:** 最新解析結果のハイライト + "Run Analysis" CTA

**Components:**
- `<TopNav />`
- `<SiteSwitcher />`
- `<HeroRunCard />` (cool CTA)
- `<LatestResultCard />` (main cause, scores, P0 todo count)
- `<RecentRunsTable />`
- `<QuickActions />` (Add URL / Run analysis)

**Data:**
- GET /sites
- GET /sites/{site_id}/analysis-results
- GET /sites/{site_id}/analysis-jobs

---

#### 1.2 `/sites/[siteId]/pages` (URL管理)

**Purpose:** 公式/競合/紹介記事の登録と整理

**Components:**
- `<TopNav />`
- `<PageTypeTabs />` (Official / Competitors / Third-party)
- `<UrlAddModal />`
- `<PagesTable />` (label, url, type, actions)
- `<SelectionTray />` (official1 + competitor2 + thirdParty optional)

**UX:**
- 公式は1つ選択必須（radio）
- 競合は最大2つ（checkbox）
- 紹介記事は任意（checkbox）

**Data:**
- GET /sites/{siteId}/pages
- POST /sites/{siteId}/pages
- PATCH /sites/{siteId}/pages/{pageId}
- DELETE /sites/{siteId}/pages/{pageId}

---

#### 1.3 `/sites/[siteId]/run` (実行設定)

**Purpose:** デバイス/期間/AIレポートを設定して実行

**Components:**
- `<RunConfigCard />`
  - device toggle (Mobile/Desktop)
  - enable pagespeed toggle
  - enable gsc toggle (if enabled show property input)
  - brand terms input chips
  - report style select (consultant/concise/technical)
- `<TargetSummaryCard />` (選択済みURL)
- `<RunButton />` (primary, animated)
- `<RunProgressToast />`

**Data:**
- POST /sites/{siteId}/analysis-jobs
- GET /sites/{siteId}/analysis-jobs/{jobId} (polling)

---

#### 1.4 `/sites/[siteId]/results/[resultId]` (結果ビュー)

**Purpose:** "コンサル級"に見せるメイン画面

**Layout:** 2-column (left: navigation, right: content)

**Components:**
- `<ResultHeader />`
  - main cause badge (Content/CTR/Tech)
  - scores chips (A/B/C/D)
  - generated_at
  - actions: Download JSON / Regenerate report
- `<InsightSummary />`
  - Top 3 conclusions (from report or derived)
- `<TodoBoard />`
  - P0/P1/P2 columns
  - each card shows impact/effort + evidence tooltip
- `<CompetitorDiffPanel />`
  - diff table (h2 count, FAQ schema, pagespeed)
  - "missing intent items" chips
- `<ReportMarkdown />` (AI report)
- `<EvidenceDrawer />` (click to see evidence strings)
- `<JsonViewerModal />`

**Data:**
- GET /sites/{siteId}/analysis-results/{resultId}
- GET /sites/{siteId}/analysis-results/{resultId}/report
- POST /sites/{siteId}/analysis-results/{resultId}/report/regenerate

---

### 2. Shared UI Components

#### 2.1 Navigation
- `<TopNav />` brand mark + site switcher + theme toggle
- `<SideRail />` icons only (Dashboard, Pages, Run, Results)

#### 2.2 Cards
- `<GlassCard />` (base container)
- `<MetricChip />` (mono font, subtle border glow)
- `<ScoreBadge />` (A/B/C/D)

#### 2.3 Forms
- `<UrlAddModal />`
  - URL input with validation
  - page_type select (Official/Competitor/Third-party)
  - label optional
- `<BrandTermsChipsInput />`

#### 2.4 Data display
- `<DiffTable />`
- `<TodoCard />`
- `<MarkdownRenderer />`

---

### 3. UI Copy (tone)

Short, punchy, techy:
- "RUN DIAGNOSTIC"
- "PRIORITY FIXES (P0)"
- "WHY THIS MATTERS"
- "EVIDENCE"

Japanese text in body, but section headers can be EN/JP mix for coolness:
- "INSIGHTS / 要点"
- "TODO / 対策"
- "DIFF / 競合差分"

---

### 4. "かっこいい" Theme Tokens (Tailwind example)

> Colors are conceptual; actual values decided in CSS variables

```css
:root {
  --bg: #0B1020;
  --panel: rgba(255,255,255,0.06);
  --border: rgba(255,255,255,0.10);
  --text: rgba(255,255,255,0.92);
  --muted: rgba(255,255,255,0.70);
  --accent-cyan: #35D4FF;
  --accent-violet: #A78BFA;
}
```

**Effects:**
- Backdrop blur: 12px
- Border: 1px solid var(--border)
- Glow on hover: `box-shadow: 0 0 0 1px rgba(accent,0.3), 0 0 24px rgba(accent,0.25)`

---

### 5. Minimal Screen Acceptance Criteria (MVP)

- URL登録・選択ができる（公式1 + 競合2 + 紹介記事任意）
- 実行 → ジョブ進行状況が見える（queued/running/done）
- 結果画面で以下が見える
  - main_cause / scores
  - P0/P1/P2 ToDoカード（最大15）
  - 競合差分（h2/FAQ/pagespeed）
  - AIレポート（Markdown）
  - JSONダウンロード

---

### 6. "カッコよくする"ための実装上のコツ

- **余白をしっかり**（詰め込まない）
- **ToDoは カード＋優先度カラム**（Trelloっぽく、でも上品に）
- **スコアは チップ（A/B/C/D）**で瞬時に理解
- **"根拠"は常時表示せず ツールチップ/ドロワーで見せる**（玄人感）

---

## Appendix G — Next.js Screen Wireframes + TS Props + API Client

### 0. Font & Readability Spec（視認性＋デザイン）

#### Font Pairing（推奨）
- **Body (JP):** `"Noto Sans JP"` or `"Zen Kaku Gothic New"`（読みやすい・現代的）
- **Numbers/Code:** `"JetBrains Mono"`（メトリクスが締まって見える）

#### Typography rules
- Base font-size: 16px
- Headings: 600–700 weight
- Body: 400–500 weight
- Line height:
  - Body: 1.7（日本語は気持ち広め）
  - Headings: 1.2–1.3
- Metric chips: mono + 12–13px（詰まりすぎない）

#### Color/Contrast rules (dark theme)
- Main text: opacity 0.92
- Muted text: opacity 0.70
- Borders: opacity 0.10
- Ensure WCAG-ish: text vs bg contrast >= 4.5 recommended

---

### 1. Folder Structure (Next.js App Router)

```
app/
  layout.tsx
  page.tsx                         # Dashboard (default site)
  sites/[siteId]/
    layout.tsx                     # Site-scoped layout with SideRail
    pages/
      page.tsx                     # URL management
    run/
      page.tsx                     # Run config + trigger
    results/
      page.tsx                     # Results list
      [resultId]/
        page.tsx                   # Result details (main)
components/
  ui/                              # shadcn/ui wrappers
  layout/
    TopNav.tsx
    SideRail.tsx
    GlassCard.tsx
  sites/
    SiteSwitcher.tsx
  pages/
    PageTypeTabs.tsx
    PagesTable.tsx
    UrlAddModal.tsx
    SelectionTray.tsx
  run/
    RunConfigCard.tsx
    TargetSummaryCard.tsx
    RunButton.tsx
    JobStatusBanner.tsx
  results/
    ResultHeader.tsx
    InsightSummary.tsx
    TodoBoard.tsx
    TodoCard.tsx
    CompetitorDiffPanel.tsx
    ReportMarkdown.tsx
    EvidenceDrawer.tsx
    JsonViewerModal.tsx
lib/
  api/
    client.ts                      # fetch wrapper
    routes.ts                      # endpoint builders
    types.ts                       # shared TS types
    queries.ts                     # typed API calls
  utils/
    cn.ts
    format.ts
styles/
  globals.css
```

---

### 2. Screen Wireframes（Layout骨組み）

#### 2.1 `app/layout.tsx`
- Global providers (theme, toasts)
- Loads fonts
- Body uses Body font, metrics components use mono class

**Wireframe:**
```
<html>
  <body class="bg">
    <TopNav global />
    <main>{children}</main>
```

#### 2.2 `app/page.tsx` (Dashboard)

**Goal:** "Run Diagnostic" + latest results highlight

**Wireframe:**
- Top section: Hero
  - Title: "SEO DIAGNOSTIC"
  - Subtitle JP: "公式HP + 競合2URLの差分から、次の一手を提示"
  - Primary CTA: "RUN DIAGNOSTIC" -> /sites/[siteId]/run
  - Secondary CTA: "ADD URL" -> /sites/[siteId]/pages
- Grid:
  - `<LatestResultCard />`
  - `<QuickStatsCard />` (P0 count / main cause)
  - `<RecentRunsTable />`

**Data needs:**
- sites list (choose default)
- analysis-results latest (limit=10)

#### 2.3 `app/sites/[siteId]/layout.tsx`

**Wireframe:**
```
<div class="grid grid-cols-[72px_1fr]">
  <SideRail />
  <div class="p-6">
    {children}
  </div>
</div>
```

#### 2.4 `app/sites/[siteId]/pages/page.tsx` (URL管理)

**Wireframe:**
- Header row:
  - Title: "URL BASE"
  - Right: `<UrlAddModalTrigger />`
- `<PageTypeTabs />` (Official / Competitors / Third-party)
- `<PagesTable />` filtered by tab
- Bottom sticky: `<SelectionTray />`
  - Official (radio) 1
  - Competitors (checkbox) up to 2
  - Third-party (checkbox) optional
  - CTA: "CONTINUE" -> /sites/[siteId]/run

#### 2.5 `app/sites/[siteId]/run/page.tsx` (実行設定)

**Wireframe:**
- Title: "RUN CONFIG"
- Two-column:
  - Left:
    - `<RunConfigCard />` (device toggles, pagespeed, gsc, brand terms, report style)
    - `<RunButton />`
    - `<JobStatusBanner />` (after start)
  - Right:
    - `<TargetSummaryCard />` (selected URLs)
    - Help tips card (what data is collected)

**Flow:**
- POST analysis-job
- Poll GET job status
- On done: navigate to latest result detail

#### 2.6 `app/sites/[siteId]/results/page.tsx` (結果一覧)

**Wireframe:**
- Title: "RESULTS"
- `<ResultsTable />`
  - row: generated_at, main_cause badge, link to detail

#### 2.7 `app/sites/[siteId]/results/[resultId]/page.tsx` (結果詳細)

**Wireframe (main):**
- `<ResultHeader />`
- 3-column responsive grid:
  - Left column (desktop):
    - `<InsightSummary />` (Top 3)
    - `<CompetitorDiffPanel />`
  - Middle (main):
    - `<TodoBoard />` (P0/P1/P2 columns)
  - Right column:
    - `<ReportMarkdown />`
- Floating actions:
  - Download JSON
  - Open Evidence Drawer
  - Regenerate report

---

### 3. TypeScript Types & Props Interfaces

#### 3.1 Shared domain types (`lib/api/types.ts`)

```typescript
export type UUID = string;

export type PageType = "official_homepage" | "competitor_page" | "third_party_profile_page";
export type DeviceType = "mobile" | "desktop";

export type JobStatus = "queued" | "running" | "done" | "failed";

export type MainCause = "content_quality" | "ctr" | "technical" | "mixed" | "unknown";
export type ScoreGrade = "A" | "B" | "C" | "D";

export type TodoPriority = "P0" | "P1" | "P2";
export type TodoCategory = "content" | "technical" | "ctr" | "outreach" | "internal_linking";

export interface Site {
  site_id: UUID;
  name: string;
  created_at: string;
}

export interface Page {
  page_id: UUID;
  site_id: UUID;
  url: string;
  page_type: PageType;
  label?: string | null;
  created_at: string;
}

export interface AnalysisJobTarget {
  page_id: UUID;
  role: "official" | "competitor" | "third_party";
  sort_order: number;
}

export interface AnalysisJob {
  job_id: UUID;
  site_id: UUID;
  status: JobStatus;
  error_message?: string | null;
  created_at: string;
  started_at?: string | null;
  finished_at?: string | null;
  targets: AnalysisJobTarget[];
}

export interface Diagnosis {
  main_cause: MainCause;
  cause_breakdown: { content_quality: number; ctr: number; technical: number };
  scores: { content: ScoreGrade; technical: ScoreGrade; ctr: ScoreGrade };
  evidence: { claim: string; support: string[] }[];
}

export interface Todo {
  todo_id: UUID;
  priority: TodoPriority;
  category: TodoCategory;
  title: string;
  details: string;
  evidence: string[];
  impact: "high" | "medium" | "low";
  effort: "small" | "medium" | "large";
  examples?: {
    title_variants?: string[];
    meta_description_variants?: string[];
    h2_outline?: string[];
    faq_questions?: string[];
    outreach_message_draft_jp?: string;
  };
}

export interface AnalysisResultListItem {
  result_id: UUID;
  job_id: UUID;
  generated_at: string;
  diagnosis_main_cause?: MainCause | null;
}

export interface AnalysisResult {
  result_id: UUID;
  job_id: UUID;
  generated_at: string;
  analysis_json: any; // keep raw for now; optional: strongly type later
}

export interface Report {
  result_id: UUID;
  report_markdown: string;
}
```

#### 3.2 UI Component Props (`components/*`)

```typescript
// layout
export interface TopNavProps {
  title?: string;
  rightSlot?: React.ReactNode;
}

export interface SideRailProps {
  siteId: UUID;
  active: "dashboard" | "pages" | "run" | "results";
}

// pages
export interface PageTypeTabsProps {
  value: "official" | "competitor" | "third_party";
  onChange: (v: PageTypeTabsProps["value"]) => void;
}

export interface PagesTableProps {
  pages: Page[];
  selectedIds: Set<UUID>;
  selectionMode: "single" | "multi";
  maxSelect?: number;
  onToggle: (pageId: UUID) => void;
  onEdit: (pageId: UUID) => void;
  onDelete: (pageId: UUID) => void;
}

export interface UrlAddModalProps {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  onSubmit: (input: { url: string; page_type: PageType; label?: string }) => Promise<void>;
}

export interface SelectionTrayProps {
  official?: Page | null;
  competitors: Page[];
  thirdParties: Page[];
  canContinue: boolean;
  onContinue: () => void;
}

// run
export interface RunConfigCardProps {
  device: DeviceType;
  onDeviceChange: (v: DeviceType) => void;

  enablePagespeed: boolean;
  onEnablePagespeed: (v: boolean) => void;

  enableGsc: boolean;
  onEnableGsc: (v: boolean) => void;
  gscProperty?: string;
  onGscProperty: (v: string) => void;

  brandTerms: string[];
  onBrandTerms: (terms: string[]) => void;

  reportStyle: "consultant" | "concise" | "technical";
  onReportStyle: (v: RunConfigCardProps["reportStyle"]) => void;
}

export interface TargetSummaryCardProps {
  official: Page;
  competitors: Page[];
  thirdParties: Page[];
}

export interface RunButtonProps {
  disabled: boolean;
  onClick: () => Promise<void>;
  loading?: boolean;
}

export interface JobStatusBannerProps {
  job?: AnalysisJob | null;
  onViewResult?: () => void;
}

// results
export interface ResultHeaderProps {
  generatedAt: string;
  mainCause: MainCause;
  scores: Diagnosis["scores"];
  onDownloadJson: () => void;
  onRegenerateReport: () => Promise<void>;
  onOpenEvidence: () => void;
}

export interface InsightSummaryProps {
  diagnosis: Diagnosis;
  todos: Todo[];
}

export interface TodoBoardProps {
  todos: Todo[];
  onSelectTodo?: (todo: Todo) => void;
}

export interface TodoCardProps {
  todo: Todo;
  onClick?: () => void;
}

export interface CompetitorDiffPanelProps {
  analysisJson: any; // can type later: comparisons
}

export interface ReportMarkdownProps {
  markdown: string;
}

export interface EvidenceDrawerProps {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  evidence: Diagnosis["evidence"];
}

export interface JsonViewerModalProps {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  json: any;
}
```

---

### 4. API Client (fetch wrappers)

#### 4.1 Base fetch client (`lib/api/client.ts`)

```typescript
export class ApiError extends Error {
  status: number;
  payload?: any;
  constructor(message: string, status: number, payload?: any) {
    super(message);
    this.status = status;
    this.payload = payload;
  }
}

type FetchOptions = Omit<RequestInit, "body"> & { body?: any };

export async function apiFetch<T>(path: string, options: FetchOptions = {}): Promise<T> {
  const res = await fetch(`/api/v1${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {})
    },
    body: options.body ? JSON.stringify(options.body) : undefined
  });

  const contentType = res.headers.get("content-type") || "";
  const payload = contentType.includes("application/json") ? await res.json() : await res.text();

  if (!res.ok) {
    throw new ApiError(`API Error: ${res.status}`, res.status, payload);
  }
  return payload as T;
}
```

#### 4.2 Route builders (`lib/api/routes.ts`)

```typescript
import type { UUID } from "./types";

export const routes = {
  health: () => `/health`,

  sites: () => `/sites`,
  site: (siteId: UUID) => `/sites/${siteId}`,

  pages: (siteId: UUID) => `/sites/${siteId}/pages`,
  page: (siteId: UUID, pageId: UUID) => `/sites/${siteId}/pages/${pageId}`,

  jobs: (siteId: UUID) => `/sites/${siteId}/analysis-jobs`,
  job: (siteId: UUID, jobId: UUID) => `/sites/${siteId}/analysis-jobs/${jobId}`,
  runJob: (siteId: UUID, jobId: UUID) => `/sites/${siteId}/analysis-jobs/${jobId}/run`,

  results: (siteId: UUID) => `/sites/${siteId}/analysis-results`,
  result: (siteId: UUID, resultId: UUID) => `/sites/${siteId}/analysis-results/${resultId}`,
  report: (siteId: UUID, resultId: UUID) => `/sites/${siteId}/analysis-results/${resultId}/report`,
  regenReport: (siteId: UUID, resultId: UUID) => `/sites/${siteId}/analysis-results/${resultId}/report/regenerate`
};
```

#### 4.3 Typed API calls (`lib/api/queries.ts`)

```typescript
import { apiFetch } from "./client";
import { routes } from "./routes";
import type {
  Site, Page, UUID, DeviceType, AnalysisJob, AnalysisJobTarget,
  AnalysisResultListItem, AnalysisResult, Report
} from "./types";

export async function listSites(): Promise<{ items: Site[] }> {
  return apiFetch(routes.sites());
}
export async function createSite(input: { name: string }): Promise<Site> {
  return apiFetch(routes.sites(), { method: "POST", body: input });
}

export async function listPages(siteId: UUID): Promise<{ items: Page[] }> {
  return apiFetch(routes.pages(siteId));
}
export async function createPage(siteId: UUID, input: { url: string; page_type: Page["page_type"]; label?: string }): Promise<Page> {
  return apiFetch(routes.pages(siteId), { method: "POST", body: input });
}
export async function updatePage(siteId: UUID, pageId: UUID, input: Partial<{ label: string; page_type: Page["page_type"] }>): Promise<Page> {
  return apiFetch(routes.page(siteId, pageId), { method: "PATCH", body: input });
}
export async function deletePage(siteId: UUID, pageId: UUID): Promise<{ deleted: boolean }> {
  return apiFetch(routes.page(siteId, pageId), { method: "DELETE" });
}

export async function createAnalysisJob(siteId: UUID, input: {
  device: DeviceType;
  locale: string;
  target_country: string;
  enable_pagespeed: boolean;
  enable_gsc: boolean;
  enable_ai_report: boolean;
  gsc_property?: string;
  brand_terms?: string[];
  targets: AnalysisJobTarget[];
}): Promise<{ job_id: UUID; status: string; created_at: string }> {
  return apiFetch(routes.jobs(siteId), { method: "POST", body: input });
}

export async function getJob(siteId: UUID, jobId: UUID): Promise<AnalysisJob> {
  return apiFetch(routes.job(siteId, jobId));
}

export async function listResults(siteId: UUID, limit = 20): Promise<{ items: AnalysisResultListItem[] }> {
  return apiFetch(`${routes.results(siteId)}?limit=${limit}`);
}
export async function getResult(siteId: UUID, resultId: UUID): Promise<AnalysisResult> {
  return apiFetch(routes.result(siteId, resultId));
}
export async function getReport(siteId: UUID, resultId: UUID): Promise<Report> {
  return apiFetch(routes.report(siteId, resultId));
}
export async function regenerateReport(siteId: UUID, resultId: UUID, input?: { report_style?: "consultant" | "concise" | "technical" }): Promise<{ ok: boolean; report_id: UUID }> {
  return apiFetch(routes.regenReport(siteId, resultId), { method: "POST", body: input || {} });
}
```

---

### 5. Page-level Skeleton Code (wireframe snippet examples)

> 目的: "骨組み" を即実装できるように。詳細UIは各コンポーネントで。

#### 5.1 `app/sites/[siteId]/pages/page.tsx` (skeleton)

```typescript
import { listPages } from "@/lib/api/queries";

export default async function PagesPage({ params }: { params: { siteId: string } }) {
  const { items } = await listPages(params.siteId);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">URL BASE</h1>
          <p className="text-sm text-muted-foreground">公式 / 競合 / 紹介記事を整理して解析ターゲットを選択</p>
        </div>
        {/* UrlAddModalTrigger */}
      </div>

      {/* Tabs + Table + SelectionTray (client components) */}
      <div className="grid gap-6">
        {/* PageTypeTabs */}
        {/* PagesTable */}
        {/* SelectionTray */}
      </div>
    </div>
  );
}
```

#### 5.2 `app/sites/[siteId]/run/page.tsx` (skeleton)

```typescript
export default function RunPage({ params }: { params: { siteId: string } }) {
  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <div className="space-y-6">
        {/* RunConfigCard */}
        {/* RunButton */}
        {/* JobStatusBanner */}
      </div>
      <div className="space-y-6">
        {/* TargetSummaryCard */}
        {/* TipsCard */}
      </div>
    </div>
  );
}
```

#### 5.3 `app/sites/[siteId]/results/[resultId]/page.tsx` (skeleton)

```typescript
import { getResult, getReport } from "@/lib/api/queries";

export default async function ResultDetailPage({ params }: { params: { siteId: string; resultId: string } }) {
  const result = await getResult(params.siteId, params.resultId);
  const report = await getReport(params.siteId, params.resultId);

  const analysis = result.analysis_json;
  const diagnosis = analysis.diagnosis;
  const todos = analysis.todos;

  return (
    <div className="space-y-6">
      {/* ResultHeader (client) */}
      <div className="grid gap-6 xl:grid-cols-3">
        <div className="space-y-6">
          {/* InsightSummary */}
          {/* CompetitorDiffPanel */}
        </div>
        <div className="xl:col-span-1 xl:order-none space-y-6">
          {/* TodoBoard */}
        </div>
        <div className="space-y-6">
          {/* ReportMarkdown */}
        </div>
      </div>
    </div>
  );
}
```

---

# Appendix H: UI Implementation — Midnight Neon

## H-1. Global Styles（`styles/globals.css`）

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

/* ============================
   Midnight Neon Theme Variables
   ============================ */
:root {
  /* Base colors */
  --color-bg-base: #0f1729;          /* Deep navy */
  --color-bg-surface: #1a2744;       /* Card background */
  --color-bg-elevated: #243351;      /* Hover / elevated */

  /* Accent colors */
  --color-accent-cyan: #35D4FF;
  --color-accent-violet: #A78BFA;
  --color-accent-green: #4ADE80;     /* Success */
  --color-accent-amber: #FBBF24;     /* Warning */
  --color-accent-red: #F87171;       /* Error */

  /* Text colors */
  --color-text-primary: #F1F5F9;     /* slate-100 */
  --color-text-secondary: #94A3B8;   /* slate-400 */
  --color-text-muted: #64748B;       /* slate-500 */

  /* Border / Glass */
  --color-border: rgba(148, 163, 184, 0.15);
  --color-glass-bg: rgba(26, 39, 68, 0.6);
  --color-glass-border: rgba(53, 212, 255, 0.2);

  /* Shadows */
  --shadow-glow-cyan: 0 0 20px rgba(53, 212, 255, 0.15);
  --shadow-glow-violet: 0 0 20px rgba(167, 139, 250, 0.15);

  /* Fonts */
  --font-body: "Noto Sans JP", sans-serif;
  --font-mono: "JetBrains Mono", monospace;
}

/* ============================
   Base Layer
   ============================ */
@layer base {
  body {
    @apply bg-[var(--color-bg-base)] text-[var(--color-text-primary)];
    font-family: var(--font-body);
    font-feature-settings: "palt" 1;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
  }

  /* Monospace for metrics */
  .font-mono {
    font-family: var(--font-mono);
  }

  /* Japanese text optimization */
  p, li, dd {
    line-height: 1.8;
    letter-spacing: 0.02em;
  }

  h1, h2, h3 {
    font-feature-settings: "palt" 1;
    letter-spacing: 0.04em;
  }
}

/* ============================
   Component Layer
   ============================ */
@layer components {
  /* Glass Card */
  .glass-card {
    @apply rounded-2xl p-6;
    background: var(--color-glass-bg);
    border: 1px solid var(--color-glass-border);
    backdrop-filter: blur(12px);
    box-shadow: var(--shadow-glow-cyan);
  }

  .glass-card:hover {
    border-color: rgba(53, 212, 255, 0.4);
    box-shadow: 0 0 30px rgba(53, 212, 255, 0.2);
  }

  /* Score Badge */
  .score-badge {
    @apply inline-flex items-center justify-center rounded-full font-mono font-bold;
  }

  .score-badge-a {
    @apply bg-emerald-500/20 text-emerald-400 border border-emerald-500/30;
  }

  .score-badge-b {
    @apply bg-cyan-500/20 text-cyan-400 border border-cyan-500/30;
  }

  .score-badge-c {
    @apply bg-amber-500/20 text-amber-400 border border-amber-500/30;
  }

  .score-badge-d {
    @apply bg-red-500/20 text-red-400 border border-red-500/30;
  }

  /* Priority Tags */
  .priority-tag {
    @apply text-xs font-mono font-bold px-2 py-0.5 rounded;
  }

  .priority-p0 {
    @apply bg-red-500/20 text-red-400;
  }

  .priority-p1 {
    @apply bg-amber-500/20 text-amber-400;
  }

  .priority-p2 {
    @apply bg-slate-500/20 text-slate-400;
  }
}
```

---

## H-2. Utility: `lib/utils.ts`

```typescript
import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * Merge Tailwind classes with clsx
 * Handles conflicts and conditional classes
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

---

## H-3. GlassCard Component

```tsx
// components/layout/GlassCard.tsx
import { cn } from "@/lib/utils";
import { ReactNode } from "react";

interface GlassCardProps {
  children: ReactNode;
  className?: string;
  hover?: boolean;
  glow?: "cyan" | "violet" | "none";
}

export function GlassCard({
  children,
  className,
  hover = true,
  glow = "cyan",
}: GlassCardProps) {
  return (
    <div
      className={cn(
        "rounded-2xl p-6",
        "bg-[var(--color-glass-bg)]",
        "border border-[var(--color-glass-border)]",
        "backdrop-blur-xl",
        hover && "transition-all duration-300",
        hover && "hover:border-cyan-400/40 hover:shadow-[0_0_30px_rgba(53,212,255,0.2)]",
        glow === "cyan" && "shadow-[var(--shadow-glow-cyan)]",
        glow === "violet" && "shadow-[var(--shadow-glow-violet)]",
        className
      )}
    >
      {children}
    </div>
  );
}
```

---

## H-4. ScoreBadge Component

```tsx
// components/results/ScoreBadge.tsx
import { cn } from "@/lib/utils";
import type { ScoreGrade } from "@/types/analysis";

interface ScoreBadgeProps {
  grade: ScoreGrade;
  label?: string;
  size?: "sm" | "md" | "lg";
  showLabel?: boolean;
}

const gradeStyles: Record<ScoreGrade, string> = {
  A: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
  B: "bg-cyan-500/20 text-cyan-400 border-cyan-500/30",
  C: "bg-amber-500/20 text-amber-400 border-amber-500/30",
  D: "bg-red-500/20 text-red-400 border-red-500/30",
};

const sizeStyles = {
  sm: "w-8 h-8 text-sm",
  md: "w-12 h-12 text-lg",
  lg: "w-16 h-16 text-2xl",
};

export function ScoreBadge({
  grade,
  label,
  size = "md",
  showLabel = false,
}: ScoreBadgeProps) {
  return (
    <div className="flex flex-col items-center gap-1">
      <div
        className={cn(
          "inline-flex items-center justify-center",
          "rounded-full border font-mono font-bold",
          "transition-transform hover:scale-105",
          gradeStyles[grade],
          sizeStyles[size]
        )}
      >
        {grade}
      </div>
      {showLabel && label && (
        <span className="text-xs text-[var(--color-text-secondary)]">
          {label}
        </span>
      )}
    </div>
  );
}
```

---

## H-5. TodoCard Component

```tsx
// components/results/TodoCard.tsx
import { cn } from "@/lib/utils";
import type { Todo } from "@/types/analysis";
import { GlassCard } from "@/components/layout/GlassCard";
import {
  Zap,           // high impact
  TrendingUp,    // medium impact
  Minus,         // low impact
  Clock,         // effort indicator
} from "lucide-react";

interface TodoCardProps {
  todo: Todo;
  onClick?: () => void;
}

const priorityStyles = {
  P0: "border-l-red-500 bg-red-500/5",
  P1: "border-l-amber-500 bg-amber-500/5",
  P2: "border-l-slate-500 bg-slate-500/5",
};

const priorityLabels = {
  P0: { text: "今すぐ", color: "text-red-400" },
  P1: { text: "1-2週", color: "text-amber-400" },
  P2: { text: "中長期", color: "text-slate-400" },
};

const impactIcons = {
  high: <Zap className="w-4 h-4 text-amber-400" />,
  medium: <TrendingUp className="w-4 h-4 text-cyan-400" />,
  low: <Minus className="w-4 h-4 text-slate-400" />,
};

const effortLabels = {
  small: "軽",
  medium: "中",
  large: "重",
};

export function TodoCard({ todo, onClick }: TodoCardProps) {
  const { priority, title, details, impact, effort, evidence } = todo;

  return (
    <div
      onClick={onClick}
      className={cn(
        "rounded-lg p-4 border-l-4 cursor-pointer",
        "bg-[var(--color-bg-surface)]",
        "border border-[var(--color-border)]",
        "transition-all duration-200",
        "hover:bg-[var(--color-bg-elevated)]",
        "hover:translate-x-1",
        priorityStyles[priority]
      )}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-2 mb-2">
        <h4 className="font-medium text-[var(--color-text-primary)] line-clamp-2">
          {title}
        </h4>
        <span
          className={cn(
            "text-xs font-mono font-bold px-2 py-0.5 rounded shrink-0",
            priority === "P0" && "bg-red-500/20 text-red-400",
            priority === "P1" && "bg-amber-500/20 text-amber-400",
            priority === "P2" && "bg-slate-500/20 text-slate-400"
          )}
        >
          {priority}
        </span>
      </div>

      {/* Details */}
      <p className="text-sm text-[var(--color-text-secondary)] line-clamp-2 mb-3">
        {details}
      </p>

      {/* Footer: Impact & Effort */}
      <div className="flex items-center gap-4 text-xs">
        <div className="flex items-center gap-1">
          {impactIcons[impact]}
          <span className="text-[var(--color-text-muted)]">効果</span>
        </div>
        <div className="flex items-center gap-1">
          <Clock className="w-3 h-3 text-[var(--color-text-muted)]" />
          <span className="text-[var(--color-text-muted)]">
            {effortLabels[effort]}
          </span>
        </div>
      </div>

      {/* Evidence (collapsed) */}
      {evidence.length > 0 && (
        <div className="mt-2 pt-2 border-t border-[var(--color-border)]">
          <span className="text-xs text-[var(--color-text-muted)]">
            根拠: {evidence.length}件
          </span>
        </div>
      )}
    </div>
  );
}
```

---

## H-6. TodoBoard Component（P0 / P1 / P2 カラム）

```tsx
// components/results/TodoBoard.tsx
import { cn } from "@/lib/utils";
import type { Todo, TodoPriority } from "@/types/analysis";
import { TodoCard } from "./TodoCard";
import { GlassCard } from "@/components/layout/GlassCard";
import { AlertTriangle, Clock, Calendar } from "lucide-react";

interface TodoBoardProps {
  todos: Todo[];
  onTodoClick?: (todo: Todo) => void;
}

interface ColumnConfig {
  priority: TodoPriority;
  label: string;
  sublabel: string;
  icon: React.ReactNode;
  headerColor: string;
}

const columns: ColumnConfig[] = [
  {
    priority: "P0",
    label: "今すぐ対応",
    sublabel: "Critical",
    icon: <AlertTriangle className="w-4 h-4" />,
    headerColor: "text-red-400",
  },
  {
    priority: "P1",
    label: "1-2週間以内",
    sublabel: "Important",
    icon: <Clock className="w-4 h-4" />,
    headerColor: "text-amber-400",
  },
  {
    priority: "P2",
    label: "中長期",
    sublabel: "Nice to have",
    icon: <Calendar className="w-4 h-4" />,
    headerColor: "text-slate-400",
  },
];

export function TodoBoard({ todos, onTodoClick }: TodoBoardProps) {
  const groupedTodos = {
    P0: todos.filter((t) => t.priority === "P0"),
    P1: todos.filter((t) => t.priority === "P1"),
    P2: todos.filter((t) => t.priority === "P2"),
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {columns.map((col) => (
        <div key={col.priority} className="flex flex-col">
          {/* Column Header */}
          <div
            className={cn(
              "flex items-center gap-2 mb-3 pb-2",
              "border-b border-[var(--color-border)]"
            )}
          >
            <span className={col.headerColor}>{col.icon}</span>
            <div>
              <h3 className={cn("font-bold", col.headerColor)}>
                {col.label}
              </h3>
              <span className="text-xs text-[var(--color-text-muted)]">
                {col.sublabel} ({groupedTodos[col.priority].length})
              </span>
            </div>
          </div>

          {/* Cards */}
          <div className="flex flex-col gap-3">
            {groupedTodos[col.priority].length === 0 ? (
              <div className="text-center py-8 text-[var(--color-text-muted)] text-sm">
                該当なし
              </div>
            ) : (
              groupedTodos[col.priority].map((todo) => (
                <TodoCard
                  key={todo.todo_id}
                  todo={todo}
                  onClick={() => onTodoClick?.(todo)}
                />
              ))
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
```

---

## H-7. MainCauseBadge Component

> main cause を "一瞬で理解できる" バッジに。派手すぎず、洗練。

```tsx
// components/results/MainCauseBadge.tsx
import * as React from "react";
import { cn } from "@/lib/utils/cn";
import type { MainCause } from "@/lib/api/types";

export interface MainCauseBadgeProps {
  cause: MainCause;
  subtle?: boolean;
}

function causeTone(cause: MainCause) {
  switch (cause) {
    case "content_quality":
      return {
        label: "CONTENT",
        fg: "rgba(var(--cyan),0.95)",
        bg: "rgba(var(--cyan),0.10)",
        bd: "rgba(var(--cyan),0.20)"
      };
    case "ctr":
      return {
        label: "CTR",
        fg: "rgba(var(--violet),0.95)",
        bg: "rgba(var(--violet),0.10)",
        bd: "rgba(var(--violet),0.20)"
      };
    case "technical":
      return {
        label: "TECH",
        fg: "rgba(var(--amber),0.95)",
        bg: "rgba(var(--amber),0.10)",
        bd: "rgba(var(--amber),0.20)"
      };
    case "mixed":
      return {
        label: "MIXED",
        fg: "rgba(var(--fg),0.92)",
        bg: "rgba(var(--panel),0.10)",
        bd: "rgba(var(--border),0.16)"
      };
    default:
      return {
        label: "UNKNOWN",
        fg: "rgba(var(--muted),0.95)",
        bg: "rgba(var(--panel),0.08)",
        bd: "rgba(var(--border),0.14)"
      };
  }
}

export function MainCauseBadge({ cause, subtle }: MainCauseBadgeProps) {
  const t = causeTone(cause);
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-3 py-1 text-[10px] font-semibold tracking-[0.18em] uppercase",
        subtle && "opacity-90"
      )}
      style={{ color: t.fg, background: t.bg, borderColor: t.bd }}
      title={`Main cause: ${cause}`}
    >
      {t.label}
    </span>
  );
}
```

---

## H-8. ResultHeader Component

> "プロダクト感"が出る要素を全部ここに集約：
> - main cause badge
> - score chips（Content/Tech/CTR）
> - generated_at
> - actions（Download JSON / Evidence / Regenerate）

```tsx
// components/results/ResultHeader.tsx
"use client";

import * as React from "react";
import type { Diagnosis } from "@/lib/api/types";
import { GlassCard } from "@/components/layout/GlassCard";
import { MainCauseBadge } from "@/components/results/MainCauseBadge";
import { ScoreBadge } from "@/components/results/ScoreBadge";
import { cn } from "@/lib/utils/cn";
import { Download, RefreshCw, FileText, ShieldAlert } from "lucide-react";

export interface ResultHeaderProps {
  generatedAt: string;
  mainCause: Diagnosis["main_cause"];
  scores: Diagnosis["scores"];

  onDownloadJson: () => void;
  onRegenerateReport: () => Promise<void>;
  onOpenEvidence: () => void;

  reportStatus?: "ready" | "generating" | "failed";
}

function formatDateTime(iso: string) {
  // Keep simple for MVP; replace with date-fns if needed
  const d = new Date(iso);
  return d.toLocaleString();
}

function ActionButton({
  icon,
  label,
  onClick,
  disabled,
  subtle
}: {
  icon: React.ReactNode;
  label: string;
  onClick: () => void;
  disabled?: boolean;
  subtle?: boolean;
}) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className={cn(
        "inline-flex items-center gap-2 rounded-full border px-3 py-2 text-xs",
        "border-[rgba(var(--border),var(--border-alpha))]",
        "bg-[rgba(var(--panel),0.06)] backdrop-blur-[12px]",
        "hover:shadow-[0_0_0_1px_rgba(var(--cyan),0.22),var(--glow-cyan)]",
        "transition-all duration-200 ease-out",
        "disabled:opacity-50 disabled:cursor-not-allowed",
        subtle && "text-muted-foreground"
      )}
    >
      {icon}
      <span className="font-medium">{label}</span>
    </button>
  );
}

export function ResultHeader({
  generatedAt,
  mainCause,
  scores,
  onDownloadJson,
  onRegenerateReport,
  onOpenEvidence,
  reportStatus = "ready"
}: ResultHeaderProps) {
  const [regenLoading, setRegenLoading] = React.useState(false);

  const regen = async () => {
    try {
      setRegenLoading(true);
      await onRegenerateReport();
    } finally {
      setRegenLoading(false);
    }
  };

  return (
    <GlassCard glow="cyan" className="p-5">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        {/* Left: title + meta */}
        <div className="space-y-2">
          <div className="flex flex-wrap items-center gap-3">
            <MainCauseBadge cause={mainCause} />
            <span className="text-sm font-semibold tracking-tight">
              RESULT / 診断結果
            </span>
            <span className="text-xs text-muted-foreground">
              generated {formatDateTime(generatedAt)}
            </span>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <ScoreBadge label="Content" grade={scores.content} />
            <ScoreBadge label="Technical" grade={scores.technical} />
            <ScoreBadge label="CTR" grade={scores.ctr} />
          </div>
        </div>

        {/* Right: actions */}
        <div className="flex flex-wrap items-center gap-2">
          <ActionButton
            icon={<Download className="h-4 w-4 opacity-80" />}
            label="Download JSON"
            onClick={onDownloadJson}
          />
          <ActionButton
            icon={<FileText className="h-4 w-4 opacity-80" />}
            label="Evidence"
            onClick={onOpenEvidence}
            subtle
          />
          <ActionButton
            icon={
              reportStatus === "failed" ? (
                <ShieldAlert className="h-4 w-4 opacity-80" />
              ) : (
                <RefreshCw className={cn("h-4 w-4 opacity-80", regenLoading && "animate-spin")} />
              )
            }
            label={regenLoading ? "Regenerating..." : "Regenerate report"}
            onClick={regen}
            disabled={regenLoading || reportStatus === "generating"}
          />
        </div>
      </div>
    </GlassCard>
  );
}
```

---

## H-9. Markdown Styles（`styles/markdown.css`）

> "読みやすさ"が命。Markdownはそのままだとダサくなりがちなので、
> 見出し・コード・引用・表を整えてプロダクト感を出す。

```css
/* styles/markdown.css */
.markdown {
  color: rgba(var(--fg), 0.90);
  line-height: 1.75;
  font-size: 14.5px;
}

.markdown h1,
.markdown h2,
.markdown h3 {
  line-height: 1.25;
  font-weight: 700;
  letter-spacing: -0.015em;
  margin-top: 1.2em;
  margin-bottom: 0.6em;
}

.markdown h1 {
  font-size: 20px;
}
.markdown h2 {
  font-size: 16.5px;
}
.markdown h3 {
  font-size: 15px;
  font-weight: 650;
}

.markdown p {
  margin: 0.8em 0;
  color: rgba(var(--fg), 0.88);
}

.markdown ul,
.markdown ol {
  padding-left: 1.2em;
  margin: 0.8em 0;
}

.markdown li {
  margin: 0.35em 0;
}

/* Inline code */
.markdown code {
  font-family: var(--font-mono, ui-monospace), SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
  font-size: 0.92em;
  padding: 0.18em 0.35em;
  border-radius: 8px;
  background: rgba(var(--panel), 0.10);
  border: 1px solid rgba(var(--border), 0.12);
}

/* Code blocks */
.markdown pre {
  font-family: var(--font-mono, ui-monospace), SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
  font-size: 13px;
  padding: 14px 14px;
  border-radius: 14px;
  overflow: auto;
  background: rgba(var(--panel), 0.08);
  border: 1px solid rgba(var(--border), 0.12);
  box-shadow: 0 10px 30px rgba(0,0,0,0.25);
}

.markdown pre code {
  padding: 0;
  border: none;
  background: transparent;
}

/* Blockquote */
.markdown blockquote {
  margin: 1em 0;
  padding: 0.9em 1em;
  border-left: 3px solid rgba(var(--cyan), 0.55);
  background: rgba(var(--panel), 0.06);
  border-radius: 12px;
  color: rgba(var(--fg), 0.82);
}

/* Tables */
.markdown table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  margin: 1em 0;
  overflow: hidden;
  border-radius: 14px;
  border: 1px solid rgba(var(--border), 0.12);
  background: rgba(var(--panel), 0.05);
}

.markdown th,
.markdown td {
  padding: 10px 12px;
  border-bottom: 1px solid rgba(var(--border), 0.10);
}

.markdown th {
  text-align: left;
  font-size: 12px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: rgba(var(--fg), 0.75);
  background: rgba(var(--panel), 0.06);
}

.markdown tr:last-child td {
  border-bottom: none;
}

/* Horizontal rule */
.markdown hr {
  border: none;
  height: 1px;
  background: rgba(var(--border), 0.12);
  margin: 1.2em 0;
}

/* Links inside markdown */
.markdown a {
  color: rgba(var(--cyan), 0.92);
  text-decoration: none;
}
.markdown a:hover {
  text-decoration: underline;
}
```

### H-9.1 Import CSS

`app/layout.tsx` または `app/sites/[siteId]/layout.tsx` で：

```tsx
import "@/styles/markdown.css";
```

---

## H-10. ReportMarkdown Component

> 余計な装飾なしで"綺麗に読める"を保証。
> remark-gfm で表や箇条書きを正しくレンダリング。

```tsx
// components/results/ReportMarkdown.tsx
"use client";

import * as React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { GlassCard } from "@/components/layout/GlassCard";

export interface ReportMarkdownProps {
  markdown: string;
  title?: string;
}

export function ReportMarkdown({ markdown, title = "REPORT / レポート" }: ReportMarkdownProps) {
  return (
    <GlassCard className="p-5">
      <div className="mb-3 flex items-center justify-between">
        <div className="text-sm font-semibold tracking-tight">{title}</div>
        <div className="text-[10px] text-muted-foreground uppercase tracking-[0.18em]">AI generated</div>
      </div>

      <div className="markdown">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{markdown}</ReactMarkdown>
      </div>
    </GlassCard>
  );
}
```

---

## H-11. ResultView Usage Example

> ResultHeader + TodoBoard + ReportMarkdown を並べる例（client handling部分のみ）

```tsx
// components/results/ResultView.tsx
"use client";

import * as React from "react";
import { ResultHeader } from "@/components/results/ResultHeader";
import { TodoBoard } from "@/components/results/TodoBoard";
import { ReportMarkdown } from "@/components/results/ReportMarkdown";
import { EvidenceDrawer } from "@/components/results/EvidenceDrawer";
import type { Diagnosis, Todo } from "@/lib/api/types";

export function ResultView({
  generatedAt,
  diagnosis,
  todos,
  reportMarkdown,
  onDownloadJson,
  onRegenerateReport
}: {
  generatedAt: string;
  diagnosis: Diagnosis;
  todos: Todo[];
  reportMarkdown: string;
  onDownloadJson: () => void;
  onRegenerateReport: () => Promise<void>;
}) {
  const [evidenceOpen, setEvidenceOpen] = React.useState(false);

  return (
    <div className="space-y-6">
      <ResultHeader
        generatedAt={generatedAt}
        mainCause={diagnosis.main_cause}
        scores={diagnosis.scores}
        onDownloadJson={onDownloadJson}
        onRegenerateReport={onRegenerateReport}
        onOpenEvidence={() => setEvidenceOpen(true)}
      />

      <div className="grid gap-6 xl:grid-cols-3">
        <div className="xl:col-span-2">
          <TodoBoard todos={todos} />
        </div>
        <div>
          <ReportMarkdown markdown={reportMarkdown} />
        </div>
      </div>

      <EvidenceDrawer open={evidenceOpen} onOpenChange={setEvidenceOpen} evidence={diagnosis.evidence} />
    </div>
  );
}
```

---

## H-12. Acceptance Criteria (UI polish)

- [ ] ResultHeader が "バッジ→スコア→アクション" の順で一瞬で理解できる
- [ ] ReportMarkdown の見出し/コード/引用/表が崩れず、読みやすい
- [ ] すべてのコンポーネントが dark theme で十分なコントラスト
- [ ] Hover時の発光は上品（眩しすぎない）

---

## 次のステップ（必要なら追記）
さらに追加が有効なコンポーネント:
- `EvidenceDrawer`: 根拠を気持ちよく見せるスライドパネル
- `TodoDetailModal`: 例文・h2案・FAQ案を"コピーボタン付き"で表示
