# Appendix AN — 競合構成差分ハイライト 設計仕様

Version: 0.1
目的:
- 競合ページが「どこまで・何を」書いているかを可視化する
- 自社ページとの構成・観点・情報量の差を明確にする
- コンテンツ設計・改善判断の根拠を提供する

前提:
- Appendix AL（キーワードクラスタ）
- Appendix AM（アウトライン/H2/FAQ生成）

---

## AN-0. 基本思想（重要）

```md
競合構成差分とは、
「真似るため」ではなく
「何が不足しているかを知るため」に見るものである。
```

---

## AN-1. 比較対象

### 対象ページ

* 自社ページ（assigned_page）
* 競合ページ（最大2〜3URL）

### 比較軸（すべて見る）

| 軸 | 内容 |
|----|------|
| 見出し構成 | H1/H2/H3 |
| 観点 | 各見出しが扱うテーマ |
| FAQ | Q&A有無・内容 |
| 情報量 | セクション数・文字量 |
| 検索意図 | どのintentをカバーしているか |

---

## AN-2. Backend 抽出仕様

### 2.1 データ構造

```python
@dataclass
class PageStructure:
    url: str
    title: str
    h1: str
    h2s: List[str]
    h3s: List[str]
    faqs: List[Dict[str, str]]  # [{"q": "...", "a": "..."}]
    section_count: int
    estimated_chars: int
    meta_description: str

@dataclass
class StructureDiff:
    diff_type: str  # "missing" | "weak" | "unique"
    category: str   # "heading" | "faq" | "topic" | "depth"
    our_value: Any
    competitor_value: Any
    description: str
```

### 2.2 抽出サービス

```python
# app/services/competitor_structure_extractor.py
import httpx
from bs4 import BeautifulSoup
from typing import List, Dict, Any

async def extract_page_structure(url: str) -> PageStructure:
    """Extract structure from a page"""

    async with httpx.AsyncClient() as client:
        response = await client.get(url, follow_redirects=True, timeout=15.0)
        html = response.text

    soup = BeautifulSoup(html, "html.parser")

    # Title
    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else ""

    # H1
    h1_tag = soup.find("h1")
    h1 = h1_tag.get_text(strip=True) if h1_tag else ""

    # H2s
    h2s = [h2.get_text(strip=True) for h2 in soup.find_all("h2")]

    # H3s
    h3s = [h3.get_text(strip=True) for h3 in soup.find_all("h3")]

    # FAQ extraction (JSON-LD or common patterns)
    faqs = extract_faqs(soup)

    # Estimate character count (visible text)
    body = soup.find("body")
    text = body.get_text(separator=" ", strip=True) if body else ""
    estimated_chars = len(text)

    # Meta description
    meta_desc_tag = soup.find("meta", attrs={"name": "description"})
    meta_description = meta_desc_tag.get("content", "") if meta_desc_tag else ""

    return PageStructure(
        url=url,
        title=title,
        h1=h1,
        h2s=h2s,
        h3s=h3s,
        faqs=faqs,
        section_count=len(h2s),
        estimated_chars=estimated_chars,
        meta_description=meta_description
    )


def extract_faqs(soup: BeautifulSoup) -> List[Dict[str, str]]:
    """Extract FAQs from JSON-LD or common HTML patterns"""

    faqs = []

    # Try JSON-LD FAQPage
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            import json
            data = json.loads(script.string)

            if isinstance(data, dict) and data.get("@type") == "FAQPage":
                for item in data.get("mainEntity", []):
                    faqs.append({
                        "q": item.get("name", ""),
                        "a": item.get("acceptedAnswer", {}).get("text", "")
                    })
        except:
            pass

    # Try common FAQ patterns (details/summary, accordion)
    for details in soup.find_all("details"):
        summary = details.find("summary")
        if summary:
            q = summary.get_text(strip=True)
            a = details.get_text(strip=True).replace(q, "", 1).strip()
            faqs.append({"q": q, "a": a})

    return faqs
```

### 2.3 差分計算

