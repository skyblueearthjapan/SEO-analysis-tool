# Appendix AK — 改善実例テンプレ

Version: 0.1
目的:
- 改善パターンを再利用できるようにする
- 「どう直せばいいか」の具体例を蓄積する
- ToDoの納得感を高める参考事例として表示する

---

## AK-1. 基本方針

- 最初は 3〜5件で十分
- テンプレだけ用意して、あとから貯める
- 断定しない表現を徹底

---

## AK-2. テンプレ構造

```typescript
interface CaseTemplate {
  id: string;
  title: string;
  category: string;           // technical, content, structure, speed
  related_todo_types: string[]; // 関連するToDoの種類

  background: string;         // 背景
  problem: string;            // 課題
  solution: string;           // 実施した改善
  result: string;             // 結果（数値含む）
  learning: string;           // 学び

  created_at: string;
  updated_at: string;
}
```

---

## AK-3. 初期データ（サンプル5件）

### Case 1: title最適化

```json
{
  "id": "case_001",
  "title": "titleタグの最適化でCTRが改善した事例",
  "category": "content",
  "related_todo_types": ["title_too_long", "title_missing_keyword"],

  "background": "ECサイトの商品一覧ページで、検索結果での表示はされているがクリック率が低い状態が続いていました。",

  "problem": "titleタグが60文字を超えており、検索結果で途中で切れて表示されていました。また、主要キーワードが含まれていませんでした。",

  "solution": "titleを50文字以内に短縮し、主要キーワードを先頭に配置しました。\n\n変更前: 「お買い得商品多数！○○ショップの商品一覧ページ | 送料無料キャンペーン中」\n変更後: 「○○ 商品一覧 | 送料無料 - ○○ショップ」",

  "result": "変更後2週間でCTRが1.2%から2.1%に上昇しました。インプレッション数は変わらなかったため、titleの改善が寄与した可能性があります。",

  "learning": "titleは「何のページか」が一目で分かることが重要です。検索結果で切れない長さに収めることで、ユーザーの判断材料を提供できます。"
}
```

### Case 2: PageSpeed改善

```json
{
  "id": "case_002",
  "title": "画像最適化でPageSpeedが改善した事例",
  "category": "speed",
  "related_todo_types": ["pagespeed_low", "lcp_slow"],

  "background": "コーポレートサイトのトップページでPageSpeedスコアが40点台と低く、ユーザーから「表示が遅い」という声がありました。",

  "problem": "ヒーロー画像が5MB以上あり、LCP（Largest Contentful Paint）が4秒を超えていました。",

  "solution": "画像をWebP形式に変換し、適切なサイズにリサイズしました。また、loading=\"lazy\"を適用し、Above the foldの画像のみ即時読み込みにしました。",

  "result": "PageSpeedスコアが42点から78点に改善。LCPは4.2秒から1.8秒に短縮しました。",

  "learning": "画像最適化はPageSpeed改善の中で最もコストパフォーマンスが高い施策です。特にヒーロー画像など大きな画像から着手するのが効果的です。"
}
```

### Case 3: 構造化データ追加

```json
{
  "id": "case_003",
  "title": "FAQ構造化データでリッチリザルト表示された事例",
  "category": "technical",
  "related_todo_types": ["missing_faq_schema", "structured_data_missing"],

  "background": "サービス紹介ページにFAQセクションがあるものの、検索結果では通常の表示のみでした。",

  "problem": "FAQ構造化データ（JSON-LD）が実装されておらず、リッチリザルトの対象になっていませんでした。",

  "solution": "既存のFAQセクションの内容をJSON-LD形式でマークアップしました。5つの質問と回答を構造化データとして追加しました。",

  "result": "実装後1週間でGoogle Search Consoleの「拡張」レポートにFAQが認識されました。検索結果でFAQが展開表示されるようになり、視認性が向上しました。",

  "learning": "構造化データは既存コンテンツの価値を検索エンジンに正しく伝える手段です。FAQなど定型的なコンテンツは比較的実装が簡単で効果が見えやすいです。"
}
```

### Case 4: 内部リンク改善

```json
{
  "id": "case_004",
  "title": "孤立ページへの内部リンク追加で検索流入が増加した事例",
  "category": "structure",
  "related_todo_types": ["orphan_page", "low_internal_links"],

  "background": "ブログ記事の一部が検索結果に表示されにくく、アクセスがほとんどない状態でした。",

  "problem": "サイトクロールの結果、該当ページが孤立ページ（他のページからリンクされていない）であることが判明しました。",

  "solution": "関連する記事からの内部リンクを3本追加しました。また、カテゴリページからも該当記事へのリンクを追加しました。",

  "result": "追加後1ヶ月でインデックス状況が改善し、検索流入が月間0→47に増加しました。",

  "learning": "内部リンクは検索エンジンのクロールにとって重要な導線です。価値のあるコンテンツでも、到達手段がなければ評価されにくくなります。"
}
```

### Case 5: meta description改善

