# Appendix Y — Site Crawl（サイト全体クロール）MVP仕様

Version: 0.1
目的: サイト構造問題（Orphan/深さ/4xx/5xx）を検出する
対象: 中規模サイト（〜100ページ）

---

## Y-1. クロール設計（MVP決め打ち）

### 制限値（固定）

```yaml
MAX_PAGES: 100
MAX_DEPTH: 3
REQUEST_INTERVAL_SEC: 1
```

### ポリシー

- 同一ホストのみ
- robots.txt 尊重（Disallow最低限）
- クエリ除去・末尾スラッシュ正規化

---

## Y-2. データモデル

### テーブル（追加）

```sql
CREATE TABLE crawl_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  site_id UUID NOT NULL REFERENCES sites(site_id),
  start_url TEXT NOT NULL,
  status VARCHAR(20) DEFAULT 'pending',  -- pending, running, completed, failed
  pages_crawled INT DEFAULT 0,
  errors_count INT DEFAULT 0,
  started_at TIMESTAMP,
  finished_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE crawl_pages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id UUID NOT NULL REFERENCES crawl_runs(id),
  url TEXT NOT NULL,
  status_code INT,
  depth INT,
  title TEXT,
  canonical TEXT,
  inlinks INT DEFAULT 0,
  outlinks INT DEFAULT 0,
  response_time_ms INT,
  crawled_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_crawl_pages_run_id ON crawl_pages(run_id);
CREATE INDEX idx_crawl_pages_url ON crawl_pages(url);
```

---

## Y-3. Analyzer仕様

### ファイル

```
app/services/analyzers/site_crawl.py
```

### 実装

