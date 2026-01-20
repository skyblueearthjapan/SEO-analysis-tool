# Appendix AB — ユーザー向け「このツールは何を解析しているか」説明仕様

Version: 0.1
目的:
- ユーザーの **不安・不信感を消す**
- 「なぜこのToDoが出たのか」を説明できるようにする
- サポート・説明・営業コストを下げる

対象:
- Result画面の「About / How this works」
- LP / ヘルプ / 初回オンボーディング

---

## AB-1. このAppendixで作るもの

### UIとして作るもの

- **Analysis Overview（説明ページ）**
- Checklistと完全連動した説明

### コンテンツとして作るもの

- 解析カテゴリ別の説明文
- 「見ていること / 見ていないこと」
- このツールの立ち位置（≠魔法、＝構造理解）

---

## AB-2. 表示場所（推奨）

### パターンA（最優先）

- Result画面右上 → `How this analysis works`

### パターンB（補助）

- サイドバー → `About Analysis`

---

## AB-3. ページ構成（そのままUI化できる）

```
# このSEO診断ツールについて

## 1. このツールは何をしているのか
## 2. 実行している解析一覧
## 3. 各解析で「分かること」
## 4. このツールが見ていないもの
## 5. ToDoはどうやって作られているか
## 6. 競合比較の考え方
## 7. 注意点と限界
```

---

## AB-4. コンテンツ原稿（完成版）

### 1. このツールは何をしているのか

このツールは、SEOにおいて重要な「構造・技術・コンテンツの欠損や差分」を機械的に洗い出し、**今やるべき改善を優先度付きで提示する**診断ツールです。

検索順位を直接予測したり、必ず順位が上がることを保証するものではありません。

---

### 2. 実行している解析一覧

（AnalysisChecklist と同じ並び）

- HTTP取得・ステータス確認
- title / meta / canonical / robots
- 見出し構造（h1/h2/h3）
- テキスト量・リンク構造
- 画像alt属性
- 構造化データ（FAQ / Organization 等）
- PageSpeed / Core Web Vitals
- Search Console（連携時）
- コンテンツ意図カバー
- 競合ページとの構造差分

---

### 3. 各解析で「分かること」

#### HTTP / 技術

検索エンジンがページを正しく取得・評価できる状態かどうかが分かります。取得できないページは、内容に関わらず評価されません。

#### 見出し・構造

検索ユーザーにとって必要な情報が、論理的な構造で整理されているかを確認します。

#### 意図カバー

公式サイトや紹介ページにおいて「ユーザーが知りたいであろう要素」が十分に含まれているかをチェックします。

#### 競合比較

競合ページにあって、自社ページに無い構造・要素を差分として検出します。

---

### 4. このツールが見ていないもの（重要）

このツールは、以下の点については直接は解析していません。

- Googleの検索アルゴリズム内部
- 被リンクの質（外部API未連携時）
- 実際のユーザー行動（滞在時間・直帰率など）
- 広告やSNSによる影響

---

### 5. ToDoはどうやって作られているか

ToDoは、解析結果をもとに以下に分類して生成されています：

- **P0（致命的）**: 今すぐ対応が必要な問題
- **P1（優先）**: 1-2週間以内に対応したい問題
- **P2（継続）**: 継続的に取り組む改善

すべてのToDoには、必ず「どの解析が根拠か」が紐づいています。

---

### 6. 競合比較の考え方

競合より多く書けば良い、という考え方ではありません。

競合が満たしていて、かつ自社が満たしていない「情報の欠損」を中心に見ています。

---

### 7. 注意点と限界

SEOは不確実性のある領域です。本ツールの結果は「改善判断の材料」であり、すべての結果を保証するものではありません。

---

## AB-5. Frontend実装

### AB-5.1 コンポーネント

```tsx
// components/help/AboutAnalysis.tsx
"use client";

import { GlassCard } from "@/components/layout/GlassCard";
import { Info, CheckCircle, AlertTriangle, HelpCircle } from "lucide-react";

const sections = [
  {
    id: "what",
    title: "このツールは何をしているのか",
    content: `このツールは、SEOにおいて重要な「構造・技術・コンテンツの欠損や差分」を機械的に洗い出し、今やるべき改善を優先度付きで提示する診断ツールです。