```json
{
  "id": "case_005",
  "title": "meta description最適化でCTRが改善した事例",
  "category": "content",
  "related_todo_types": ["meta_description_missing", "meta_description_too_long"],

  "background": "サービスページが検索結果に表示されているものの、クリック率が競合より低い状態でした。",

  "problem": "meta descriptionが設定されておらず、Googleが本文から自動生成した説明文が表示されていました。その内容が魅力的でなく、ユーザーの行動を促せていませんでした。",

  "solution": "ユーザーのメリットを明確に伝える120文字程度のmeta descriptionを作成しました。CTA（「無料で相談」など）も含めました。",

  "result": "変更後3週間でCTRが0.8%から1.6%に上昇しました。",

  "learning": "meta descriptionは検索結果での「広告文」のような役割があります。ユーザーが「クリックする理由」を明確に伝えることが重要です。"
}
```

---

## AK-4. データベース

```sql
CREATE TABLE case_templates (
  id VARCHAR(50) PRIMARY KEY,
  title TEXT NOT NULL,
  category VARCHAR(50) NOT NULL,
  related_todo_types JSONB DEFAULT '[]',
  background TEXT,
  problem TEXT,
  solution TEXT,
  result TEXT,
  learning TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_case_templates_category ON case_templates(category);
```

---

## AK-5. API

```python
# app/routers/cases.py

@router.get("/cases")
async def list_cases(
    category: str = Query(None),
    todo_type: str = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """List case templates with optional filters"""

    query = select(CaseTemplate)

    if category:
        query = query.where(CaseTemplate.category == category)

    if todo_type:
        query = query.where(
            CaseTemplate.related_todo_types.contains([todo_type])
        )

    result = await db.execute(query)
    cases = result.scalars().all()

    return {"cases": [case.to_dict() for case in cases]}


@router.get("/cases/{case_id}")
async def get_case(
    case_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific case template"""

    result = await db.execute(
        select(CaseTemplate).where(CaseTemplate.id == case_id)
    )
    case = result.scalar_one_or_none()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    return case.to_dict()
```

---

## AK-6. Frontend（TodoDetailDrawer連携）

```tsx
// components/todo/RelatedCases.tsx
"use client";

import { useEffect, useState } from "react";
import { GlassCard } from "@/components/layout/GlassCard";
import { Lightbulb, ChevronRight } from "lucide-react";

interface Case {
  id: string;
  title: string;
  category: string;
  background: string;
  problem: string;
  solution: string;
  result: string;
  learning: string;
}

interface RelatedCasesProps {
  todoType: string;
}

export function RelatedCases({ todoType }: RelatedCasesProps) {
  const [cases, setCases] = useState<Case[]>([]);
  const [expanded, setExpanded] = useState<string | null>(null);

  useEffect(() => {
    async function loadCases() {
      const res = await fetch(`/api/v1/cases?todo_type=${todoType}`);
      if (res.ok) {
        const data = await res.json();
        setCases(data.cases || []);
      }
    }
    loadCases();
  }, [todoType]);

  if (cases.length === 0) {
    return null;
  }

  return (
    <div className="space-y-3">
      <h4 className="text-sm font-semibold flex items-center gap-2 text-text-secondary">
        <Lightbulb className="h-4 w-4 text-yellow-400" />
        参考事例
      </h4>

      {cases.map((c) => (
        <GlassCard key={c.id} className="p-3">
          <button
            onClick={() => setExpanded(expanded === c.id ? null : c.id)}
            className="w-full flex items-center justify-between text-left"
          >
            <span className="text-sm font-medium text-text-primary">
              {c.title}
            </span>
            <ChevronRight
              className={`h-4 w-4 text-text-muted transition-transform ${
                expanded === c.id ? "rotate-90" : ""
              }`}
            />
          </button>

          {expanded === c.id && (
            <div className="mt-3 space-y-3 text-xs text-text-secondary">
              <div>
                <div className="font-semibold text-text-muted mb-1">背景</div>
                <p>{c.background}</p>
              </div>
              <div>
                <div className="font-semibold text-text-muted mb-1">課題</div>
                <p>{c.problem}</p>
              </div>
              <div>
                <div className="font-semibold text-text-muted mb-1">実施した改善</div>
                <p className="whitespace-pre-line">{c.solution}</p>
              </div>
              <div>
                <div className="font-semibold text-text-muted mb-1">結果</div>
                <p>{c.result}</p>
              </div>
              <div className="bg-yellow-400/10 border border-yellow-400/30 rounded p-2">
                <div className="font-semibold text-yellow-400 mb-1">学び</div>
                <p>{c.learning}</p>
              </div>
            </div>
          )}
        </GlassCard>
      ))}
    </div>
  );
}
```

---

## AK-7. 表示場所

- TodoDetailDrawer内の「参考事例」セクション
- 該当するtodo_typeに紐づく事例のみ表示

---

## AK-8. 今後の拡張

- ユーザー投稿による事例追加
- 業種別の事例分類
- 成功/失敗パターンの分類

---

## AK-9. 受け入れ基準

- [ ] 初期データ（5件）が表示される
- [ ] ToDoタイプに応じた事例がフィルタされる
- [ ] 具体的で再利用できる内容になっている
- [ ] 断定しない表現になっている
- [ ] TodoDetailDrawerから参照できる