```python
# app/services/analyzers/site_crawl.py
import asyncio
import httpx
from dataclasses import dataclass
from typing import List, Dict, Any, Literal, Set
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

CheckStatus = Literal["done", "partial", "skipped", "not_supported"]

@dataclass
class AnalyzerOutput:
    check_code: str
    status: CheckStatus
    notes: List[str]
    evidence: List[Dict[str, Any]]
    todo_candidates: List[Dict[str, Any]]

@dataclass
class CrawlConfig:
    max_pages: int = 100
    max_depth: int = 3
    request_interval: float = 1.0
    timeout: float = 10.0

@dataclass
class CrawledPage:
    url: str
    status_code: int
    depth: int
    title: str
    canonical: str
    outlinks: List[str]
    response_time_ms: int

class SiteCrawler:
    def __init__(self, start_url: str, config: CrawlConfig):
        self.start_url = start_url
        self.config = config
        self.base_host = urlparse(start_url).netloc
        self.visited: Set[str] = set()
        self.pages: List[CrawledPage] = []
        self.errors: Dict[str, int] = {"4xx": 0, "5xx": 0}

    def normalize_url(self, url: str) -> str:
        """Normalize URL (remove query, trailing slash)"""
        parsed = urlparse(url)
        path = parsed.path.rstrip("/") or "/"
        return f"{parsed.scheme}://{parsed.netloc}{path}"

    def is_same_host(self, url: str) -> bool:
        """Check if URL is same host"""
        return urlparse(url).netloc == self.base_host

    async def crawl_page(self, url: str, depth: int, client: httpx.AsyncClient) -> CrawledPage | None:
        """Crawl a single page"""
        if depth > self.config.max_depth:
            return None
        if len(self.visited) >= self.config.max_pages:
            return None

        normalized = self.normalize_url(url)
        if normalized in self.visited:
            return None

        self.visited.add(normalized)

        try:
            import time
            start = time.time()
            response = await client.get(url, follow_redirects=True, timeout=self.config.timeout)
            response_time = int((time.time() - start) * 1000)

            status_code = response.status_code

            if 400 <= status_code < 500:
                self.errors["4xx"] += 1
            elif status_code >= 500:
                self.errors["5xx"] += 1

            if status_code != 200:
                return CrawledPage(
                    url=normalized,
                    status_code=status_code,
                    depth=depth,
                    title="",
                    canonical="",
                    outlinks=[],
                    response_time_ms=response_time
                )

            soup = BeautifulSoup(response.text, "html.parser")

            # Extract title
            title_tag = soup.find("title")
            title = title_tag.get_text(strip=True) if title_tag else ""

            # Extract canonical
            canonical_tag = soup.find("link", rel="canonical")
            canonical = canonical_tag.get("href", "") if canonical_tag else ""

            # Extract outlinks
            outlinks = []
            for a in soup.find_all("a", href=True):
                href = a["href"]
                full_url = urljoin(url, href)
                if self.is_same_host(full_url) and not href.startswith("#"):
                    outlinks.append(self.normalize_url(full_url))

            return CrawledPage(
                url=normalized,
                status_code=status_code,
                depth=depth,
                title=title,
                canonical=canonical,
                outlinks=list(set(outlinks)),
                response_time_ms=response_time
            )

        except Exception:
            return None

    async def crawl(self) -> List[CrawledPage]:
        """Run the crawl"""
        queue = [(self.start_url, 0)]  # (url, depth)

        async with httpx.AsyncClient(
            headers={"User-Agent": "SEOAnalysisTool/1.0"},
            follow_redirects=True
        ) as client:
            while queue and len(self.visited) < self.config.max_pages:
                url, depth = queue.pop(0)

                page = await self.crawl_page(url, depth, client)
                if page:
                    self.pages.append(page)

                    # Add outlinks to queue
                    for outlink in page.outlinks:
                        if outlink not in self.visited and depth + 1 <= self.config.max_depth:
                            queue.append((outlink, depth + 1))

                # Rate limiting
                await asyncio.sleep(self.config.request_interval)

        return self.pages

    def find_orphans(self) -> List[str]:
        """Find potential orphan pages (no inlinks from crawled pages)"""
        all_outlinks: Set[str] = set()
        crawled_urls = {p.url for p in self.pages}

        for page in self.pages:
            all_outlinks.update(page.outlinks)

        # Pages that were crawled but not linked from any other page
        orphans = []
        for page in self.pages:
            if page.url != self.start_url:
                inlinks = sum(1 for p in self.pages if page.url in p.outlinks)
                if inlinks == 0:
                    orphans.append(page.url)

        return orphans


async def analyze_site_crawl(
    start_url: str,
    enabled: bool = True
) -> AnalyzerOutput:
    """Run site crawl analysis"""
    if not enabled:
        return AnalyzerOutput(
            check_code="site_crawl",
            status="skipped",
            notes=["Site crawl disabled"],
            evidence=[],
            todo_candidates=[]
        )

    config = CrawlConfig()
    crawler = SiteCrawler(start_url, config)

    try:
        pages = await crawler.crawl()
        orphans = crawler.find_orphans()

        # Calculate max depth reached
        max_depth_reached = max((p.depth for p in pages), default=0)

        evidence = [{
            "id": "ev_crawl_summary",
            "kind": "crawl",
            "title": "サイトクロールサマリ",
            "severity": "info",
            "data": {
                "pages_crawled": len(pages),
                "errors_4xx": crawler.errors["4xx"],
                "errors_5xx": crawler.errors["5xx"],
                "orphan_candidates": len(orphans),
                "max_depth": max_depth_reached,
                "orphan_urls": orphans[:10]  # Top 10
            }
        }]

        # Error pages evidence
        error_pages = [p for p in pages if p.status_code >= 400]
        if error_pages:
            evidence.append({
                "id": "ev_crawl_errors",
                "kind": "crawl",
                "title": "エラーページ一覧",
                "severity": "warning" if crawler.errors["5xx"] > 0 else "info",
                "data": {
                    "error_pages": [
                        {"url": p.url, "status": p.status_code, "depth": p.depth}
                        for p in error_pages[:20]
                    ]
                }
            })

        # Generate todos
        todo_candidates = []

        if crawler.errors["5xx"] > 0:
            todo_candidates.append({
                "title": "サーバーエラー（5xx）の修正",
                "priority": "P0",
                "category": "technical",
                "details": f"{crawler.errors['5xx']}件のサーバーエラーが検出されました",
                "source_checks": ["site_crawl"]
            })

        if crawler.errors["4xx"] > 0:
            todo_candidates.append({
                "title": "ページエラー（4xx）の修正",
                "priority": "P1",
                "category": "technical",
                "details": f"{crawler.errors['4xx']}件のページエラーが検出されました",
                "source_checks": ["site_crawl"]
            })

        if len(orphans) > 0:
            todo_candidates.append({
                "title": "孤立ページへの内部リンク追加",
                "priority": "P1",
                "category": "structure",
                "details": f"{len(orphans)}件の孤立ページ候補が検出されました",
                "source_checks": ["site_crawl"]
            })

        return AnalyzerOutput(
            check_code="site_crawl",
            status="done",
            notes=[],
            evidence=evidence,
            todo_candidates=todo_candidates
        )

    except Exception as e:
        return AnalyzerOutput(
            check_code="site_crawl",
            status="partial",
            notes=[f"Crawl error: {str(e)}"],
            evidence=[],
            todo_candidates=[]
        )
```

