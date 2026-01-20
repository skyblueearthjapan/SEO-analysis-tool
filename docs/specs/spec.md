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

# Appendix I: EvidenceDrawer + Todo Detail Modal (Copy buttons)

**Target**: Next.js + Tailwind + lucide-react + shadcn/ui (Radix Dialog/Drawer)

**Goal**:
- 根拠（evidence）を"気持ちよく"閲覧できるDrawer
- Todoカードをクリック → 詳細モーダル
  - 手順/根拠/具体案（title案・h2案・FAQ・依頼文）を整理
  - コピーボタンで即使える（コンサル感UP）

---

## I-0. Dependencies (recommended)

- shadcn/ui:
  - `Dialog`, `Sheet` (or `Drawer`)
  - `Button`, `Separator`, `Tabs`, `ScrollArea`, `Badge`, `Toast` (optional)
- icons: `lucide-react`
- clipboard: `navigator.clipboard.writeText`

> If you don't use shadcn/ui, keep logic and replace components.

---

## I-1. Clipboard Utility（`lib/utils/clipboard.ts`）

> Copyの共通関数。失敗時のfallback付き。

```ts
// lib/utils/clipboard.ts
export async function copyToClipboard(text: string) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    // Fallback for older browsers
    try {
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.style.position = "fixed";
      ta.style.left = "-9999px";
      document.body.appendChild(ta);
      ta.focus();
      ta.select();
      const ok = document.execCommand("copy");
      document.body.removeChild(ta);
      return ok;
    } catch {
      return false;
    }
  }
}
```

---

## I-2. EvidenceDrawer Component

> Evidence（claim + support）をカード化。検索/フィルタがあると最高に気持ちいい。
> MVP: search input + highlight（簡易）

```tsx
// components/results/EvidenceDrawer.tsx
"use client";

import * as React from "react";
import type { Diagnosis } from "@/lib/api/types";
import { GlassCard } from "@/components/layout/GlassCard";
import { cn } from "@/lib/utils/cn";
import { Search, X } from "lucide-react";

// If using shadcn/ui Sheet:
// import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from "@/components/ui/sheet";

export interface EvidenceDrawerProps {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  evidence: Diagnosis["evidence"];
}

/**
 * Minimal drawer implementation without shadcn:
 * - fixed overlay + side panel
 * Replace with shadcn Sheet for nicer a11y if available.
 */
export function EvidenceDrawer({ open, onOpenChange, evidence }: EvidenceDrawerProps) {
  const [q, setQ] = React.useState("");

  const filtered = React.useMemo(() => {
    if (!q.trim()) return evidence;
    const query = q.toLowerCase();
    return evidence.filter((e) => {
      const s = (e.claim + " " + e.support.join(" ")).toLowerCase();
      return s.includes(query);
    });
  }, [q, evidence]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50">
      {/* overlay */}
      <div
        className="absolute inset-0 bg-black/60"
        onClick={() => onOpenChange(false)}
      />
      {/* panel */}
      <div className="absolute right-0 top-0 h-full w-full max-w-[520px] p-4">
        <GlassCard className="h-full p-5">
          <div className="flex items-start justify-between gap-3">
            <div>
              <div className="text-sm font-semibold tracking-tight">EVIDENCE / 根拠</div>
              <div className="mt-1 text-xs text-muted-foreground">
                重要な指摘の裏付け（数値・差分・観測）を一覧できます
              </div>
            </div>
            <button
              type="button"
              className="rounded-full border px-3 py-2 text-xs border-[rgba(var(--border),var(--border-alpha))] bg-[rgba(var(--panel),0.06)] hover:shadow-[0_0_0_1px_rgba(var(--cyan),0.22),var(--glow-cyan)] transition"
              onClick={() => onOpenChange(false)}
            >
              <X className="h-4 w-4 opacity-80" />
            </button>
          </div>

          {/* Search */}
          <div className="mt-4 flex items-center gap-2 rounded-[var(--r-md)] border px-3 py-2 bg-[rgba(var(--panel),0.06)] border-[rgba(var(--border),0.12)]">
            <Search className="h-4 w-4 opacity-70" />
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="検索（例：CTR / h2 / pagespeed）"
              className="w-full bg-transparent text-sm outline-none placeholder:text-[rgba(var(--fg),0.45)]"
            />
            {q && (
              <button
                type="button"
                className="text-xs text-muted-foreground hover:opacity-90"
                onClick={() => setQ("")}
              >
                clear
              </button>
            )}
          </div>

          {/* List */}
          <div className="mt-4 h-[calc(100%-140px)] overflow-auto pr-2">
            <div className="space-y-3">
              {filtered.length === 0 ? (
                <div className="text-xs text-muted-foreground">一致する根拠がありません</div>
              ) : (
                filtered.map((e, idx) => (
                  <div
                    key={idx}
                    className={cn(
                      "rounded-[var(--r-md)] border p-4",
                      "bg-[rgba(var(--panel),0.06)]",
                      "border-[rgba(var(--border),0.12)]"
                    )}
                  >
                    <div className="text-sm font-semibold leading-snug">{e.claim}</div>
                    <ul className="mt-2 space-y-1">
                      {e.support.map((s, i) => (
                        <li key={i} className="text-xs text-muted-foreground">
                          • {s}
                        </li>
                      ))}
                    </ul>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Footer note */}
          <div className="mt-4 text-[10px] text-muted-foreground uppercase tracking-[0.18em]">
            evidence is generated by rule engine
          </div>
        </GlassCard>
      </div>
    </div>
  );
}
```

---

## I-3. TodoDetailModal Component

> Todoをクリックした時の"コンサル納品物感"を演出する要。
> - Summary（title/details/impact/effort）
> - Steps（手順）
> - Evidence（根拠）
> - Examples（title案/h2案/FAQ/依頼文）をタブ化
> - Copyボタン：1クリックでコピー

```tsx
// components/results/TodoDetailModal.tsx
"use client";

import * as React from "react";
import type { Todo } from "@/lib/api/types";
import { GlassCard } from "@/components/layout/GlassCard";
import { copyToClipboard } from "@/lib/utils/clipboard";
import { cn } from "@/lib/utils/cn";
import { Check, Copy, X } from "lucide-react";

export interface TodoDetailModalProps {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  todo: Todo | null;
}

function Chip({ children }: { children: React.ReactNode }) {
  return (
    <span className="rounded-full border px-2 py-1 text-[10px] uppercase tracking-wider border-[rgba(var(--border),0.14)] bg-[rgba(var(--panel),0.06)]">
      {children}
    </span>
  );
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <div className="text-xs font-semibold tracking-wide text-muted-foreground">{children}</div>;
}

function CopyButton({ text }: { text: string }) {
  const [ok, setOk] = React.useState(false);

  const onCopy = async () => {
    const done = await copyToClipboard(text);
    setOk(done);
    setTimeout(() => setOk(false), 1200);
  };

  return (
    <button
      type="button"
      onClick={onCopy}
      className={cn(
        "inline-flex items-center gap-2 rounded-full border px-3 py-2 text-xs",
        "border-[rgba(var(--border),var(--border-alpha))]",
        "bg-[rgba(var(--panel),0.06)] backdrop-blur-[12px]",
        "hover:shadow-[0_0_0_1px_rgba(var(--cyan),0.22),var(--glow-cyan)]",
        "transition-all duration-200 ease-out"
      )}
    >
      {ok ? <Check className="h-4 w-4 opacity-80" /> : <Copy className="h-4 w-4 opacity-80" />}
      <span className="font-medium">{ok ? "Copied" : "Copy"}</span>
    </button>
  );
}

function renderListOrEmpty(items?: string[]) {
  if (!items || items.length === 0) return <div className="text-xs text-muted-foreground">なし</div>;
  return (
    <ul className="space-y-1">
      {items.map((x, i) => (
        <li key={i} className="text-xs text-muted-foreground">• {x}</li>
      ))}
    </ul>
  );
}

export function TodoDetailModal({ open, onOpenChange, todo }: TodoDetailModalProps) {
  const [tab, setTab] = React.useState<"steps" | "examples" | "evidence">("steps");

  React.useEffect(() => {
    if (open) setTab("steps");
  }, [open]);

  if (!open || !todo) return null;

  // Copy targets
  const copyPack: { label: string; text: string; show: boolean }[] = [
    {
      label: "ToDo details",
      text: `${todo.title}\n\n${todo.details}\n\nPriority: ${todo.priority}\nCategory: ${todo.category}\nImpact: ${todo.impact}\nEffort: ${todo.effort}`,
      show: true
    },
    {
      label: "Title variants",
      text: (todo.examples?.title_variants || []).join("\n"),
      show: !!todo.examples?.title_variants?.length
    },
    {
      label: "H2 outline",
      text: (todo.examples?.h2_outline || []).join("\n"),
      show: !!todo.examples?.h2_outline?.length
    },
    {
      label: "FAQ questions",
      text: (todo.examples?.faq_questions || []).join("\n"),
      show: !!todo.examples?.faq_questions?.length
    },
    {
      label: "Outreach message",
      text: todo.examples?.outreach_message_draft_jp || "",
      show: !!todo.examples?.outreach_message_draft_jp
    }
  ];

  return (
    <div className="fixed inset-0 z-50">
      {/* overlay */}
      <div className="absolute inset-0 bg-black/60" onClick={() => onOpenChange(false)} />
      {/* modal */}
      <div className="absolute left-1/2 top-1/2 w-[min(920px,calc(100%-24px))] -translate-x-1/2 -translate-y-1/2 p-2">
        <GlassCard className="p-5">
          {/* header */}
          <div className="flex items-start justify-between gap-4">
            <div className="space-y-2">
              <div className="text-sm font-semibold tracking-tight">TODO DETAIL / 対策詳細</div>
              <div className="text-lg font-semibold leading-snug">{todo.title}</div>
              <div className="text-sm text-muted-foreground">{todo.details}</div>

              <div className="mt-2 flex flex-wrap gap-2">
                <Chip>{todo.priority}</Chip>
                <Chip>{todo.category}</Chip>
                <Chip>impact {todo.impact}</Chip>
                <Chip>effort {todo.effort}</Chip>
              </div>
            </div>

            <button
              type="button"
              className="rounded-full border px-3 py-2 text-xs border-[rgba(var(--border),var(--border-alpha))] bg-[rgba(var(--panel),0.06)] hover:shadow-[0_0_0_1px_rgba(var(--cyan),0.22),var(--glow-cyan)] transition"
              onClick={() => onOpenChange(false)}
            >
              <X className="h-4 w-4 opacity-80" />
            </button>
          </div>

          {/* tabs */}
          <div className="mt-5 flex items-center gap-2">
            {[
              { k: "steps", label: "STEPS / 手順" },
              { k: "examples", label: "EXAMPLES / 具体案" },
              { k: "evidence", label: "EVIDENCE / 根拠" }
            ].map((t) => (
              <button
                key={t.k}
                type="button"
                onClick={() => setTab(t.k as any)}
                className={cn(
                  "rounded-full border px-3 py-2 text-xs tracking-wide",
                  "border-[rgba(var(--border),0.14)] bg-[rgba(var(--panel),0.06)]",
                  tab === t.k
                    ? "shadow-[0_0_0_1px_rgba(var(--cyan),0.25),var(--glow-cyan)]"
                    : "opacity-80 hover:opacity-100"
                )}
              >
                {t.label}
              </button>
            ))}

            <div className="ml-auto flex flex-wrap gap-2">
              {copyPack.filter((c) => c.show).map((c) => (
                <CopyButton key={c.label} text={c.text} />
              ))}
            </div>
          </div>

          {/* content */}
          <div className="mt-4 grid gap-4 lg:grid-cols-3">
            {/* left: navigation/summary */}
            <div className="lg:col-span-1 space-y-3">
              <GlassCard className="p-4">
                <SectionTitle>SUMMARY</SectionTitle>
                <div className="mt-2 text-xs text-muted-foreground">
                  このToDoは <span className="font-semibold text-[rgba(var(--fg),0.9)]">{todo.priority}</span> として提案されています。
                  まずは小さく直して反応を見る設計です。
                </div>
              </GlassCard>

              <GlassCard className="p-4">
                <SectionTitle>QUICK NOTES</SectionTitle>
                <ul className="mt-2 space-y-1 text-xs text-muted-foreground">
                  <li>• 変更日を記録して、7日/28日で検証</li>
                  <li>• 同時に大改修しない（原因特定が難しくなる）</li>
                  <li>• 競合差分がある場合はそこを優先</li>
                </ul>
              </GlassCard>
            </div>

            {/* right: main */}
            <div className="lg:col-span-2">
              <GlassCard className="p-4">
                {tab === "steps" && (
                  <div className="space-y-3">
                    <SectionTitle>STEPS / 手順</SectionTitle>
                    <ol className="mt-2 space-y-2 pl-4 text-sm">
                      <li className="text-sm">
                        <span className="font-semibold">1.</span>{" "}
                        対象箇所を特定（title/h2/FAQ/リンクなど）
                      </li>
                      <li className="text-sm">
                        <span className="font-semibold">2.</span>{" "}
                        修正案を適用（下の具体案をコピーして使える）
                      </li>
                      <li className="text-sm">
                        <span className="font-semibold">3.</span>{" "}
                        変更日を記録し、7日/28日でCTR/順位/表示回数を確認
                      </li>
                    </ol>

                    <div className="mt-3">
                      <SectionTitle>DETAIL</SectionTitle>
                      <div className="mt-2 text-sm text-muted-foreground whitespace-pre-wrap">
                        {todo.details}
                      </div>
                    </div>
                  </div>
                )}

                {tab === "examples" && (
                  <div className="space-y-5">
                    <SectionTitle>EXAMPLES / 具体案</SectionTitle>

                    <div className="grid gap-4 md:grid-cols-2">
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <div className="text-xs font-semibold text-muted-foreground">TITLE VARIANTS</div>
                          {todo.examples?.title_variants?.length ? (
                            <CopyButton text={todo.examples.title_variants.join("\n")} />
                          ) : null}
                        </div>
                        {renderListOrEmpty(todo.examples?.title_variants)}
                      </div>

                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <div className="text-xs font-semibold text-muted-foreground">META DESCRIPTION</div>
                          {todo.examples?.meta_description_variants?.length ? (
                            <CopyButton text={todo.examples.meta_description_variants.join("\n")} />
                          ) : null}
                        </div>
                        {renderListOrEmpty(todo.examples?.meta_description_variants)}
                      </div>
                    </div>

                    <div className="grid gap-4 md:grid-cols-2">
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <div className="text-xs font-semibold text-muted-foreground">H2 OUTLINE</div>
                          {todo.examples?.h2_outline?.length ? (
                            <CopyButton text={todo.examples.h2_outline.join("\n")} />
                          ) : null}
                        </div>
                        {renderListOrEmpty(todo.examples?.h2_outline)}
                      </div>

                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <div className="text-xs font-semibold text-muted-foreground">FAQ QUESTIONS</div>
                          {todo.examples?.faq_questions?.length ? (
                            <CopyButton text={todo.examples.faq_questions.join("\n")} />
                          ) : null}
                        </div>
                        {renderListOrEmpty(todo.examples?.faq_questions)}
                      </div>
                    </div>

                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <div className="text-xs font-semibold text-muted-foreground">OUTREACH MESSAGE (JP)</div>
                        {todo.examples?.outreach_message_draft_jp ? (
                          <CopyButton text={todo.examples.outreach_message_draft_jp} />
                        ) : null}
                      </div>
                      {todo.examples?.outreach_message_draft_jp ? (
                        <pre className="mt-2 whitespace-pre-wrap rounded-[var(--r-md)] border p-3 text-xs bg-[rgba(var(--panel),0.06)] border-[rgba(var(--border),0.12)]">
{todo.examples.outreach_message_draft_jp}
                        </pre>
                      ) : (
                        <div className="text-xs text-muted-foreground">なし</div>
                      )}
                    </div>
                  </div>
                )}

                {tab === "evidence" && (
                  <div className="space-y-3">
                    <SectionTitle>EVIDENCE / 根拠</SectionTitle>
                    {todo.evidence?.length ? (
                      <ul className="mt-2 space-y-1">
                        {todo.evidence.map((e, i) => (
                          <li key={i} className="text-xs text-muted-foreground">• {e}</li>
                        ))}
                      </ul>
                    ) : (
                      <div className="text-xs text-muted-foreground">なし</div>
                    )}
                  </div>
                )}
              </GlassCard>
            </div>
          </div>
        </GlassCard>
      </div>
    </div>
  );
}
```

---

## I-4. TodoBoard Wiring（click → open modal）

> TodoBoardに `onSelectTodo` を渡し、ResultViewでmodal state管理。

```tsx
// components/results/TodoBoardWithModal.tsx
"use client";

import * as React from "react";
import type { Diagnosis, Todo } from "@/lib/api/types";
import { TodoBoard } from "@/components/results/TodoBoard";
import { TodoDetailModal } from "@/components/results/TodoDetailModal";

export function TodoBoardWithModal({ todos }: { todos: Todo[] }) {
  const [open, setOpen] = React.useState(false);
  const [selected, setSelected] = React.useState<Todo | null>(null);

  return (
    <>
      <TodoBoard
        todos={todos}
        onSelectTodo={(t) => {
          setSelected(t);
          setOpen(true);
        }}
      />
      <TodoDetailModal open={open} onOpenChange={setOpen} todo={selected} />
    </>
  );
}
```

---

## I-5. (Optional) Micro-polish for "気持ちよさ"

### I-5.1 Keyboard UX
- `Escape`で閉じる（shadcn Dialog/Sheetなら自動）
- Focus trap（同上）

### I-5.2 Copy feedback
- 本当は toast が最高（shadcn Sonner 等）
- MVPはボタンが "Copied" に変わるだけでも十分

### I-5.3 Evidence to Todo
- ToDo詳細のevidence tabに、`Diagnosis.evidence`（全体根拠）もリンクできるとプロ感UP
- 例：evidence文字列の一部一致で関連根拠を表示

---

## I-6. Acceptance Criteria

### EvidenceDrawer
- [ ] open/closeできる
- [ ] 検索でフィルタできる
- [ ] claim + support が読みやすいカードで並ぶ

### TodoDetailModal
- [ ] TodoCardクリックで開く
- [ ] Steps/Examples/Evidence のタブ切替が可能
- [ ] Copyボタンが機能し、Copied表示になる
- [ ] title案/h2案/FAQ/依頼文がある場合にのみ表示される

---

# Appendix J: Run Screen Progress UX (queued → running → done)

**Target**: Next.js + Tailwind + lucide-react

**Goal**:
- "実行中"が気持ちよく伝わる（プロダクト感UP）
- queued/running/done/failed を視覚的に表現
- doneになったら「結果へ」導線が強く出る
- pollingは軽量（2〜3秒間隔、上限タイムアウトあり）

