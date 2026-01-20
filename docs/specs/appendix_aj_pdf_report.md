# Appendix AJ — PDFレポート生成仕様

Version: 0.1
目的:
- 診断・改善・成果を1つの資料にまとめる
- 提出・保存・共有に使える形にする
- クライアントや社内報告に使えるプロフェッショナルな出力

---

## AJ-1. PDF構成

```text
1. 表紙
   - サイト名
   - URL
   - レポート期間
   - 生成日時

2. 診断サマリ
   - 総合スコア
   - 主要指標
   - 解析実行項目

3. ToDo一覧
   - P0 / P1 / P2 分類
   - 完了 / 未完了 状態

4. Progress（指標推移）
   - SERP順位推移
   - クロールエラー推移
   - 被リンク推移

5. 改善ストーリー
   - 実施した改善
   - 観測された変化
   - 考察

6. 注意事項
   - 免責事項
   - データソース説明
```

---

## AJ-2. Backend実装

### エンドポイント

```python
# app/routers/reports.py
from fastapi import BackgroundTasks
from fastapi.responses import FileResponse
import tempfile

@router.post("/{site_id}/reports/pdf")
async def generate_pdf_report(
    site_id: UUID,
    from_date: date = Query(alias="from"),
    to_date: date = Query(alias="to"),
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Generate PDF report"""

    # 1. 全データ収集
    report_data = await collect_report_data(db, site_id, from_date, to_date)

    # 2. HTML生成
    html_content = render_report_html(report_data)

    # 3. PDF生成
    pdf_path = await generate_pdf_from_html(html_content)

    # 4. 一時ファイルを後で削除
    background_tasks.add_task(cleanup_temp_file, pdf_path)

    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"seo_report_{site_id}_{to_date}.pdf"
    )


async def collect_report_data(db, site_id: UUID, from_date: date, to_date: date) -> dict:
    """Collect all data needed for report"""

    site = await get_site(db, site_id)
    latest_result = await get_latest_analysis_result(db, site_id)
    todos = await get_todos(db, site_id)
    progress = await get_progress_data(db, site_id, from_date, to_date)
    story = await generate_improvement_story(db, site_id, from_date, to_date)

    return {
        "site": site,
        "range": {"from": from_date, "to": to_date},
        "generated_at": datetime.now(),
        "analysis_result": latest_result,
        "todos": todos,
        "progress": progress,
        "story": story
    }
```

### HTMLテンプレート

```python
# app/services/pdf_generator.py
from jinja2 import Environment, FileSystemLoader

def render_report_html(data: dict) -> str:
    """Render HTML from template"""

    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("report.html")

    return template.render(**data)
```

### PDF変換（Playwright推奨）

```python
# app/services/pdf_generator.py
from playwright.async_api import async_playwright
import tempfile

async def generate_pdf_from_html(html_content: str) -> str:
    """Convert HTML to PDF using Playwright"""

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        await page.set_content(html_content)

        # 一時ファイルにPDF出力
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            pdf_path = f.name

        await page.pdf(
            path=pdf_path,
            format="A4",
            margin={"top": "20mm", "bottom": "20mm", "left": "15mm", "right": "15mm"},
            print_background=True
        )

        await browser.close()

    return pdf_path
```

---

## AJ-3. HTMLテンプレート（report.html）

