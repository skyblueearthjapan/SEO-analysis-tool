# Appendix AO — 本文ドラフト生成（コピー・編集・履歴対応）

Version: 0.1
目的:
- コンテンツ改善を「実際に書ける」レベルまで落とす
- SEO会社の執筆ディレクション業務を再現する
- 編集・議論・記録を残せる状態にする

前提:
- Appendix AM（アウトライン/H2/FAQ）
- Appendix AN（競合差分）

---

## AO-0. 重要な前提

```md
本文ドラフトは「完成原稿」ではない。
編集されることを前提とした下書きである。
```

---

## AO-1. 出力単位

* **H2セクション単位**
* 各H2に対して以下を生成

---

## AO-2. H2セクション構成（1ユニット）

```md
## 社会人演劇に参加するメリット

【このセクションで伝えること】
- 社会人にとっての価値
- 趣味・自己表現・人間関係

【含めたい観点】
- 未経験歓迎
- 年齢層の幅

【競合との差分ポイント】
- 競合は「趣味」中心だが、自社は「成長」も強調可能

【本文ドラフト（編集可能）】
社会人演劇に参加することで、日常とは異なる自己表現の場を持つことができます。
未経験から始める方も多く、年齢や経験に関わらず参加できる点が特徴です。
```

---

## AO-3. データ構造

### 3.1 ドラフトセクション

```python
@dataclass
class DraftSection:
    section_id: str
    h2_text: str
    purpose: List[str]           # このセクションで伝えること
    topics: List[str]            # 含めたい観点
    competitor_diff: str         # 競合との差分ポイント
    draft_content: str           # 本文ドラフト
    status: str                  # "generated" | "edited" | "approved"
    edited_content: Optional[str]
    edited_at: Optional[datetime]
    edited_by: Optional[str]
```

### 3.2 DBテーブル

```sql
CREATE TABLE content_drafts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  site_id UUID NOT NULL REFERENCES sites(site_id),
  cluster_id UUID REFERENCES keyword_clusters(id),
  page_url TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE draft_sections (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  draft_id UUID NOT NULL REFERENCES content_drafts(id) ON DELETE CASCADE,
  section_order INT NOT NULL,
  h2_text TEXT NOT NULL,
  purpose JSONB DEFAULT '[]',
  topics JSONB DEFAULT '[]',
  competitor_diff TEXT,
  draft_content TEXT,
  status VARCHAR(20) DEFAULT 'generated',
  edited_content TEXT,
  edited_at TIMESTAMP,
  edited_by TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_draft_sections_draft ON draft_sections(draft_id);
```

---

## AO-4. Backend 実装

### 4.1 ファイル構成

```
app/services/
├─ draft_generator.py
└─ draft_manager.py
```

### 4.2 ドラフト生成

