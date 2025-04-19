# Slack × arXiv 要約ボット

SlackでarXivの論文URLをメンションすると、OpenAI APIを使って論文の「課題・貢献・結論」を日本語で要約して返信するボットです。

---

## 出力例

<img width="1027" alt="image" src="https://github.com/user-attachments/assets/73fc527b-f816-4fcf-8861-c9bb37233525" />

## ディレクトリ構成

```
.
├── main.py              # FastAPI アプリ (Slack webhook)
├── handler.py           # arXiv 取得 & 要約ロジック
├── test_main_local.py   # ローカルテスト用スクリプト
├── pyproject.toml       # uv 用依存管理
├── requirements.txt     # Cloud 用依存定義（make freeze で生成）
├── Dockerfile           # Cloud Run 向けビルド
├── .dockerignore
├── Makefile             # ビルド/デプロイ用コマンド
└── cloudbuild.yaml      # Cloud Build 用設定
```

---

## 必要な環境変数

`.env` または GitHub Secrets に設定します：

```env
PROJECT_ID=your-gcp-project-id
REGION=asia-northeast1
SERVICE_NAME=slack-arxiv-bot
SLACK_BOT_TOKEN=xoxb-xxx
OPENAI_API_KEY=sk-xxx
SLACK_SIGNING_SECRET=xxx
```

---

## ローカル開発

```bash
make install          # 依存インストール（uv）
make test-local       # handler.py の直接テスト
make freeze           # requirements.txtの生成
make run              # Docker 実行（.env 読み込み）
```

---

## デプロイ方法

### Cloud Run へ手動デプロイ（ローカルから）
```bash
make freeze
make deploy
```

### Cloud Build による自動ビルド・デプロイ
```bash
make submit
```

---

## Slack App 設定手順

1. Slack API → アプリ作成 → Bot Token & Signing Secret 取得
2. スコープ： `app_mentions:read`, `chat:write`
3. イベント購読： `app_mention`
4. イベントURL： Cloud Run の URL（例：https://xxx.a.run.app/）

---

## 📄 ライセンス
MIT