検索順位を直接予測したり、必ず順位が上がることを保証するものではありません。`
  },
  {
    id: "checklist",
    title: "実行している解析一覧",
    content: `• HTTP取得・ステータス確認
• title / meta / canonical / robots
• 見出し構造（h1/h2/h3）
• テキスト量・リンク構造
• 画像alt属性
• 構造化データ（FAQ / Organization 等）
• PageSpeed / Core Web Vitals
• Search Console（連携時）
• コンテンツ意図カバー
• 競合ページとの構造差分`
  },
  {
    id: "findings",
    title: "各解析で分かること",
    content: `【HTTP / 技術】
検索エンジンがページを正しく取得・評価できる状態かどうかが分かります。

【見出し・構造】
検索ユーザーにとって必要な情報が、論理的な構造で整理されているかを確認します。

【意図カバー】
公式サイトや紹介ページにおいて「ユーザーが知りたいであろう要素」が十分に含まれているかをチェックします。

【競合比較】
競合ページにあって、自社ページに無い構造・要素を差分として検出します。`
  },
  {
    id: "limitations",
    title: "このツールが見ていないもの",
    content: `このツールは、以下の点については直接は解析していません。

• Googleの検索アルゴリズム内部
• 被リンクの質（外部API未連携時）
• 実際のユーザー行動（滞在時間・直帰率など）
• 広告やSNSによる影響`
  },
  {
    id: "todos",
    title: "ToDoはどうやって作られているか",
    content: `ToDoは、解析結果をもとに以下に分類して生成されています：

• P0（致命的）: 今すぐ対応が必要な問題
• P1（優先）: 1-2週間以内に対応したい問題
• P2（継続）: 継続的に取り組む改善

すべてのToDoには、必ず「どの解析が根拠か」が紐づいています。`
  },
  {
    id: "compare",
    title: "競合比較の考え方",
    content: `競合より多く書けば良い、という考え方ではありません。

競合が満たしていて、かつ自社が満たしていない「情報の欠損」を中心に見ています。`
  },
  {
    id: "notes",
    title: "注意点と限界",
    content: `SEOは不確実性のある領域です。本ツールの結果は「改善判断の材料」であり、すべての結果を保証するものではありません。`
  }
];

export function AboutAnalysis() {
  return (
    <div className="space-y-6 max-w-3xl mx-auto">
      <div className="text-center mb-8">
        <h1 className="text-2xl font-bold text-text-primary mb-2">
          このSEO診断ツールについて
        </h1>
        <p className="text-text-muted">
          解析内容と結果の見方を理解する
        </p>
      </div>

      {sections.map((section) => (
        <GlassCard key={section.id}>
          <h2 className="text-lg font-semibold text-text-primary mb-3 flex items-center gap-2">
            <Info className="h-5 w-5 text-accent-cyan" />
            {section.title}
          </h2>
          <p className="text-text-secondary whitespace-pre-line text-sm leading-relaxed">
            {section.content}
          </p>
        </GlassCard>
      ))}
    </div>
  );
}
```

### AB-5.2 ヘルプボタン（Result画面用）

```tsx
// components/help/HelpButton.tsx
"use client";

import { useState } from "react";
import { HelpCircle, X } from "lucide-react";
import { AboutAnalysis } from "./AboutAnalysis";

export function HelpButton() {
  const [open, setOpen] = useState(false);

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="flex items-center gap-1 text-xs text-text-muted hover:text-accent-cyan transition-colors"
      >
        <HelpCircle className="h-4 w-4" />
        <span>解析について</span>
      </button>

      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="relative w-full max-w-4xl max-h-[90vh] overflow-y-auto bg-bg-base rounded-xl p-6 m-4">
            <button
              onClick={() => setOpen(false)}
              className="absolute top-4 right-4 p-2 hover:bg-bg-elevated rounded-lg"
            >
              <X className="h-5 w-5" />
            </button>
            <AboutAnalysis />
          </div>
        </div>
      )}
    </>
  );
}
```

---

## AB-6. 受け入れ基準

- [ ] ユーザーが「何を見ているツールか」理解できる
- [ ] ToDoの納得感が上がる
- [ ] サポート説明にそのまま使える
- [ ] Result画面からヘルプにアクセスできる
- [ ] 過度な約束・保証がない表現になっている
