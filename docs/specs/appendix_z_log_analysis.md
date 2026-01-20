# Appendix Z — Log Analysis（ログ解析）MVP仕様

Version: 0.1
目的: クローラ挙動とエラー傾向を把握する
方針: **最初は「ファイルアップロード型」**

---

## Z-1. MVP前提（超重要）

### 対応ログ形式

- NGINX / Apache アクセスログ（Combined Log Format）
- CSV / TSV

### 取得方法

- UIから **手動アップロード**
- 自動連携はしない（Phase Z-2で検討）

### Combined Log Format例

```
127.0.0.1 - - [20/Jan/2026:10:00:00 +0900] "GET /about HTTP/1.1" 200 1234 "-" "Googlebot/2.1"
```

---

## Z-2. 解析項目（MVP）

| 項目 | 説明 |
|------|------|
| bot_hits | Googlebot/Bingbot等のアクセス数 |
| status_4xx | 4xxエラー数 |
| status_5xx | 5xxエラー数 |
| heavy_urls | 応答時間が重いURL（response timeがある場合） |
| top_urls | 最もアクセスの多いURL |

---

## Z-3. データモデル

### テーブル（追加）

```sql
CREATE TABLE log_uploads (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  site_id UUID NOT NULL REFERENCES sites(site_id),
  filename TEXT NOT NULL,
  file_size INT,
  log_format VARCHAR(50),  -- nginx, apache, csv
  date_range_start DATE,
  date_range_end DATE,
  total_lines INT,
  parsed_lines INT,
  status VARCHAR(20) DEFAULT 'pending',  -- pending, processing, completed, failed
  uploaded_at TIMESTAMP DEFAULT NOW(),
  processed_at TIMESTAMP
);

CREATE TABLE log_analysis_results (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  upload_id UUID NOT NULL REFERENCES log_uploads(id),
  analysis_json JSONB,
  created_at TIMESTAMP DEFAULT NOW()
);
```

---

## Z-4. Analyzer仕様

### ファイル

```
app/services/analyzers/log_analysis.py
```

### 実装