**Includes**:
- `components/run/JobStatusCard.tsx`（メイン）
- `components/run/ProgressSteps.tsx`（ステップUI）
- `components/run/StatusPulse.tsx`（ネオンパルス）
- `components/run/useJobPoll.ts`（polling hook）
- wiring example (Run page)

---

## J-1. StatusPulse Component

> "動いてる感"の最小エッセンス。眩しすぎないネオンパルス。

```tsx
// components/run/StatusPulse.tsx
import * as React from "react";
import { cn } from "@/lib/utils/cn";

export interface StatusPulseProps {
  tone?: "cyan" | "violet" | "amber" | "rose";
  className?: string;
}

export function StatusPulse({ tone = "cyan", className }: StatusPulseProps) {
  const color =
    tone === "violet"
      ? "rgba(var(--violet),0.95)"
      : tone === "amber"
      ? "rgba(var(--amber),0.95)"
      : tone === "rose"
      ? "rgba(var(--rose),0.95)"
      : "rgba(var(--cyan),0.95)";

  return (
    <span className={cn("relative inline-flex h-2.5 w-2.5", className)}>
      <span
        className="absolute inline-flex h-full w-full rounded-full animate-ping opacity-60"
        style={{ background: color }}
      />
      <span className="relative inline-flex h-2.5 w-2.5 rounded-full" style={{ background: color }} />
    </span>
  );
}
```

---

## J-2. ProgressSteps Component

> queued → running → done を "3ステップ" で分かりやすく。
> runningは中央ステップが強調される。

```tsx
// components/run/ProgressSteps.tsx
import * as React from "react";
import { cn } from "@/lib/utils/cn";
import type { JobStatus } from "@/lib/api/types";
import { Check } from "lucide-react";

export interface ProgressStepsProps {
  status: JobStatus;
}

function stepState(status: JobStatus, step: 0 | 1 | 2) {
  // 0: queued, 1: running, 2: done
  if (status === "failed") return "failed";
  if (status === "queued") return step === 0 ? "active" : "idle";
  if (status === "running") return step <= 1 ? (step === 1 ? "active" : "done") : "idle";
  if (status === "done") return "done";
  return "idle";
}

export function ProgressSteps({ status }: ProgressStepsProps) {
  const steps = [
    { key: 0 as const, label: "QUEUED", sub: "準備中" },
    { key: 1 as const, label: "RUNNING", sub: "解析実行中" },
    { key: 2 as const, label: "DONE", sub: "完了" }
  ];

  return (
    <div className="grid gap-3">
      <div className="grid grid-cols-3 gap-3">
        {steps.map((s) => {
          const st = stepState(status, s.key);
          const isActive = st === "active";
          const isDone = st === "done";
          const isFailed = status === "failed";

          const border = isFailed
            ? "rgba(var(--rose),0.25)"
            : isActive
            ? "rgba(var(--cyan),0.28)"
            : "rgba(var(--border),0.12)";
          const bg = isFailed
            ? "rgba(var(--rose),0.10)"
            : isActive
            ? "rgba(var(--cyan),0.10)"
            : "rgba(var(--panel),0.06)";

          return (
            <div
              key={s.key}
              className={cn(
                "rounded-[var(--r-md)] border px-3 py-3",
                "transition-all duration-200 ease-out"
              )}
              style={{ borderColor: border, background: bg }}
            >
              <div className="flex items-center justify-between">
                <div className="text-[10px] font-semibold tracking-[0.18em] uppercase">
                  {s.label}
                </div>
                {isDone && !isFailed ? (
                  <span className="inline-flex items-center justify-center rounded-full border px-2 py-0.5 text-[10px]"
                        style={{ borderColor: "rgba(var(--lime),0.22)", background: "rgba(var(--lime),0.08)", color: "rgba(var(--lime),0.95)" }}>
                    <Check className="mr-1 h-3 w-3" />
                    OK
                  </span>
                ) : null}
              </div>
              <div className="mt-1 text-xs text-muted-foreground">{s.sub}</div>
            </div>
          );
        })}
      </div>

      {/* Status line */}
      <div className="text-xs text-muted-foreground">
        {status === "queued" && "キューに入りました。解析環境を準備しています。"}
        {status === "running" && "解析中：HTML/構造/速度/比較/ToDo生成を実行しています。"}
        {status === "done" && "完了：レポートが生成されました。結果画面へ移動できます。"}
        {status === "failed" && "失敗：エラーが発生しました。URLやネットワーク、設定を確認してください。"}
      </div>
    </div>
  );
}
```

---

## J-3. useJobPoll Hook

> job statusをポーリングで更新。done/failedで停止。
> 2.5秒間隔＋上限（例: 10分）で安全。

```ts
// components/run/useJobPoll.ts
"use client";

import * as React from "react";
import type { AnalysisJob, UUID } from "@/lib/api/types";
import { getJob } from "@/lib/api/queries";

export function useJobPoll(siteId: UUID, jobId: UUID | null, opts?: { intervalMs?: number; timeoutMs?: number }) {
  const intervalMs = opts?.intervalMs ?? 2500;
  const timeoutMs = opts?.timeoutMs ?? 10 * 60 * 1000;

  const [job, setJob] = React.useState<AnalysisJob | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [isPolling, setIsPolling] = React.useState(false);

  React.useEffect(() => {
    if (!jobId) return;

    let alive = true;
    let timer: any = null;
    const started = Date.now();

    const tick = async () => {
      try {
        setIsPolling(true);
        const j = await getJob(siteId, jobId);
        if (!alive) return;
        setJob(j);
        setError(null);

        if (j.status === "done" || j.status === "failed") {
          setIsPolling(false);
          return; // stop
        }
        if (Date.now() - started > timeoutMs) {
          setIsPolling(false);
          setError("Polling timeout");
          return;
        }
        timer = setTimeout(tick, intervalMs);
      } catch (e: any) {
        if (!alive) return;
        setIsPolling(false);
        setError(e?.message ?? "poll error");
      }
    };

    tick();

    return () => {
      alive = false;
      if (timer) clearTimeout(timer);
    };
  }, [siteId, jobId, intervalMs, timeoutMs]);

  return { job, error, isPolling };
}
```

---

## J-4. JobStatusCard Component

> "ステータスカード"がRun画面の主役。上品な発光＋状況に応じたCTA。
> - running: パルス＋軽いスピナー
> - done: 「View Result」ボタンが主ボタンになる
> - failed: エラー表示 + retry導線

```tsx
// components/run/JobStatusCard.tsx
"use client";

import * as React from "react";
import type { AnalysisJob, UUID } from "@/lib/api/types";
import { GlassCard } from "@/components/layout/GlassCard";
import { ProgressSteps } from "@/components/run/ProgressSteps";
import { StatusPulse } from "@/components/run/StatusPulse";
import { cn } from "@/lib/utils/cn";
import { ArrowRight, RotateCcw, Loader2, AlertTriangle } from "lucide-react";

export interface JobStatusCardProps {
  job: AnalysisJob | null;
  pollingError?: string | null;
  isPolling?: boolean;

  onViewResult?: () => void;
  onRetry?: () => void;
}

function toneFromStatus(status?: AnalysisJob["status"]) {
  if (status === "failed") return "rose" as const;
  if (status === "running") return "cyan" as const;
  if (status === "done") return "violet" as const;
  return "amber" as const;
}

export function JobStatusCard({ job, pollingError, isPolling, onViewResult, onRetry }: JobStatusCardProps) {
  const status = job?.status ?? "queued";
  const tone = toneFromStatus(status);

  const headerText =
    status === "queued"
      ? "JOB QUEUED / 準備中"
      : status === "running"
      ? "ANALYZING / 解析実行中"
      : status === "done"
      ? "COMPLETE / 完了"
      : "FAILED / 失敗";

  return (
    <GlassCard glow={status === "running" ? "cyan" : status === "done" ? "violet" : "none"} className="p-5">
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-3">
            <StatusPulse tone={tone} />
            <div className="text-sm font-semibold tracking-tight">{headerText}</div>
            {status === "running" ? (
              <Loader2 className="h-4 w-4 animate-spin opacity-70" />
            ) : null}
          </div>
          <div className="text-xs text-muted-foreground">
            {job ? `job_id: ${job.job_id}` : "ジョブが開始されるとここに表示されます"}
          </div>
        </div>

        {/* Right actions */}
        <div className="flex items-center gap-2">
          {status === "done" && onViewResult ? (
            <button
              type="button"
              onClick={onViewResult}
              className={cn(
                "inline-flex items-center gap-2 rounded-full border px-4 py-2 text-xs font-semibold",
                "border-[rgba(var(--violet),0.24)] bg-[rgba(var(--violet),0.10)]",
                "hover:shadow-[0_0_0_1px_rgba(var(--violet),0.25),var(--glow-violet)] transition"
              )}
            >
              View Result <ArrowRight className="h-4 w-4 opacity-80" />
            </button>
          ) : null}

          {status === "failed" && onRetry ? (
            <button
              type="button"
              onClick={onRetry}
              className={cn(
                "inline-flex items-center gap-2 rounded-full border px-4 py-2 text-xs font-semibold",
                "border-[rgba(var(--rose),0.24)] bg-[rgba(var(--rose),0.10)]",
                "hover:shadow-[0_0_0_1px_rgba(var(--rose),0.25)] transition"
              )}
            >
              Retry <RotateCcw className="h-4 w-4 opacity-80" />
            </button>
          ) : null}
        </div>
      </div>

      <div className="mt-4">
        <ProgressSteps status={status} />
      </div>

      {(pollingError || job?.error_message) && (
        <div className="mt-4 rounded-[var(--r-md)] border p-3 text-xs"
             style={{ borderColor: "rgba(var(--rose),0.22)", background: "rgba(var(--rose),0.08)" }}>
          <div className="flex items-center gap-2 font-semibold" style={{ color: "rgba(var(--rose),0.95)" }}>
            <AlertTriangle className="h-4 w-4" /> Error
          </div>
          <div className="mt-1 text-muted-foreground">
            {job?.error_message || pollingError}
          </div>
        </div>
      )}

      <div className="mt-4 text-[10px] text-muted-foreground uppercase tracking-[0.18em]">
        {isPolling ? "polling…" : "idle"}
      </div>
    </GlassCard>
  );
}
```

---

## J-5. Run Screen Wiring Example

> run画面で "Run" を押す → job_id発行 → polling開始 → doneで結果ページに誘導。

### J-5.1 Backend small tweak (recommended)

- `GET /analysis-jobs/{job_id}` response に `result_id?: UUID` を追加（status==done時）
- DB: `analysis_results.job_id` を参照して1件取得

### J-5.2 Front code (skeleton)

```tsx
// app/sites/[siteId]/run/RunScreen.tsx
"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import type { UUID, AnalysisJobTarget } from "@/lib/api/types";
import { createAnalysisJob } from "@/lib/api/queries";
import { useJobPoll } from "@/components/run/useJobPoll";
import { JobStatusCard } from "@/components/run/JobStatusCard";
import { RunConfigCard } from "@/components/run/RunConfigCard";
import { TargetSummaryCard } from "@/components/run/TargetSummaryCard";

export function RunScreen({
  siteId,
  targets
}: {
  siteId: UUID;
  targets: {
    official: any;
    competitors: any[];
    thirdParties: any[];
    apiTargets: AnalysisJobTarget[];
  };
}) {
  const router = useRouter();

  const [jobId, setJobId] = React.useState<UUID | null>(null);
  const { job, error, isPolling } = useJobPoll(siteId, jobId);

  // Config states (MVP defaults)
  const [device, setDevice] = React.useState<"mobile" | "desktop">("mobile");
  const [enablePagespeed, setEnablePagespeed] = React.useState(true);
  const [enableGsc, setEnableGsc] = React.useState(false);
  const [gscProperty, setGscProperty] = React.useState("");
  const [brandTerms, setBrandTerms] = React.useState<string[]>([]);
  const [reportStyle, setReportStyle] = React.useState<"consultant" | "concise" | "technical">("consultant");

  const [running, setRunning] = React.useState(false);

  const onRun = async () => {
    setRunning(true);
    try {
      const res = await createAnalysisJob(siteId, {
        device,
        locale: "ja-JP",
        target_country: "JP",
        enable_pagespeed: enablePagespeed,
        enable_gsc: enableGsc,
        enable_ai_report: true,
        gsc_property: enableGsc ? gscProperty : undefined,
        brand_terms: brandTerms,
        targets: targets.apiTargets
      });
      setJobId(res.job_id);
    } finally {
      setRunning(false);
    }
  };

  const onViewResult = () => {
    // If backend provides job.result_id, navigate directly:
    // router.push(`/sites/${siteId}/results/${job.result_id}`);
    router.push(`/sites/${siteId}/results`); // fallback
  };

  const onRetry = () => {
    setJobId(null);
  };

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <div className="space-y-6">
        <RunConfigCard
          device={device}
          onDeviceChange={setDevice}
          enablePagespeed={enablePagespeed}
          onEnablePagespeed={setEnablePagespeed}
          enableGsc={enableGsc}
          onEnableGsc={setEnableGsc}
          gscProperty={gscProperty}
          onGscProperty={setGscProperty}
          brandTerms={brandTerms}
          onBrandTerms={setBrandTerms}
          reportStyle={reportStyle}
          onReportStyle={setReportStyle}
        />

        <button
          type="button"
          onClick={onRun}
          disabled={running || !targets.official || targets.competitors.length !== 2}
          className="w-full rounded-[var(--r-lg)] border px-5 py-4 text-sm font-semibold tracking-wide
                     border-[rgba(var(--cyan),0.22)] bg-[rgba(var(--cyan),0.10)]
                     hover:shadow-[0_0_0_1px_rgba(var(--cyan),0.25),var(--glow-cyan)] transition
                     disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {running ? "Launching…" : "RUN DIAGNOSTIC"}
        </button>

        <JobStatusCard
          job={job}
          pollingError={error}
          isPolling={isPolling}
          onViewResult={job?.status === "done" ? onViewResult : undefined}
          onRetry={job?.status === "failed" ? onRetry : undefined}
        />
      </div>

      <div className="space-y-6">
        <TargetSummaryCard
          official={targets.official}
          competitors={targets.competitors}
          thirdParties={targets.thirdParties}
        />

        <div className="rounded-[var(--r-lg)] border p-5 bg-[rgba(var(--panel),0.06)] border-[rgba(var(--border),0.12)]">
          <div className="text-sm font-semibold">WHAT'S RUNNING</div>
          <ul className="mt-2 space-y-1 text-sm text-muted-foreground">
            <li>• HTML/見出し構造/リンク/構造化データ</li>
            <li>• 速度（PageSpeed）</li>
            <li>• 競合との差分（構造・訴求・技術）</li>
            <li>• 対策ToDo（P0/P1/P2）＋レポート生成</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
```

---

## J-6. Micro-animations (Optional but high impact)

> Tailwindだけで十分。派手すぎず"動いてる感"。

### J-6.1 Add utility animations in globals.css

```css
@keyframes floatUp {
  0% { transform: translateY(0); opacity: 0.7; }
  100% { transform: translateY(-6px); opacity: 1; }
}
.float-up {
  animation: floatUp 220ms ease-out;
}
```

**Usage**: status changes時に header text container に `float-up` を追加

---

## J-7. Acceptance Criteria

- [ ] Runボタン押下で job作成→ status card が表示される
- [ ] queued → running → done が3ステップUIで分かる
- [ ] running中に "パルス + スピナー" が表示される
- [ ] doneで "View Result" CTA が目立つ
- [ ] failedでエラーメッセージ + Retryが出る
- [ ] pollingはdone/failedで停止し、timeoutもある

---

# Appendix K: Estimated Tasks Row (Run button helper)

**Goal**:
- Runボタン直下に「何を・どれくらい」実行するかを1行で提示
- 信頼感＋プロダクト感UP（地味に効く）
- URL数/Pagespeed/GSC/AI report/想定時間（推定）を表示
  - ※時間は"推定"として控えめに（実測で後から改善可能）

**Includes**:
- `components/run/EstimatedTasksRow.tsx`
- wiring snippet for RunScreen

---

## K-1. EstimatedTasksRow Component

> 視認性：小さく、でも読みやすく。monoで数字が締まる。
> 表示は "チップ" で短く。

```tsx
// components/run/EstimatedTasksRow.tsx
"use client";

import * as React from "react";
import { cn } from "@/lib/utils/cn";
import type { DeviceType } from "@/lib/api/types";
import { Zap, Cpu, Search, FileText, Gauge, Smartphone, Monitor } from "lucide-react";

export interface EstimatedTasksRowProps {
  urlCount: number;
  competitorCount: number;
  thirdPartyCount: number;

  device: DeviceType;
  enablePagespeed: boolean;
  enableGsc: boolean;
  enableAiReport: boolean;

  /** Optional: provide real estimate if you have historical data */
  estimatedSeconds?: number | null;
}

function Chip({
  icon,
  children,
  tone = "neutral"
}: {
  icon?: React.ReactNode;
  children: React.ReactNode;
  tone?: "neutral" | "cyan" | "violet" | "amber";
}) {
  const style =
    tone === "cyan"
      ? "border-[rgba(var(--cyan),0.20)] bg-[rgba(var(--cyan),0.08)]"
      : tone === "violet"
      ? "border-[rgba(var(--violet),0.20)] bg-[rgba(var(--violet),0.08)]"
      : tone === "amber"
      ? "border-[rgba(var(--amber),0.20)] bg-[rgba(var(--amber),0.08)]"
      : "border-[rgba(var(--border),0.14)] bg-[rgba(var(--panel),0.06)]";

  return (
    <span
      className={cn(
        "inline-flex items-center gap-2 rounded-full border px-3 py-1",
        "text-[11px] text-muted-foreground",
        style
      )}
    >
      {icon}
      <span className="font-medium">{children}</span>
    </span>
  );
}

function formatEstimate(sec?: number | null) {
  if (!sec || sec <= 0) return "≈ —";
  if (sec < 60) return `≈ ${sec}s`;
  const m = Math.round(sec / 60);
  return `≈ ${m}m`;
}

/**
 * Lightweight estimation (MVP):
 * - base: 8s
 * - per url: +6s
 * - pagespeed: +10s per url
 * - gsc: +8s (official only)
 * - ai report: +6s
 * Clamp: 12s..240s
 */
function estimateSecondsFallback(args: {
  urlCount: number;
  enablePagespeed: boolean;
  enableGsc: boolean;
  enableAiReport: boolean;
}) {
  const base = 8;
  const perUrl = 6 * args.urlCount;
  const ps = args.enablePagespeed ? 10 * args.urlCount : 0;
  const gsc = args.enableGsc ? 8 : 0;
  const ai = args.enableAiReport ? 6 : 0;

  const raw = base + perUrl + ps + gsc + ai;
  return Math.max(12, Math.min(240, raw));
}

export function EstimatedTasksRow(props: EstimatedTasksRowProps) {
  const {
    urlCount,
    competitorCount,
    thirdPartyCount,
    device,
    enablePagespeed,
    enableGsc,
    enableAiReport
  } = props;

  const sec = props.estimatedSeconds ?? estimateSecondsFallback({ urlCount, enablePagespeed, enableGsc, enableAiReport });

  const deviceIcon = device === "mobile" ? <Smartphone className="h-4 w-4 opacity-70" /> : <Monitor className="h-4 w-4 opacity-70" />;

  return (
    <div className="mt-3 flex flex-wrap items-center gap-2">
      <Chip icon={<Zap className="h-4 w-4 opacity-70" />} tone="cyan">
        <span className="font-mono text-[11px]">{urlCount}</span> URLs
      </Chip>

      <Chip icon={<Cpu className="h-4 w-4 opacity-70" />}>
        Competitors <span className="font-mono">{competitorCount}</span>
      </Chip>

      {thirdPartyCount > 0 ? (
        <Chip icon={<Search className="h-4 w-4 opacity-70" />}>
          Third-party <span className="font-mono">{thirdPartyCount}</span>
        </Chip>
      ) : null}

      <Chip icon={deviceIcon}>{device === "mobile" ? "Mobile" : "Desktop"}</Chip>

      {enablePagespeed ? (
        <Chip icon={<Gauge className="h-4 w-4 opacity-70" />} tone="violet">
          PageSpeed ON
        </Chip>
      ) : (
        <Chip icon={<Gauge className="h-4 w-4 opacity-70" />}>PageSpeed OFF</Chip>
      )}

      {enableGsc ? (
        <Chip icon={<Search className="h-4 w-4 opacity-70" />} tone="amber">
          GSC ON
        </Chip>
      ) : (
        <Chip icon={<Search className="h-4 w-4 opacity-70" />}>GSC OFF</Chip>
      )}

      {enableAiReport ? (
        <Chip icon={<FileText className="h-4 w-4 opacity-70" />} tone="cyan">
          AI report ON
        </Chip>
      ) : (
        <Chip icon={<FileText className="h-4 w-4 opacity-70" />}>AI report OFF</Chip>
      )}

      <span className="ml-auto text-[11px] text-muted-foreground-2">
        Estimated <span className="font-mono">{formatEstimate(sec)}</span>
      </span>
    </div>
  );
}
```

