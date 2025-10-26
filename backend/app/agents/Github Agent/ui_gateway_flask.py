# ui_gateway_flask.py
from __future__ import annotations
from uagents import Agent, Context, Model
from typing import Dict, Any, Optional
import os, uuid, threading
from queue import Queue, Empty

from flask import Flask, request, jsonify

# ----- Config -----
PUBLISHER_CLIENT_ADDR = os.getenv("PUBLISHER_CLIENT_ADDR", "").strip()
if not PUBLISHER_CLIENT_ADDR:
    print("WARNING: set PUBLISHER_CLIENT_ADDR to your publisher_client address (agent1...)")

# ----- Models (must match publisher_client_agent.py) -----
class PushDoc(Model):
    payload: Dict[str, Any]
    visibility: str = "private"
    request_id: str = ""
    callback_address: Optional[str] = None
    gh_owner: Optional[str] = None
    gh_token: Optional[str] = None

class PublishOutcome(Model):
    request_id: str
    success: bool
    repo_url: Optional[str] = None
    error: Optional[str] = None

# ----- State -----
SEND_QUEUE: "Queue[Dict[str, Any]]" = Queue()
RESULTS: Dict[str, Dict[str, Any]] = {}   # request_id -> {"status": "...", ...}

# ----- Flask app -----
app = Flask(__name__)

@app.post("/push")
def push_handler():
    if not PUBLISHER_CLIENT_ADDR:
        return jsonify({"error": "PUBLISHER_CLIENT_ADDR not configured"}), 500
    data = request.get_json(silent=True) or {}

    payload = data.get("payload")
    visibility = data.get("visibility", "private")
    creds = data.get("credentials") or {}
    gh_owner = (creds.get("owner") or "").strip() if isinstance(creds, dict) else ""
    gh_token = (creds.get("token") or "").strip() if isinstance(creds, dict) else ""

    if not isinstance(payload, dict):
        return jsonify({"error": "payload must be a JSON object"}), 400

    rid = str(uuid.uuid4())
    RESULTS[rid] = {"status": "pending"}

    SEND_QUEUE.put({
        "request_id": rid,
        "visibility": visibility,
        "payload": payload,
        "gh_owner": gh_owner or None,
        "gh_token": gh_token or None,
    })
    return jsonify({"accepted": True, "request_id": rid})

@app.get("/result/<rid>")
def result_handler(rid: str):
    data = RESULTS.get(rid)
    if not data:
        return jsonify({"error": "unknown request_id"}), 404
    return jsonify(data)

# ----- Bridge agent (forward to publisher client, receive outcome) -----
bridge = Agent(
    name="ui-gateway",
    seed="hackathon-ui-gateway-seed",
    port=8091,
    endpoint=["http://127.0.0.1:8091/submit"],
)

@bridge.on_event("startup")
async def announce(ctx: Context):
    ctx.logger.info(f"[ui-gateway] Address: {bridge.address}")

@bridge.on_interval(period=0.1)
async def pump(ctx: Context):
    try:
        while True:
            item = SEND_QUEUE.get_nowait()
            rid = item["request_id"]
            msg = PushDoc(
                payload=item["payload"],
                visibility=item["visibility"],
                request_id=rid,
                callback_address=bridge.address,
                gh_owner=item.get("gh_owner"),
                gh_token=item.get("gh_token"),
            )
            # DO NOT log tokens
            await ctx.send(PUBLISHER_CLIENT_ADDR, msg)
            ctx.logger.info(f"[ui-gateway] → Forwarded PushDoc ({rid}) to {PUBLISHER_CLIENT_ADDR}")
    except Empty:
        pass

@bridge.on_message(PublishOutcome)
async def on_outcome(ctx: Context, sender: str, msg: PublishOutcome):
    RESULTS[msg.request_id] = {
        "status": "done",
        "success": msg.success,
        "repo_url": msg.repo_url,
        "error": msg.error,
    }
    ctx.logger.info(f"[ui-gateway] ← Outcome for {msg.request_id}: success={msg.success}")

def run_flask():
    app.run(host="0.0.0.0", port=8090, debug=False, use_reloader=False, threaded=True)

if __name__ == "__main__":
    t = threading.Thread(target=run_flask, daemon=True)
    t.start()
    print("ui-gateway:", bridge.address)
    bridge.run()