```python
# app/services/draft_generator.py
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class GeneratedSection:
    h2_text: str
    purpose: List[str]
    topics: List[str]
    competitor_diff: str
    draft_content: str

async def generate_draft_sections(
    h2_proposals: List[Dict[str, str]],
    cluster: Dict[str, Any],
    competitor_diffs: Optional[List[Dict]] = None,
    use_llm: bool = True
) -> List[GeneratedSection]:
    """Generate draft sections for each H2"""

    sections = []

    for h2 in h2_proposals:
        h2_text = h2.get("text", "")
        intent = h2.get("intent", "informational")

        # Find relevant competitor diff
        comp_diff = ""
        if competitor_diffs:
            for diff in competitor_diffs:
                if diff.get("category") == "heading" and is_related_topic(h2_text, diff.get("competitor_value", "")):
                    comp_diff = f"競合は「{diff.get('competitor_value')}」として扱っています。差別化ポイントを意識してください。"
                    break

        if use_llm:
            section = await generate_section_with_llm(
                h2_text=h2_text,
                intent=intent,
                cluster=cluster,
                competitor_diff=comp_diff
            )
        else:
            section = generate_section_template(
                h2_text=h2_text,
                intent=intent,
                competitor_diff=comp_diff
            )

        sections.append(section)

    return sections


async def generate_section_with_llm(
    h2_text: str,
    intent: str,
    cluster: Dict[str, Any],
    competitor_diff: str
) -> GeneratedSection:
    """Generate section using LLM"""

    queries = [q["query"] for q in cluster.get("queries", [])[:5]]
    topic = cluster.get("cluster_name", "")

    prompt = f"""
あなたはSEOコンテンツディレクターです。
以下の見出しに対する本文セクションを設計してください。

見出し: {h2_text}
検索意図: {intent}
関連クエリ: {', '.join(queries)}
トピック: {topic}

{f'競合との差分: {competitor_diff}' if competitor_diff else ''}

出力形式（JSON）:
{{
  "purpose": ["このセクションで伝えること1", "伝えること2"],
  "topics": ["含めたい観点1", "観点2", "観点3"],
  "draft_content": "本文ドラフト（150〜300文字程度）"
}}

条件:
- 完成原稿にしない（編集される前提）
- 断定表現を避ける
- 固有情報（価格、日程など）は【要確認】と仮置き
- 検索意図を満たすことを最優先
"""

    response = await call_llm(prompt, temperature=0.4)

    import json
    try:
        data = json.loads(response)
        return GeneratedSection(
            h2_text=h2_text,
            purpose=data.get("purpose", []),
            topics=data.get("topics", []),
            competitor_diff=competitor_diff,
            draft_content=data.get("draft_content", "")
        )
    except:
        return generate_section_template(h2_text, intent, competitor_diff)


def generate_section_template(
    h2_text: str,
    intent: str,
    competitor_diff: str
) -> GeneratedSection:
    """Template-based fallback"""

    templates = {
        "informational": {
            "purpose": ["基本情報を伝える", "理解を深める"],
            "draft": f"{h2_text}について説明します。【詳細を追記してください】"
        },
        "commercial": {
            "purpose": ["選択肢を提示する", "判断材料を提供する"],
            "draft": f"{h2_text}を選ぶ際のポイントを解説します。【具体例を追記してください】"
        },
        "transactional": {
            "purpose": ["行動を促す", "手順を示す"],
            "draft": f"{h2_text}の方法をステップごとに説明します。【詳細手順を追記してください】"
        }
    }

    template = templates.get(intent, templates["informational"])

    return GeneratedSection(
        h2_text=h2_text,
        purpose=template["purpose"],
        topics=[],
        competitor_diff=competitor_diff,
        draft_content=template["draft"]
    )


def is_related_topic(h2: str, competitor_topic: str, threshold: float = 0.4) -> bool:
    """Check if H2 is related to competitor topic"""
    from difflib import SequenceMatcher
    return SequenceMatcher(None, h2.lower(), competitor_topic.lower()).ratio() >= threshold
```

### 4.3 ドラフト管理

```python
# app/services/draft_manager.py
from uuid import UUID
from datetime import datetime
from typing import List, Optional

async def save_draft(
    db,
    site_id: UUID,
    cluster_id: Optional[UUID],
    page_url: Optional[str],
    sections: List[GeneratedSection]
) -> UUID:
    """Save generated draft to database"""

    # Create draft record
    draft = ContentDraft(
        site_id=site_id,
        cluster_id=cluster_id,
        page_url=page_url
    )
    db.add(draft)
    await db.flush()

    # Create section records
    for i, section in enumerate(sections):
        draft_section = DraftSection(
            draft_id=draft.id,
            section_order=i,
            h2_text=section.h2_text,
            purpose=section.purpose,
            topics=section.topics,
            competitor_diff=section.competitor_diff,
            draft_content=section.draft_content,
            status="generated"
        )
        db.add(draft_section)

    await db.commit()
    return draft.id


async def update_section(
    db,
    section_id: UUID,
    edited_content: str,
    edited_by: str
) -> None:
    """Update section with edited content"""

    section = await db.get(DraftSection, section_id)
    if section:
        section.edited_content = edited_content
        section.edited_at = datetime.utcnow()
        section.edited_by = edited_by
        section.status = "edited"
        await db.commit()


async def approve_section(db, section_id: UUID) -> None:
    """Mark section as approved"""

    section = await db.get(DraftSection, section_id)
    if section:
        section.status = "approved"
        await db.commit()
```

---

## AO-5. API

### エンドポイント