```python
# app/services/analyzers/log_analysis.py
import re
from dataclasses import dataclass
from typing import List, Dict, Any, Literal
from collections import defaultdict
from datetime import datetime

CheckStatus = Literal["done", "partial", "skipped", "not_supported"]

@dataclass
class AnalyzerOutput:
    check_code: str
    status: CheckStatus
    notes: List[str]
    evidence: List[Dict[str, Any]]
    todo_candidates: List[Dict[str, Any]]

# Combined Log Format regex
COMBINED_LOG_PATTERN = re.compile(
    r'(?P<ip>[\d\.]+)\s+-\s+\S+\s+'
    r'\[(?P<datetime>[^\]]+)\]\s+'
    r'"(?P<method>\w+)\s+(?P<url>\S+)\s+HTTP/[\d\.]+"\s+'
    r'(?P<status>\d+)\s+'
    r'(?P<size>\d+|-)\s+'
    r'"(?P<referer>[^"]*)"\s+'
    r'"(?P<user_agent>[^"]*)"'
)

BOT_PATTERNS = {
    "googlebot": re.compile(r'googlebot', re.I),
    "bingbot": re.compile(r'bingbot', re.I),
    "yandex": re.compile(r'yandex', re.I),
    "baiduspider": re.compile(r'baiduspider', re.I),
    "duckduckbot": re.compile(r'duckduckbot', re.I),
}

@dataclass
class LogEntry:
    ip: str
    datetime_str: str
    method: str
    url: str
    status: int
    size: int
    referer: str
    user_agent: str

def parse_log_line(line: str) -> LogEntry | None:
    """Parse a single log line"""
    match = COMBINED_LOG_PATTERN.match(line.strip())
    if not match:
        return None

    try:
        return LogEntry(
            ip=match.group("ip"),
            datetime_str=match.group("datetime"),
            method=match.group("method"),
            url=match.group("url"),
            status=int(match.group("status")),
            size=int(match.group("size")) if match.group("size") != "-" else 0,
            referer=match.group("referer"),
            user_agent=match.group("user_agent")
        )
    except (ValueError, AttributeError):
        return None

def detect_bot(user_agent: str) -> str | None:
    """Detect bot from user agent"""
    for bot_name, pattern in BOT_PATTERNS.items():
        if pattern.search(user_agent):
            return bot_name
    return None

def analyze_log_content(log_content: str) -> Dict[str, Any]:
    """Analyze log content and return statistics"""
    lines = log_content.strip().split("\n")

    bot_hits: Dict[str, int] = defaultdict(int)
    status_counts: Dict[str, int] = defaultdict(int)
    url_hits: Dict[str, int] = defaultdict(int)
    error_urls: Dict[str, List[int]] = defaultdict(list)

    parsed_count = 0
    total_count = len(lines)

    for line in lines:
        entry = parse_log_line(line)
        if not entry:
            continue

        parsed_count += 1

        # Bot detection
        bot = detect_bot(entry.user_agent)
        if bot:
            bot_hits[bot] += 1

        # Status counting
        if 400 <= entry.status < 500:
            status_counts["4xx"] += 1
            error_urls[entry.url].append(entry.status)
        elif entry.status >= 500:
            status_counts["5xx"] += 1
            error_urls[entry.url].append(entry.status)
        else:
            status_counts["2xx"] += 1

        # URL hits
        url_hits[entry.url] += 1

    # Sort and get top URLs
    top_urls = sorted(url_hits.items(), key=lambda x: x[1], reverse=True)[:20]
    top_error_urls = sorted(
        [(url, statuses) for url, statuses in error_urls.items()],
        key=lambda x: len(x[1]),
        reverse=True
    )[:10]

    return {
        "total_lines": total_count,
        "parsed_lines": parsed_count,
        "bot_hits": dict(bot_hits),
        "status_counts": dict(status_counts),
        "top_urls": [{"url": url, "hits": hits} for url, hits in top_urls],
        "top_error_urls": [
            {"url": url, "errors": statuses[:5], "count": len(statuses)}
            for url, statuses in top_error_urls
        ]
    }

async def analyze_logs(
    log_content: str | None = None,
    enabled: bool = True
) -> AnalyzerOutput:
    """Run log analysis"""
    if not enabled or not log_content:
        return AnalyzerOutput(
            check_code="log_analysis",
            status="skipped",
            notes=["No log data provided"],
            evidence=[],
            todo_candidates=[]
        )

    try:
        stats = analyze_log_content(log_content)

        evidence = [{
            "id": "ev_logs_summary",
            "kind": "logs",
            "title": "アクセスログ解析サマリ",
            "severity": "info",
            "data": {
                "total_lines": stats["total_lines"],
                "parsed_lines": stats["parsed_lines"],
                "googlebot_hits": stats["bot_hits"].get("googlebot", 0),
                "bingbot_hits": stats["bot_hits"].get("bingbot", 0),
                "status_4xx": stats["status_counts"].get("4xx", 0),
                "status_5xx": stats["status_counts"].get("5xx", 0),
                "top_urls": stats["top_urls"][:10]
            }
        }]

        # Error URLs evidence
        if stats["top_error_urls"]:
            evidence.append({
                "id": "ev_logs_errors",
                "kind": "logs",
                "title": "エラーURL一覧（ログより）",
                "severity": "warning" if stats["status_counts"].get("5xx", 0) > 0 else "info",
                "data": {
                    "error_urls": stats["top_error_urls"]
                }
            })

        # Generate todos
        todo_candidates = []

        if stats["status_counts"].get("5xx", 0) > 0:
            todo_candidates.append({
                "title": "サーバーエラー（5xx）の調査・修正",
                "priority": "P0",
                "category": "technical",
                "details": f"ログから {stats['status_counts']['5xx']} 件のサーバーエラーが検出されました",
                "source_checks": ["log_analysis"]
            })

        if stats["status_counts"].get("4xx", 0) > 10:
            todo_candidates.append({
                "title": "ページエラー（4xx）の調査",
                "priority": "P1",
                "category": "technical",
                "details": f"ログから {stats['status_counts']['4xx']} 件のページエラーが検出されました",
                "source_checks": ["log_analysis"]
            })

        googlebot_hits = stats["bot_hits"].get("googlebot", 0)
        if googlebot_hits == 0 and stats["parsed_lines"] > 100:
            todo_candidates.append({
                "title": "Googlebotのクロール促進",
                "priority": "P1",
                "category": "technical",
                "details": "ログにGooglebotのアクセスが検出されませんでした。サイトマップ送信や内部リンク改善を検討してください",
                "source_checks": ["log_analysis"]
            })

        return AnalyzerOutput(
            check_code="log_analysis",
            status="done",
            notes=[],
            evidence=evidence,
            todo_candidates=todo_candidates
        )

    except Exception as e:
        return AnalyzerOutput(
            check_code="log_analysis",
            status="partial",
            notes=[f"Parse error: {str(e)}"],
            evidence=[],
            todo_candidates=[]
        )
```

---

## Z-5. API（ログアップロード）

### エンドポイント

```
POST /api/v1/sites/{site_id}/logs/upload
```

### リクエスト

```
Content-Type: multipart/form-data
file: <log file>
```

### レスポンス

```json
{
  "upload_id": "uuid",
  "status": "processing",
  "filename": "access.log",
  "file_size": 1234567
}
```

### 実装

```python
# app/routers/logs.py
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

router = APIRouter()

@router.post("/{site_id}/logs/upload")
async def upload_log(
    site_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """Upload access log for analysis"""
    # Validate file size (max 50MB)
    MAX_SIZE = 50 * 1024 * 1024
    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(400, "File too large (max 50MB)")

    # Save upload record
    upload = LogUpload(
        site_id=site_id,
        filename=file.filename,
        file_size=len(content),
        log_format="auto",  # Auto-detect
        status="processing"
    )
    db.add(upload)
    await db.flush()

    # Process in background (or sync for MVP)
    from app.services.analyzers.log_analysis import analyze_logs
    result = await analyze_logs(content.decode("utf-8", errors="ignore"))

    # Save result
    analysis_result = LogAnalysisResult(
        upload_id=upload.id,
        analysis_json=result.__dict__
    )
    db.add(analysis_result)

    upload.status = "completed"
    upload.processed_at = datetime.utcnow()

    await db.commit()

    return {
        "upload_id": upload.id,
        "status": "completed",
        "filename": file.filename,
        "file_size": len(content)
    }
```

