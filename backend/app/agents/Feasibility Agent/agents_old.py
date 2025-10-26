# agents.py
from __future__ import annotations

import os
import uuid
import time
import threading
import asyncio
from queue import Queue, Empty
from typing import Dict, List, Optional

from flask import Flask, request, jsonify, g
from werkzeug.middleware.proxy_fix import ProxyFix

from uagents import Agent, Bureau, Context, Model

# =========================
# Message Schemas (originals + corr_id)
# =========================
class FeasibilityRequest(Model):
    title: str
    summary: str
    weights: Optional[Dict[str, float]] = None  # we will pass None to use defaults
    version: int = 1
    corr_id: Optional[str] = None  # for HTTP<->agent correlation

class SubscoreRequest(Model):
    request_id: str
    title: str
    summary: str
    parameter: str  # "cost" | "ethics" | "market" | "tech" | "timing"
    version: int = 1

class SubscoreResponse(Model):
    request_id: str
    parameter: str
    score: float              # 0..100
    confidence: float         # 0..1
    rationale: str
    version: int = 1

class FeasibilityAggregate(Model):
    request_id: str
    overall: float            # weighted 0..100
    breakdown: List[SubscoreResponse]
    version: int = 1
    corr_id: Optional[str] = None

# =========================
# Config
# =========================
DEFAULT_WEIGHTS = {"cost": 0.2, "ethics": 0.2, "market": 0.25, "tech": 0.2, "timing": 0.15}
PARAMS = ["cost", "ethics", "market", "tech", "timing"]
TIMEOUT_S = float(os.getenv("AGENT_TIMEOUT_S", "10.0"))  # configurable agent timeout
FEASIBILITY_THRESHOLD = float(os.getenv("FEASIBILITY_THRESHOLD", "75.0"))
ALLOW_ORIGINS = os.getenv("ALLOW_ORIGINS", "*")
MAX_BODY_BYTES = int(os.getenv("MAX_BODY_BYTES", "65536"))

# =========================
# Agents (in-process)
# =========================
orchestrator = Agent(name="orchestrator", seed="hackathon-orchestrator-seed")
cost_agent   = Agent(name="cost",         seed="hackathon-cost-seed")
ethics_agent = Agent(name="ethics",       seed="hackathon-ethics-seed")
market_agent = Agent(name="market",       seed="hackathon-market-seed")
tech_agent   = Agent(name="tech",         seed="hackathon-tech-seed")
timing_agent = Agent(name="timing",       seed="hackathon-timing-seed")
gateway      = Agent(name="gateway",      seed="hackathon-gateway-seed")

# ---------- Orchestrator state ----------
PENDING: Dict[str, dict] = {}  # request_id -> {sender, weights, expected, received, created_at, corr_id}

DISPATCH = {
    "cost":   lambda: cost_agent.address,
    "ethics": lambda: ethics_agent.address,
    "market": lambda: market_agent.address,
    "tech":   lambda: tech_agent.address,
    "timing": lambda: timing_agent.address,
}

# ---------- Helpers ----------
IMPOSSIBLE_KWS = {
    "teleportation", "warp", "ftl", "faster-than-light", "time travel", "antigravity",
    "room-temperature superconductor", "ambient-pressure superconductor",
    "cold fusion", "perpetual motion", "instant terraforming", "space elevator"
}

def contains_impossible(text: str) -> bool:
    t = (text or "").lower()
    return any(k in t for k in IMPOSSIBLE_KWS)

def quick_score(text: str, bias: float = 0.0, clamp=(0, 100)) -> float:
    # toy heuristic: grows with description length
    n = max(len((text or "").split()), 1)
    base = min(100, 20 + (n ** 0.5) * 10)
    val = base + bias
    return max(clamp[0], min(clamp[1], val))

def normalize_weights(w: Dict[str, float]) -> Dict[str, float]:
    w = {p: float(w.get(p, 0.0)) for p in PARAMS}
    s = sum(w.values())
    if s <= 0:
        w = DEFAULT_WEIGHTS.copy()
        s = sum(w.values())
    return {p: w[p] / s for p in PARAMS}

# ---------- Orchestrator: receive request & fan out ----------
@orchestrator.on_message(model=FeasibilityRequest)
async def on_feasibility_request(ctx: Context, sender: str, msg: FeasibilityRequest):
    title = (msg.title or "").strip()
    summary = (msg.summary or "").strip()
    if not title or not summary:
        agg = FeasibilityAggregate(request_id="invalid", overall=0.0, breakdown=[], version=1, corr_id=msg.corr_id)
        await ctx.send(sender, agg)
        ctx.logger.warning("[orchestrator] Rejected empty title/summary")
        return

    rid = str(uuid.uuid4())
    weights = normalize_weights(msg.weights or DEFAULT_WEIGHTS)

    PENDING[rid] = {
        "sender": sender,
        "weights": weights,
        "expected": set(PARAMS),
        "received": [],
        "created_at": time.time(),
        "corr_id": msg.corr_id,
    }

    for p in PARAMS:
        await ctx.send(DISPATCH[p](), SubscoreRequest(
            request_id=rid, title=title, summary=summary, parameter=p, version=msg.version
        ))
    ctx.logger.info(f"[orchestrator] Dispatched {rid} to specialists for '{title}'")