```python
# app/routers/drafts.py
from fastapi import APIRouter, Depends
from uuid import UUID

router = APIRouter(prefix="/api/v1/sites/{site_id}/drafts", tags=["drafts"])

@router.post("/generate")
async def generate_draft(
    site_id: UUID,
    cluster_id: UUID,
    use_llm: bool = True,
    db: AsyncSession = Depends(get_db)
):
    """Generate draft for a cluster"""

    # Get cluster with design
    cluster = await get_cluster_with_queries(db, cluster_id)
    design = await get_content_design(db, cluster_id)

    if not design:
        raise HTTPException(400, "先にコンテンツ設計を生成してください")

    # Get competitor diffs if available
    competitor_diffs = await get_competitor_diffs(db, site_id, cluster.target_page)

    # Generate sections
    sections = await generate_draft_sections(
        h2_proposals=design.h2_proposals,
        cluster=cluster.to_dict(),
        competitor_diffs=competitor_diffs,
        use_llm=use_llm
    )

    # Save draft
    draft_id = await save_draft(
        db,
        site_id=site_id,
        cluster_id=cluster_id,
        page_url=cluster.target_page,
        sections=sections
    )

    return {
        "draft_id": str(draft_id),
        "sections": [
            {
                "h2_text": s.h2_text,
                "purpose": s.purpose,
                "topics": s.topics,
                "competitor_diff": s.competitor_diff,
                "draft_content": s.draft_content
            }
            for s in sections
        ]
    }


@router.get("/{draft_id}")
async def get_draft(
    site_id: UUID,
    draft_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get draft with sections"""

    draft = await db.get(ContentDraft, draft_id)
    if not draft or draft.site_id != site_id:
        raise HTTPException(404, "Draft not found")

    sections = await db.execute(
        select(DraftSection)
        .where(DraftSection.draft_id == draft_id)
        .order_by(DraftSection.section_order)
    )

    return {
        "draft_id": str(draft.id),
        "cluster_id": str(draft.cluster_id) if draft.cluster_id else None,
        "page_url": draft.page_url,
        "created_at": draft.created_at.isoformat(),
        "sections": [
            {
                "section_id": str(s.id),
                "h2_text": s.h2_text,
                "purpose": s.purpose,
                "topics": s.topics,
                "competitor_diff": s.competitor_diff,
                "draft_content": s.draft_content,
                "status": s.status,
                "edited_content": s.edited_content,
                "edited_at": s.edited_at.isoformat() if s.edited_at else None
            }
            for s in sections.scalars().all()
        ]
    }


@router.patch("/{draft_id}/sections/{section_id}")
async def update_draft_section(
    site_id: UUID,
    draft_id: UUID,
    section_id: UUID,
    content: str,
    db: AsyncSession = Depends(get_db),
    current_user: str = "user"
):
    """Update section content"""

    await update_section(db, section_id, content, current_user)

    return {"success": True, "section_id": str(section_id)}


@router.post("/{draft_id}/sections/{section_id}/approve")
async def approve_draft_section(
    site_id: UUID,
    draft_id: UUID,
    section_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Approve section"""

    await approve_section(db, section_id)

    return {"success": True, "section_id": str(section_id)}
```

---

## AO-6. Frontend UI

### 6.1 コンポーネント構成

```
components/drafts/
├─ DraftEditor.tsx
├─ DraftSection.tsx
├─ SectionEditor.tsx
├─ CopyButton.tsx
└─ StatusBadge.tsx
```

### 6.2 DraftEditor.tsx