---

## K-2. Wiring: Runボタン直下に追加 (RunScreen)

> Runボタンの下に置くのがポイント（押す前に実行内容が分かる）。
> 「3 URLs / pagespeed enabled / AI report enabled」的な信頼感が出ます。

```tsx
import { EstimatedTasksRow } from "@/components/run/EstimatedTasksRow";

/* ...inside RunScreen return... */

<button
  type="button"
  onClick={onRun}
  disabled={running || !targets.official || targets.competitors.length !== 2}
  className="w-full rounded-[var(--r-lg)] border px-5 py-4 text-sm font-semibold tracking-wide
             border-[rgba(var(--cyan),0.22)] bg-[rgba(var(--cyan),0.10)]
             hover:shadow-[0_0_0_1px_rgba(var(--cyan),0.25),var(--glow-cyan)] transition
             disabled:opacity-50 disabled:cursor-not-allowed"
>
  {running ? "Launching…" : "RUN DIAGNOSTIC"}
</button>

<EstimatedTasksRow
  urlCount={1 + targets.competitors.length + targets.thirdParties.length}
  competitorCount={targets.competitors.length}
  thirdPartyCount={targets.thirdParties.length}
  device={device}
  enablePagespeed={enablePagespeed}
  enableGsc={enableGsc}
  enableAiReport={true}
/>
```

---

## K-3. (Optional) Better estimates later

MVPの推定は簡易なので、次の段階で精度UPできます：

1. `analysis_jobs` に `started_at/finished_at` があるので、実測 duration を記録
2. `daily_metrics` とは別に `job_durations` を作るか、jobsに `duration_ms` を保存
3. 直近N回の平均で `estimatedSeconds` を算出して `EstimatedTasksRow` に渡す

---

## K-4. Acceptance Criteria

- [ ] Runボタン直下にチップ群が表示される
- [ ] URL数/Pagespeed/GSC/AI report が一目で分かる
- [ ] 推定時間は "≈" 表記で控えめ（過信させない）

---

# Appendix L: Chips → Checklist Morph (Running Task List)

**Goal**:
- Run前: EstimatedTasksRow（chipsで実行内容の要約）
- Run後: 同じ場所が "Task Checklist" に変形（今どこまで終わったか）
- queued/running/done/failed に応じて
  - 未実行: idle
  - 実行中: running（スピナー/パルス）
  - 完了: done（チェック）
  - 失敗: failed（警告）

**Approach (MVP-friendly)**:
- バックエンド側の詳細進捗が無い場合でも、フェーズ推定で十分"気持ちいい"
- 余裕があれば後で `job.progress` をAPIで返して本物の進捗に差し替え可能

**Includes**:
- `lib/run/progress.ts` (phase mapping + task definitions)
- `components/run/RunTasksMorph.tsx` (chips → checklist)
- `components/run/TaskChecklist.tsx`
- wiring snippet for RunScreen

---

## L-0. Progress Model (MVP)

### L-0.1 JobStatus only (minimum)
- queued / running / done / failed

### L-0.2 Phase (derived locally)

running の時、経過時間でフェーズ推定（*雰囲気でOK*）:
- **phase0**: Fetch & parse HTML
- **phase1**: PageSpeed (optional)
- **phase2**: Comparisons & rule engine
- **phase3**: AI report (optional)

This makes the UI feel alive without backend changes.

**Later upgrade**: backend returns `job.progress = {phase, tasks:[{id,status,detail}...]}`

---

## L-1. Progress Utilities（`lib/run/progress.ts`）

> タスク定義と、job状態/経過時間→タスク状態を推定するロジック。
> 推定時間は thresholds.yml の簡易推定と同じ思想でOK。

```ts
// lib/run/progress.ts
import type { JobStatus } from "@/lib/api/types";

export type TaskState = "idle" | "running" | "done" | "failed";

export interface RunTask {
  id: "fetch" | "structure" | "pagespeed" | "compare" | "todos" | "report";
  label: string;
  sub?: string;
  enabled: boolean;
}

export function buildTasks(opts: {
  urlCount: number;
  enablePagespeed: boolean;
  enableGsc: boolean; // reserved
  enableAiReport: boolean;
}): RunTask[] {
  return [
    { id: "fetch", label: "Fetch pages", sub: `${opts.urlCount} URLs`, enabled: true },
    { id: "structure", label: "Parse structure", sub: "title / headings / links / schema", enabled: true },
    { id: "pagespeed", label: "Run PageSpeed", sub: opts.enablePagespeed ? "enabled" : "skipped", enabled: opts.enablePagespeed },
    { id: "compare", label: "Compare vs competitors", sub: "diff / gaps", enabled: true },
    { id: "todos", label: "Generate ToDos", sub: "P0 / P1 / P2", enabled: true },
    { id: "report", label: "Generate report", sub: opts.enableAiReport ? "AI enabled" : "skipped", enabled: opts.enableAiReport }
  ].filter(t => t.enabled || t.id === "pagespeed" || t.id === "report"); // keep skipped visible if you want
}

/**
 * Derive task states:
 * - queued: all idle
 * - failed: best-effort show running until fail, or mark all failed
 * - done: all done (except skipped -> done/idle policy)
 * - running: estimate phase by elapsed
 */
export function deriveTaskStates(args: {
  jobStatus: JobStatus;
  startedAt?: string | null;
  nowIso?: string; // for testing
  enablePagespeed: boolean;
  enableAiReport: boolean;
}): Record<RunTask["id"], TaskState> {
  const now = args.nowIso ? new Date(args.nowIso).getTime() : Date.now();
  const started = args.startedAt ? new Date(args.startedAt).getTime() : now;
  const elapsed = Math.max(0, now - started);

  const init: Record<RunTask["id"], TaskState> = {
    fetch: "idle",
    structure: "idle",
    pagespeed: "idle",
    compare: "idle",
    todos: "idle",
    report: "idle"
  };

  if (args.jobStatus === "queued") return init;

  if (args.jobStatus === "failed") {
    // Conservative: mark everything failed (or refine if backend provides phase)
    return {
      fetch: "failed",
      structure: "failed",
      pagespeed: args.enablePagespeed ? "failed" : "idle",
      compare: "failed",
      todos: "failed",
      report: args.enableAiReport ? "failed" : "idle"
    };
  }

  if (args.jobStatus === "done") {
    return {
      fetch: "done",
      structure: "done",
      pagespeed: args.enablePagespeed ? "done" : "done", // treat skipped as done for neatness
      compare: "done",
      todos: "done",
      report: args.enableAiReport ? "done" : "done"
    };
  }

  // running: phase estimate by elapsed buckets
  // Tuned for "feels right" (not accuracy).
  const t0 = 6_000;  // fetch
  const t1 = 12_000; // parse
  const t2 = args.enablePagespeed ? 28_000 : 14_000; // pagespeed optional
  const t3 = (args.enablePagespeed ? 38_000 : 24_000); // compare+todos
  const t4 = args.enableAiReport ? (args.enablePagespeed ? 55_000 : 40_000) : (args.enablePagespeed ? 45_000 : 30_000); // report optional

  // Fetch
  if (elapsed < t0) {
    init.fetch = "running";
    return init;
  }
  init.fetch = "done";

  // Parse
  if (elapsed < t1) {
    init.structure = "running";
    return init;
  }
  init.structure = "done";

  // PageSpeed (optional)
  if (args.enablePagespeed) {
    if (elapsed < t2) {
      init.pagespeed = "running";
      return init;
    }
    init.pagespeed = "done";
  } else {
    init.pagespeed = "done"; // skipped but "done" for smooth UI
  }

  // Compare + ToDos
  if (elapsed < t3) {
    init.compare = "running";
    return init;
  }
  init.compare = "done";

  if (elapsed < t4) {
    init.todos = "running";
    return init;
  }
  init.todos = "done";

  // Report
  if (args.enableAiReport) {
    init.report = "running";
  } else {
    init.report = "done";
  }

  return init;
}
```

---

## L-2. TaskChecklist Component

> "今どこまで終わったか" を縦リストで気持ちよく。
> 状態アイコン：idle(○) / running(spinner) / done(check) / failed(alert)

```tsx
// components/run/TaskChecklist.tsx
"use client";

import * as React from "react";
import { cn } from "@/lib/utils/cn";
import type { RunTask, TaskState } from "@/lib/run/progress";
import { Check, Circle, Loader2, AlertTriangle } from "lucide-react";

export interface TaskChecklistProps {
  tasks: RunTask[];
  states: Record<RunTask["id"], TaskState>;
}

function StateIcon({ state }: { state: TaskState }) {
  if (state === "running") return <Loader2 className="h-4 w-4 animate-spin opacity-80" />;
  if (state === "done") return <Check className="h-4 w-4" style={{ color: "rgba(var(--lime),0.95)" }} />;
  if (state === "failed") return <AlertTriangle className="h-4 w-4" style={{ color: "rgba(var(--rose),0.95)" }} />;
  return <Circle className="h-4 w-4 opacity-50" />;
}

export function TaskChecklist({ tasks, states }: TaskChecklistProps) {
  return (
    <div className="space-y-2">
      {tasks.map((t) => {
        const st = states[t.id];
        const active = st === "running";
        const done = st === "done";
        const failed = st === "failed";

        const border = failed
          ? "rgba(var(--rose),0.20)"
          : active
          ? "rgba(var(--cyan),0.22)"
          : "rgba(var(--border),0.12)";

        const bg = failed
          ? "rgba(var(--rose),0.08)"
          : active
          ? "rgba(var(--cyan),0.08)"
          : "rgba(var(--panel),0.05)";

        return (
          <div
            key={t.id}
            className={cn(
              "flex items-start gap-3 rounded-[var(--r-md)] border px-3 py-2",
              "transition-all duration-200 ease-out"
            )}
            style={{ borderColor: border, background: bg }}
          >
            <div className="mt-0.5">
              <StateIcon state={st} />
            </div>
            <div className="min-w-0">
              <div className="text-xs font-semibold tracking-wide">
                {t.label}
                {done && <span className="ml-2 text-[10px] text-muted-foreground uppercase">done</span>}
                {failed && <span className="ml-2 text-[10px] uppercase" style={{ color: "rgba(var(--rose),0.95)" }}>failed</span>}
              </div>
              <div className="text-xs text-muted-foreground-2 truncate">
                {t.sub ?? ""}
              </div>
            </div>
            <div className="ml-auto text-[10px] text-muted-foreground uppercase tracking-[0.18em]">
              {st}
            </div>
          </div>
        );
      })}
    </div>
  );
}
```

---

## L-3. RunTasksMorph Component

> 「押す前: chips」「押した後: checklist」に切り替えるコンテナ。
> - jobIdが無い or status=queuedで未実行: chips
> - running/done/failed: checklist
> - doneなら小さく "View Result" ヒントを出す（主導線はJobStatusCardに任せる）

```tsx
// components/run/RunTasksMorph.tsx
"use client";

import * as React from "react";
import type { AnalysisJob, DeviceType } from "@/lib/api/types";
import { GlassCard } from "@/components/layout/GlassCard";
import { EstimatedTasksRow } from "@/components/run/EstimatedTasksRow";
import { TaskChecklist } from "@/components/run/TaskChecklist";
import { buildTasks, deriveTaskStates } from "@/lib/run/progress";

export interface RunTasksMorphProps {
  job: AnalysisJob | null;
  device: DeviceType;
  enablePagespeed: boolean;
  enableGsc: boolean;
  enableAiReport: boolean;

  urlCount: number;
  competitorCount: number;
  thirdPartyCount: number;
}

export function RunTasksMorph(props: RunTasksMorphProps) {
  const { job } = props;
  const status = job?.status;

  const tasks = React.useMemo(
    () =>
      buildTasks({
        urlCount: props.urlCount,
        enablePagespeed: props.enablePagespeed,
        enableGsc: props.enableGsc,
        enableAiReport: props.enableAiReport
      }),
    [props.urlCount, props.enablePagespeed, props.enableGsc, props.enableAiReport]
  );

  const states = React.useMemo(
    () =>
      deriveTaskStates({
        jobStatus: status ?? "queued",
        startedAt: job?.started_at ?? null,
        enablePagespeed: props.enablePagespeed,
        enableAiReport: props.enableAiReport
      }),
    [status, job?.started_at, props.enablePagespeed, props.enableAiReport]
  );

  // Morph condition:
  const showChecklist = !!job && (status === "running" || status === "done" || status === "failed");

  return (
    <GlassCard className="p-4">
      <div className="flex items-center justify-between">
        <div className="text-xs font-semibold tracking-wide text-muted-foreground">
          {showChecklist ? "TASKS / 実行中" : "ESTIMATED TASKS / 実行内容"}
        </div>
        <div className="text-[10px] text-muted-foreground uppercase tracking-[0.18em]">
          {showChecklist ? status : "preview"}
        </div>
      </div>

      {!showChecklist ? (
        <EstimatedTasksRow
          urlCount={props.urlCount}
          competitorCount={props.competitorCount}
          thirdPartyCount={props.thirdPartyCount}
          device={props.device}
          enablePagespeed={props.enablePagespeed}
          enableGsc={props.enableGsc}
          enableAiReport={props.enableAiReport}
        />
      ) : (
        <div className="mt-3">
          <TaskChecklist tasks={tasks} states={states} />
          {status === "done" ? (
            <div className="mt-3 text-xs text-muted-foreground">
              完了しました。右上の <span className="font-semibold">View Result</span> から結果へ進めます。
            </div>
          ) : null}
        </div>
      )}
    </GlassCard>
  );
}
```

---

## L-4. Wiring: RunScreen に組み込み（Runボタン直下）

> "押す前のchips" は RunTasksMorph に統合されるため、以前の EstimatedTasksRow は置き換え。

```tsx
import { RunTasksMorph } from "@/components/run/RunTasksMorph";

/* ...inside RunScreen return... */

<button
  type="button"
  onClick={onRun}
  disabled={running || !targets.official || targets.competitors.length !== 2}
  className="w-full rounded-[var(--r-lg)] border px-5 py-4 text-sm font-semibold tracking-wide
             border-[rgba(var(--cyan),0.22)] bg-[rgba(var(--cyan),0.10)]
             hover:shadow-[0_0_0_1px_rgba(var(--cyan),0.25),var(--glow-cyan)] transition
             disabled:opacity-50 disabled:cursor-not-allowed"
>
  {running ? "Launching…" : "RUN DIAGNOSTIC"}
</button>

<RunTasksMorph
  job={job}
  device={device}
  enablePagespeed={enablePagespeed}
  enableGsc={enableGsc}
  enableAiReport={true}
  urlCount={1 + targets.competitors.length + targets.thirdParties.length}
  competitorCount={targets.competitors.length}
  thirdPartyCount={targets.thirdParties.length}
/>
```

---

## L-5. (Optional) Backend-driven Real Progress

When ready, add in job response:

```json
"progress": {
  "phase": "fetch|structure|pagespeed|compare|todos|report",
  "tasks": [
    {"id":"fetch","status":"done"},
    {"id":"structure","status":"running"}
  ]
}
```

**Frontend change**: `deriveTaskStates()` を使わず、`job.progress.tasks` をそのまま states にマップ。

---

## L-6. Acceptance Criteria

- [ ] job開始前: chips（Estimated tasks）が表示される
- [ ] job開始後: 同じ位置が checklist に切り替わる（morph）
- [ ] running中: どこが動いてるか一目で分かる（spinner）
- [ ] done: 全チェック + 結果導線のヒントが出る
- [ ] failed: failed表示で原因確認が促される

---

# Appendix M: RunConfigCard / TargetSummaryCard / JobHistoryList

**Scope**:
- Props (TypeScript interfaces)
- UI骨組み（実装寄り）
- 状態管理（RunScreenでの使い方）
- API接続（jobs list / job detail / create job）

**Assumptions**:
- Next.js App Router
- Tailwind
- lucide-react
- `lib/api/queries.ts` が既にある（createAnalysisJob, getJob, listJobs を追加/利用）
- `AnalysisJob` 型に `result_id?: UUID | null` を追加推奨（done時に結果へ直行）

---

## M-0. API追加（jobs list）

### M-0.1 lib/api/types.ts (add)

```ts
export interface AnalysisJobListItem {
  job_id: UUID;
  site_id: UUID;
  status: JobStatus;
  created_at: string;
  started_at?: string | null;
  finished_at?: string | null;
  error_message?: string | null;
  // Recommended:
  result_id?: UUID | null;
}
```

### M-0.2 lib/api/queries.ts (add)

```ts
import type { AnalysisJobListItem } from "./types";
import { apiFetch } from "./client";
import { routes } from "./routes";
import type { UUID } from "./types";

export async function listJobs(siteId: UUID, limit = 20): Promise<{ items: AnalysisJobListItem[] }> {
  return apiFetch(`${routes.jobs(siteId)}?limit=${limit}`);
}
```

### M-0.3 Backend expectation (minimal)

