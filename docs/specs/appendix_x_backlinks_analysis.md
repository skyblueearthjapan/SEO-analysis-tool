# Appendix X — Backlinks（被リンク分析）MVP仕様 & Providerアダプタ

Version: 0.1
目的: 外部評価（被リンク）を定量化し、競合との差を ToDo として出す
対象: FastAPI + analysis_checks + TodoDetailDrawer

---

## X-1. MVP方針（決め打ち）

### 採用方針

- **初期MVPは Provider 1社固定**
- **スナップショット取得（毎日/毎回Runではない）**
- **競合比較できる最低限指標のみ**

### 推奨Provider（結論）

**Moz Link API**

理由:
- API仕様がシンプル
- 月額が比較的安価
- ドメイン評価（Domain Authority）が使いやすい
- MVPには十分

---

## X-2. 取得する指標（MVP）

| 指標 | 説明 |
|------|------|
| ref_domains | 参照ドメイン数 |
| backlinks_total | 被リンク総数 |
| dofollow_ratio | dofollow比率 |
| domain_authority | ドメインオーソリティ |
| top_ref_domains | 上位参照元 |

---

## X-3. Analyzer仕様

### ファイル

```
app/services/analyzers/backlinks_moz.py
```

### 入力

- official_url
- competitor_urls[]
- moz_api_key（設定）

### 出力（AnalyzerOutput）

```json
{
  "check_code": "backlinks",
  "status": "done",
  "notes": [],
  "evidence": [
    {
      "id": "ev_backlinks_summary_official",
      "kind": "backlinks",
      "title": "被リンクサマリ（公式）",
      "severity": "info",
      "data": {
        "ref_domains": 32,
        "backlinks_total": 420,
        "dofollow_ratio": 0.68,
        "domain_authority": 18,
        "top_ref_domains": ["example.jp", "theater-info.com"]
      }
    }
  ],
  "todo_candidates": []
}
```

---

## X-4. analysis_checks 反映ルール

| 条件 | status |
|------|--------|
| APIキーあり & 成功 | done |
| APIキーあり & timeout | partial |
| APIキーなし | skipped |

---

## X-5. ToDo生成ルール（例）

競合平均との差が大きい場合:
- **P1**「被リンク獲得施策を検討」

ref_domains が 10 未満:
- **P1**「外部掲載・紹介依頼を強化」

```json
{
  "title": "被リンク獲得施策の実施",
  "priority": "P1",
  "category": "authority",
  "source_checks": ["backlinks"]
}
```

---

## X-6. UI連動

- Checklist → backlinks = Done
- TodoDetailDrawer:
  - 根拠: ref_domains / 競合比較
  - テンプレ: 「掲載依頼メール文」

---

## X-7. Backend実装詳細

### X-7.1 設定（config.py追加）

```python
MOZ_API_KEY: str = os.getenv("MOZ_API_KEY", "")
MOZ_ACCESS_ID: str = os.getenv("MOZ_ACCESS_ID", "")
```

### X-7.2 Moz APIクライアント

```python
# app/services/moz_client.py
import httpx
from typing import Optional, Dict, Any

class MozClient:
    BASE_URL = "https://lsapi.seomoz.com/v2"

    def __init__(self, access_id: str, api_key: str):
        self.access_id = access_id
        self.api_key = api_key

    async def get_url_metrics(self, url: str) -> Optional[Dict[str, Any]]:
        """Get URL metrics from Moz API"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/url_metrics",
                auth=(self.access_id, self.api_key),
                json={"targets": [url]},
                timeout=30.0
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("results"):
                    result = data["results"][0]
                    return {
                        "ref_domains": result.get("root_domains_to_root_domain", 0),
                        "backlinks_total": result.get("external_links_to_root_domain", 0),
                        "domain_authority": result.get("domain_authority", 0),
                        "page_authority": result.get("page_authority", 0)
                    }
            return None
```

### X-7.3 Analyzer実装