```tsx
"use client";

import { useState, useEffect } from "react";
import { GlassCard } from "@/components/layout/GlassCard";
import { FileEdit, Loader2 } from "lucide-react";
import { DraftSection } from "./DraftSection";

interface Section {
  section_id: string;
  h2_text: string;
  purpose: string[];
  topics: string[];
  competitor_diff: string;
  draft_content: string;
  status: string;
  edited_content: string | null;
}

interface DraftEditorProps {
  siteId: string;
  clusterId: string;
}

export function DraftEditor({ siteId, clusterId }: DraftEditorProps) {
  const [draftId, setDraftId] = useState<string | null>(null);
  const [sections, setSections] = useState<Section[]>([]);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);

  async function generateDraft() {
    setGenerating(true);
    try {
      const res = await fetch(
        `/api/v1/sites/${siteId}/drafts/generate?cluster_id=${clusterId}`,
        { method: "POST" }
      );

      if (res.ok) {
        const data = await res.json();
        setDraftId(data.draft_id);
        // Reload to get section IDs
        await loadDraft(data.draft_id);
      }
    } finally {
      setGenerating(false);
    }
  }

  async function loadDraft(id: string) {
    setLoading(true);
    try {
      const res = await fetch(`/api/v1/sites/${siteId}/drafts/${id}`);
      if (res.ok) {
        const data = await res.json();
        setSections(data.sections);
      }
    } finally {
      setLoading(false);
    }
  }

  async function updateSection(sectionId: string, content: string) {
    await fetch(
      `/api/v1/sites/${siteId}/drafts/${draftId}/sections/${sectionId}`,
      {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content })
      }
    );

    setSections(prev =>
      prev.map(s =>
        s.section_id === sectionId
          ? { ...s, edited_content: content, status: "edited" }
          : s
      )
    );
  }

  if (!draftId) {
    return (
      <GlassCard>
        <div className="text-center py-8">
          <FileEdit className="h-12 w-12 text-accent-cyan mx-auto mb-4" />
          <h3 className="text-lg font-semibold mb-2">本文ドラフトを生成</h3>
          <p className="text-text-muted text-sm mb-4">
            H2構成に基づいて本文の下書きを生成します<br />
            編集・コピーしてご利用ください
          </p>
          <button
            onClick={generateDraft}
            disabled={generating}
            className="px-6 py-2 bg-accent-cyan text-bg-base rounded-lg font-medium hover:bg-accent-cyan/90 transition-colors disabled:opacity-50"
          >
            {generating ? (
              <span className="flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin" />
                生成中...
              </span>
            ) : (
              "生成する"
            )}
          </button>
        </div>
      </GlassCard>
    );
  }

  if (loading) {
    return (
      <div className="text-center py-8 text-text-muted">
        <Loader2 className="h-8 w-8 animate-spin mx-auto" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {sections.map((section, i) => (
        <DraftSection
          key={section.section_id}
          section={section}
          onUpdate={(content) => updateSection(section.section_id, content)}
        />
      ))}
    </div>
  );
}
```

### 6.3 DraftSection.tsx

