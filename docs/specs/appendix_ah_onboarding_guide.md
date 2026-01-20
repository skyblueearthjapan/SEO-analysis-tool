# Appendix AH — 利用者向けガイド（Onboarding）

Version: 0.1
目的:
- 初めて使う人が迷わない
- 「何をすればいいツールか」を即理解できる
- SEOに詳しくなくても判断できるようにする

---

## AH-1. 表示タイミング（重要）

- 初回サイト作成後
- または「Guide」メニューからいつでも開ける

---

## AH-2. ガイド構成

```text
# はじめに
# このツールでできること
# 基本的な使い方（3ステップ）
# 結果画面の見方
# ToDoの考え方
# Progress（成果）の見方
# 注意点
```

---

## AH-3. 原稿（完成版）

### はじめに

```md
このツールは、SEOの専門知識がなくても
「今、何を直せばいいか」
「改善は進んでいるか」
を判断できるように設計されています。
```

---

### このツールでできること

```md
1. URLを登録して、SEO上の問題点を自動診断します
2. 優先度付きのToDoリストで「何から手をつけるか」が分かります
3. 改善の経過を時系列で追跡し、成果を可視化します
4. 競合サイトとの差分を分析し、不足している要素を特定します
```

---

### 基本的な使い方（3ステップ）

```md
1. URLを登録して解析を実行します
2. 表示されたToDoを上から順に対応します
3. Progress画面で変化を確認します
```

---

### 結果画面の見方

```md
スコアやToDoは、順位を保証するものではありません。
改善の「方向性」を示すものです。

- スコア: 現状の技術的な健全性を示す目安
- ToDo: 優先度順に並んだ改善項目
- Evidence: ToDoの根拠となるデータ
```

---

### ToDoの考え方

```md
P0: 今すぐ直すべき問題
    例：ページが表示されない、noindexが付いている

P1: 優先的に直す問題
    例：titleが長すぎる、meta descriptionがない

P2: 継続的に改善する項目
    例：コンテンツの充実、内部リンクの最適化
```

---

### Progressの見方

```md
改善はすぐに結果が出ないこともあります。
重要なのは、指標が「上向きかどうか」です。

- SERP順位: 検索結果での表示位置
- CTR: 検索結果からのクリック率
- PageSpeed: ページ表示速度スコア
- クロールエラー: 検索エンジンの取得エラー数
```

---

### 注意点

```md
- SEOは不確実性のある領域です
- 本ツールの結果は「改善判断の材料」です
- すべての結果を保証するものではありません
- 改善には時間がかかることがあります
```

---

## AH-4. Frontend実装

### コンポーネント構成

```
components/guide/
├─ OnboardingGuide.tsx
├─ GuideSection.tsx
├─ GuideModal.tsx
└─ FirstTimeOverlay.tsx
```

### OnboardingGuide.tsx

```tsx
"use client";

import { useState } from "react";
import { GlassCard } from "@/components/layout/GlassCard";
import { ChevronRight, BookOpen, Target, TrendingUp, AlertCircle } from "lucide-react";

const sections = [
  {
    id: "intro",
    icon: BookOpen,
    title: "はじめに",
    content: `このツールは、SEOの専門知識がなくても
「今、何を直せばいいか」
「改善は進んでいるか」
を判断できるように設計されています。`
  },
  {
    id: "steps",
    icon: Target,
    title: "基本的な使い方（3ステップ）",
    content: `1. URLを登録して解析を実行します
2. 表示されたToDoを上から順に対応します
3. Progress画面で変化を確認します`
  },
  {
    id: "todos",
    icon: ChevronRight,
    title: "ToDoの考え方",
    content: `P0: 今すぐ直すべき問題
P1: 優先的に直す問題
P2: 継続的に改善する項目`
  },
  {
    id: "progress",
    icon: TrendingUp,
    title: "Progressの見方",
    content: `改善はすぐに結果が出ないこともあります。
重要なのは、指標が「上向きかどうか」です。`
  },
  {
    id: "notes",
    icon: AlertCircle,
    title: "注意点",
    content: `SEOは不確実性のある領域です。
本ツールの結果は「改善判断の材料」であり、
すべての結果を保証するものではありません。`
  }
];

export function OnboardingGuide() {
  const [expandedId, setExpandedId] = useState<string | null>("intro");

  return (
    <div className="space-y-4 max-w-2xl mx-auto">
      <div className="text-center mb-6">
        <h1 className="text-2xl font-bold text-text-primary mb-2">
          利用ガイド
        </h1>
        <p className="text-text-muted">
          このツールの使い方を理解する
        </p>
      </div>

      {sections.map((section) => {
        const Icon = section.icon;
        const isExpanded = expandedId === section.id;

        return (
          <GlassCard key={section.id}>
            <button
              onClick={() => setExpandedId(isExpanded ? null : section.id)}
              className="w-full flex items-center justify-between text-left"
            >
              <div className="flex items-center gap-3">
                <Icon className="h-5 w-5 text-accent-cyan" />
                <span className="font-semibold text-text-primary">
                  {section.title}
                </span>
              </div>
              <ChevronRight
                className={`h-5 w-5 text-text-muted transition-transform ${
                  isExpanded ? "rotate-90" : ""
                }`}
              />
            </button>

            {isExpanded && (
              <p className="mt-4 text-text-secondary whitespace-pre-line text-sm leading-relaxed pl-8">
                {section.content}
              </p>
            )}
          </GlassCard>
        );
      })}
    </div>
  );
}
```

---

## AH-5. 初回表示ロジック

```tsx
// hooks/useFirstTimeUser.ts
import { useState, useEffect } from "react";

const STORAGE_KEY = "seo_tool_onboarding_completed";

export function useFirstTimeUser() {
  const [isFirstTime, setIsFirstTime] = useState(false);

  useEffect(() => {
    const completed = localStorage.getItem(STORAGE_KEY);
    if (!completed) {
      setIsFirstTime(true);
    }
  }, []);

  const markCompleted = () => {
    localStorage.setItem(STORAGE_KEY, "true");
    setIsFirstTime(false);
  };

  return { isFirstTime, markCompleted };
}
```

---

## AH-6. 受け入れ基準

- [ ] 初回ユーザーが迷わない
- [ ] SEO初心者でも判断できる
- [ ] サポート説明に使える
- [ ] いつでもガイドにアクセスできる
- [ ] スキップ可能