`GET /sites/{site_id}/analysis-jobs?limit=20` returns:

```json
{
  "items": [
    {
      "job_id": "...",
      "status": "done",
      "created_at": "...",
      "finished_at": "...",
      "error_message": null,
      "result_id": "..."
    }
  ]
}
```

---

## M-1. RunConfigCard

### M-1.1 Props

```ts
// components/run/RunConfigCard.types.ts
import type { DeviceType } from "@/lib/api/types";

export interface RunConfigCardProps {
  device: DeviceType;
  onDeviceChange: (v: DeviceType) => void;

  enablePagespeed: boolean;
  onEnablePagespeed: (v: boolean) => void;

  enableGsc: boolean;
  onEnableGsc: (v: boolean) => void;

  gscProperty: string;
  onGscProperty: (v: string) => void;

  brandTerms: string[];
  onBrandTerms: (terms: string[]) => void;

  reportStyle: "consultant" | "concise" | "technical";
  onReportStyle: (v: RunConfigCardProps["reportStyle"]) => void;
}
```

### M-1.2 UI実装（`components/run/RunConfigCard.tsx`）

> 視認性重視：セクション分割＋トグル風ボタン。brand termsは "chips input" 風。

```tsx
// components/run/RunConfigCard.tsx
"use client";

import * as React from "react";
import type { RunConfigCardProps } from "./RunConfigCard.types";
import { GlassCard } from "@/components/layout/GlassCard";
import { cn } from "@/lib/utils/cn";
import { Monitor, Smartphone, Gauge, Search, Sparkles } from "lucide-react";

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <div className="text-xs font-semibold tracking-wide text-muted-foreground">{children}</div>;
}

function TogglePill({
  active,
  label,
  icon,
  onClick
}: {
  active: boolean;
  label: string;
  icon?: React.ReactNode;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "inline-flex items-center gap-2 rounded-full border px-3 py-2 text-xs",
        "border-[rgba(var(--border),0.14)] bg-[rgba(var(--panel),0.06)]",
        active && "shadow-[0_0_0_1px_rgba(var(--cyan),0.25),var(--glow-cyan)]"
      )}
    >
      {icon}
      <span className="font-medium">{label}</span>
    </button>
  );
}

function ChipsInput({
  value,
  onChange,
  placeholder
}: {
  value: string[];
  onChange: (v: string[]) => void;
  placeholder?: string;
}) {
  const [draft, setDraft] = React.useState("");

  const add = () => {
    const t = draft.trim();
    if (!t) return;
    if (value.includes(t)) {
      setDraft("");
      return;
    }
    onChange([...value, t].slice(0, 12));
    setDraft("");
  };

  const remove = (t: string) => onChange(value.filter((x) => x !== t));

  return (
    <div className="rounded-[var(--r-md)] border p-3 bg-[rgba(var(--panel),0.06)] border-[rgba(var(--border),0.12)]">
      <div className="flex flex-wrap gap-2">
        {value.map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => remove(t)}
            className="rounded-full border px-3 py-1 text-xs
                       border-[rgba(var(--border),0.14)] bg-[rgba(var(--panel),0.06)]
                       hover:shadow-[0_0_0_1px_rgba(var(--cyan),0.20)] transition"
            title="クリックで削除"
          >
            {t}
          </button>
        ))}
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              add();
            }
          }}
          placeholder={placeholder}
          className="min-w-[160px] flex-1 bg-transparent text-sm outline-none placeholder:text-[rgba(var(--fg),0.45)]"
        />
        <button
          type="button"
          onClick={add}
          className="rounded-full border px-3 py-1 text-xs
                     border-[rgba(var(--cyan),0.20)] bg-[rgba(var(--cyan),0.08)]
                     hover:shadow-[0_0_0_1px_rgba(var(--cyan),0.22),var(--glow-cyan)] transition"
        >
          Add
        </button>
      </div>
      <div className="mt-2 text-[11px] text-muted-foreground-2">
        例：劇団名 / 社会人演劇 / 地域名（ブランド検索・指名検索の判定に利用）
      </div>
    </div>
  );
}

export function RunConfigCard(props: RunConfigCardProps) {
  return (
    <GlassCard className="p-5">
      <div className="flex items-center justify-between">
        <div className="text-sm font-semibold tracking-tight">RUN CONFIG / 実行設定</div>
        <div className="text-[10px] text-muted-foreground uppercase tracking-[0.18em]">
          MVP
        </div>
      </div>

      {/* Device */}
      <div className="mt-5 space-y-2">
        <SectionTitle>DEVICE</SectionTitle>
        <div className="flex flex-wrap gap-2">
          <TogglePill
            active={props.device === "mobile"}
            label="Mobile"
            icon={<Smartphone className="h-4 w-4 opacity-70" />}
            onClick={() => props.onDeviceChange("mobile")}
          />
          <TogglePill
            active={props.device === "desktop"}
            label="Desktop"
            icon={<Monitor className="h-4 w-4 opacity-70" />}
            onClick={() => props.onDeviceChange("desktop")}
          />
        </div>
      </div>

      {/* Toggles */}
      <div className="mt-5 space-y-2">
        <SectionTitle>OPTIONS</SectionTitle>
        <div className="flex flex-wrap gap-2">
          <TogglePill
            active={props.enablePagespeed}
            label={props.enablePagespeed ? "PageSpeed ON" : "PageSpeed OFF"}
            icon={<Gauge className="h-4 w-4 opacity-70" />}
            onClick={() => props.onEnablePagespeed(!props.enablePagespeed)}
          />
          <TogglePill
            active={props.enableGsc}
            label={props.enableGsc ? "GSC ON" : "GSC OFF"}
            icon={<Search className="h-4 w-4 opacity-70" />}
            onClick={() => props.onEnableGsc(!props.enableGsc)}
          />
          <TogglePill
            active={props.reportStyle === "consultant"}
            label="Consultant"
            icon={<Sparkles className="h-4 w-4 opacity-70" />}
            onClick={() => props.onReportStyle("consultant")}
          />
          <TogglePill
            active={props.reportStyle === "concise"}
            label="Concise"
            onClick={() => props.onReportStyle("concise")}
          />
          <TogglePill
            active={props.reportStyle === "technical"}
            label="Technical"
            onClick={() => props.onReportStyle("technical")}
          />
        </div>
      </div>

      {/* GSC property */}
      {props.enableGsc && (
        <div className="mt-5 space-y-2">
          <SectionTitle>GSC PROPERTY</SectionTitle>
          <div className="rounded-[var(--r-md)] border px-3 py-2 bg-[rgba(var(--panel),0.06)] border-[rgba(var(--border),0.12)]">
            <input
              value={props.gscProperty}
              onChange={(e) => props.onGscProperty(e.target.value)}
              placeholder="例: sc-domain:example.com"
              className="w-full bg-transparent text-sm outline-none placeholder:text-[rgba(var(--fg),0.45)]"
            />
          </div>
          <div className="text-[11px] text-muted-foreground-2">
            Search Console API連携が有効な場合のみ利用されます
          </div>
        </div>
      )}

      {/* Brand terms */}
      <div className="mt-5 space-y-2">
        <SectionTitle>BRAND TERMS</SectionTitle>
        <ChipsInput value={props.brandTerms} onChange={props.onBrandTerms} placeholder="キーワードを入力してEnter…" />
      </div>
    </GlassCard>
  );
}
```

---

## M-2. TargetSummaryCard

### M-2.1 Props

```ts
// components/run/TargetSummaryCard.types.ts
import type { Page } from "@/lib/api/types";

export interface TargetSummaryCardProps {
  official: Page;
  competitors: Page[];     // exactly 2 expected
  thirdParties: Page[];    // optional
}
```

### M-2.2 UI実装（`components/run/TargetSummaryCard.tsx`）

> "実行前の最終確認"。ミスが最も出る箇所なので、強く見せる。

```tsx
// components/run/TargetSummaryCard.tsx
"use client";

import * as React from "react";
import type { TargetSummaryCardProps } from "./TargetSummaryCard.types";
import { GlassCard } from "@/components/layout/GlassCard";
import { cn } from "@/lib/utils/cn";
import { Crown, Swords, Link as LinkIcon } from "lucide-react";

function Row({
  icon,
  title,
  url,
  sub
}: {
  icon: React.ReactNode;
  title: string;
  url: string;
  sub?: string;
}) {
  return (
    <div className="flex items-start gap-3 rounded-[var(--r-md)] border p-3 bg-[rgba(var(--panel),0.06)] border-[rgba(var(--border),0.12)]">
      <div className="mt-0.5">{icon}</div>
      <div className="min-w-0">
        <div className="text-xs font-semibold">{title}</div>
        {sub && <div className="text-[11px] text-muted-foreground">{sub}</div>}
        <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
          <LinkIcon className="h-3.5 w-3.5 opacity-70" />
          <span className="truncate">{url}</span>
        </div>
      </div>
    </div>
  );
}

export function TargetSummaryCard({ official, competitors, thirdParties }: TargetSummaryCardProps) {
  return (
    <GlassCard className="p-5">
      <div className="flex items-center justify-between">
        <div className="text-sm font-semibold tracking-tight">TARGETS / 対象URL</div>
        <div className="text-[10px] text-muted-foreground uppercase tracking-[0.18em]">
          confirm
        </div>
      </div>

      <div className="mt-4 space-y-3">
        <Row
          icon={<Crown className="h-4 w-4" style={{ color: "rgba(var(--cyan),0.95)" }} />}
          title={official.label || "Official"}
          sub="公式サイト（必須）"
          url={official.url}
        />

        {competitors.map((c, idx) => (
          <Row
            key={c.page_id}
            icon={<Swords className="h-4 w-4" style={{ color: "rgba(var(--violet),0.95)" }} />}
            title={c.label || `Competitor ${idx + 1}`}
            sub="競合（必須: 2件）"
            url={c.url}
          />
        ))}

        {thirdParties.length > 0 ? (
          <div className="pt-1">
            <div className="mb-2 text-[11px] text-muted-foreground uppercase tracking-[0.18em]">
              third-party pages
            </div>
            <div className="space-y-2">
              {thirdParties.map((t) => (
                <Row
                  key={t.page_id}
                  icon={<LinkIcon className="h-4 w-4 opacity-80" />}
                  title={t.label || "Third-party"}
                  sub="掲載/紹介ページ（任意）"
                  url={t.url}
                />
              ))}
            </div>
          </div>
        ) : (
          <div className="text-xs text-muted-foreground">
            紹介記事ページは未選択（任意）
          </div>
        )}
      </div>

      <div className="mt-4 text-[11px] text-muted-foreground-2">
        ※ 公式1 / 競合2 の組み合わせがMVPの想定です。対象が違う場合は pages 画面で修正してください。
      </div>
    </GlassCard>
  );
}
```

---

## M-3. JobHistoryList (Run画面の右側、またはResults一覧の簡易版)

### M-3.1 Props

```ts
// components/run/JobHistoryList.types.ts
import type { AnalysisJobListItem, UUID } from "@/lib/api/types";

export interface JobHistoryListProps {
  siteId: UUID;
  items: AnalysisJobListItem[];
  onOpenJob?: (jobId: UUID) => void;
  onOpenResult?: (resultId: UUID) => void;
  onRefresh?: () => Promise<void>;
}
```

### M-3.2 UI実装（`components/run/JobHistoryList.tsx`）

> "運用感"が出る。MVPは最新10件で十分。

```tsx
// components/run/JobHistoryList.tsx
"use client";

import * as React from "react";
import type { JobHistoryListProps } from "./JobHistoryList.types";
import { GlassCard } from "@/components/layout/GlassCard";
import { cn } from "@/lib/utils/cn";
import { RefreshCcw, ArrowRight, AlertTriangle, CheckCircle2, Loader2, Clock } from "lucide-react";

function statusIcon(status: string) {
  if (status === "done") return <CheckCircle2 className="h-4 w-4" style={{ color: "rgba(var(--lime),0.95)" }} />;
  if (status === "failed") return <AlertTriangle className="h-4 w-4" style={{ color: "rgba(var(--rose),0.95)" }} />;
  if (status === "running") return <Loader2 className="h-4 w-4 animate-spin opacity-80" />;
  return <Clock className="h-4 w-4 opacity-70" />;
}

function fmt(iso?: string | null) {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleString();
}

export function JobHistoryList({ items, onOpenJob, onOpenResult, onRefresh }: JobHistoryListProps) {
  return (
    <GlassCard className="p-5">
      <div className="flex items-center justify-between">
        <div className="text-sm font-semibold tracking-tight">JOB HISTORY / 実行履歴</div>
        {onRefresh && (
          <button
            type="button"
            onClick={() => onRefresh()}
            className="rounded-full border px-3 py-2 text-xs
                       border-[rgba(var(--border),0.14)] bg-[rgba(var(--panel),0.06)]
                       hover:shadow-[0_0_0_1px_rgba(var(--cyan),0.20),var(--glow-cyan)] transition"
          >
            <RefreshCcw className="h-4 w-4 opacity-80" />
          </button>
        )}
      </div>

      <div className="mt-4 space-y-2">
        {items.length === 0 ? (
          <div className="text-xs text-muted-foreground">まだ実行履歴がありません</div>
        ) : (
          items.map((j) => (
            <div
              key={j.job_id}
              className="flex items-start gap-3 rounded-[var(--r-md)] border p-3
                         bg-[rgba(var(--panel),0.06)] border-[rgba(var(--border),0.12)]"
            >
              <div className="mt-0.5">{statusIcon(j.status)}</div>

              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between gap-2">
                  <div className="text-xs font-semibold">
                    {j.status.toUpperCase()}
                  </div>
                  <div className="text-[10px] text-muted-foreground uppercase tracking-[0.18em]">
                    {fmt(j.created_at)}
                  </div>
                </div>

                <div className="mt-1 text-[11px] text-muted-foreground">
                  started {fmt(j.started_at)} / finished {fmt(j.finished_at)}
                </div>

                {j.error_message ? (
                  <div className="mt-2 text-xs" style={{ color: "rgba(var(--rose),0.90)" }}>
                    {j.error_message}
                  </div>
                ) : null}
              </div>

              <div className="flex flex-col gap-2">
                {onOpenJob && (
                  <button
                    type="button"
                    onClick={() => onOpenJob(j.job_id)}
                    className="rounded-full border px-3 py-2 text-xs
                               border-[rgba(var(--border),0.14)] bg-[rgba(var(--panel),0.06)]
                               hover:shadow-[0_0_0_1px_rgba(var(--cyan),0.18)] transition"
                  >
                    Job
                  </button>
                )}

                {j.result_id && onOpenResult && (
                  <button
                    type="button"
                    onClick={() => onOpenResult(j.result_id!)}
                    className="rounded-full border px-3 py-2 text-xs font-semibold
                               border-[rgba(var(--violet),0.22)] bg-[rgba(var(--violet),0.10)]
                               hover:shadow-[0_0_0_1px_rgba(var(--violet),0.22),var(--glow-violet)] transition"
                  >
                    Result <ArrowRight className="ml-1 inline h-3.5 w-3.5 opacity-80" />
                  </button>
                )}
              </div>
            </div>
          ))
        )}
      </div>

      <div className="mt-4 text-[10px] text-muted-foreground uppercase tracking-[0.18em]">
        latest {items.length} jobs
      </div>
    </GlassCard>
  );
}
```

---

## M-4. RunScreen 状態管理 + API接続（統合例）

> Run画面に3つを組み込み。右側にTargetSummary + JobHistory を並べるのが"完成度高い"。

```tsx
// app/sites/[siteId]/run/RunScreenMVP.tsx
"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import type { UUID, AnalysisJobTarget, Page, AnalysisJobListItem } from "@/lib/api/types";
import { createAnalysisJob, listJobs } from "@/lib/api/queries";
import { useJobPoll } from "@/components/run/useJobPoll";
import { RunConfigCard } from "@/components/run/RunConfigCard";
import { TargetSummaryCard } from "@/components/run/TargetSummaryCard";
import { JobStatusCard } from "@/components/run/JobStatusCard";
import { JobHistoryList } from "@/components/run/JobHistoryList";
import { RunTasksMorph } from "@/components/run/RunTasksMorph";

export function RunScreenMVP({
  siteId,
  official,
  competitors,
  thirdParties,
  apiTargets
}: {
  siteId: UUID;
  official: Page;
  competitors: Page[];
  thirdParties: Page[];
  apiTargets: AnalysisJobTarget[];
}) {
  const router = useRouter();

  // Config
  const [device, setDevice] = React.useState<"mobile" | "desktop">("mobile");
  const [enablePagespeed, setEnablePagespeed] = React.useState(true);
  const [enableGsc, setEnableGsc] = React.useState(false);
  const [gscProperty, setGscProperty] = React.useState("");
  const [brandTerms, setBrandTerms] = React.useState<string[]>([]);
  const [reportStyle, setReportStyle] = React.useState<"consultant" | "concise" | "technical">("consultant");

  // Job
  const [jobId, setJobId] = React.useState<UUID | null>(null);
  const { job, error, isPolling } = useJobPoll(siteId, jobId);

  // History
  const [history, setHistory] = React.useState<AnalysisJobListItem[]>([]);
  const [historyLoading, setHistoryLoading] = React.useState(false);

  const refreshHistory = async () => {
    setHistoryLoading(true);
    try {
      const res = await listJobs(siteId, 10);
      setHistory(res.items);
    } finally {
      setHistoryLoading(false);
    }
  };

  React.useEffect(() => {
    refreshHistory();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [siteId]);

  // Run button
  const [running, setRunning] = React.useState(false);
  const onRun = async () => {
    setRunning(true);
    try {
      const res = await createAnalysisJob(siteId, {
        device,
        locale: "ja-JP",
        target_country: "JP",
        enable_pagespeed: enablePagespeed,
        enable_gsc: enableGsc,
        enable_ai_report: true,
        gsc_property: enableGsc ? gscProperty : undefined,
        brand_terms: brandTerms,
        targets: apiTargets
      });
      setJobId(res.job_id as UUID);
      refreshHistory();
    } finally {
      setRunning(false);
    }
  };

  const onViewResult = () => {
    // recommended: job has result_id when done
    // if not, fallback to results list
    // @ts-ignore
    const rid = (job as any)?.result_id;
    if (rid) router.push(`/sites/${siteId}/results/${rid}`);
    else router.push(`/sites/${siteId}/results`);
  };

  const urlCount = 1 + competitors.length + thirdParties.length;

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      {/* Left: config + run */}
      <div className="space-y-6">
        <RunConfigCard
          device={device}
          onDeviceChange={setDevice}
          enablePagespeed={enablePagespeed}
          onEnablePagespeed={setEnablePagespeed}
          enableGsc={enableGsc}
          onEnableGsc={setEnableGsc}
          gscProperty={gscProperty}
          onGscProperty={setGscProperty}
          brandTerms={brandTerms}
          onBrandTerms={setBrandTerms}
          reportStyle={reportStyle}
          onReportStyle={setReportStyle}
        />

        <button
          type="button"
          onClick={onRun}
          disabled={running || competitors.length !== 2}
          className="w-full rounded-[var(--r-lg)] border px-5 py-4 text-sm font-semibold tracking-wide
                     border-[rgba(var(--cyan),0.22)] bg-[rgba(var(--cyan),0.10)]
                     hover:shadow-[0_0_0_1px_rgba(var(--cyan),0.25),var(--glow-cyan)] transition
                     disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {running ? "Launching…" : "RUN DIAGNOSTIC"}
        </button>

        {/* Morph row: preview → checklist */}
        <RunTasksMorph
          job={job}
          device={device}
          enablePagespeed={enablePagespeed}
          enableGsc={enableGsc}
          enableAiReport={true}
          urlCount={urlCount}
          competitorCount={competitors.length}
          thirdPartyCount={thirdParties.length}
        />

        <JobStatusCard
          job={job}
          pollingError={error}
          isPolling={isPolling}
          onViewResult={job?.status === "done" ? onViewResult : undefined}
          onRetry={job?.status === "failed" ? () => setJobId(null) : undefined}
        />
      </div>

      {/* Right: targets + history */}
      <div className="space-y-6">
        <TargetSummaryCard official={official} competitors={competitors} thirdParties={thirdParties} />

        <JobHistoryList
          siteId={siteId}
          items={history}
          onRefresh={refreshHistory}
          onOpenJob={(jid) => setJobId(jid)}
          onOpenResult={(rid) => router.push(`/sites/${siteId}/results/${rid}`)}
        />
      </div>
    </div>
  );
}
```

