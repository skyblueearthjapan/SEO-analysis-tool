# Appendix T — TodoDetailDrawer (カードクリック → 詳細Drawer) 実装仕様
Version: 0.1
目的: ToDoカードの要約UIから、根拠→原因→手順→コピペ→検証までを1画面で完結させる
方式: **右側スライド Drawer（推奨）**
対象: Next.js(App Router) + FastAPI + Postgres(JSONB) + Midnight Neon UI

---

## 0) このAppendixで実装するもの（スコープ）
### Frontend
- `TodoCard` クリックで Drawer を開く
- `TodoDetailDrawer`（右スライド）
- Drawer内UI:
  - `TodoDetailHeader`（優先度/カテゴリ/Impact/Effort/ステータス）
  - `EvidenceAccordion`（根拠の展開表示）
  - `RootCauseList`（原因候補 + 可能性）
  - `StepsChecklist`（手順チェックリスト）
  - `CopyBlock`（コピペ用：文章/JSON-LD/見出し案）
  - `VerificationPanel`（検証指標）
  - `RelatedTodos`（関連ToDo）

### Backend
- **保存型（推奨）**：ジョブ完了時に `todo_details` を `analysis_result.json` へ内包して保存
- API追加:
  - `GET /api/v1/sites/{site_id}/analysis-results/{result_id}/todos/{todo_id}`（詳細取得）

### DB
- MVPは **analysis_results.raw_json(JSONB)** 内に detail を含める（テーブル追加なし）
- 将来拡張で `todo_details` テーブル分離も可能（本Appendixでは任意）

---

## 1) データ仕様（analysis_result.json 拡張）
### 1.1 既存: todos[]（例）
```json
{
  "todo_id": "todo_001",
  "priority": "P0",
  "category": "technical",
  "title": "HTTPステータスコードの修正",
  "summary": "ステータスコード0を200に修正する",
  "impact": "high",
  "effort": "medium",
  "evidence_refs": ["ev_fetch_status_official"]
}
```

### 1.2 追加: todo.detail（詳細オブジェクト）

**todos[].detail** を追加する（保存型）

```json
{
  "detail": {
    "why": "検索エンジンがページを正しく取得できず、インデックス/評価が進まない可能性があります。",
    "root_causes": [
      { "label": "サーバ側で500/404が返っている", "likelihood": "high", "notes": "fetch.status_code が 200 以外" },
      { "label": "WAF/認証でBotが弾かれている", "likelihood": "medium", "notes": "UAやIPで挙動差がある場合" }
    ],
    "evidence": [
      {
        "id": "ev_fetch_status_official",
        "title": "HTTP取得結果（公式）",
        "kind": "fetch",
        "severity": "critical",
        "data": {
          "url": "https://example.com",
          "status_code": 404,
          "final_url": "https://example.com/",
          "redirect_chain": ["..."],
          "headers": { "x-robots-tag": "noindex" }
        }
      }
    ],
    "steps": [
      { "text": "公式URLをブラウザとcurlで取得し、200が返るか確認する", "done": false },
      { "text": "サーバ/ルーティング設定（rewrite/redirect）を確認して200へ修正する", "done": false },
      { "text": "Search ConsoleのURL検査で再クロールを依頼する", "done": false }
    ],
    "templates": [
      {
        "title": "紹介サイトへ修正依頼テンプレ（例）",
        "type": "text",
        "content": "お世話になっております。掲載ページの以下点をご対応いただけますでしょうか…"
      },
      {
        "title": "FAQPage JSON-LD 雛形",
        "type": "code",
        "language": "json",
        "content": "{\n  \"@context\": \"https://schema.org\",\n  \"@type\": \"FAQPage\",\n  ...\n}"
      }
    ],
    "verification": [
      { "metric": "HTTP status", "target": "200", "how_to_check": "curl -I / ブラウザ" },
      { "metric": "Indexing", "target": "Valid", "how_to_check": "GSC URL検査" }
    ],
    "related_todo_ids": ["todo_002", "todo_010"]
  }
}
```

#### 1.3 値の型（規約）

* `likelihood`: `"high" | "medium" | "low"`
* `severity`: `"critical" | "warning" | "info"`
* `templates[].type`: `"text" | "code" | "bullets"`
* `impact/effort`: 既存の enum を踏襲

---

## 2) 詳細生成の方針（ルール優先 + AI補助）

### 2.1 ルールで必ず埋める（安定）

* `why`（短い説明）
* `evidence`（計測値/抽出値をそのまま）
* `steps`（定型手順）
* `verification`（チェック手段）

### 2.2 AIに補助させる（任意）