```python
# app/services/structure_diff_calculator.py
from typing import List
from difflib import SequenceMatcher

def calculate_structure_diff(
    our_structure: PageStructure,
    competitor_structures: List[PageStructure]
) -> List[StructureDiff]:
    """Calculate differences between our page and competitors"""

    diffs = []

    # Aggregate competitor data
    competitor_h2s = set()
    competitor_faqs = set()
    competitor_topics = set()

    for comp in competitor_structures:
        competitor_h2s.update(comp.h2s)
        for faq in comp.faqs:
            competitor_faqs.add(faq["q"])
        # Extract topics from H2s
        for h2 in comp.h2s:
            competitor_topics.add(normalize_topic(h2))

    our_h2s = set(our_structure.h2s)
    our_topics = set(normalize_topic(h2) for h2 in our_structure.h2s)
    our_faq_questions = set(faq["q"] for faq in our_structure.faqs)

    # Find missing H2 topics
    for comp_topic in competitor_topics:
        if not any(is_similar_topic(comp_topic, our_topic) for our_topic in our_topics):
            # Find original H2 text
            original_h2 = next(
                (h2 for comp in competitor_structures for h2 in comp.h2s
                 if normalize_topic(h2) == comp_topic),
                comp_topic
            )
            diffs.append(StructureDiff(
                diff_type="missing",
                category="heading",
                our_value=None,
                competitor_value=original_h2,
                description=f"競合にある見出し「{original_h2}」が自社ページにありません"
            ))

    # Find missing FAQs
    for comp_faq in competitor_faqs:
        if not any(is_similar_text(comp_faq, our_faq) for our_faq in our_faq_questions):
            diffs.append(StructureDiff(
                diff_type="missing",
                category="faq",
                our_value=None,
                competitor_value=comp_faq,
                description=f"競合にあるFAQ「{comp_faq}」が自社ページにありません"
            ))

    # Check depth (section count)
    avg_competitor_sections = sum(c.section_count for c in competitor_structures) / len(competitor_structures)
    if our_structure.section_count < avg_competitor_sections * 0.7:
        diffs.append(StructureDiff(
            diff_type="weak",
            category="depth",
            our_value=our_structure.section_count,
            competitor_value=avg_competitor_sections,
            description=f"自社ページのセクション数（{our_structure.section_count}）が競合平均（{avg_competitor_sections:.0f}）より少ないです"
        ))

    # Check content volume
    avg_competitor_chars = sum(c.estimated_chars for c in competitor_structures) / len(competitor_structures)
    if our_structure.estimated_chars < avg_competitor_chars * 0.6:
        diffs.append(StructureDiff(
            diff_type="weak",
            category="volume",
            our_value=our_structure.estimated_chars,
            competitor_value=avg_competitor_chars,
            description=f"自社ページの情報量が競合と比べて少ない可能性があります"
        ))

    # Find unique (our advantage)
    for our_topic in our_topics:
        if not any(is_similar_topic(our_topic, comp_topic) for comp_topic in competitor_topics):
            original_h2 = next(
                (h2 for h2 in our_structure.h2s if normalize_topic(h2) == our_topic),
                our_topic
            )
            diffs.append(StructureDiff(
                diff_type="unique",
                category="heading",
                our_value=original_h2,
                competitor_value=None,
                description=f"自社独自の観点「{original_h2}」があります"
            ))

    return diffs


def normalize_topic(text: str) -> str:
    """Normalize text for comparison"""
    import re
    # Remove common suffixes, punctuation
    text = re.sub(r'[？?！!。、]', '', text)
    text = re.sub(r'(とは|について|の方法|のやり方|の仕方)$', '', text)
    return text.lower().strip()


def is_similar_topic(topic1: str, topic2: str, threshold: float = 0.6) -> bool:
    """Check if two topics are similar"""
    return SequenceMatcher(None, topic1, topic2).ratio() >= threshold


def is_similar_text(text1: str, text2: str, threshold: float = 0.7) -> bool:
    """Check if two texts are similar"""
    return SequenceMatcher(None, text1.lower(), text2.lower()).ratio() >= threshold
```

---

## AN-3. API

### エンドポイント