---

## M-5. Acceptance Criteria

### RunConfigCard
- [ ] device/Pagespeed/GSC/reportStyle/brandTerms が操作できる
- [ ] enableGsc=true で property入力欄が出る

### TargetSummaryCard
- [ ] 公式1/競合2/紹介（任意）のURLが一覧で確認できる

### JobHistoryList
- [ ] 最新10件が表示され、status/datetimeが分かる
- [ ] doneの場合 Resultボタンが出て結果へ遷移できる
- [ ] クリックで過去jobを再表示（jobIdセット）できる

### RunScreenMVP
- [ ] Create job → polling → done で結果導線が出る
- [ ] preview chips → checklist に自然に変形する

---

# Appendix N: RunConfig Presets (Default / Fast / Deep)

**Goal**:
- RunConfigCard 右上に "Preset" を追加（ResultHeaderと同じ雰囲気）
- 1クリックで設定を切り替え（pagespeed / gsc / reportStyle / device など）
- UX:
  - 現在の設定がどのPresetに近いかが分かる（active表示）
  - 適用時に小さくフィードバック（"Preset applied"）

**Includes**:
- Preset definition (`lib/run/presets.ts`)
- PresetPills UI (`components/run/RunPresetPills.tsx`)
- RunConfigCard integration snippet

---

## N-1. Preset Definitions（`lib/run/presets.ts`）

> MVPのpreset定義。後でconfig化も可能（server側で返すでもOK）。

```ts
// lib/run/presets.ts
import type { DeviceType } from "@/lib/api/types";
import type { RunConfigCardProps } from "@/components/run/RunConfigCard.types";

export type RunPresetKey = "default" | "fast" | "deep";

export interface RunPreset {
  key: RunPresetKey;
  label: string;
  sub: string;
  apply: {
    device?: DeviceType;
    enablePagespeed?: boolean;
    enableGsc?: boolean;
    reportStyle?: RunConfigCardProps["reportStyle"];
  };
}

export const RUN_PRESETS: RunPreset[] = [
  {
    key: "default",
    label: "Default",
    sub: "balanced",
    apply: {
      device: "mobile",
      enablePagespeed: true,
      enableGsc: false,
      reportStyle: "consultant"
    }
  },
  {
    key: "fast",
    label: "Fast",
    sub: "quick check",
    apply: {
      device: "mobile",
      enablePagespeed: false,
      enableGsc: false,
      reportStyle: "concise"
    }
  },
  {
    key: "deep",
    label: "Deep",
    sub: "thorough",
    apply: {
      device: "desktop",
      enablePagespeed: true,
      enableGsc: true,
      reportStyle: "technical"
    }
  }
];

export function detectPreset(current: {
  device: DeviceType;
  enablePagespeed: boolean;
  enableGsc: boolean;
  reportStyle: RunConfigCardProps["reportStyle"];
}): RunPresetKey | null {
  const match = RUN_PRESETS.find((p) => {
    const a = p.apply;
    return (
      (a.device ?? current.device) === current.device &&
      (a.enablePagespeed ?? current.enablePagespeed) === current.enablePagespeed &&
      (a.enableGsc ?? current.enableGsc) === current.enableGsc &&
      (a.reportStyle ?? current.reportStyle) === current.reportStyle
    );
  });
  return match?.key ?? null;
}
```

---

## N-2. RunPresetPills Component

> ResultHeaderのActionボタンに近い "丸ピル" スタイル。
> active時はネオンの輪郭。

```tsx
// components/run/RunPresetPills.tsx
"use client";

import * as React from "react";
import { cn } from "@/lib/utils/cn";
import { RUN_PRESETS, detectPreset, type RunPresetKey } from "@/lib/run/presets";
import { Zap, Layers, SlidersHorizontal, Check } from "lucide-react";

export interface RunPresetPillsProps {
  value: {
    device: "mobile" | "desktop";
    enablePagespeed: boolean;
    enableGsc: boolean;
    reportStyle: "consultant" | "concise" | "technical";
  };
  onApplyPreset: (key: RunPresetKey) => void;
}

function presetIcon(key: RunPresetKey) {
  if (key === "fast") return <Zap className="h-4 w-4 opacity-80" />;
  if (key === "deep") return <Layers className="h-4 w-4 opacity-80" />;
  return <SlidersHorizontal className="h-4 w-4 opacity-80" />;
}

export function RunPresetPills({ value, onApplyPreset }: RunPresetPillsProps) {
  const active = detectPreset(value);
  const [applied, setApplied] = React.useState<RunPresetKey | null>(null);

  const apply = (k: RunPresetKey) => {
    onApplyPreset(k);
    setApplied(k);
    setTimeout(() => setApplied(null), 900);
  };

  return (
    <div className="flex items-center gap-2">
      <div className="text-[10px] text-muted-foreground uppercase tracking-[0.18em] mr-1">
        Preset
      </div>

      {RUN_PRESETS.map((p) => {
        const isActive = active === p.key;
        const justApplied = applied === p.key;

        return (
          <button
            key={p.key}
            type="button"
            onClick={() => apply(p.key)}
            className={cn(
              "inline-flex items-center gap-2 rounded-full border px-3 py-2 text-xs",
              "border-[rgba(var(--border),0.14)] bg-[rgba(var(--panel),0.06)]",
              "hover:shadow-[0_0_0_1px_rgba(var(--cyan),0.18),var(--glow-cyan)] transition",
              isActive && "shadow-[0_0_0_1px_rgba(var(--cyan),0.25),var(--glow-cyan)]"
            )}
            title={`${p.label} — ${p.sub}`}
          >
            {justApplied ? <Check className="h-4 w-4 opacity-80" /> : presetIcon(p.key)}
            <span className="font-medium">{p.label}</span>
            <span className="text-[10px] text-muted-foreground uppercase tracking-wider">{p.sub}</span>
          </button>
        );
      })}
    </div>
  );
}
```

---

## N-3. RunConfigCard Integration

### N-3.1 RunConfigCardProps 追加（推奨）

```ts
export interface RunConfigCardProps {
  /* existing... */
  // Add optional preset apply hook
  onApplyPreset?: (key: "default" | "fast" | "deep") => void;
}
```

### N-3.2 RunConfigCard.tsx のヘッダー差し替え例

> RunConfigCard のヘッダー右側にPresetを表示。
> apply時は props の setter を呼ぶだけ。

```tsx
import { RunPresetPills } from "@/components/run/RunPresetPills";
import { RUN_PRESETS } from "@/lib/run/presets";

/* inside RunConfigCard component header */
<div className="flex items-center justify-between">
  <div className="text-sm font-semibold tracking-tight">RUN CONFIG / 実行設定</div>

  <RunPresetPills
    value={{
      device: props.device,
      enablePagespeed: props.enablePagespeed,
      enableGsc: props.enableGsc,
      reportStyle: props.reportStyle
    }}
    onApplyPreset={(key) => {
      const preset = RUN_PRESETS.find((p) => p.key === key)!;

      if (preset.apply.device) props.onDeviceChange(preset.apply.device);
      if (typeof preset.apply.enablePagespeed === "boolean") props.onEnablePagespeed(preset.apply.enablePagespeed);
      if (typeof preset.apply.enableGsc === "boolean") props.onEnableGsc(preset.apply.enableGsc);
      if (preset.apply.reportStyle) props.onReportStyle(preset.apply.reportStyle);

      // optional: deep preset + empty property -> hint value
      if (key === "deep" && !props.gscProperty) {
        props.onGscProperty("sc-domain:");
      }

      props.onApplyPreset?.(key);
    }}
  />
</div>
```

---

## N-4. RunScreen Wiring (state management)

> RunConfigCardに `onApplyPreset` を渡せば、必要ならログやUI通知に使える。

```tsx
<RunConfigCard
  device={device}
  onDeviceChange={setDevice}
  enablePagespeed={enablePagespeed}
  onEnablePagespeed={setEnablePagespeed}
  enableGsc={enableGsc}
  onEnableGsc={setEnableGsc}
  gscProperty={gscProperty}
  onGscProperty={setGscProperty}
  brandTerms={brandTerms}
  onBrandTerms={setBrandTerms}
  reportStyle={reportStyle}
  onReportStyle={setReportStyle}
  onApplyPreset={(key) => {
    // optional: analytics/log
    // console.log("Preset applied:", key);
  }}
/>
```

---

## N-5. UX Notes (重要)

- **Presetは "強制" ではなく "ショートカット"**
  - ユーザーは適用後に細かくトグルを変更できる
- **Active判定は `detectPreset()` で自動**（気持ち良い）
- **GSCは環境によって使えない場合がある**
  - Deepを押しても "GSC ON だけど未連携なら無効化" はバック側で安全に処理

---

## N-6. Acceptance Criteria

- [ ] RunConfigCard右上に Preset pills が表示
- [ ] クリックで device/pagespeed/gsc/reportStyle が即反映
- [ ] 現在設定がPreset一致なら active 表示になる
- [ ] Deep適用時に gscProperty が空なら `sc-domain:` が入る（任意）

---

# Appendix O: PageEditModal (URL編集 / 削除)

**Scope**:
- ページURLの編集・ラベル変更・ページタイプ変更
- 削除（確認付き）
- 運用事故防止（dirty state / confirm）
- API接続（PATCH / DELETE）

**Target**:
- Next.js App Router
- Tailwind
- lucide-react
- shadcn/ui Dialog（※未使用でも動く設計）

---

## O-0. 位置づけ（重要）

PageEditModal は **P0必須UI**。

- URL登録ミス
- 競合URLの差し替え
- ラベル修正
- 不要ページの削除

これが無いと **DB直編集 or 作り直し** が発生するため、MVPでも必ず入れる。

---

## O-1. Props 定義

```ts
// components/pages/PageEditModal.types.ts
import type { Page, PageType, UUID } from "@/lib/api/types";

export interface PageEditModalProps {
  open: boolean;
  onOpenChange: (v: boolean) => void;

  page: Page | null;

  onSaved?: (page: Page) => void;
  onDeleted?: (pageId: UUID) => void;
}
```

---

## O-2. API 接続（既存APIの利用）

**利用する既存エンドポイント**:
- `PATCH /sites/{site_id}/pages/{page_id}`
- `DELETE /sites/{site_id}/pages/{page_id}`

※ `lib/api/queries.ts` に既に以下がある前提:

```ts
updatePage(siteId, pageId, input)
deletePage(siteId, pageId)
```

---

## O-3. UI 実装

```tsx
// components/pages/PageEditModal.tsx
"use client";

import * as React from "react";
import type { PageEditModalProps } from "./PageEditModal.types";
import { updatePage, deletePage } from "@/lib/api/queries";
import { GlassCard } from "@/components/layout/GlassCard";
import { cn } from "@/lib/utils/cn";
import { X, Trash2, Save, AlertTriangle } from "lucide-react";

const PAGE_TYPES = [
  { value: "official_homepage", label: "公式ホームページ" },
  { value: "competitor_page", label: "競合ページ" },
  { value: "third_party_profile_page", label: "紹介・掲載ページ" }
] as const;

export function PageEditModal({
  open,
  onOpenChange,
  page,
  onSaved,
  onDeleted
}: PageEditModalProps) {
  const [url, setUrl] = React.useState("");
  const [label, setLabel] = React.useState("");
  const [pageType, setPageType] = React.useState<PageEditModalProps["page"] extends infer P ? any : any>();
  const [saving, setSaving] = React.useState(false);
  const [deleting, setDeleting] = React.useState(false);
  const [confirmDelete, setConfirmDelete] = React.useState(false);

  const [dirty, setDirty] = React.useState(false);

  React.useEffect(() => {
    if (!page) return;
    setUrl(page.url);
    setLabel(page.label ?? "");
    setPageType(page.page_type);
    setDirty(false);
    setConfirmDelete(false);
  }, [page, open]);

  if (!open || !page) return null;

  const canSave =
    dirty &&
    url.trim().length > 0 &&
    pageType;

  const onClose = () => {
    if (dirty && !confirmDelete) {
      const ok = window.confirm("変更が保存されていません。閉じてもよいですか？");
      if (!ok) return;
    }
    onOpenChange(false);
  };

  const onSave = async () => {
    setSaving(true);
    try {
      const updated = await updatePage(page.site_id, page.page_id, {
        label: label || null,
        page_type: pageType,
        url
      });
      onSaved?.(updated);
      onOpenChange(false);
    } finally {
      setSaving(false);
    }
  };

  const onDelete = async () => {
    if (!confirmDelete) {
      setConfirmDelete(true);
      return;
    }
    setDeleting(true);
    try {
      await deletePage(page.site_id, page.page_id);
      onDeleted?.(page.page_id);
      onOpenChange(false);
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50">
      {/* overlay */}
      <div
        className="absolute inset-0 bg-black/60"
        onClick={onClose}
      />

      {/* modal */}
      <div className="absolute left-1/2 top-1/2 w-[min(520px,calc(100%-24px))] -translate-x-1/2 -translate-y-1/2 p-2">
        <GlassCard className="p-5">
          {/* header */}
          <div className="flex items-start justify-between gap-3">
            <div>
              <div className="text-sm font-semibold tracking-tight">
                PAGE EDIT / ページ編集
              </div>
              <div className="mt-1 text-xs text-muted-foreground">
                URL・種別・ラベルを変更できます
              </div>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="rounded-full border px-3 py-2 text-xs
                         border-[rgba(var(--border),0.14)] bg-[rgba(var(--panel),0.06)]
                         hover:shadow-[0_0_0_1px_rgba(var(--cyan),0.18)] transition"
            >
              <X className="h-4 w-4 opacity-80" />
            </button>
          </div>

          {/* form */}
          <div className="mt-5 space-y-4">
            {/* URL */}
            <div className="space-y-1">
              <div className="text-xs font-semibold text-muted-foreground">URL</div>
              <input
                value={url}
                onChange={(e) => {
                  setUrl(e.target.value);
                  setDirty(true);
                }}
                className="w-full rounded-[var(--r-md)] border px-3 py-2 text-sm
                           bg-[rgba(var(--panel),0.06)] border-[rgba(var(--border),0.12)]
                           outline-none"
              />
            </div>

            {/* Label */}
            <div className="space-y-1">
              <div className="text-xs font-semibold text-muted-foreground">LABEL（任意）</div>
              <input
                value={label}
                onChange={(e) => {
                  setLabel(e.target.value);
                  setDirty(true);
                }}
                placeholder="例：公式トップ / 劇団A"
                className="w-full rounded-[var(--r-md)] border px-3 py-2 text-sm
                           bg-[rgba(var(--panel),0.06)] border-[rgba(var(--border),0.12)]
                           outline-none placeholder:text-[rgba(var(--fg),0.45)]"
              />
            </div>

            {/* Page type */}
            <div className="space-y-1">
              <div className="text-xs font-semibold text-muted-foreground">PAGE TYPE</div>
              <div className="flex flex-wrap gap-2">
                {PAGE_TYPES.map((t) => (
                  <button
                    key={t.value}
                    type="button"
                    onClick={() => {
                      setPageType(t.value);
                      setDirty(true);
                    }}
                    className={cn(
                      "rounded-full border px-3 py-2 text-xs",
                      "border-[rgba(var(--border),0.14)] bg-[rgba(var(--panel),0.06)]",
                      pageType === t.value &&
                        "shadow-[0_0_0_1px_rgba(var(--cyan),0.25),var(--glow-cyan)]"
                    )}
                  >
                    {t.label}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* footer */}
          <div className="mt-6 flex items-center justify-between gap-3">
            {/* delete */}
            <button
              type="button"
              onClick={onDelete}
              disabled={deleting}
              className={cn(
                "inline-flex items-center gap-2 rounded-full border px-3 py-2 text-xs",
                "border-[rgba(var(--rose),0.22)] bg-[rgba(var(--rose),0.10)]",
                "hover:shadow-[0_0_0_1px_rgba(var(--rose),0.25)] transition"
              )}
            >
              {confirmDelete ? (
                <>
                  <AlertTriangle className="h-4 w-4" />
                  本当に削除
                </>
              ) : (
                <>
                  <Trash2 className="h-4 w-4" />
                  削除
                </>
              )}
            </button>

            {/* save */}
            <button
              type="button"
              onClick={onSave}
              disabled={!canSave || saving}
              className={cn(
                "inline-flex items-center gap-2 rounded-full border px-4 py-2 text-xs font-semibold",
                "border-[rgba(var(--cyan),0.22)] bg-[rgba(var(--cyan),0.10)]",
                "hover:shadow-[0_0_0_1px_rgba(var(--cyan),0.25),var(--glow-cyan)] transition",
                "disabled:opacity-50 disabled:cursor-not-allowed"
              )}
            >
              <Save className="h-4 w-4 opacity-80" />
              保存
            </button>
          </div>

          {dirty && (
            <div className="mt-3 text-[11px] text-muted-foreground">
              ※ 変更があります。保存してから閉じてください。
            </div>
          )}
        </GlassCard>
      </div>
    </div>
  );
}
```

---

## O-4. PagesTable からの呼び出し例

```tsx
// components/pages/PagesTable.tsx（抜粋）

const [editPage, setEditPage] = useState<Page | null>(null);
const [editOpen, setEditOpen] = useState(false);

/* row action */
<button
  type="button"
  onClick={() => {
    setEditPage(p);
    setEditOpen(true);
  }}
>
  Edit
</button>

<PageEditModal
  open={editOpen}
  page={editPage}
  onOpenChange={setEditOpen}
  onSaved={(updated) => {
    // local state update or refetch
  }}
  onDeleted={(pageId) => {
    // remove from local list or refetch
  }}
/>
```

