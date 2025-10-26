# merged_github_publisher.py
"""
Merged GitHub Publisher System
Combines github_agent, publisher_client_agent, and ui_gateway_flask into a single file.
All three agents run in the same process with different ports.
"""
from __future__ import annotations
from uagents import Agent, Context, Model
from typing import List, Optional, Dict, Any
import os, base64, aiohttp, re, unicodedata, uuid, threading
from queue import Queue, Empty
from flask import Flask, request, jsonify

# ============================================================================
# SHARED MODELS
# ============================================================================

class GithubFile(Model):
    path: str
    content: str

class GithubPushRequest(Model):
    repo_name: str
    visibility: str              # "public" | "private"
    readme_md: str
    files: List[GithubFile]
    branch: str = "main"
    commit_message: str = "chore: initial commit from feasibility pipeline"
    owner: Optional[str] = None
    token: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class GithubPushResult(Model):
    success: bool
    repo_url: Optional[str] = None
    error: Optional[str] = None

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

# ============================================================================
# CONFIGURATION
# ============================================================================

ENV_GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "").strip()
ENV_GITHUB_USERNAME = os.getenv("GITHUB_USERNAME", "").strip()

if not ENV_GITHUB_USERNAME:
    print("WARNING: GITHUB_USERNAME is not set; will require 'owner' in request if not provided.")

# ============================================================================
# GITHUB AGENT (Port 8010)
# ============================================================================

github_agent = Agent(
    name="github-agent",
    seed="hackathon-github-agent-seed",
    port=8010,
    endpoint=["http://127.0.0.1:8010/submit"],
)

def _headers(token: str):
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
    }

def safe_desc(text: str, limit: int = 140) -> str:
    if not text:
        return ""
    text = text.splitlines()[0]
    text = re.sub(r'[\r\n\t]+', ' ', text)
    text = ''.join(ch for ch in text if unicodedata.category(ch)[0] != 'C')
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:limit]

async def gh_create_repo(session: aiohttp.ClientSession, owner: str, name: str, description: str, private: bool):
    if not owner:
        raise RuntimeError("Missing owner")
    payload = {
        "name": name,
        "description": description[:200] if description else "",
        "private": private,
        "auto_init": True,
    }
    if owner.lower() == (ENV_GITHUB_USERNAME or owner).lower():
        url = "https://api.github.com/user/repos"
    else:
        url = f"https://api.github.com/orgs/{owner}/repos"
    async with session.post(url, json=payload) as r:
        data = await r.json()
        if r.status == 201:
            return data
        if r.status == 422 and isinstance(data, dict) and "name already exists on this account" in str(data):
            return None
        raise RuntimeError(f"Create repo failed [{r.status}]: {data}")

async def gh_get_file_sha(session: aiohttp.ClientSession, owner: str, repo: str, path: str, ref: str) -> Optional[str]:
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    params = {"ref": ref}
    async with session.get(url, params=params) as r:
        if r.status == 200:
            data = await r.json()
            return data.get("sha")
        return None

async def gh_put_file(session: aiohttp.ClientSession, owner: str, repo: str, path: str, content: str, message: str, branch: str):
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    sha = await gh_get_file_sha(session, owner, repo, path, branch)
    payload = {
        "message": message,
        "content": base64.b64encode(content.encode("utf-8")).decode("utf-8"),
        "branch": branch,
    }
    if sha:
        payload["sha"] = sha
    async with session.put(url, json=payload) as r:
        data = await r.json()
        if r.status not in (200, 201):
            raise RuntimeError(f"Put file failed [{r.status}]: {data}")

@github_agent.on_message(GithubPushRequest)
async def on_push(ctx: Context, sender: str, req: GithubPushRequest):
    owner = (req.owner or ENV_GITHUB_USERNAME).strip()
    token = (req.token or ENV_GITHUB_TOKEN).strip()
    if not owner or not token:
        await ctx.send(sender, GithubPushResult(success=False, error="Missing GitHub owner or token"))
        return

    private = req.visibility != "public"
    repo = req.repo_name
    branch = req.branch or "main"

    try:
        async with aiohttp.ClientSession(headers=_headers(token)) as session:
            desc_source = (req.metadata or {}).get("approach") or (req.readme_md or repo)
            description = safe_desc(desc_source)
            await gh_create_repo(session, owner, repo, description, private)

            await gh_put_file(session, owner, repo, "README.md", req.readme_md, req.commit_message, branch)
            for f in req.files:
                await gh_put_file(session, owner, repo, f.path, f.content, req.commit_message, branch)

        repo_url = f"https://github.com/{owner}/{repo}"
        await ctx.send(sender, GithubPushResult(success=True, repo_url=repo_url))
        ctx.logger.info(f"[github-agent] ✅ Pushed → {repo_url}")

    except Exception as e:
        msg = str(e)
        await ctx.send(sender, GithubPushResult(success=False, error=msg))
        ctx.logger.error(f"[github-agent] ❌ Push failed: {msg}")

@github_agent.on_event("startup")
async def github_startup(ctx: Context):
    ctx.logger.info(f"[github-agent] Address: {github_agent.address}")