```html
<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <title>SEO診断レポート - {{ site.name }}</title>
  <style>
    @page {
      size: A4;
      margin: 20mm;
    }

    body {
      font-family: "Hiragino Sans", "Meiryo", sans-serif;
      font-size: 12px;
      line-height: 1.6;
      color: #333;
    }

    .cover {
      height: 100vh;
      display: flex;
      flex-direction: column;
      justify-content: center;
      align-items: center;
      text-align: center;
      page-break-after: always;
    }

    .cover h1 {
      font-size: 28px;
      margin-bottom: 20px;
    }

    .cover .url {
      font-size: 14px;
      color: #666;
    }

    .cover .period {
      margin-top: 40px;
      font-size: 12px;
      color: #999;
    }

    .section {
      page-break-inside: avoid;
      margin-bottom: 30px;
    }

    .section h2 {
      font-size: 18px;
      border-bottom: 2px solid #0ea5e9;
      padding-bottom: 8px;
      margin-bottom: 16px;
    }

    .summary-grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 16px;
      margin-bottom: 24px;
    }

    .summary-card {
      background: #f8fafc;
      border-radius: 8px;
      padding: 16px;
      text-align: center;
    }

    .summary-card .label {
      font-size: 10px;
      color: #64748b;
      margin-bottom: 4px;
    }

    .summary-card .value {
      font-size: 24px;
      font-weight: bold;
      color: #0f172a;
    }

    .todo-list {
      list-style: none;
      padding: 0;
    }

    .todo-item {
      display: flex;
      align-items: center;
      padding: 8px 0;
      border-bottom: 1px solid #e2e8f0;
    }

    .todo-priority {
      width: 32px;
      height: 20px;
      border-radius: 4px;
      font-size: 10px;
      font-weight: bold;
      display: flex;
      align-items: center;
      justify-content: center;
      margin-right: 12px;
    }

    .todo-priority.p0 { background: #fecaca; color: #991b1b; }
    .todo-priority.p1 { background: #fed7aa; color: #9a3412; }
    .todo-priority.p2 { background: #e0e7ff; color: #3730a3; }

    .chart-placeholder {
      background: #f1f5f9;
      border-radius: 8px;
      padding: 40px;
      text-align: center;
      color: #64748b;
    }

    .story-content {
      background: #f8fafc;
      border-radius: 8px;
      padding: 20px;
      white-space: pre-line;
    }

    .disclaimer {
      background: #fef3c7;
      border-radius: 8px;
      padding: 16px;
      font-size: 11px;
      color: #92400e;
    }

    .footer {
      margin-top: 40px;
      text-align: center;
      font-size: 10px;
      color: #94a3b8;
    }
  </style>
</head>
<body>
  <!-- 表紙 -->
  <div class="cover">
    <h1>SEO診断レポート</h1>
    <div class="url">{{ site.official_url }}</div>
    <div class="period">
      対象期間: {{ range.from }} 〜 {{ range.to }}<br>
      生成日時: {{ generated_at.strftime('%Y-%m-%d %H:%M') }}
    </div>
  </div>

  <!-- 診断サマリ -->
  <div class="section">
    <h2>診断サマリ</h2>
    <div class="summary-grid">
      <div class="summary-card">
        <div class="label">総合スコア</div>
        <div class="value">{{ analysis_result.overall_score or '-' }}</div>
      </div>
      <div class="summary-card">
        <div class="label">グレード</div>
        <div class="value">{{ analysis_result.grade or '-' }}</div>
      </div>
      <div class="summary-card">
        <div class="label">ToDo数</div>
        <div class="value">{{ todos | length }}</div>
      </div>
      <div class="summary-card">
        <div class="label">完了数</div>
        <div class="value">{{ todos | selectattr('status', 'equalto', 'done') | list | length }}</div>
      </div>
    </div>
  </div>

  <!-- ToDo一覧 -->
  <div class="section">
    <h2>ToDo一覧</h2>
    <ul class="todo-list">
      {% for todo in todos[:15] %}
      <li class="todo-item">
        <span class="todo-priority {{ todo.priority | lower }}">{{ todo.priority }}</span>
        <span>{{ todo.title }}</span>
      </li>
      {% endfor %}
    </ul>
    {% if todos | length > 15 %}
    <p style="color: #64748b; font-size: 11px;">他 {{ todos | length - 15 }}件</p>
    {% endif %}
  </div>

  <!-- Progress -->
  <div class="section">
    <h2>Progress（指標推移）</h2>
    <div class="chart-placeholder">
      ※ グラフはWebアプリケーションでご確認ください
    </div>
    {% if progress %}
    <table style="width: 100%; margin-top: 16px; border-collapse: collapse;">
      <tr style="background: #f1f5f9;">
        <th style="padding: 8px; text-align: left;">指標</th>
        <th style="padding: 8px; text-align: right;">改善前</th>
        <th style="padding: 8px; text-align: right;">改善後</th>
        <th style="padding: 8px; text-align: right;">変化</th>
      </tr>
      {% if progress.summary.serp %}
      <tr>
        <td style="padding: 8px;">平均掲載順位</td>
        <td style="padding: 8px; text-align: right;">{{ progress.summary.serp.before or '-' }}</td>
        <td style="padding: 8px; text-align: right;">{{ progress.summary.serp.after or '-' }}</td>
        <td style="padding: 8px; text-align: right;">
          {% if progress.summary.serp.before and progress.summary.serp.after %}
            {% set diff = progress.summary.serp.before - progress.summary.serp.after %}
            {% if diff > 0 %}▲ 改善{% elif diff < 0 %}▼ 低下{% else %}- {% endif %}
          {% endif %}
        </td>
      </tr>
      {% endif %}
    </table>
    {% endif %}
  </div>

  <!-- 改善ストーリー -->
  <div class="section">
    <h2>改善ストーリー</h2>
    <div class="story-content">{{ story }}</div>
  </div>

  <!-- 注意事項 -->
  <div class="section">
    <h2>注意事項</h2>
    <div class="disclaimer">
      <strong>免責事項</strong><br>
      本レポートは改善判断の参考情報です。検索順位の向上を保証するものではありません。<br>
      SEOは不確実性のある領域であり、結果には時間がかかることがあります。<br>
      データソース: Google Search Console, PageSpeed Insights, 独自クローラー
    </div>
  </div>

  <div class="footer">
    Generated by SEO Analysis Tool
  </div>
</body>
</html>
```

---

## AJ-4. Frontend UI

```tsx
// components/report/ExportPdfButton.tsx
"use client";

import { useState } from "react";
import { FileDown, Loader2 } from "lucide-react";

interface ExportPdfButtonProps {
  siteId: string;
  from: string;
  to: string;
}

export function ExportPdfButton({ siteId, from, to }: ExportPdfButtonProps) {
  const [loading, setLoading] = useState(false);

  async function handleExport() {
    setLoading(true);
    try {
      const res = await fetch(
        `/api/v1/sites/${siteId}/reports/pdf?from=${from}&to=${to}`,
        { method: "POST" }
      );

      if (res.ok) {
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `seo_report_${siteId}_${to}.pdf`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <button
      onClick={handleExport}
      disabled={loading}
      className="flex items-center gap-2 px-4 py-2 bg-accent-cyan/20 border border-accent-cyan text-accent-cyan rounded-lg hover:bg-accent-cyan/30 transition-colors disabled:opacity-50"
    >
      {loading ? (
        <Loader2 className="h-4 w-4 animate-spin" />
      ) : (
        <FileDown className="h-4 w-4" />
      )}
      <span>PDF出力</span>
    </button>
  );
}
```

---

## AJ-5. 依存関係

### Backend

```txt
# requirements.txt に追加
playwright==1.40.0
jinja2==3.1.2
```

### インストール

```bash
pip install playwright
playwright install chromium
```

---

## AJ-6. 受け入れ基準

- [ ] PDFが正常に生成される
- [ ] レイアウトが崩れない
- [ ] 日本語フォントが正しく表示される
- [ ] A4サイズで印刷できる
- [ ] 第三者に渡せるクオリティ
- [ ] 免責事項が含まれている
