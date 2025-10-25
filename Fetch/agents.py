from __future__ import annotations
from uagents import Agent, Bureau, Context, Model
from typing import Dict, List, Optional
import time
import uuid
import json
import os

# ---------- Message Schemas ----------
class FeasibilityRequest(Model):
    title: str
    summary: str
    weights: Optional[Dict[str, float]] = None  # {"cost":0.2,"ethics":0.2,"market":0.25,"tech":0.2,"timing":0.15}
    version: int = 1

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

# ---------- Config ----------
DEFAULT_WEIGHTS = {"cost":0.2, "ethics":0.2, "market":0.25, "tech":0.2, "timing":0.15}
PARAMS = ["cost", "ethics", "market", "tech", "timing"]
TIMEOUT_S = 10.0
IDEAS_PATHS = ["ideas.json", "/mnt/data/ideas.json"]  # tries local first, then the sample I provided

# ---------- Agents (stable seeds give stable agent1... addresses) ----------
orchestrator = Agent(name="orchestrator", seed="hackathon-orchestrator-seed", port=8000, endpoint=["http://127.0.0.1:8000/submit"])
cost_agent   = Agent(name="cost",         seed="hackathon-cost-seed",         port=8001, endpoint=["http://127.0.0.1:8001/submit"])
ethics_agent = Agent(name="ethics",       seed="hackathon-ethics-seed",       port=8002, endpoint=["http://127.0.0.1:8002/submit"])
market_agent = Agent(name="market",       seed="hackathon-market-seed",       port=8003, endpoint=["http://127.0.0.1:8003/submit"])
tech_agent   = Agent(name="tech",         seed="hackathon-tech-seed",         port=8004, endpoint=["http://127.0.0.1:8004/submit"])
timing_agent = Agent(name="timing",       seed="hackathon-timing-seed",       port=8005, endpoint=["http://127.0.0.1:8005/submit"])

# ---------- Orchestrator state ----------
PENDING: Dict[str, dict] = {}  # request_id -> {sender, weights, expected, received, created_at}

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
    t = text.lower()
    return any(k in t for k in IMPOSSIBLE_KWS)

def quick_score(text: str, bias: float = 0.0, clamp=(0, 100)) -> float:
    # toy heuristic: grows with description length
    n = max(len(text.split()), 1)
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
        agg = FeasibilityAggregate(request_id="invalid", overall=0.0, breakdown=[])
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
        "created_at": time.time()
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
        agg = FeasibilityAggregate(request_id=resp.request_id, overall=overall, breakdown=state["received"])
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
            agg = FeasibilityAggregate(request_id=rid, overall=overall, breakdown=recv)
            await ctx.send(st["sender"], agg)
            ctx.logger.warning(f"[orchestrator] Timed out {rid}; sent partial {overall:.1f}")
            del PENDING[rid]

# ---------- Specialists (replace internals with real logic later) ----------
@cost_agent.on_message(model=SubscoreRequest)
async def cost_handler(ctx: Context, sender: str, req: SubscoreRequest):
    if req.parameter != "cost": return
    score = 100 - quick_score(req.summary)  # cheaper -> higher score
    if contains_impossible(req.summary):
        score = max(0.0, score - 40.0)  # impossible ideas → very costly in practice
    await ctx.send(sender, SubscoreResponse(
        request_id=req.request_id, parameter="cost", score=score, confidence=0.6,
        rationale="Estimated infra & staffing for MVP; penalized for speculative prerequisites" if contains_impossible(req.summary)
                  else "Estimated infra & staffing for MVP"
    ))

@ethics_agent.on_message(model=SubscoreRequest)
async def ethics_handler(ctx: Context, sender: str, req: SubscoreRequest):
    if req.parameter != "ethics": return
    # Neutral baseline; you can add keyword penalties (e.g., surveillance) later
    score = 85.0
    await ctx.send(sender, SubscoreResponse(
        request_id=req.request_id, parameter="ethics", score=score, confidence=0.7,
        rationale="No immediate harmful externalities detected in description"
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
                  else "Clear pain point; several adjacent use cases"
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
                  else "Requires speculative physics/undeveloped materials"
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
                  else "Timeline unrealistic given scientific/industrial readiness"
    ))

# ---------- Client (reads ideas.json and sends first idea) ----------
client = Agent(name="client", seed="hackathon-client-seed", port=8006, endpoint=["http://127.0.0.1:8006/submit"])

def load_first_idea() -> Dict[str, str]:
    for p in IDEAS_PATHS:
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list) and data:
                    return {"title": data[0]["title"], "summary": data[0]["summary"]}
    # Fallback idea (if no file found)
    return {
        "title": "Teleportation-Based Global Logistics Network by 2026",
        "summary": "Quantum teleportation of macroscopic objects for logistics within 12 months; consumer booths worldwide."
    }

@client.on_event("startup")
async def kick_off(ctx: Context):
    idea = load_first_idea()
    req = FeasibilityRequest(
        title=idea["title"],
        summary=idea["summary"],
        weights={"cost":0.15,"ethics":0.2,"market":0.3,"tech":0.2,"timing":0.15},
        version=1
    )
    await ctx.send(orchestrator.address, req)
    ctx.logger.info(f"[client] Sent feasibility request to {orchestrator.address} :: {req.title}")

@client.on_message(model=FeasibilityAggregate)
async def show_result(ctx: Context, sender: str, msg: FeasibilityAggregate):
    ctx.logger.info(f"[client] Overall: {msg.overall:.1f}")
    for p in msg.breakdown:
        ctx.logger.info(f"  - {p.parameter}: {p.score:.1f} (conf {p.confidence:.2f}) :: {p.rationale}")
    # Optional: structured JSON line for easy ingestion by a UI
    try:
        breakdown = [{"parameter": b.parameter, "score": b.score, "confidence": b.confidence, "rationale": b.rationale} for b in msg.breakdown]
        print({"overall": msg.overall, "breakdown": breakdown})
    except Exception:
        pass

# ---------- Run all agents together ----------
if __name__ == "__main__":
    print("orchestrator:", orchestrator.address)
    print("cost:", cost_agent.address)
    print("ethics:", ethics_agent.address)
    print("market:", market_agent.address)
    print("tech:", tech_agent.address)
    print("timing:", timing_agent.address)
    print("client:", client.address)

    bureau = Bureau(port=8000, endpoint="http://127.0.0.1:8000/submit")
    for a in [orchestrator, cost_agent, ethics_agent, market_agent, tech_agent, timing_agent, client]:
        bureau.add(a)
    bureau.run()