---

## O-5. Acceptance Criteria

- [ ] URL / label / page_type が編集できる
- [ ] 変更がある状態で閉じようとすると警告
- [ ] 削除は2段階確認
- [ ] 保存・削除後に親状態が更新される
- [ ] GlassCard / Midnight Neon のデザインに統一されている

---

# Appendix P: SiteCreateWizard (新規サイト作成ウィザード)

**Scope**:
- サイト新規作成の "最初の体験" をウィザード化
- 事故防止：入力漏れ/不正URL/導線不足を減らす
- MVP: 3 steps
  1) Site info（名前/説明）
  2) Pages seed（公式URL + 競合2 + 任意の紹介ページ）
  3) Review & Create（作成→Runへ誘導）

**Target**:
- Next.js App Router
- Tailwind
- lucide-react
- 既存UI: GlassCard / Midnight Neon
- API: createSite, createPages (bulk) もしくは createPage を複数回

---

## P-0. 前提API（MVPで必要）

### P-0.1 Required endpoints
- `POST /sites` → site作成
- `POST /sites/{site_id}/pages:bulk`（推奨） or `POST /sites/{site_id}/pages` を複数回
- (optional) `GET /sites/{site_id}`

### P-0.2 Types (lib/api/types.ts)

```ts
export type PageType = "official_homepage" | "competitor_page" | "third_party_profile_page";
export type DeviceType = "mobile" | "desktop";

export interface Site {
  site_id: UUID;
  name: string;
  description?: string | null;
  created_at: string;
}

export interface CreateSiteInput {
  name: string;
  description?: string | null;
}

export interface CreatePageInput {
  url: string;
  label?: string | null;
  page_type: PageType;
}

export interface CreatePagesBulkInput {
  pages: CreatePageInput[];
}
```

### P-0.3 Queries (lib/api/queries.ts)

```ts
import type { Site, CreateSiteInput, CreatePagesBulkInput, Page } from "./types";
import { apiFetch } from "./client";
import { routes } from "./routes";
import type { UUID } from "./types";

export async function createSite(input: CreateSiteInput): Promise<Site> {
  return apiFetch(routes.sites(), { method: "POST", body: JSON.stringify(input) });
}

// Recommended bulk
export async function createPagesBulk(siteId: UUID, input: CreatePagesBulkInput): Promise<{ items: Page[] }> {
  return apiFetch(routes.pagesBulk(siteId), { method: "POST", body: JSON.stringify(input) });
}

// Fallback: single
export async function createPage(siteId: UUID, input: any): Promise<Page> {
  return apiFetch(routes.pages(siteId), { method: "POST", body: JSON.stringify(input) });
}
```

### P-0.4 Routes (lib/api/routes.ts)

```ts
export const routes = {
  sites: () => `/sites`,
  pages: (siteId: UUID) => `/sites/${siteId}/pages`,
  pagesBulk: (siteId: UUID) => `/sites/${siteId}/pages:bulk`,
};
```

---

## P-1. Wizard UX 仕様

### P-1.1 Steps
- **Step 1: Site Info**
  - name (required)
  - description (optional)
- **Step 2: Seed Pages**
  - official_url (required, 1)
  - competitor_urls (required, 2)
  - third_party_urls (optional, 0..5)
- **Step 3: Review & Create**
  - 入力内容の確認
  - Create実行
  - 完了後「Run画面へ」導線（/sites/{siteId}/run）

### P-1.2 Validation Rules (MVP)
- URLは http:// or https:// で始まる
- competitor_urls は ちょうど2件
- official_url は competitor と重複不可
- 同一URL重複禁止
- third_party_urls は空行を許可（入力中のUX）

---

## P-2. Props 定義

```ts
// components/sites/SiteCreateWizard.types.ts
export interface SiteCreateWizardProps {
  open: boolean;
  onOpenChange: (v: boolean) => void;

  /** create完了時 */
  onCreated?: (siteId: string) => void;

  /** create後にrunへ飛ばす場合 */
  navigateToRun?: boolean;
}
```

---

## P-3. Helper: URL validation / normalize

```ts
// lib/utils/url.ts
export function normalizeUrl(raw: string) {
  return raw.trim();
}

export function isValidHttpUrl(raw: string) {
  const s = raw.trim();
  if (!/^https?:\/\//i.test(s)) return false;
  try {
    new URL(s);
    return true;
  } catch {
    return false;
  }
}
```

---

## P-4. UI コンポーネント

### P-4.1 WizardStepper

```tsx
// components/sites/WizardStepper.tsx
import * as React from "react";
import { cn } from "@/lib/utils/cn";
import { Check } from "lucide-react";

export interface WizardStepperProps {
  step: number; // 1..3
}

export function WizardStepper({ step }: WizardStepperProps) {
  const steps = [
    { n: 1, label: "Site Info" },
    { n: 2, label: "Seed Pages" },
    { n: 3, label: "Review" },
  ];

  return (
    <div className="grid grid-cols-3 gap-2">
      {steps.map((s) => {
        const done = step > s.n;
        const active = step === s.n;

        return (
          <div
            key={s.n}
            className={cn(
              "rounded-[var(--r-md)] border px-3 py-2 bg-[rgba(var(--panel),0.06)]",
              "border-[rgba(var(--border),0.12)]",
              active && "shadow-[0_0_0_1px_rgba(var(--cyan),0.22),var(--glow-cyan)]"
            )}
          >
            <div className="flex items-center justify-between">
              <div className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
                Step {s.n}
              </div>
              {done ? (
                <span className="inline-flex items-center gap-1 text-[10px]"
                      style={{ color: "rgba(var(--lime),0.95)" }}>
                  <Check className="h-3 w-3" /> OK
                </span>
              ) : null}
            </div>
            <div className="text-xs font-semibold">{s.label}</div>
          </div>
        );
      })}
    </div>
  );
}
```

### P-4.2 UrlRowsInput

複数URL入力用。空行を許可しつつ、正規化・削除もできる。

```tsx
// components/sites/UrlRowsInput.tsx
"use client";

import * as React from "react";
import { cn } from "@/lib/utils/cn";
import { Plus, X } from "lucide-react";
import { isValidHttpUrl, normalizeUrl } from "@/lib/utils/url";

export interface UrlRowsInputProps {
  label: string;
  hint?: string;
  rows: string[];
  onChange: (rows: string[]) => void;
  requiredCount?: number;     // if set, show count hint
  maxCount?: number;          // optional
  allowEmptyRows?: boolean;   // default true
}

export function UrlRowsInput({
  label,
  hint,
  rows,
  onChange,
  requiredCount,
  maxCount = 8,
  allowEmptyRows = true
}: UrlRowsInputProps) {
  const setRow = (idx: number, v: string) => {
    const next = [...rows];
    next[idx] = v;
    onChange(next);
  };

  const addRow = () => {
    if (rows.length >= maxCount) return;
    onChange([...rows, ""]);
  };

  const removeRow = (idx: number) => {
    const next = rows.filter((_, i) => i !== idx);
    onChange(next.length === 0 ? [""] : next);
  };

  const normalizeAll = () => {
    const next = rows.map((r) => normalizeUrl(r));
    onChange(next);
  };

  return (
    <div className="space-y-2">
      <div className="flex items-baseline justify-between">
        <div className="text-xs font-semibold text-muted-foreground">{label}</div>
        {requiredCount != null ? (
          <div className="text-[10px] text-muted-foreground uppercase tracking-[0.18em]">
            {rows.filter((r) => r.trim()).length}/{requiredCount}
          </div>
        ) : null}
      </div>

      <div className="space-y-2">
        {rows.map((r, idx) => {
          const trimmed = r.trim();
          const showErr = trimmed.length > 0 && !isValidHttpUrl(trimmed);

          return (
            <div key={idx} className="flex items-center gap-2">
              <input
                value={r}
                onChange={(e) => setRow(idx, e.target.value)}
                onBlur={normalizeAll}
                placeholder="https://example.com/..."
                className={cn(
                  "w-full rounded-[var(--r-md)] border px-3 py-2 text-sm outline-none",
                  "bg-[rgba(var(--panel),0.06)] border-[rgba(var(--border),0.12)]",
                  showErr && "border-[rgba(var(--rose),0.35)]"
                )}
              />
              <button
                type="button"
                onClick={() => removeRow(idx)}
                className="rounded-full border px-3 py-2 text-xs
                           border-[rgba(var(--border),0.14)] bg-[rgba(var(--panel),0.06)]
                           hover:shadow-[0_0_0_1px_rgba(var(--cyan),0.18)] transition"
                title="削除"
              >
                <X className="h-4 w-4 opacity-75" />
              </button>
            </div>
          );
        })}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={addRow}
          disabled={rows.length >= maxCount}
          className="inline-flex items-center gap-2 rounded-full border px-3 py-2 text-xs
                     border-[rgba(var(--cyan),0.20)] bg-[rgba(var(--cyan),0.08)]
                     hover:shadow-[0_0_0_1px_rgba(var(--cyan),0.22),var(--glow-cyan)] transition
                     disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Plus className="h-4 w-4 opacity-80" />
          Add row
        </button>

        {hint ? (
          <div className="text-[11px] text-muted-foreground-2">{hint}</div>
        ) : null}
      </div>

      {allowEmptyRows ? (
        <div className="text-[11px] text-muted-foreground-2">
          ※ 空行は無視されます（入力途中OK）
        </div>
      ) : null}
    </div>
  );
}
```

---

## P-5. SiteCreateWizard 実装

```tsx
// components/sites/SiteCreateWizard.tsx
"use client";

import * as React from "react";
import type { SiteCreateWizardProps } from "./SiteCreateWizard.types";
import { GlassCard } from "@/components/layout/GlassCard";
import { WizardStepper } from "@/components/sites/WizardStepper";
import { UrlRowsInput } from "@/components/sites/UrlRowsInput";
import { cn } from "@/lib/utils/cn";
import { isValidHttpUrl, normalizeUrl } from "@/lib/utils/url";
import { createSite, createPagesBulk, createPage } from "@/lib/api/queries";
import { useRouter } from "next/navigation";
import { X, ArrowRight, Sparkles, AlertTriangle } from "lucide-react";
import type { CreatePageInput, PageType } from "@/lib/api/types";

type Step = 1 | 2 | 3;

function uniqueNonEmpty(urls: string[]) {
  const set = new Set<string>();
  for (const u of urls.map(normalizeUrl)) {
    if (!u) continue;
    set.add(u);
  }
  return [...set];
}

function buildPagesPayload(args: {
  officialUrl: string;
  competitorUrls: string[];
  thirdPartyUrls: string[];
}): CreatePageInput[] {
  const pages: CreatePageInput[] = [];

  pages.push({
    url: args.officialUrl,
    page_type: "official_homepage",
    label: "Official"
  });

  args.competitorUrls.forEach((u, i) => {
    pages.push({
      url: u,
      page_type: "competitor_page",
      label: `Competitor ${i + 1}`
    });
  });

  args.thirdPartyUrls.forEach((u, i) => {
    pages.push({
      url: u,
      page_type: "third_party_profile_page",
      label: `Third-party ${i + 1}`
    });
  });

  return pages;
}

export function SiteCreateWizard({ open, onOpenChange, onCreated, navigateToRun = true }: SiteCreateWizardProps) {
  const router = useRouter();

  const [step, setStep] = React.useState<Step>(1);

  // Step1
  const [name, setName] = React.useState("");
  const [description, setDescription] = React.useState("");

  // Step2
  const [officialRows, setOfficialRows] = React.useState<string[]>([""]);
  const [competitorRows, setCompetitorRows] = React.useState<string[]>(["", ""]);
  const [thirdPartyRows, setThirdPartyRows] = React.useState<string[]>([""]);

  // Errors
  const [error, setError] = React.useState<string | null>(null);

  // Create state
  const [creating, setCreating] = React.useState(false);

  React.useEffect(() => {
    if (!open) return;
    // reset when opened
    setStep(1);
    setName("");
    setDescription("");
    setOfficialRows([""]);
    setCompetitorRows(["", ""]);
    setThirdPartyRows([""]);
    setError(null);
    setCreating(false);
  }, [open]);

  if (!open) return null;

  const officialUrl = uniqueNonEmpty(officialRows)[0] ?? "";
  const competitorUrls = uniqueNonEmpty(competitorRows).slice(0, 2);
  const thirdPartyUrls = uniqueNonEmpty(thirdPartyRows).slice(0, 5);

  const validateStep1 = () => {
    if (!name.trim()) return "サイト名を入力してください";
    return null;
  };

  const validateStep2 = () => {
    if (!officialUrl) return "公式URLを入力してください";
    if (!isValidHttpUrl(officialUrl)) return "公式URLが正しくありません（http/https）";
    if (competitorUrls.length !== 2) return "競合URLは2件入力してください";
    if (competitorUrls.some((u) => !isValidHttpUrl(u))) return "競合URLが正しくありません（http/https）";
    if (new Set([officialUrl, ...competitorUrls, ...thirdPartyUrls]).size !== 1 + competitorUrls.length + thirdPartyUrls.length)
      return "同一URLが重複しています（公式/競合/紹介の重複を解消してください）";
    if (competitorUrls.includes(officialUrl)) return "公式URLと競合URLが重複しています";
    return null;
  };

  const close = () => {
    if (creating) return;
    onOpenChange(false);
  };

  const next = () => {
    setError(null);
    if (step === 1) {
      const e = validateStep1();
      if (e) return setError(e);
      setStep(2);
      return;
    }
    if (step === 2) {
      const e = validateStep2();
      if (e) return setError(e);
      setStep(3);
      return;
    }
  };

  const back = () => {
    setError(null);
    if (step === 2) setStep(1);
    if (step === 3) setStep(2);
  };

  const onCreate = async () => {
    setError(null);
    const e1 = validateStep1();
    if (e1) return setError(e1);
    const e2 = validateStep2();
    if (e2) return setError(e2);

    setCreating(true);
    try {
      // 1) create site
      const site = await createSite({
        name: name.trim(),
        description: description.trim() ? description.trim() : null
      });

      // 2) create pages
      const pages = buildPagesPayload({ officialUrl, competitorUrls, thirdPartyUrls });

      // Preferred: bulk
      try {
        await createPagesBulk(site.site_id, { pages });
      } catch {
        // Fallback: single calls
        for (const p of pages) {
          await createPage(site.site_id, p);
        }
      }

      onCreated?.(site.site_id);

      // 3) navigate
      onOpenChange(false);
      if (navigateToRun) router.push(`/sites/${site.site_id}/run`);
      else router.push(`/sites/${site.site_id}`);
    } catch (err: any) {
      setError(err?.message ?? "作成に失敗しました");
    } finally {
      setCreating(false);
    }
  };

  const canCreate = !validateStep1() && !validateStep2();

  return (
    <div className="fixed inset-0 z-50">
      {/* overlay */}
      <div className="absolute inset-0 bg-black/60" onClick={close} />

      {/* modal */}
      <div className="absolute left-1/2 top-1/2 w-[min(760px,calc(100%-24px))] -translate-x-1/2 -translate-y-1/2 p-2">
        <GlassCard className="p-6">
          {/* Header */}
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="flex items-center gap-2">
                <Sparkles className="h-5 w-5 opacity-80" />
                <div className="text-sm font-semibold tracking-tight">
                  CREATE SITE / サイト作成ウィザード
                </div>
              </div>
              <div className="mt-1 text-xs text-muted-foreground">
                公式1・競合2を登録して、すぐ診断を開始できます
              </div>
            </div>

            <button
              type="button"
              onClick={close}
              className="rounded-full border px-3 py-2 text-xs
                         border-[rgba(var(--border),0.14)] bg-[rgba(var(--panel),0.06)]
                         hover:shadow-[0_0_0_1px_rgba(var(--cyan),0.18)] transition"
              disabled={creating}
            >
              <X className="h-4 w-4 opacity-80" />
            </button>
          </div>

          {/* Stepper */}
          <div className="mt-5">
            <WizardStepper step={step} />
          </div>

          {/* Body */}
          <div className="mt-6 space-y-5">
            {step === 1 ? (
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <div className="text-xs font-semibold text-muted-foreground">SITE NAME *</div>
                  <input
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="例：〇〇劇団 公式"
                    className="w-full rounded-[var(--r-md)] border px-3 py-2 text-sm outline-none
                               bg-[rgba(var(--panel),0.06)] border-[rgba(var(--border),0.12)]
                               placeholder:text-[rgba(var(--fg),0.45)]"
                  />
                  <div className="text-[11px] text-muted-foreground-2">
                    管理用の名称です（検索クエリではありません）
                  </div>
                </div>

                <div className="space-y-2">
                  <div className="text-xs font-semibold text-muted-foreground">DESCRIPTION（任意）</div>
                  <textarea
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="例：社会人演劇・東京中心。月1稽古。"
                    className="min-h-[92px] w-full rounded-[var(--r-md)] border px-3 py-2 text-sm outline-none
                               bg-[rgba(var(--panel),0.06)] border-[rgba(var(--border),0.12)]
                               placeholder:text-[rgba(var(--fg),0.45)]"
                  />
                  <div className="text-[11px] text-muted-foreground-2">
                    レポートの文脈補助に使えます
                  </div>
                </div>
              </div>
            ) : null}

            {step === 2 ? (
              <div className="space-y-5">
                <UrlRowsInput
                  label="OFFICIAL URL *（公式サイト）"
                  hint="例：https://your-site.com"
                  rows={officialRows}
                  onChange={setOfficialRows}
                  requiredCount={1}
                  maxCount={1}
                />

                <UrlRowsInput
                  label="COMPETITOR URLS *（競合：2件）"
                  hint="競合は2件入力（MVP要件）"
                  rows={competitorRows}
                  onChange={setCompetitorRows}
                  requiredCount={2}
                  maxCount={2}
                  allowEmptyRows={false}
                />

                <UrlRowsInput
                  label="THIRD-PARTY URLS（紹介/掲載ページ：任意）"
                  hint="紹介サイト内の自分たちの掲載ページURL（0〜5件）"
                  rows={thirdPartyRows}
                  onChange={setThirdPartyRows}
                  maxCount={5}
                />
              </div>
            ) : null}

            {step === 3 ? (
              <div className="space-y-4">
                <div className="rounded-[var(--r-lg)] border p-4 bg-[rgba(var(--panel),0.06)] border-[rgba(var(--border),0.12)]">
                  <div className="text-xs font-semibold text-muted-foreground">REVIEW</div>
                  <div className="mt-2 grid gap-3 md:grid-cols-2">
                    <div>
                      <div className="text-xs font-semibold">Site name</div>
                      <div className="text-sm text-muted-foreground">{name.trim() || "—"}</div>
                    </div>
                    <div>
                      <div className="text-xs font-semibold">Description</div>
                      <div className="text-sm text-muted-foreground">{description.trim() || "—"}</div>
                    </div>
                  </div>

                  <div className="mt-4 grid gap-3">
                    <div>
                      <div className="text-xs font-semibold">Official</div>
                      <div className="text-sm text-muted-foreground break-all">{officialUrl || "—"}</div>
                    </div>
                    <div>
                      <div className="text-xs font-semibold">Competitors</div>
                      <ul className="mt-1 space-y-1">
                        {competitorUrls.map((u, i) => (
                          <li key={i} className="text-sm text-muted-foreground break-all">• {u}</li>
                        ))}
                      </ul>
                    </div>
                    <div>
                      <div className="text-xs font-semibold">Third-party</div>
                      {thirdPartyUrls.length ? (
                        <ul className="mt-1 space-y-1">
                          {thirdPartyUrls.map((u, i) => (
                            <li key={i} className="text-sm text-muted-foreground break-all">• {u}</li>
                          ))}
                        </ul>
                      ) : (
                        <div className="text-sm text-muted-foreground">—</div>
                      )}
                    </div>
                  </div>

                  <div className="mt-4 text-[11px] text-muted-foreground-2">
                    作成後、自動でRun画面に移動します（設定はRun画面で調整可能）
                  </div>
                </div>
              </div>
            ) : null}

            {/* Error */}
            {error ? (
              <div className="rounded-[var(--r-md)] border p-3 text-xs"
                   style={{ borderColor: "rgba(var(--rose),0.22)", background: "rgba(var(--rose),0.08)" }}>
                <div className="flex items-center gap-2 font-semibold" style={{ color: "rgba(var(--rose),0.95)" }}>
                  <AlertTriangle className="h-4 w-4" />
                  Error
                </div>
                <div className="mt-1 text-muted-foreground">{error}</div>
              </div>
            ) : null}
          </div>

          {/* Footer actions */}
          <div className="mt-6 flex items-center justify-between">
            <button
              type="button"
              onClick={back}
              disabled={step === 1 || creating}
              className="rounded-full border px-4 py-2 text-xs
                         border-[rgba(var(--border),0.14)] bg-[rgba(var(--panel),0.06)]
                         hover:shadow-[0_0_0_1px_rgba(var(--cyan),0.18)] transition
                         disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Back
            </button>

            <div className="flex items-center gap-2">
              {step < 3 ? (
                <button
                  type="button"
                  onClick={next}
                  disabled={creating}
                  className="inline-flex items-center gap-2 rounded-full border px-4 py-2 text-xs font-semibold
                             border-[rgba(var(--cyan),0.22)] bg-[rgba(var(--cyan),0.10)]
                             hover:shadow-[0_0_0_1px_rgba(var(--cyan),0.25),var(--glow-cyan)] transition
                             disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Next <ArrowRight className="h-4 w-4 opacity-80" />
                </button>
              ) : (
                <button
                  type="button"
                  onClick={onCreate}
                  disabled={creating || !canCreate}
                  className="inline-flex items-center gap-2 rounded-full border px-5 py-2 text-xs font-semibold
                             border-[rgba(var(--violet),0.22)] bg-[rgba(var(--violet),0.10)]
                             hover:shadow-[0_0_0_1px_rgba(var(--violet),0.22),var(--glow-violet)] transition
                             disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {creating ? "Creating…" : "Create & Run"}
                </button>
              )}
            </div>
          </div>
        </GlassCard>
      </div>
    </div>
  );
}
```

