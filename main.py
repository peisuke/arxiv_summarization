# arxiv_slack_bot/main.py
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from handler import handle_arxiv_request
import os
import hashlib
import hmac
import time
import json
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

app = FastAPI()
SLACK_SIGNING_SECRET = os.environ["SLACK_SIGNING_SECRET"]
SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
client = WebClient(token=SLACK_BOT_TOKEN)

# リトライ検出用のイベントID記録セット（メモリ内）
recent_event_ids = set()


def verify_slack_request(headers, body):
    timestamp = headers.get("x-slack-request-timestamp")
    signature = headers.get("x-slack-signature")

    if not timestamp or not signature:
        return False

    if abs(time.time() - int(timestamp)) > 60 * 5:
        return False

    sig_basestring = f"v0:{timestamp}:{body}".encode("utf-8")
    computed_signature = "v0=" + hmac.new(
        SLACK_SIGNING_SECRET.encode("utf-8"),
        sig_basestring,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(computed_signature, signature)


@app.post("/")
async def slack_webhook(request: Request):
    raw_body = await request.body()
    headers = request.headers

    if not verify_slack_request(headers, raw_body.decode("utf-8")):
        return JSONResponse(content={"error": "unauthorized"}, status_code=401)

    slack_event = await request.json()

    # ✅ 正しく challenge 応答を返す
    if slack_event.get("type") == "url_verification":
        return JSONResponse(content={"challenge": slack_event["challenge"]})

    # ✅ リトライイベントの重複防止（event_id を使う）
    event_id = slack_event.get("event_id")
    if event_id in recent_event_ids:
        return {"message": "Duplicate event ignored"}
    if event_id:
        recent_event_ids.add(event_id)

    if "event" not in slack_event or slack_event["event"].get("type") != "app_mention":
        return {"message": "No action taken"}

    channel = slack_event["event"]["channel"]
    text = slack_event["event"].get("text", "")
    thread_ts = slack_event["event"].get("ts")

    response_text = handle_arxiv_request(text)

    try:
        client.chat_postMessage(
            channel=channel,
            text=response_text,
            thread_ts=thread_ts,
            reply_broadcast=True
        )
    except SlackApiError as e:
        print(f"Slack API error: {e}")

    return {"message": "Processed"}