# ============================================================================
# PUBLISHER CLIENT AGENT (Port 8008)
# ============================================================================

publisher_client = Agent(
    name="publisher-client",
    seed="hackathon-publisher-client-seed",
    port=8008,
    endpoint=["http://127.0.0.1:8008/submit"],
)

PENDING: Dict[str, Dict[str, Any]] = {}

def _slugify(title: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9-_]+", "-", (title or "project").strip()).strip("-")
    return s[:90] or "project"

def build_push_request_from_doc(doc: Dict[str, Any], *, visibility: str = "private") -> GithubPushRequest:
    ideas = doc.get("ideas") or []
    idea = ideas[0] if ideas else {}
    title = idea.get("title") or "project"
    readme_md = idea.get("documentation") or f"# {title}\n\n(Generated README)\n"

    files: List[GithubFile] = []
    for cs in (idea.get("code_samples") or []):
        fn = cs.get("filename") or "main.py"
        files.append(GithubFile(path=fn, content=cs.get("content") or ""))

    if not any(f.path == ".gitignore" for f in files):
        files.append(GithubFile(path=".gitignore", content="__pycache__/\n.env\n.venv/\n*.pyc\n"))
    if not any(f.path.lower().startswith("license") for f in files):
        files.append(GithubFile(path="LICENSE", content="MIT License\n\n<add your name/year>"))

    return GithubPushRequest(
        repo_name=_slugify(title),
        visibility=visibility,
        readme_md=readme_md,
        files=files,
        metadata={
            "coding_related": doc.get("coding_related"),
            "classification": doc.get("classification"),
            "research_titles": doc.get("research_titles"),
            "stack": idea.get("stack"),
            "approach": idea.get("approach"),
        },
    )

@publisher_client.on_event("startup")
async def publisher_startup(ctx: Context):
    ctx.logger.info(f"[publisher-client] Address: {publisher_client.address}")

@publisher_client.on_message(PushDoc)
async def on_pushdoc(ctx: Context, sender: str, msg: PushDoc):
    req = build_push_request_from_doc(msg.payload, visibility=msg.visibility)

    if msg.gh_owner:
        req.owner = msg.gh_owner.strip()
    if msg.gh_token:
        req.token = msg.gh_token.strip()

    rid = msg.request_id or str(uuid.uuid4())
    PENDING[req.repo_name] = {"cb": msg.callback_address, "rid": rid}

    await ctx.send(github_agent.address, req)
    ctx.logger.info(f"[publisher-client] Sent GithubPushRequest to github-agent for {req.repo_name}")

@publisher_client.on_message(GithubPushResult)
async def on_github_result(ctx: Context, sender: str, res: GithubPushResult):
    repo_name = None
    if res.repo_url:
        repo_name = res.repo_url.rstrip("/").split("/")[-1]
    key = repo_name if repo_name in PENDING else (next(iter(PENDING)) if PENDING else None)

    if key:
        meta = PENDING.pop(key)
        cb, rid = meta["cb"], meta["rid"]
        if cb:
            await ctx.send(cb, PublishOutcome(
                request_id=rid, success=res.success, repo_url=res.repo_url, error=res.error
            ))

    if res.success:
        ctx.logger.info(f"[publisher-client] ✅ GitHub pushed: {res.repo_url}")
        print({"pushed": True, "repo_url": res.repo_url})
    else:
        ctx.logger.error(f"[publisher-client] ❌ GitHub push failed: {res.error}")
        print({"pushed": False, "error": res.error})

# ============================================================================
# UI GATEWAY (Flask on port 8090, Agent on port 8091)
# ============================================================================

bridge = Agent(
    name="ui-gateway",
    seed="hackathon-ui-gateway-seed",
    port=8091,
    endpoint=["http://127.0.0.1:8091/submit"],
)

SEND_QUEUE: "Queue[Dict[str, Any]]" = Queue()
RESULTS: Dict[str, Dict[str, Any]] = {}

app = Flask(__name__)

@app.post("/push")
def push_handler():
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

@bridge.on_event("startup")
async def bridge_startup(ctx: Context):
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
            await ctx.send(publisher_client.address, msg)
            ctx.logger.info(f"[ui-gateway] → Forwarded PushDoc ({rid}) to publisher-client")
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

# ============================================================================
# MAIN - Run all three agents in the same process
# ============================================================================

if __name__ == "__main__":
    import sys
    from uagents import Bureau
    
    print("=" * 60)
    print("MERGED GITHUB PUBLISHER SYSTEM")
    print("=" * 60)
    print(f"github-agent:      {github_agent.address}")
    print(f"publisher-client:  {publisher_client.address}")
    print(f"ui-gateway:        {bridge.address}")
    print(f"Flask API:         http://0.0.0.0:8090")
    print("=" * 60)
    
    # Start Flask in background thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Run all agents using Bureau
    bureau = Bureau()
    bureau.add(github_agent)
    bureau.add(publisher_client)
    bureau.add(bridge)
    
    try:
        bureau.run()
    except KeyboardInterrupt:
        print("\nShutting down...")
        sys.exit(0)