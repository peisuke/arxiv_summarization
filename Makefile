# Makefile for slack-arxiv-bot (FastAPI + Docker + Cloud Build + Cloud Run Gen2)

# .env の環境変数を読み込む
include .env
export

IMAGE = gcr.io/$(PROJECT_ID)/$(SERVICE_NAME)
CLOUD_BUILD_IMAGE=${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${SERVICE_NAME}

# 🔹 ローカル開発用
install:
	uv pip install -r pyproject.toml --system

freeze:
	uv pip freeze > requirements.txt

# 🔹 ローカル実行（M1 Mac対応）
run: freeze
	docker build --platform=linux/amd64 -t $(SERVICE_NAME) .
	docker run --rm -p 8080:8080 --env-file .env $(SERVICE_NAME)

# 🔹 Dockerイメージ作成 & GCRへPush
build: freeze
	docker build --platform=linux/amd64 -t $(IMAGE) .
	docker push $(IMAGE)

# 🔹 Cloud Runへデプロイ（M1でもOK）
deploy: build
	gcloud run deploy $(SERVICE_NAME) \
	  --image=$(IMAGE) \
	  --region=$(REGION) \
	  --platform=managed \
	  --allow-unauthenticated \
	  --set-env-vars SLACK_BOT_TOKEN=$$SLACK_BOT_TOKEN,OPENAI_API_KEY=$$OPENAI_API_KEY,SLACK_SIGNING_SECRET=$$SLACK_SIGNING_SECRET

create:
	gcloud artifacts repositories create $(REPO_NAME) \
  	--repository-format=docker \
  	--location=${REGION} \
  	--description="Arxiv Summarization Container Repository"

# 🔹 Cloud Build で一括ビルド＆デプロイ
submit:
	gcloud builds submit . \
		--config cloudbuild.yaml \
		--substitutions=_SERVICE_NAME=$(SERVICE_NAME),_REGION=$(REGION),_IMAGE=$(CLOUD_BUILD_IMAGE)

# 🔹 handler.py のローカルテスト
test-local:
	python test_main_local.py

# 🔹 pytest でのテスト実行
test:
	pytest -v

# 🔹 テスト用の依存関係をインストール
install-test:
	uv pip install -e ".[test]" --system