# ---------- Orchestrator: collect subscores, aggregate, reply ----------
@orchestrator.on_message(model=SubscoreResponse)
async def on_subscore(ctx: Context, sender: str, resp: SubscoreResponse):
    state = PENDING.get(resp.request_id)
    if not state:
        return
    if resp.parameter in state["expected"]:
        state["expected"].remove(resp.parameter)
        state["received"].append(resp)
        ctx.logger.info(f"[orchestrator] Collected {resp.parameter} for {resp.request_id}")

    if not state["expected"]:  # all in
        w = state["weights"]
        overall = sum(r.score * w.get(r.parameter, 0.0) for r in state["received"])
        agg = FeasibilityAggregate(
            request_id=resp.request_id,
            overall=overall,
            breakdown=state["received"],
            version=1,
            corr_id=state.get("corr_id"),
        )
        await ctx.send(state["sender"], agg)
        ctx.logger.info(f"[orchestrator] Sent aggregate score {overall:.1f} for {resp.request_id}")
        del PENDING[resp.request_id]

# ---------- Orchestrator: timeout sweep (partial aggregate if needed) ----------
@orchestrator.on_interval(period=2.0)
async def timeout_sweeper(ctx: Context):
    now = time.time()
    for rid, st in list(PENDING.items()):
        if now - st["created_at"] > TIMEOUT_S:
            w = st["weights"]
            recv = st["received"]
            overall = sum(r.score * w.get(r.parameter, 0.0) for r in recv) if recv else 0.0
            agg = FeasibilityAggregate(
                request_id=rid,
                overall=overall,
                breakdown=recv,
                version=1,
                corr_id=st.get("corr_id"),
            )
            await ctx.send(st["sender"], agg)
            ctx.logger.warning(f"[orchestrator] Timed out {rid}; sent partial {overall:.1f}")
            del PENDING[rid]

# ---------- Specialists (exact scoring as your code) ----------
@cost_agent.on_message(model=SubscoreRequest)
async def cost_handler(ctx: Context, sender: str, req: SubscoreRequest):
    if req.parameter != "cost": return
    score = 100 - quick_score(req.summary)  # cheaper -> higher score
    if contains_impossible(req.summary):
        score = max(0.0, score - 40.0)  # impossible ideas → very costly
    await ctx.send(sender, SubscoreResponse(
        request_id=req.request_id, parameter="cost", score=score, confidence=0.6,
        rationale="Estimated infra & staffing for MVP; penalized for speculative prerequisites" if contains_impossible(req.summary)
                  else "Estimated infra & staffing for MVP", version=1
    ))

@ethics_agent.on_message(model=SubscoreRequest)
async def ethics_handler(ctx: Context, sender: str, req: SubscoreRequest):
    if req.parameter != "ethics": return
    score = 85.0
    await ctx.send(sender, SubscoreResponse(
        request_id=req.request_id, parameter="ethics", score=score, confidence=0.7,
        rationale="No immediate harmful externalities detected in description", version=1
    ))

@market_agent.on_message(model=SubscoreRequest)
async def market_handler(ctx: Context, sender: str, req: SubscoreRequest):
    if req.parameter != "market": return
    score = quick_score(req.summary, bias=10)
    if contains_impossible(req.summary):
        score = max(0.0, score - 30.0)  # market viability drops if product can't exist soon
    await ctx.send(sender, SubscoreResponse(
        request_id=req.request_id, parameter="market", score=score, confidence=0.55,
        rationale="Clear pain point; adjusted for deliverability constraints" if contains_impossible(req.summary)
                  else "Clear pain point; several adjacent use cases", version=1
    ))

@tech_agent.on_message(model=SubscoreRequest)
async def tech_handler(ctx: Context, sender: str, req: SubscoreRequest):
    if req.parameter != "tech": return
    score = quick_score(req.summary, bias=5)
    if contains_impossible(req.summary):
        score = 5.0  # technology infeasible today
    await ctx.send(sender, SubscoreResponse(
        request_id=req.request_id, parameter="tech", score=score, confidence=0.6,
        rationale="Feasible with existing OSS/APIs" if not contains_impossible(req.summary)
                  else "Requires speculative physics/undeveloped materials", version=1
    ))

@timing_agent.on_message(model=SubscoreRequest)
async def timing_handler(ctx: Context, sender: str, req: SubscoreRequest):
    if req.parameter != "timing": return
    score = 75.0
    if contains_impossible(req.summary):
        score = 10.0  # not viable in the stated timeline
    await ctx.send(sender, SubscoreResponse(
        request_id=req.request_id, parameter="timing", score=score, confidence=0.5,
        rationale="Platform & trend alignment looks favorable" if not contains_impossible(req.summary)
                  else "Timeline unrealistic given scientific/industrial readiness", version=1
    ))

