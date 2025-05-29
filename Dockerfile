# arxiv_slack_bot/Dockerfile
FROM python:3.10-slim

# 環境変数設定
ENV PORT=8080
WORKDIR /app

# poetry/uv等使わず pip で依存インストール（requirements.txt使用）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリコードをコピー
COPY src/ ./src/
COPY pyproject.toml .

# パッケージを開発モードでインストール
RUN pip install -e .

# FastAPIのサーバ起動（Cloud RunがPORT環境変数を提供）
CMD ["uvicorn", "src.arxiv_slack_bot.main:app", "--host=0.0.0.0", "--port=8080"]
