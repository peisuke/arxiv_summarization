from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from .handler import handle_arxiv_request
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
    #print(headers)

    if not verify_slack_request(headers, raw_body.decode("utf-8")):
        return JSONResponse(content={"error": "unauthorized"}, status_code=401)

    x_slack_retry_num = headers.get("x-slack-retry-num")
    if x_slack_retry_num is not None:
        print(f"Retry request: {x_slack_retry_num}")
        return JSONResponse(content={"message": "Retry ignored"}, status_code=200)

    slack_event = await request.json()

    # ✅ 正しく challenge 応答を返す
    if slack_event.get("type") == "url_verification":
        return JSONResponse(content={"challenge": slack_event["challenge"]})

    if "event" not in slack_event or slack_event["event"].get("type") != "app_mention":
        return {"message": "No action taken"}

    channel = slack_event["event"]["channel"]
    text = slack_event["event"].get("text", "")
    thread_ts = slack_event["event"].get("ts")
    print(channel, text, thread_ts)

    first_post, second_post = handle_arxiv_request(text)

    try:
        # 1つ目の投稿: タイトル・課題・貢献・結論
        client.chat_postMessage(
            channel=channel,
            text=first_post,
            thread_ts=thread_ts,
            reply_broadcast=True
        )
        
        # 2つ目の投稿: 概要（second_postがNoneでない場合のみ）
        if second_post:
            client.chat_postMessage(
                channel=channel,
                text=second_post,
                thread_ts=thread_ts,
                reply_broadcast=True
            )
    except SlackApiError as e:
        print(f"Slack API error: {e}")

    return {"message": "Processed"}