```python
# app/routers/competitor_diff.py
from fastapi import APIRouter, Depends, Query
from uuid import UUID
from typing import List

router = APIRouter(prefix="/api/v1/sites/{site_id}/competitor-diff", tags=["competitor-diff"])

@router.post("/analyze")
async def analyze_competitor_diff(
    site_id: UUID,
    our_url: str = Query(...),
    competitor_urls: List[str] = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """Analyze structure difference with competitors"""

    # Extract our structure
    our_structure = await extract_page_structure(our_url)

    # Extract competitor structures
    competitor_structures = []
    for url in competitor_urls[:3]:  # Max 3
        try:
            structure = await extract_page_structure(url)
            competitor_structures.append(structure)
        except:
            pass

    if not competitor_structures:
        raise HTTPException(400, "競合ページを取得できませんでした")

    # Calculate diff
    diffs = calculate_structure_diff(our_structure, competitor_structures)

    return {
        "our_page": {
            "url": our_structure.url,
            "title": our_structure.title,
            "h2s": our_structure.h2s,
            "faqs": our_structure.faqs,
            "section_count": our_structure.section_count,
            "estimated_chars": our_structure.estimated_chars
        },
        "competitors": [
            {
                "url": c.url,
                "title": c.title,
                "h2s": c.h2s,
                "faqs": c.faqs,
                "section_count": c.section_count,
                "estimated_chars": c.estimated_chars
            }
            for c in competitor_structures
        ],
        "diffs": [
            {
                "diff_type": d.diff_type,
                "category": d.category,
                "our_value": d.our_value,
                "competitor_value": d.competitor_value,
                "description": d.description
            }
            for d in diffs
        ],
        "summary": {
            "missing_count": len([d for d in diffs if d.diff_type == "missing"]),
            "weak_count": len([d for d in diffs if d.diff_type == "weak"]),
            "unique_count": len([d for d in diffs if d.diff_type == "unique"])
        }
    }
```

---

## AN-4. Frontend UI

### 4.1 コンポーネント構成

```
components/competitor-diff/
├─ CompetitorDiffPanel.tsx
├─ StructureComparison.tsx
├─ DiffHighlightList.tsx
└─ PageStructureCard.tsx
```

### 4.2 CompetitorDiffPanel.tsx

```tsx
"use client";

import { useState } from "react";
import { GlassCard } from "@/components/layout/GlassCard";
import { GitCompare, AlertTriangle, CheckCircle, Sparkles, Loader2 } from "lucide-react";
import { StructureComparison } from "./StructureComparison";
import { DiffHighlightList } from "./DiffHighlightList";

interface PageStructure {
  url: string;
  title: string;
  h2s: string[];
  faqs: Array<{ q: string; a: string }>;
  section_count: number;
  estimated_chars: number;
}

interface Diff {
  diff_type: "missing" | "weak" | "unique";
  category: string;
  our_value: any;
  competitor_value: any;
  description: string;
}

interface CompetitorDiffPanelProps {
  siteId: string;
  ourUrl: string;
  competitorUrls: string[];
}

export function CompetitorDiffPanel({ siteId, ourUrl, competitorUrls }: CompetitorDiffPanelProps) {
  const [result, setResult] = useState<{
    our_page: PageStructure;
    competitors: PageStructure[];
    diffs: Diff[];
    summary: { missing_count: number; weak_count: number; unique_count: number };
  } | null>(null);
  const [loading, setLoading] = useState(false);

  async function analyze() {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.append("our_url", ourUrl);
      competitorUrls.forEach(url => params.append("competitor_urls", url));

      const res = await fetch(
        `/api/v1/sites/${siteId}/competitor-diff/analyze?${params}`,
        { method: "POST" }
      );

      if (res.ok) {
        setResult(await res.json());
      }
    } finally {
      setLoading(false);
    }
  }

  if (!result) {
    return (
      <GlassCard>
        <div className="text-center py-8">
          <GitCompare className="h-12 w-12 text-accent-cyan mx-auto mb-4" />
          <h3 className="text-lg font-semibold mb-2">競合構成を比較</h3>
          <p className="text-text-muted text-sm mb-4">
            自社ページと競合ページの構成を比較し、<br />
            不足している観点を特定します
          </p>
          <button
            onClick={analyze}
            disabled={loading}
            className="px-6 py-2 bg-accent-cyan text-bg-base rounded-lg font-medium hover:bg-accent-cyan/90 transition-colors disabled:opacity-50"
          >
            {loading ? (
              <span className="flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin" />
                分析中...
              </span>
            ) : (
              "分析する"
            )}
          </button>
        </div>
      </GlassCard>
    );
  }

  return (
    <div className="space-y-6">
      {/* Summary */}
      <div className="grid grid-cols-3 gap-4">
        <GlassCard className="bg-red-400/10">
          <div className="flex items-center gap-2 text-red-400">
            <AlertTriangle className="h-5 w-5" />
            <span className="text-2xl font-bold">{result.summary.missing_count}</span>
          </div>
          <p className="text-xs text-text-muted mt-1">不足している観点</p>
        </GlassCard>
        <GlassCard className="bg-yellow-400/10">
          <div className="flex items-center gap-2 text-yellow-400">
            <AlertTriangle className="h-5 w-5" />
            <span className="text-2xl font-bold">{result.summary.weak_count}</span>
          </div>
          <p className="text-xs text-text-muted mt-1">弱い項目</p>
        </GlassCard>
        <GlassCard className="bg-green-400/10">
          <div className="flex items-center gap-2 text-green-400">
            <Sparkles className="h-5 w-5" />
            <span className="text-2xl font-bold">{result.summary.unique_count}</span>
          </div>
          <p className="text-xs text-text-muted mt-1">自社独自の強み</p>
        </GlassCard>
      </div>

      {/* Structure Comparison */}
      <StructureComparison
        ourPage={result.our_page}
        competitors={result.competitors}
      />

      {/* Diff Highlights */}
      <DiffHighlightList diffs={result.diffs} />
    </div>
  );
}
```