---

## Z-6. analysis_checks 反映ルール

| 条件 | status |
|------|--------|
| ログアップロード & 解析完了 | done |
| ログアップロード & 解析エラー | partial |
| ログ未アップロード | skipped |

---

## Z-7. ToDo生成ルール

| 条件 | ToDo |
|------|------|
| 5xx > 0 | P0「サーバーエラー修正」 |
| 4xx > threshold | P1「ページエラー調査」 |
| bot_hits == 0 | P1「クロール促進」 |

---

## Z-8. ToDo詳細テンプレート

```python
TODO_DETAIL_TEMPLATES["log_5xx_error"] = {
    "why": "サーバーエラー（5xx）がログから検出されました。ユーザーとクローラーの両方に悪影響を与えます。",
    "root_causes": [
        {"label": "アプリケーションエラー", "likelihood": "high", "notes": ""},
        {"label": "サーバー設定の問題", "likelihood": "medium", "notes": ""},
        {"label": "リソース不足（メモリ/CPU）", "likelihood": "medium", "notes": ""}
    ],
    "steps": [
        {"text": "エラーログで詳細を確認する", "done": False},
        {"text": "該当URLをブラウザで確認する", "done": False},
        {"text": "原因を特定し修正する", "done": False},
        {"text": "修正後、ログを再確認する", "done": False}
    ],
    "verification": [
        {"metric": "5xxエラー数", "target": "0", "how_to_check": "次回ログ解析で確認"}
    ]
}

TODO_DETAIL_TEMPLATES["log_no_googlebot"] = {
    "why": "ログにGooglebotのアクセスが検出されませんでした。サイトが適切にクロールされていない可能性があります。",
    "root_causes": [
        {"label": "robots.txtでブロックしている", "likelihood": "high", "notes": ""},
        {"label": "サイトマップが未登録", "likelihood": "medium", "notes": ""},
        {"label": "内部リンクが不足", "likelihood": "medium", "notes": ""}
    ],
    "steps": [
        {"text": "robots.txtを確認し、ブロックしていないか確認する", "done": False},
        {"text": "Google Search Consoleでサイトマップを送信する", "done": False},
        {"text": "主要ページへの内部リンクを確認・追加する", "done": False},
        {"text": "URL検査でクロールをリクエストする", "done": False}
    ],
    "verification": [
        {"metric": "Googlebotアクセス", "target": "検出される", "how_to_check": "次回ログ解析で確認"}
    ]
}
```

---

## Z-9. UI連動

### Checklist
- 未アップロード → `log_analysis = skipped`
- アップロード済 → `log_analysis = done`

### ログアップロードUI（新規）

Result画面またはサイト設定に「ログアップロード」ボタンを追加:

```tsx
// components/logs/LogUploadButton.tsx
"use client";

import { useState } from "react";
import { Upload } from "lucide-react";

export function LogUploadButton({ siteId }: { siteId: string }) {
  const [uploading, setUploading] = useState(false);

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch(`/api/v1/sites/${siteId}/logs/upload`, {
        method: "POST",
        body: formData
      });
      if (res.ok) {
        // Refresh or show success
        window.location.reload();
      }
    } finally {
      setUploading(false);
    }
  }

  return (
    <label className="flex items-center gap-2 px-4 py-2 bg-bg-surface border border-border-subtle rounded-lg cursor-pointer hover:bg-bg-elevated transition-colors">
      <Upload className="h-4 w-4" />
      <span className="text-sm">{uploading ? "アップロード中..." : "ログをアップロード"}</span>
      <input
        type="file"
        accept=".log,.txt,.csv"
        className="hidden"
        onChange={handleUpload}
        disabled={uploading}
      />
    </label>
  );
}
```

### TodoDetailDrawer
- 根拠: bot_hits / エラーURL
- 手順: ログ確認 → 修正 → 再計測

---

## Z-10. 受け入れ基準

- [ ] Combined Log Formatのログファイルをパースできる
- [ ] Googlebot/Bingbotのアクセス数が集計される
- [ ] 4xx/5xxエラーが検出・集計される
- [ ] evidenceにサマリとエラーURL一覧が含まれる
- [ ] 適切なToDoが生成される
- [ ] Checklistで log_analysis の状態が表示される
- [ ] ファイルアップロードUIが動作する

---

## Z-11. 将来拡張（Phase Z-2）

- S3/GCS連携（自動取得）
- CloudFrontログ対応
- リアルタイム解析
- より詳細なBot分析（クロール頻度、パターン）