# =========================
# Gateway (bridge) + readiness
# =========================
requests_q: "Queue[tuple[str,str,str]]" = Queue()  # (corr_id, title, summary)
RESULTS: Dict[str, dict] = {}  # corr_id -> {"event": threading.Event, "response": dict}
AGENTS_READY = threading.Event()

@gateway.on_event("startup")
async def ready_flag(_: Context):
    AGENTS_READY.set()

@gateway.on_interval(period=0.05)
async def pump_outgoing(ctx: Context):
    try:
        corr_id, title, summary = requests_q.get_nowait()
    except Empty:
        return
    await ctx.send(orchestrator.address, FeasibilityRequest(
        title=title,
        summary=summary,
        weights=None,   # ALWAYS default weights
        version=1,
        corr_id=corr_id
    ))
    ctx.logger.info(f"[gateway] Sent FeasibilityRequest corr_id={corr_id}")

@gateway.on_message(model=FeasibilityAggregate)
async def on_result(ctx: Context, sender: str, msg: FeasibilityAggregate):
    corr_id = msg.corr_id or "unknown"
    overall_raw = msg.overall  # use raw for pass/fail
    overall_display = float(f"{overall_raw:.1f}")  # round for display only

    breakdown = [
        {
            "parameter": b.parameter,
            "score": float(f"{b.score:.1f}"),
            "confidence": b.confidence,
            "rationale": b.rationale,
            "version": b.version,  # include version per subscore
        } for b in msg.breakdown
    ]
    payload = {
        "request_id": corr_id,
        "version": msg.version,
        "aggregate": {
            "overall": overall_display,
            "threshold": FEASIBILITY_THRESHOLD,
            "passes_threshold": overall_raw >= FEASIBILITY_THRESHOLD
        },
        "breakdown": breakdown
    }
    entry = RESULTS.get(corr_id)
    if entry:
        entry["response"] = payload
        entry["event"].set()
        ctx.logger.info(f"[gateway] Completed corr_id={corr_id}")
    else:
        ctx.logger.warning(f"[gateway] Received unknown corr_id={corr_id}")

# =========================
# Run Bureau in background (create event loop in thread for 3.11+/3.13)
# =========================
def run_bureau():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    bureau = Bureau()  # in-process routing
    for a in [orchestrator, cost_agent, ethics_agent, market_agent, tech_agent, timing_agent, gateway]:
        bureau.add(a)
    bureau.run()

bureau_thread = threading.Thread(target=run_bureau, daemon=True, name="uAgents-Bureau")
bureau_thread.start()

# =========================
# Flask API
# =========================
app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

@app.after_request
def apply_cors(resp):
    resp.headers["Access-Control-Allow-Origin"] = ALLOW_ORIGINS
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Request-ID"
    resp.headers["Access-Control-Allow-Methods"] = "POST, GET, OPTIONS"
    return resp

@app.before_request
def add_request_id():
    g.request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "agents_ready": AGENTS_READY.is_set(),
        "version": 1
    }), 200

@app.route("/feasibility", methods=["POST", "OPTIONS"])
def feasibility_http():
    if request.method == "OPTIONS":
        return ("", 204)

    if not AGENTS_READY.is_set():
        return jsonify({"error": "Agent runtime not ready. Try again in a moment."}), 503

    if request.content_length and request.content_length > MAX_BODY_BYTES:
        return jsonify({"error": "Payload too large", "max_bytes": MAX_BODY_BYTES}), 413

    if not request.is_json:
        return jsonify({"error": "Expected application/json body"}), 400

    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    summary = (data.get("summary") or "").strip()

    if not title or not summary:
        return jsonify({
            "error": "Both 'title' and 'summary' are required.",
            "request_id": g.request_id
        }), 400

    corr_id = g.request_id
    RESULTS[corr_id] = {"event": threading.Event(), "response": None}

    requests_q.put((corr_id, title, summary))

    http_timeout = TIMEOUT_S + 3.0  # wait a bit longer than orchestrator
    done = RESULTS[corr_id]["event"].wait(timeout=http_timeout)
    slot = RESULTS.pop(corr_id, None)

    if not done or not slot or not slot["response"]:
        return jsonify({
            "request_id": corr_id,
            "error": "Timed out waiting for agent result",
            "timeout_seconds": http_timeout
        }), 504

    resp = slot["response"]
    resp["input"] = {
        "title": title,
        "summary": summary,
        "weights": DEFAULT_WEIGHTS,
        "weights_source": "default"
    }
    return jsonify(resp), 200

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5010"))  # default 5010
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    print("Starting Flask on port", port)
    app.run(host="0.0.0.0", port=port, debug=debug)