* `root_causes`（可能性の文章化）
* `templates`（依頼文/見出し案/FAQ案/セクション案）
* ただし **根拠がない断定は禁止**（spec.mdと同じ制約）

---

## 3) Backend 実装（FastAPI）

### 3.1 ルーティング追加

* `GET /api/v1/sites/{site_id}/analysis-results/{result_id}/todos/{todo_id}`

返すもの:

* `todo`（要約 + detail）
* `evidence` は detail 内に含まれる（追加フェッチ不要）

### 3.2 疑似コード（routers/results.py）

```python
@router.get("/{result_id}/todos/{todo_id}")
async def get_todo_detail(site_id: str, result_id: str, todo_id: str):
    result = await storage.load_analysis_result(site_id, result_id)  # JSONB raw_json
    todo = find_todo(result["todos"], todo_id)
    if not todo:
        raise HTTPException(404, "todo not found")
    return {"todo": todo}
```

### 3.3 storage 側

* `analysis_results.raw_json` を取得して返すだけ（MVP）

---

## 4) Frontend 実装（Next.js）

### 4.1 追加ファイル一覧

* `components/todos/TodoDetailDrawer.tsx`
* `components/todos/EvidenceAccordion.tsx`
* `components/todos/StepsChecklist.tsx`
* `components/todos/CopyBlock.tsx`
* `components/todos/VerificationPanel.tsx`
* `lib/api/queries.ts`（getTodoDetail追加）
* `lib/api/routes.ts`（todoDetailルート追加）
* `lib/todos/types.ts`（TodoDetail型）

### 4.2 API routes.ts

```ts
todoDetail: (siteId: UUID, resultId: UUID, todoId: string) =>
  `/api/v1/sites/${siteId}/analysis-results/${resultId}/todos/${todoId}`,
```

### 4.3 queries.ts

```ts
export async function getTodoDetail(siteId: UUID, resultId: UUID, todoId: string) {
  return apiFetch(routes.todoDetail(siteId, resultId, todoId));
}
```

---

## 5) UI仕様（Drawer）

### 5.1 仕様

* 右からスライド（width: 520〜680px）
* 背景にoverlay（クリックで閉じる）
* `Esc` で閉じる
* スクロールは Drawer 内のみ
* 見出し + タブ（任意）

  * Overview / Evidence / Steps / Templates / Verify

### 5.2 Drawerコンポーネント（実装方針）

* Radixの `Dialog` または `Sheet`（shadcn/uiのSheet推奨）
* Midnight Neonに合わせて `GlassCard` / `border/glow` を採用

---

## 6) 状態管理（最小）

### 6.1 画面（TodoBoard）側

* `selectedTodoId: string | null`
* `drawerOpen: boolean`
* open時に `getTodoDetail()` して stateへ保存
* 既にdetailが todos に入っている場合は **API呼ばずに即表示**（高速化）

### 6.2 キャッシュ

* 同一 todoId の詳細はメモリにキャッシュ（useRef Map）
* `resultId` が変わったらクリア

---

## 7) UX小ワザ（コンサル感アップ）

* Evidenceは "カード" → "折りたたみ詳細" に
* CopyBlockは "Copy" ボタン + toast
* Stepsはチェックでローカル状態保存（MVPはlocalStorage）
* Verifyは「測定のやり方」まで書く
* RelatedTodos で「次にやること」を繋ぐ

---

## 8) Acceptance Criteria（受け入れ基準）

* [ ] ToDoカードクリックで Drawer が開く
* [ ] Drawer に why / root_causes / evidence / steps / templates / verification が表示される
* [ ] Copyボタンでクリップボードにコピーできる
* [ ] Esc / overlayクリックで閉じる
* [ ] detailがJSONにある場合、API無しで表示される
* [ ] detailが無い場合、APIから取得して表示される（ローディング表示）

---

## 9) 実装順（コーディングエージェント向け）

P0:

1. `TodoDetail` 型定義（frontend）
2. Drawer UI（空の静的UI）を作る
3. Cardクリック → Drawer open の配線
4. `getTodoDetail` API を追加して表示（loading/empty含む）
5. EvidenceAccordion / CopyBlock / StepsChecklist / VerificationPanel を埋める

P1:
6. localStorageで steps チェック状態保存
7. RelatedTodos のジャンプ（スクロール/フィルタ）
8. タブ切り替え（Overview/Evidence/Steps/Templates/Verify）

---

## 10) 実装メモ（重要）

* detail生成は **解析時保存型**が基本（クリックごとにAIを叩かない）
* evidenceは "どこから来た情報か" を必ず持たせる（id/kind/data）
* AIを使う場合も「根拠がない断定禁止」を守る（spec.md準拠）