---

## Y-4. analysis_checks 反映ルール

| 条件 | status |
|------|--------|
| crawl実行完了 | done |
| crawl途中でエラー | partial |
| crawl未実行/無効 | skipped |

---

## Y-5. ToDo生成ルール

| 条件 | ToDo |
|------|------|
| 5xx > 0 | P0 サーバーエラー修正 |
| 4xx > 0 | P1 ページエラー修正 |
| orphan > 0 | P1 内部リンク改善 |
| depth == MAX | P2 構造見直し |

---

## Y-6. ToDo詳細テンプレート

```python
TODO_DETAIL_TEMPLATES["crawl_5xx_error"] = {
    "why": "サーバーエラー（5xx）は、ページが正常に表示されず、ユーザー体験とSEOに深刻な悪影響を与えます。",
    "root_causes": [
        {"label": "サーバー設定の問題", "likelihood": "high", "notes": ""},
        {"label": "アプリケーションエラー", "likelihood": "high", "notes": ""},
        {"label": "リソース不足", "likelihood": "medium", "notes": ""}
    ],
    "steps": [
        {"text": "サーバーログでエラー原因を特定する", "done": False},
        {"text": "該当ページのコードを確認し修正する", "done": False},
        {"text": "修正後、ステータスコードが200になることを確認する", "done": False}
    ],
    "verification": [
        {"metric": "ステータスコード", "target": "200", "how_to_check": "curl -I URL"}
    ]
}

TODO_DETAIL_TEMPLATES["crawl_orphan"] = {
    "why": "孤立ページ（内部リンクがないページ）は、検索エンジンがクロールしにくく、ユーザーも到達しにくいため、SEO評価が低くなります。",
    "root_causes": [
        {"label": "ナビゲーションから外れている", "likelihood": "high", "notes": ""},
        {"label": "古いページが放置されている", "likelihood": "medium", "notes": ""},
        {"label": "リンク設計が不十分", "likelihood": "medium", "notes": ""}
    ],
    "steps": [
        {"text": "孤立ページの一覧を確認する", "done": False},
        {"text": "関連ページから内部リンクを追加する", "done": False},
        {"text": "不要なページは削除またはリダイレクトを検討する", "done": False}
    ],
    "verification": [
        {"metric": "内部リンク数", "target": "1以上", "how_to_check": "再クロールで確認"}
    ]
}
```

---

## Y-7. UI連動

### Checklist
- crawl実行 → `site_crawl = done`
- crawl未実行 → `site_crawl = skipped`

### TodoDetailDrawer
- 根拠: エラーページ一覧、孤立ページ一覧
- 手順: ログ確認 → 修正 → 再クロール

---

## Y-8. 受け入れ基準

- [ ] start_urlからMAX_PAGESまでクロールできる
- [ ] robots.txtを尊重する
- [ ] 4xx/5xxエラーが検出できる
- [ ] 孤立ページ候補が検出できる
- [ ] evidenceにサマリとエラー一覧が含まれる
- [ ] 適切なToDoが生成される
- [ ] Checklistで site_crawl の状態が表示される