---

## P-6. 呼び出し例

```tsx
// app/sites/page.tsx or header button
const [open, setOpen] = useState(false);

<button onClick={() => setOpen(true)}>New Site</button>

<SiteCreateWizard
  open={open}
  onOpenChange={setOpen}
  navigateToRun={true}
  onCreated={(siteId) => {
    // optional: refresh sites list
  }}
/>
```

---

## P-7. Acceptance Criteria

- [ ] Step 1: name必須、description任意
- [ ] Step 2: 公式1、競合2必須、紹介0..5任意
- [ ] URLのhttp/httpsチェック、重複防止
- [ ] Step 3: Reviewで確認して作成
- [ ] 作成成功後 /sites/{site_id}/run に遷移
- [ ] bulkが無い場合でも createPage のループで動作

---

# Appendix Q: PageCreateFlow Improvements (URL登録体験の強化)

**Scope**:
- URL登録体験を "気持ちよく" しつつ事故率を下げる
- MVPで効果が大きい3点に絞る
  1) page_type 推定（公式/競合/紹介）
  2) 重複チェック（同一URL/同一ドメインの警告）
  3) 初回クロール preview（任意・軽量）: title / h1 / canonical / robots だけ

**Target**:
- Next.js App Router
- Tailwind
- lucide-react
- API: existing POST /pages + optional POST /pages/preview

---

## Q-0. 追加する画面/機能の位置

対象: `/sites/[siteId]/pages` の URL追加フロー（UrlAddModal）

- 既存: `<UrlAddModal />` がある前提
- 改良: `<UrlAddModalV2 />` として差し替え可能

---

## Q-1. 新API（推奨・軽量preview）

### Q-1.1 Backend (recommended)

`POST /sites/{site_id}/pages:preview`

**Request**:
```json
{ "url": "https://example.com" }
```

**Response**:
```json
{
  "url": "https://example.com",
  "ok": true,
  "http_status": 200,
  "final_url": "https://example.com/",
  "title": "…",
  "h1": "…",
  "canonical": "…",
  "robots_meta": "index,follow",
  "noindex_detected": false,
  "has_structured_data": true,
  "fetched_at": "2026-01-20T00:00:00Z",
  "error": null
}
```

### Q-1.2 Why preview is worth it (MVP)
- URLの取り違えを即座に発見（別ページを入れた等）
- noindex / canonical違いの "地雷" を登録前に気付ける
- 実装コストは低い（requests + BeautifulSoupでtitle/h1/canonical/robots）

---

## Q-2. Types + Queries

### Q-2.1 Types (lib/api/types.ts)

```ts
export interface PagePreview {
  url: string;
  ok: boolean;
  http_status?: number | null;
  final_url?: string | null;

  title?: string | null;
  h1?: string | null;
  canonical?: string | null;
  robots_meta?: string | null;
  noindex_detected?: boolean | null;
  has_structured_data?: boolean | null;

  fetched_at?: string | null;
  error?: string | null;
}
```

### Q-2.2 Routes (lib/api/routes.ts)

```ts
pagesPreview: (siteId: UUID) => `/sites/${siteId}/pages:preview`,
```

### Q-2.3 Queries (lib/api/queries.ts)

```ts
import type { UUID, PagePreview } from "./types";
import { apiFetch } from "./client";
import { routes } from "./routes";

export async function previewPage(siteId: UUID, url: string): Promise<PagePreview> {
  return apiFetch(routes.pagesPreview(siteId), {
    method: "POST",
    body: JSON.stringify({ url })
  });
}
```

---

## Q-3. page_type 推定ロジック（フロント側）

### Q-3.1 Rule (MVP)
- **公式**: siteの "official domain" と同一ドメインなら official を候補に（ただし official は1つだけ）
- **競合**: competitor は "公式と別ドメイン" かつ "同カテゴリっぽい" はMVPでは推定しない（別ドメインなら competitor候補）
- **紹介**: third-party は pathに /profile /team /directory 等がある場合は候補

※ 推定は "候補表示" に留め、最終決定はユーザーに委ねる（事故防止）

### Q-3.2 helpers (lib/pages/guess.ts)

```ts
import type { PageType } from "@/lib/api/types";

function getHostname(url: string) {
  try { return new URL(url).hostname.replace(/^www\./, ""); } catch { return ""; }
}

export function guessPageType(args: {
  url: string;
  officialDomain?: string | null; // from existing official url (if any)
  officialExists: boolean;
}): { guess: PageType; reason: string } {
  const host = getHostname(args.url);
  const off = args.officialDomain ? args.officialDomain.replace(/^www\./, "") : null;

  // If no official yet, first URL tends to be official
  if (!args.officialExists) {
    return { guess: "official_homepage", reason: "公式が未登録のため候補を公式にしました" };
  }

  if (off && host === off) {
    return { guess: "official_homepage", reason: "公式と同一ドメインのため" };
  }

  // Heuristic for third-party paths
  const u = args.url.toLowerCase();
  if (/(profile|directory|listing|companies|team|circle|group|theater|gekidan)/.test(u)) {
    return { guess: "third_party_profile_page", reason: "掲載/一覧/プロフィール系のURLパターンのため" };
  }

  return { guess: "competitor_page", reason: "公式と別ドメインのため（競合候補）" };
}
```

---

## Q-4. Duplicate check / Warnings

### Q-4.1 Rules
- **完全一致のURLが既に存在** → error（登録不可）
- **同一ホストが既に存在**
  - competitorとして同一ホスト2件以上 → warning（同じサイトの別ページを競合にしていないか）
  - officialと同一ホストを competitor にしようとしている → warning（タイプ見直し）

### Q-4.2 helpers (lib/pages/validate.ts)

```ts
import type { Page } from "@/lib/api/types";

function norm(u: string) { return u.trim(); }
function host(u: string) {
  try { return new URL(u).hostname.replace(/^www\./, ""); } catch { return ""; }
}

export function validateNewUrl(args: {
  url: string;
  pageType: "official_homepage" | "competitor_page" | "third_party_profile_page";
  existing: Page[];
}) {
  const urlN = norm(args.url);
  const hostN = host(urlN);

  const existingUrls = new Set(args.existing.map(p => norm(p.url)));
  if (existingUrls.has(urlN)) {
    return { ok: false, error: "同じURLが既に登録されています", warnings: [] as string[] };
  }

  const warnings: string[] = [];

  const official = args.existing.find(p => p.page_type === "official_homepage");
  const officialHost = official ? host(official.url) : null;

  if (officialHost && hostN === officialHost && args.pageType === "competitor_page") {
    warnings.push("公式と同一ドメインです。ページタイプが競合で正しいか確認してください。");
  }

  const sameHostCompetitors = args.existing.filter(p => p.page_type === "competitor_page" && host(p.url) === hostN);
  if (args.pageType === "competitor_page" && sameHostCompetitors.length >= 1) {
    warnings.push("競合が同一ドメインで複数件になります。別競合のURLか確認してください。");
  }

  return { ok: true, error: null as string | null, warnings };
}
```

---

## Q-5. UrlAddModalV2（UI + 状態管理 + API接続）

### Q-5.1 Props

```ts
// components/pages/UrlAddModalV2.types.ts
import type { Page, PageType, UUID } from "@/lib/api/types";

export interface UrlAddModalV2Props {
  open: boolean;
  onOpenChange: (v: boolean) => void;

  siteId: UUID;
  existingPages: Page[];

  onCreated?: (page: Page) => void;
}
```

### Q-5.2 Implementation

```tsx
// components/pages/UrlAddModalV2.tsx
"use client";

import * as React from "react";
import type { UrlAddModalV2Props } from "./UrlAddModalV2.types";
import type { PageType } from "@/lib/api/types";
import { GlassCard } from "@/components/layout/GlassCard";
import { cn } from "@/lib/utils/cn";
import { createPage, previewPage } from "@/lib/api/queries";
import { guessPageType } from "@/lib/pages/guess";
import { validateNewUrl } from "@/lib/pages/validate";
import { normalizeUrl, isValidHttpUrl } from "@/lib/utils/url";
import { X, Sparkles, Eye, AlertTriangle, CheckCircle2 } from "lucide-react";

const PAGE_TYPES: { value: PageType; label: string }[] = [
  { value: "official_homepage", label: "公式ホームページ" },
  { value: "competitor_page", label: "競合ページ" },
  { value: "third_party_profile_page", label: "紹介・掲載ページ" }
];

export function UrlAddModalV2({
  open,
  onOpenChange,
  siteId,
  existingPages,
  onCreated
}: UrlAddModalV2Props) {
  const [url, setUrl] = React.useState("");
  const [label, setLabel] = React.useState("");
  const [pageType, setPageType] = React.useState<PageType>("competitor_page");

  const [guessReason, setGuessReason] = React.useState<string | null>(null);

  const [warnings, setWarnings] = React.useState<string[]>([]);
  const [error, setError] = React.useState<string | null>(null);

  const [previewing, setPreviewing] = React.useState(false);
  const [preview, setPreview] = React.useState<any>(null);

  const [creating, setCreating] = React.useState(false);

  const official = existingPages.find(p => p.page_type === "official_homepage");
  const officialDomain = official ? new URL(official.url).hostname.replace(/^www\./, "") : null;
  const officialExists = !!official;

  React.useEffect(() => {
    if (!open) return;
    setUrl("");
    setLabel("");
    setWarnings([]);
    setError(null);
    setPreview(null);
    setPreviewing(false);
    setCreating(false);

    // initial guess
    const g = guessPageType({ url: "https://", officialDomain, officialExists });
    setPageType(g.guess);
    setGuessReason(g.reason);
  }, [open]);

  if (!open) return null;

  const urlN = normalizeUrl(url);

  const runGuess = (u: string) => {
    const g = guessPageType({ url: u, officialDomain, officialExists });
    setPageType(g.guess);
    setGuessReason(g.reason);
  };

  const runValidate = (u: string, pt: PageType) => {
    setError(null);
    if (!u.trim()) {
      setWarnings([]);
      return;
    }
    if (!isValidHttpUrl(u)) {
      setError("URLが正しくありません（http/https）");
      setWarnings([]);
      return;
    }
    const v = validateNewUrl({ url: u, pageType: pt, existing: existingPages });
    if (!v.ok) {
      setError(v.error);
      setWarnings([]);
      return;
    }
    setWarnings(v.warnings);
  };

  const doPreview = async () => {
    setError(null);
    if (!urlN || !isValidHttpUrl(urlN)) {
      setError("プレビュー前に正しいURLを入力してください（http/https）");
      return;
    }
    setPreviewing(true);
    try {
      const res = await previewPage(siteId, urlN);
      setPreview(res);
      // Also surface noindex as warning
      const w: string[] = [];
      if (res?.noindex_detected) w.push("noindex が検出されました（検索に載らない可能性）");
      if (res?.canonical && res?.final_url && res.canonical !== res.final_url) {
        w.push("canonical が別URLを指しています（評価が別URLに集約される可能性）");
      }
      setWarnings((prev) => [...prev, ...w].slice(0, 6));
    } catch (e: any) {
      setError(e?.message ?? "プレビューに失敗しました");
    } finally {
      setPreviewing(false);
    }
  };

  const canCreate = !creating && !!urlN && isValidHttpUrl(urlN) && !error;

  const doCreate = async () => {
    setError(null);
    runValidate(urlN, pageType);
    if (!isValidHttpUrl(urlN)) return;

    // hard block on duplicate
    const v = validateNewUrl({ url: urlN, pageType, existing: existingPages });
    if (!v.ok) {
      setError(v.error);
      return;
    }

    setCreating(true);
    try {
      const created = await createPage(siteId, {
        url: urlN,
        label: label.trim() ? label.trim() : null,
        page_type: pageType
      });
      onCreated?.(created);
      onOpenChange(false);
    } catch (e: any) {
      setError(e?.message ?? "作成に失敗しました");
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50">
      <div className="absolute inset-0 bg-black/60" onClick={() => onOpenChange(false)} />
      <div className="absolute left-1/2 top-1/2 w-[min(640px,calc(100%-24px))] -translate-x-1/2 -translate-y-1/2 p-2">
        <GlassCard className="p-5">
          <div className="flex items-start justify-between gap-3">
            <div>
              <div className="text-sm font-semibold tracking-tight">ADD URL / URL追加</div>
              <div className="mt-1 text-xs text-muted-foreground">
                page_type推定・重複チェック・プレビューで事故を防ぎます
              </div>
            </div>
            <button
              type="button"
              className="rounded-full border px-3 py-2 text-xs
                         border-[rgba(var(--border),0.14)] bg-[rgba(var(--panel),0.06)]
                         hover:shadow-[0_0_0_1px_rgba(var(--cyan),0.18)] transition"
              onClick={() => onOpenChange(false)}
            >
              <X className="h-4 w-4 opacity-80" />
            </button>
          </div>

          {/* URL */}
          <div className="mt-5 space-y-2">
            <div className="text-xs font-semibold text-muted-foreground">URL *</div>
            <input
              value={url}
              onChange={(e) => {
                const v = e.target.value;
                setUrl(v);
                const nn = normalizeUrl(v);
                if (nn.startsWith("http")) runGuess(nn);
                runValidate(nn, pageType);
              }}
              onBlur={() => {
                const nn = normalizeUrl(url);
                setUrl(nn);
                runValidate(nn, pageType);
              }}
              placeholder="https://example.com/..."
              className={cn(
                "w-full rounded-[var(--r-md)] border px-3 py-2 text-sm outline-none",
                "bg-[rgba(var(--panel),0.06)] border-[rgba(var(--border),0.12)]",
                error && "border-[rgba(var(--rose),0.35)]"
              )}
            />

            {guessReason ? (
              <div className="text-[11px] text-muted-foreground-2">
                <span className="inline-flex items-center gap-2">
                  <Sparkles className="h-4 w-4 opacity-70" />
                  推定：{guessReason}
                </span>
              </div>
            ) : null}
          </div>

          {/* Label */}
          <div className="mt-4 space-y-2">
            <div className="text-xs font-semibold text-muted-foreground">LABEL（任意）</div>
            <input
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              placeholder="例：公式トップ / 劇団A / 掲載ページ"
              className="w-full rounded-[var(--r-md)] border px-3 py-2 text-sm outline-none
                         bg-[rgba(var(--panel),0.06)] border-[rgba(var(--border),0.12)]
                         placeholder:text-[rgba(var(--fg),0.45)]"
            />
          </div>

          {/* PageType */}
          <div className="mt-4 space-y-2">
            <div className="text-xs font-semibold text-muted-foreground">PAGE TYPE</div>
            <div className="flex flex-wrap gap-2">
              {PAGE_TYPES.map((t) => (
                <button
                  key={t.value}
                  type="button"
                  onClick={() => {
                    setPageType(t.value);
                    runValidate(urlN, t.value);
                  }}
                  className={cn(
                    "rounded-full border px-3 py-2 text-xs",
                    "border-[rgba(var(--border),0.14)] bg-[rgba(var(--panel),0.06)]",
                    pageType === t.value && "shadow-[0_0_0_1px_rgba(var(--cyan),0.25),var(--glow-cyan)]"
                  )}
                >
                  {t.label}
                </button>
              ))}
            </div>
          </div>

          {/* Preview */}
          <div className="mt-5 flex items-center justify-between gap-2">
            <button
              type="button"
              onClick={doPreview}
              disabled={previewing}
              className="inline-flex items-center gap-2 rounded-full border px-4 py-2 text-xs
                         border-[rgba(var(--violet),0.22)] bg-[rgba(var(--violet),0.10)]
                         hover:shadow-[0_0_0_1px_rgba(var(--violet),0.22),var(--glow-violet)] transition
                         disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Eye className="h-4 w-4 opacity-80" />
              {previewing ? "Previewing…" : "Preview"}
            </button>

            <button
              type="button"
              onClick={doCreate}
              disabled={!canCreate}
              className="inline-flex items-center gap-2 rounded-full border px-4 py-2 text-xs font-semibold
                         border-[rgba(var(--cyan),0.22)] bg-[rgba(var(--cyan),0.10)]
                         hover:shadow-[0_0_0_1px_rgba(var(--cyan),0.25),var(--glow-cyan)] transition
                         disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <CheckCircle2 className="h-4 w-4 opacity-80" />
              {creating ? "Creating…" : "Add URL"}
            </button>
          </div>

          {/* Preview card */}
          {preview ? (
            <div className="mt-4 rounded-[var(--r-md)] border p-4 bg-[rgba(var(--panel),0.06)] border-[rgba(var(--border),0.12)]">
              <div className="text-xs font-semibold text-muted-foreground">PREVIEW</div>
              <div className="mt-2 space-y-1">
                <div className="text-sm font-semibold">{preview.title || "—"}</div>
                <div className="text-xs text-muted-foreground">H1: {preview.h1 || "—"}</div>
                <div className="text-xs text-muted-foreground break-all">final_url: {preview.final_url || "—"}</div>
                <div className="text-xs text-muted-foreground break-all">canonical: {preview.canonical || "—"}</div>
                <div className="text-xs text-muted-foreground">robots: {preview.robots_meta || "—"}</div>
              </div>
            </div>
          ) : null}

          {/* Errors + warnings */}
          {error ? (
            <div className="mt-4 rounded-[var(--r-md)] border p-3 text-xs"
                 style={{ borderColor: "rgba(var(--rose),0.22)", background: "rgba(var(--rose),0.08)" }}>
              <div className="flex items-center gap-2 font-semibold" style={{ color: "rgba(var(--rose),0.95)" }}>
                <AlertTriangle className="h-4 w-4" /> Error
              </div>
              <div className="mt-1 text-muted-foreground">{error}</div>
            </div>
          ) : null}

          {warnings.length ? (
            <div className="mt-3 rounded-[var(--r-md)] border p-3 text-xs
                            border-[rgba(var(--amber),0.20)] bg-[rgba(var(--amber),0.08)]">
              <div className="text-xs font-semibold" style={{ color: "rgba(var(--amber),0.95)" }}>
                Warnings
              </div>
              <ul className="mt-1 space-y-1">
                {warnings.map((w, i) => (
                  <li key={i} className="text-xs text-muted-foreground">• {w}</li>
                ))}
              </ul>
              <div className="mt-2 text-[11px] text-muted-foreground-2">
                ※ Warnings は登録可能ですが、意図を再確認してください
              </div>
            </div>
          ) : null}
        </GlassCard>
      </div>
    </div>
  );
}
```