### 4.3 DiffHighlightList.tsx

```tsx
"use client";

import { GlassCard } from "@/components/layout/GlassCard";
import { AlertTriangle, MinusCircle, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

interface Diff {
  diff_type: "missing" | "weak" | "unique";
  category: string;
  description: string;
}

const DIFF_CONFIG = {
  missing: {
    icon: MinusCircle,
    color: "text-red-400",
    bgColor: "bg-red-400/10",
    label: "不足"
  },
  weak: {
    icon: AlertTriangle,
    color: "text-yellow-400",
    bgColor: "bg-yellow-400/10",
    label: "弱い"
  },
  unique: {
    icon: Sparkles,
    color: "text-green-400",
    bgColor: "bg-green-400/10",
    label: "独自"
  }
};

interface DiffHighlightListProps {
  diffs: Diff[];
}

export function DiffHighlightList({ diffs }: DiffHighlightListProps) {
  const missingDiffs = diffs.filter(d => d.diff_type === "missing");
  const weakDiffs = diffs.filter(d => d.diff_type === "weak");
  const uniqueDiffs = diffs.filter(d => d.diff_type === "unique");

  return (
    <div className="space-y-4">
      {/* Missing */}
      {missingDiffs.length > 0 && (
        <GlassCard>
          <h4 className="font-semibold text-red-400 mb-3 flex items-center gap-2">
            <MinusCircle className="h-5 w-5" />
            不足している観点
          </h4>
          <ul className="space-y-2">
            {missingDiffs.map((diff, i) => (
              <li key={i} className="text-sm text-text-secondary flex items-start gap-2">
                <span className="text-red-400 mt-1">•</span>
                {diff.description}
              </li>
            ))}
          </ul>
        </GlassCard>
      )}

      {/* Weak */}
      {weakDiffs.length > 0 && (
        <GlassCard>
          <h4 className="font-semibold text-yellow-400 mb-3 flex items-center gap-2">
            <AlertTriangle className="h-5 w-5" />
            改善が必要な項目
          </h4>
          <ul className="space-y-2">
            {weakDiffs.map((diff, i) => (
              <li key={i} className="text-sm text-text-secondary flex items-start gap-2">
                <span className="text-yellow-400 mt-1">•</span>
                {diff.description}
              </li>
            ))}
          </ul>
        </GlassCard>
      )}

      {/* Unique */}
      {uniqueDiffs.length > 0 && (
        <GlassCard>
          <h4 className="font-semibold text-green-400 mb-3 flex items-center gap-2">
            <Sparkles className="h-5 w-5" />
            自社の強み
          </h4>
          <ul className="space-y-2">
            {uniqueDiffs.map((diff, i) => (
              <li key={i} className="text-sm text-text-secondary flex items-start gap-2">
                <span className="text-green-400 mt-1">•</span>
                {diff.description}
              </li>
            ))}
          </ul>
        </GlassCard>
      )}
    </div>
  );
}
```

---

## AN-5. ToDo連動

| 差分 | ToDo |
|------|------|
| missing (heading) | H2セクション追加 |
| missing (faq) | FAQ追加 |
| weak (depth) | コンテンツ拡充 |
| weak (volume) | 情報量追加 |

source_checks=["competitor_diff"]

---

## AN-6. 受け入れ基準

- [ ] 競合構成が一覧で見える
- [ ] 不足観点が明確に表示される
- [ ] 自社独自の強みも表示される
- [ ] ToDoに直結する
- [ ] 3社まで比較できる

---

## AN-7. この機能が完成すると

```md
・競合との差がひと目で分かる
・「何を足すべきか」が明確になる
・感覚ではなくデータで判断できる
```