```python
# app/services/analyzers/backlinks_moz.py
from dataclasses import dataclass
from typing import List, Dict, Any, Literal
from app.services.moz_client import MozClient
from app.config import get_settings

CheckStatus = Literal["done", "partial", "skipped", "not_supported"]

@dataclass
class AnalyzerOutput:
    check_code: str
    status: CheckStatus
    notes: List[str]
    evidence: List[Dict[str, Any]]
    todo_candidates: List[Dict[str, Any]]

async def analyze_backlinks(
    official_url: str,
    competitor_urls: List[str]
) -> AnalyzerOutput:
    """Analyze backlinks using Moz API"""
    settings = get_settings()

    if not settings.MOZ_API_KEY or not settings.MOZ_ACCESS_ID:
        return AnalyzerOutput(
            check_code="backlinks",
            status="skipped",
            notes=["Moz API key not configured"],
            evidence=[],
            todo_candidates=[]
        )

    client = MozClient(settings.MOZ_ACCESS_ID, settings.MOZ_API_KEY)
    evidence = []
    todo_candidates = []

    try:
        # Get official site metrics
        official_metrics = await client.get_url_metrics(official_url)
        if official_metrics:
            evidence.append({
                "id": "ev_backlinks_summary_official",
                "kind": "backlinks",
                "title": "被リンクサマリ（公式）",
                "severity": "info",
                "data": {
                    "url": official_url,
                    **official_metrics
                }
            })

            # Generate todos if ref_domains is low
            if official_metrics.get("ref_domains", 0) < 10:
                todo_candidates.append({
                    "title": "外部掲載・紹介依頼の強化",
                    "priority": "P1",
                    "category": "authority",
                    "details": f"参照ドメイン数が {official_metrics.get('ref_domains', 0)} と少ないため、外部露出を強化",
                    "source_checks": ["backlinks"]
                })

        # Get competitor metrics for comparison
        competitor_metrics = []
        for comp_url in competitor_urls[:3]:  # Limit to 3 competitors
            metrics = await client.get_url_metrics(comp_url)
            if metrics:
                competitor_metrics.append({
                    "url": comp_url,
                    **metrics
                })

        if competitor_metrics:
            evidence.append({
                "id": "ev_backlinks_competitors",
                "kind": "backlinks",
                "title": "被リンク比較（競合）",
                "severity": "info",
                "data": {
                    "competitors": competitor_metrics
                }
            })

        return AnalyzerOutput(
            check_code="backlinks",
            status="done",
            notes=[],
            evidence=evidence,
            todo_candidates=todo_candidates
        )

    except Exception as e:
        return AnalyzerOutput(
            check_code="backlinks",
            status="partial",
            notes=[f"API error: {str(e)}"],
            evidence=[],
            todo_candidates=[]
        )
```

---

## X-8. ToDo詳細テンプレート

```python
TODO_DETAIL_TEMPLATES["backlinks_low"] = {
    "why": "被リンク（外部サイトからのリンク）は、サイトの信頼性・権威性を示す重要な指標です。参照ドメイン数が少ないと、検索エンジンからの評価が低くなる可能性があります。",
    "root_causes": [
        {"label": "サイトの認知度が低い", "likelihood": "high", "notes": ""},
        {"label": "リンクされる価値のあるコンテンツが少ない", "likelihood": "medium", "notes": ""},
        {"label": "PR・広報活動が不足", "likelihood": "medium", "notes": ""}
    ],
    "steps": [
        {"text": "業界メディアやポータルサイトへの掲載を依頼する", "done": False},
        {"text": "プレスリリースを配信する", "done": False},
        {"text": "SNSでの発信を強化し、シェアされやすいコンテンツを作成する", "done": False},
        {"text": "関連団体や協会への登録を検討する", "done": False}
    ],
    "templates": [
        {
            "title": "掲載依頼メール文（日本語）",
            "type": "text",
            "content": "件名: 【掲載のお願い】〇〇について\n\nご担当者様\n\n突然のご連絡失礼いたします。\n〇〇と申します。\n\n貴サイトの〇〇に関する記事を拝見し、大変参考になりました。\n私どもは〇〇の活動をしており、もしよろしければ貴サイトでご紹介いただけないでしょうか。\n\n【サイト情報】\nURL: \n概要: \n\nご検討いただけますと幸いです。\n何卒よろしくお願いいたします。"
        }
    ],
    "verification": [
        {"metric": "参照ドメイン数", "target": "前月比+5以上", "how_to_check": "Moz / Ahrefs等で確認"},
        {"metric": "DA（ドメインオーソリティ）", "target": "前月比+1以上", "how_to_check": "Moz Link Explorerで確認"}
    ]
}
```

---

## X-9. 受け入れ基準

- [ ] Moz APIキー設定時、被リンクデータが取得できる
- [ ] 競合との比較データが evidence に含まれる
- [ ] ref_domains が閾値未満の場合、ToDoが生成される
- [ ] Checklist で backlinks = done/partial/skipped が正しく表示される
- [ ] TodoDetailDrawer で根拠・手順・テンプレートが表示される