---

## Q-6. Integration: Pages screen で差し替え

```tsx
// app/sites/[siteId]/pages/page.tsx（例・抜粋）
const [open, setOpen] = useState(false);
const [pages, setPages] = useState<Page[]>([]);

<UrlAddModalV2
  open={open}
  onOpenChange={setOpen}
  siteId={siteId}
  existingPages={pages}
  onCreated={(p) => setPages((prev) => [p, ...prev])}
/>
```

---

## Q-7. Acceptance Criteria

- [ ] URL入力すると page_type 推定理由が出る
- [ ] 既存URLと重複したら登録不可（Error）
- [ ] 同一ドメイン競合などは Warning 表示
- [ ] Previewで title/h1/canonical/robots が確認できる
- [ ] Previewで noindex/canonical mismatch などを Warning に反映
- [ ] Add URL で POST /pages が呼ばれ、一覧が更新される

---

# Appendix R: Empty / Error / Guard States (運用の完成度を決める重要部分)

**Scope**:
- "迷わない・詰まらない" ためのガード設計
- 典型的な失敗・不足状態に対して
  - 明確な原因
  - 具体的な次アクション
  - できればワンクリック導線（ボタン）
- 画面:
  - Sites list / Site detail（任意）
  - Pages（URL管理）
  - Run（実行）
  - Results（結果一覧・詳細）

**Targets**:
- Next.js App Router
- Tailwind
- lucide-react
- UI: GlassCard + Midnight Neon

---

## R-0. 重要原則（MVPの信頼感）

- 失敗を"隠さない"
- でも"責めない"
- 次にやるべきことを **P0/P1** で提示
- UIのトーンは統一（同じカード・同じボタン・同じラベル）

---

## R-1. 共通コンポーネント

### R-1.1 StatePanel（Empty/Error/Guardの共通枠）

```tsx
// components/states/StatePanel.tsx
"use client";

import * as React from "react";
import { GlassCard } from "@/components/layout/GlassCard";
import { cn } from "@/lib/utils/cn";
import { ArrowRight } from "lucide-react";

export type StateTone = "neutral" | "cyan" | "violet" | "amber" | "rose";

export interface StateAction {
  label: string;
  onClick: () => void;
  tone?: StateTone; // affects button glow
}

export interface StatePanelProps {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  tone?: StateTone;
  bullets?: string[];
  actions?: StateAction[];
  className?: string;
}

function btnTone(t?: StateTone) {
  if (t === "rose") return "border-[rgba(var(--rose),0.22)] bg-[rgba(var(--rose),0.10)] hover:shadow-[0_0_0_1px_rgba(var(--rose),0.25)]";
  if (t === "amber") return "border-[rgba(var(--amber),0.22)] bg-[rgba(var(--amber),0.10)] hover:shadow-[0_0_0_1px_rgba(var(--amber),0.22)]";
  if (t === "violet") return "border-[rgba(var(--violet),0.22)] bg-[rgba(var(--violet),0.10)] hover:shadow-[0_0_0_1px_rgba(var(--violet),0.22),var(--glow-violet)]";
  if (t === "cyan") return "border-[rgba(var(--cyan),0.22)] bg-[rgba(var(--cyan),0.10)] hover:shadow-[0_0_0_1px_rgba(var(--cyan),0.25),var(--glow-cyan)]";
  return "border-[rgba(var(--border),0.14)] bg-[rgba(var(--panel),0.06)] hover:shadow-[0_0_0_1px_rgba(var(--cyan),0.18)]";
}

export function StatePanel({
  icon,
  title,
  description,
  tone = "neutral",
  bullets,
  actions,
  className
}: StatePanelProps) {
  const border =
    tone === "rose"
      ? "rgba(var(--rose),0.22)"
      : tone === "amber"
      ? "rgba(var(--amber),0.20)"
      : tone === "violet"
      ? "rgba(var(--violet),0.20)"
      : tone === "cyan"
      ? "rgba(var(--cyan),0.20)"
      : "rgba(var(--border),0.12)";

  const bg =
    tone === "rose"
      ? "rgba(var(--rose),0.08)"
      : tone === "amber"
      ? "rgba(var(--amber),0.08)"
      : tone === "violet"
      ? "rgba(var(--violet),0.08)"
      : tone === "cyan"
      ? "rgba(var(--cyan),0.08)"
      : "rgba(var(--panel),0.06)";

  return (
    <GlassCard className={cn("p-6", className)} style={{ borderColor: border, background: bg } as any}>
      <div className="flex items-start gap-3">
        {icon ? <div className="mt-0.5">{icon}</div> : null}
        <div className="min-w-0">
          <div className="text-sm font-semibold tracking-tight">{title}</div>
          {description ? <div className="mt-1 text-sm text-muted-foreground">{description}</div> : null}

          {bullets?.length ? (
            <ul className="mt-3 space-y-1 text-sm text-muted-foreground">
              {bullets.map((b, i) => (
                <li key={i}>• {b}</li>
              ))}
            </ul>
          ) : null}

          {actions?.length ? (
            <div className="mt-4 flex flex-wrap gap-2">
              {actions.map((a, i) => (
                <button
                  key={i}
                  type="button"
                  onClick={a.onClick}
                  className={cn(
                    "inline-flex items-center gap-2 rounded-full border px-4 py-2 text-xs font-semibold transition",
                    btnTone(a.tone ?? tone)
                  )}
                >
                  {a.label} <ArrowRight className="h-4 w-4 opacity-75" />
                </button>
              ))}
            </div>
          ) : null}
        </div>
      </div>
    </GlassCard>
  );
}
```

※ GlassCard が style を透過させない場合は、GlassCard を div に変更して同じ装飾をつけてもOK。

---

### R-1.2 InlineNotice（軽い警告）

```tsx
// components/states/InlineNotice.tsx
"use client";

import * as React from "react";
import { cn } from "@/lib/utils/cn";
import { AlertTriangle, Info } from "lucide-react";

export function InlineNotice({
  tone = "amber",
  title,
  children
}: {
  tone?: "amber" | "rose" | "neutral";
  title?: string;
  children: React.ReactNode;
}) {
  const border =
    tone === "rose" ? "rgba(var(--rose),0.22)" : tone === "amber" ? "rgba(var(--amber),0.20)" : "rgba(var(--border),0.12)";
  const bg =
    tone === "rose" ? "rgba(var(--rose),0.08)" : tone === "amber" ? "rgba(var(--amber),0.08)" : "rgba(var(--panel),0.06)";
  const Icon = tone === "rose" ? AlertTriangle : Info;

  return (
    <div className={cn("rounded-[var(--r-md)] border p-3")} style={{ borderColor: border, background: bg }}>
      <div className="flex items-start gap-2">
        <Icon className="h-4 w-4 opacity-80 mt-0.5" />
        <div className="min-w-0">
          {title ? <div className="text-xs font-semibold">{title}</div> : null}
          <div className="text-xs text-muted-foreground">{children}</div>
        </div>
      </div>
    </div>
  );
}
```

---

## R-2. Guard判定ユーティリティ（Runを押せる条件）

```ts
// lib/run/guards.ts
import type { Page } from "@/lib/api/types";

export interface RunGuards {
  ok: boolean;
  reasons: { code: string; message: string }[];
}

export function evaluateRunGuards(pages: Page[]): RunGuards {
  const reasons: RunGuards["reasons"] = [];

  const official = pages.filter(p => p.page_type === "official_homepage");
  const competitors = pages.filter(p => p.page_type === "competitor_page");

  if (official.length === 0) reasons.push({ code: "NO_OFFICIAL", message: "公式ホームページが未登録です" });
  if (official.length > 1) reasons.push({ code: "MULTI_OFFICIAL", message: "公式ホームページが複数登録されています（1件にしてください）" });

  if (competitors.length < 2) reasons.push({ code: "FEW_COMPETITORS", message: "競合ページが2件未満です（2件必要）" });
  if (competitors.length > 2) reasons.push({ code: "MANY_COMPETITORS", message: "競合ページが2件を超えています（MVPは2件想定）" });

  // Optional: duplicate URL check
  const urls = pages.map(p => p.url.trim());
  if (new Set(urls).size !== urls.length) reasons.push({ code: "DUP_URL", message: "同一URLが重複登録されています" });

  return { ok: reasons.length === 0, reasons };
}
```

---

## R-3. 各画面の Empty/Error/Guard States

### R-3.1 Pages screen

**Case A: URLが0件（Empty）**
- 何が必要か：公式1・競合2
- 次アクション：Add URL / Wizardへ

```tsx
import { StatePanel } from "@/components/states/StatePanel";
import { Link2, Crown, Swords } from "lucide-react";

if (pages.length === 0) {
  return (
    <StatePanel
      icon={<Link2 className="h-5 w-5 opacity-80" />}
      title="URLが未登録です"
      description="まずは公式サイト1件と、比較用の競合2件を登録してください。"
      tone="cyan"
      bullets={[
        "公式ホームページ（必須）: 1 URL",
        "競合ページ（必須）: 2 URLs",
        "紹介・掲載ページ（任意）: 0〜5 URLs"
      ]}
      actions={[
        { label: "URLを追加", onClick: () => setAddOpen(true), tone: "cyan" },
        { label: "Wizardでまとめて作成", onClick: () => setWizardOpen(true), tone: "violet" }
      ]}
    />
  );
}
```

**Case B: official/competitor不足（Guard）**
- 表示箇所：ページ一覧上部 or Runボタン付近
- 次アクション：不足数を明示してAddへ誘導

```tsx
import { InlineNotice } from "@/components/states/InlineNotice";
import { evaluateRunGuards } from "@/lib/run/guards";

const guards = evaluateRunGuards(pages);
if (!guards.ok) {
  return (
    <InlineNotice tone="amber" title="Runの前提が満たされていません">
      {guards.reasons.map(r => <div key={r.code}>• {r.message}</div>)}
      <div className="mt-2">ページタイプを修正するには Edit を使ってください。</div>
    </InlineNotice>
  );
}
```

---

### R-3.2 Run screen

**Case A: prerequisites not met（Run disabled）**
- Runボタンは disabled
- 代わりに StatePanel を表示（右側 or ボタン直下）
- ワンクリックで Pagesへ

```tsx
import { StatePanel } from "@/components/states/StatePanel";
import { evaluateRunGuards } from "@/lib/run/guards";
import { AlertTriangle } from "lucide-react";
import { useRouter } from "next/navigation";

const guards = evaluateRunGuards(pages);
const router = useRouter();

{!guards.ok ? (
  <StatePanel
    icon={<AlertTriangle className="h-5 w-5 opacity-80" />}
    title="Runできません（前提条件未達）"
    description="公式1件・競合2件が揃うと診断を開始できます。"
    tone="amber"
    bullets={guards.reasons.map(r => r.message)}
    actions={[
      { label: "Pagesで修正する", onClick: () => router.push(`/sites/${siteId}/pages`), tone: "cyan" }
    ]}
  />
) : null}
```

**Case B: GSC 未連携（enableGsc=true だが propertyが空）**
- エラーにせず "Guard warning" として扱う（MVP）
- 表示：RunConfigCard の下に InlineNotice
- 対応：GSC OFFにするか propertyを入れる

```tsx
{enableGsc && !gscProperty ? (
  <InlineNotice tone="amber" title="GSCが有効ですがプロパティが未入力です">
    Runは可能ですが、Search Consoleデータは取り込まれません。
  </InlineNotice>
) : null}
```

---

### R-3.3 Results list

**Case A: 結果が0件（Empty）**
- "まずRunしよう" を強く
- 導線：Runへ

```tsx
import { StatePanel } from "@/components/states/StatePanel";
import { FileText } from "lucide-react";
import { useRouter } from "next/navigation";

if (results.length === 0) {
  return (
    <StatePanel
      icon={<FileText className="h-5 w-5 opacity-80" />}
      title="まだレポートがありません"
      description="Runを実行すると、スコア・原因・ToDoが生成されます。"
      tone="violet"
      bullets={[
        "公式1 + 競合2 の比較",
        "テクニカル/コンテンツの優先度付きToDo",
        "根拠（evidence）つきで"コンサルっぽい"指摘"
      ]}
      actions={[
        { label: "Runへ", onClick: () => router.push(`/sites/${siteId}/run`), tone: "violet" }
      ]}
    />
  );
}
```

---

### R-3.4 Result detail

**Case A: result_id 不正 / fetch失敗（Error）**
- "結果が見つからない" を明確に
- 導線：Results一覧へ戻る / Runする

```tsx
<StatePanel
  icon={<AlertTriangle className="h-5 w-5 opacity-80" />}
  title="レポートが見つかりません"
  description="URLが削除された、またはジョブが失敗した可能性があります。"
  tone="rose"
  actions={[
    { label: "Results一覧へ", onClick: () => router.push(`/sites/${siteId}/results`), tone: "cyan" },
    { label: "Runを再実行", onClick: () => router.push(`/sites/${siteId}/run`), tone: "violet" }
  ]}
/>
```

---

## R-4. Job failed states（失敗ジョブの扱い）

### R-4.1 JobStatusCard で failed を表示済み

追加で推奨:
- error_message を "短い要約 + 詳細（折りたたみ）"
- "Retry" で同一targets/configを再実行（MVPは「もう一度Run」でも可）

### R-4.2 JobHistoryList で failed に対策導線
- "Open Job" → 失敗ログ表示（MVP: error_message だけ）
- "Run again" → Run画面へ

```tsx
// JobHistoryList row actions
{j.status === "failed" ? (
  <button onClick={() => router.push(`/sites/${siteId}/run`)} className="...">
    Run again
  </button>
) : null}
```

---

## R-5. Empty State Copy（統一トーン）

テキストは短く・行動は具体的に。コンサルっぽく言い切る。

- **URL未登録**:
  - 「まずは公式1件と競合2件を登録してください」
- **競合不足**:
  - 「競合は2件必要です（MVP要件）」
- **結果なし**:
  - 「Runを実行するとレポートが生成されます」
- **失敗**:
  - 「原因はエラーメッセージにあります。URLとネットワークを確認してください」

---

## R-6. Acceptance Criteria（必須チェック）

**Pages:**
- [ ] URL 0件 → Empty panel が出る（Add/Wizard導線あり）
- [ ] official/competitor不足 → InlineNotice が出る（理由列挙）

**Run:**
- [ ] prerequisites未達 → Runボタン無効 + Guard panel が出る（Pages導線）
- [ ] GSC設定不足 → 警告（Runは可能）

**Results:**
- [ ] 0件 → Run導線付きEmpty panel
- [ ] result fetch失敗 → Error panel（Results/Run導線）

**Job failed:**
- [ ] failedが明示され、次アクションがある（Retry/Run again）

---

## R-7. 実装順（迷わないための順序）

**P0:**
1. StatePanel / InlineNotice（共通）
2. Pages empty / guard notice
3. Run guard panel
4. Results empty

**P1:**
5. Result detail not found
6. Failed job run again導線の改善

これで「MVPが運用で詰まらない」状態になります。

次にさらに完成度を上げるなら、Guard理由の中で **"どのページが原因か（page_id）"** を返して、ボタンで該当ページの EditModal を開けるようにすると、コンサルツール感がもう一段上がります。

---

## 仕様書完成

これで Appendix A〜R の全仕様が揃いました。

| Appendix | 内容 |
|----------|------|
| A〜D | 分析仕様 / JSONスキーマ / 判定ルール / AIプロンプト |
| F | Next.js 画面ワイヤー / Props / API client |
| G | UIテーマ（Midnight Neon）/ GlassCard / ScoreBadge / TodoBoard |
| H | ResultHeader / ReportMarkdown |
| I | EvidenceDrawer / TodoDetailModal |
| J | Run画面 進行状況（queued → running → done） |
| K | Estimated Tasks（Run前の納得感） |
| L | Chips → Checklist morph（Run後の進捗体験） |
| M | RunConfigCard / TargetSummaryCard / JobHistoryList |
| N | RunConfig Preset（Default / Fast / Deep） |
| O | PageEditModal（URL編集・削除） |
| P | SiteCreateWizard（新規サイト作成ウィザード） |
| Q | PageCreateFlow Improvements（URL登録体験の強化） |
| R | Empty / Error / Guard States |

**実装可能なMD設計が完成しました。**
