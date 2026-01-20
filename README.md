# SEO Analysis Tool

SEO診断アプリケーション - 公式ホームページと競合サイトを比較分析し、改善点を提示するツール

## 概要

このツールは、公式ホームページのSEO状況を競合サイトと比較分析し、優先度付きの改善タスク（ToDo）とAIレポートを生成します。

### 主な機能

- **HTMLコンテンツ分析**: タイトル、メタディスクリプション、見出し構造、内部/外部リンク、画像alt属性
- **構造化データ分析**: JSON-LD/schema.org の検出と評価
- **PageSpeed Insights連携**: Core Web Vitals (LCP, INP, CLS) の取得と評価
- **Google Search Console連携**: 検索クエリ、CTR、掲載順位の分析
- **競合比較**: 公式 vs 競合のコンテンツ差分を可視化
- **ルールベース診断**: スコアリング、グレード判定、主要因特定
- **AIレポート生成**: GPT-4o/Claude による改善提案レポート

## アーキテクチャ

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│    Frontend     │────▶│     Backend     │────▶│   PostgreSQL    │
│   Next.js 14    │     │    FastAPI      │     │                 │
│   Tailwind CSS  │     │    Python 3.11  │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                              │
                              ▼
                     ┌─────────────────┐
                     │  External APIs  │
                     │  - PageSpeed    │
                     │  - Search Console│
                     │  - OpenAI/Claude│
                     └─────────────────┘
```

## セットアップ

### 前提条件

- Docker & Docker Compose
- または Node.js 20+ と Python 3.11+

### Docker を使用する場合

```bash
# 1. リポジトリをクローン
git clone https://github.com/skyblueearthjapan/SEO-analysis-tool.git
cd SEO-analysis-tool

# 2. 環境変数ファイルを作成
cp .env.example .env
# .env を編集して API キーを設定

# 3. Docker Compose で起動
docker-compose up -d

# フロントエンド: http://localhost:3000
# バックエンド: http://localhost:8000
# API ドキュメント: http://localhost:8000/docs
```

### ローカル開発環境

#### バックエンド

```bash
cd backend

# 仮想環境を作成
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 依存関係をインストール
pip install -r requirements.txt

# データベースを起動 (Docker)
docker run -d --name seo-db \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=seo_analysis \
  -p 5432:5432 \
  postgres:15-alpine

# サーバーを起動
uvicorn app.main:app --reload
```

#### フロントエンド

```bash
cd frontend

# 依存関係をインストール
npm install

# 環境変数を設定
cp .env.local.example .env.local

# 開発サーバーを起動
npm run dev
```

## 環境変数

### バックエンド (.env)

| 変数名 | 説明 | 必須 |
|--------|------|------|
| `DATABASE_URL` | PostgreSQL接続URL | ○ |
| `PAGESPEED_API_KEY` | Google PageSpeed Insights API キー | △ |
| `OPENAI_API_KEY` | OpenAI API キー | △ |
| `ANTHROPIC_API_KEY` | Anthropic API キー | △ |
| `GSC_CREDENTIALS_PATH` | Search Console認証ファイルパス | △ |

### フロントエンド (.env.local)

| 変数名 | 説明 | デフォルト |
|--------|------|------------|
| `NEXT_PUBLIC_API_BASE_URL` | バックエンドAPIのURL | `http://localhost:8000/api/v1` |

## API ドキュメント

バックエンド起動後、以下のURLでSwagger UIにアクセスできます:

- http://localhost:8000/docs (Swagger UI)
- http://localhost:8000/redoc (ReDoc)

### 主要エンドポイント

- `GET /api/v1/sites` - サイト一覧
- `POST /api/v1/sites` - サイト作成
- `GET /api/v1/sites/{site_id}/pages` - ページ一覧
- `POST /api/v1/sites/{site_id}/pages` - ページ登録
- `POST /api/v1/sites/{site_id}/analysis-jobs` - 解析ジョブ作成
- `GET /api/v1/sites/{site_id}/analysis-results` - 解析結果一覧

## テスト

```bash
cd backend

# テストを実行
pytest

# カバレッジ付きで実行
pytest --cov=app --cov-report=html
```

## プロジェクト構成

```
.
├── backend/
│   ├── app/
│   │   ├── config.py           # 設定管理
│   │   ├── database.py         # DB接続
│   │   ├── main.py             # FastAPIエントリポイント
│   │   ├── models/
│   │   │   ├── db_models.py    # SQLAlchemy ORM
│   │   │   └── schemas.py      # Pydantic スキーマ
│   │   ├── routers/            # APIエンドポイント
│   │   └── services/           # ビジネスロジック
│   │       ├── analysis_pipeline.py
│   │       ├── fetcher.py
│   │       ├── parser_html.py
│   │       ├── parser_schema.py
│   │       ├── pagespeed_client.py
│   │       ├── gsc_client.py
│   │       ├── intent_classifier.py
│   │       ├── comparator.py
│   │       ├── rule_engine.py
│   │       └── ai_reporter.py
│   ├── config/
│   │   └── thresholds.yml      # 閾値設定
│   └── tests/
├── frontend/
│   ├── app/                    # Next.js App Router
│   ├── components/             # React コンポーネント
│   ├── lib/
│   │   ├── api/               # API クライアント
│   │   └── utils.ts           # ユーティリティ
│   └── styles/
│       └── globals.css        # グローバルCSS
├── docs/
│   └── specs/
│       └── spec.md            # 詳細設計書
├── docker-compose.yml
└── README.md
```

## ライセンス

MIT License