```tsx
"use client";

import { useState } from "react";
import { GlassCard } from "@/components/layout/GlassCard";
import { Copy, Check, Edit2, Save, RotateCcw, CheckCircle } from "lucide-react";
import { cn } from "@/lib/utils";

interface Section {
  section_id: string;
  h2_text: string;
  purpose: string[];
  topics: string[];
  competitor_diff: string;
  draft_content: string;
  status: string;
  edited_content: string | null;
}

const STATUS_CONFIG = {
  generated: { label: "AI生成", color: "text-blue-400", bg: "bg-blue-400/20" },
  edited: { label: "編集済み", color: "text-yellow-400", bg: "bg-yellow-400/20" },
  approved: { label: "承認済み", color: "text-green-400", bg: "bg-green-400/20" }
};

interface DraftSectionProps {
  section: Section;
  onUpdate: (content: string) => void;
}

export function DraftSection({ section, onUpdate }: DraftSectionProps) {
  const [editing, setEditing] = useState(false);
  const [editContent, setEditContent] = useState(
    section.edited_content || section.draft_content
  );
  const [copied, setCopied] = useState(false);

  const status = STATUS_CONFIG[section.status as keyof typeof STATUS_CONFIG] || STATUS_CONFIG.generated;
  const displayContent = section.edited_content || section.draft_content;

  function handleCopy() {
    const fullText = `## ${section.h2_text}\n\n${displayContent}`;
    navigator.clipboard.writeText(fullText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  function handleSave() {
    onUpdate(editContent);
    setEditing(false);
  }

  function handleReset() {
    setEditContent(section.draft_content);
  }

  return (
    <GlassCard>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-text-primary">
          {section.h2_text}
        </h3>
        <div className="flex items-center gap-2">
          <span className={cn("px-2 py-1 text-xs rounded-full", status.bg, status.color)}>
            {status.label}
          </span>
        </div>
      </div>

      {/* Meta Info */}
      <div className="space-y-2 mb-4 text-xs">
        {section.purpose.length > 0 && (
          <div>
            <span className="text-text-muted">伝えること: </span>
            <span className="text-text-secondary">{section.purpose.join("、")}</span>
          </div>
        )}
        {section.topics.length > 0 && (
          <div>
            <span className="text-text-muted">観点: </span>
            <span className="text-text-secondary">{section.topics.join("、")}</span>
          </div>
        )}
        {section.competitor_diff && (
          <div className="bg-yellow-400/10 border border-yellow-400/30 rounded p-2 mt-2">
            <span className="text-yellow-400">差分: </span>
            <span className="text-text-secondary">{section.competitor_diff}</span>
          </div>
        )}
      </div>

      {/* Content */}
      <div className="relative">
        {editing ? (
          <div className="space-y-2">
            <textarea
              value={editContent}
              onChange={(e) => setEditContent(e.target.value)}
              className="w-full h-40 bg-bg-surface border border-border-subtle rounded-lg p-3 text-sm text-text-primary resize-none focus:outline-none focus:border-accent-cyan"
            />
            <div className="flex justify-end gap-2">
              <button
                onClick={handleReset}
                className="px-3 py-1 text-xs text-text-muted hover:text-text-primary transition-colors flex items-center gap-1"
              >
                <RotateCcw className="h-3 w-3" />
                リセット
              </button>
              <button
                onClick={() => setEditing(false)}
                className="px-3 py-1 text-xs text-text-muted hover:text-text-primary transition-colors"
              >
                キャンセル
              </button>
              <button
                onClick={handleSave}
                className="px-3 py-1 text-xs bg-accent-cyan text-bg-base rounded hover:bg-accent-cyan/90 transition-colors flex items-center gap-1"
              >
                <Save className="h-3 w-3" />
                保存
              </button>
            </div>
          </div>
        ) : (
          <div className="bg-bg-surface rounded-lg p-4">
            <p className="text-sm text-text-secondary whitespace-pre-wrap leading-relaxed">
              {displayContent}
            </p>
          </div>
        )}
      </div>

      {/* Actions */}
      {!editing && (
        <div className="flex justify-end gap-2 mt-3">
          <button
            onClick={() => setEditing(true)}
            className="px-3 py-1 text-xs text-text-muted hover:text-accent-cyan transition-colors flex items-center gap-1"
          >
            <Edit2 className="h-3 w-3" />
            編集
          </button>
          <button
            onClick={handleCopy}
            className="px-3 py-1 text-xs text-text-muted hover:text-accent-cyan transition-colors flex items-center gap-1"
          >
            {copied ? (
              <>
                <Check className="h-3 w-3 text-green-400" />
                <span className="text-green-400">コピー済み</span>
              </>
            ) : (
              <>
                <Copy className="h-3 w-3" />
                コピー
              </>
            )}
          </button>
        </div>
      )}
    </GlassCard>
  );
}
```

---

## AO-7. LLM生成指針（重要）

### プロンプト原則

```md
あなたはSEOコンテンツディレクターです。
以下の条件で本文ドラフトを生成してください。

条件:
- 完成原稿にしない（編集される前提）
- 断定表現を避ける
- 固有情報（価格、日程など）は【要確認】と仮置き
- 検索意図を満たすことを最優先
- 150〜300文字程度で簡潔に
```

### 温度設定

| タスク | temperature |
|--------|-------------|
| ドラフト生成 | 0.4 |

---

## AO-8. ToDo連動

| 状態 | ToDo |
|------|------|
| generated（未編集） | 原稿作成・編集 |
| edited（編集済み） | サイトへの実装 |
| approved（承認済み） | 完了確認 |

source_checks=["content_draft"]

---

## AO-9. Progress連動

* 編集・実装後
* SERP / CTR / カニバリ改善を Progress Dashboard で追跡

---

## AO-10. 利用シーン

```md
・ホームページ制作会社へ共有
・社内での改善方針検討
・ライターへの指示書として
・原稿作成の叩き台
```

---

## AO-11. 受け入れ基準

- [ ] H2単位でドラフトが生成される
- [ ] コピーできる
- [ ] 編集できる
- [ ] 編集内容が保存される
- [ ] 競合差分が反映されている
- [ ] ステータス管理ができる

---

## AO-12. この機能が完成すると

```md
・「どう書くか」で迷わなくなる
・外注・内製どちらでも使える
・SEO改善が設計から実装まで繋がる
・記録が残るので振り返りができる
```

---

## AO-13. 将来拡張

- 編集履歴（バージョン管理）
- コメント機能（チーム議論）
- CMS連携（下書き投稿）
- A/Bパターン生成
