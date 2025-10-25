# publisher_client_agent.py
from __future__ import annotations
from uagents import Agent, Context, Model
from typing import List, Dict, Any, Optional
import os, re, json, argparse, uuid  # <-- added uuid

# --------- Protocol (must match github_agent.py) ---------
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
    owner: Optional[str] = None   # optional; defaults to server's GITHUB_USERNAME
    metadata: Optional[Dict[str, Any]] = None

class GithubPushResult(Model):
    success: bool
    repo_url: Optional[str] = None
    error: Optional[str] = None

# --------- New: outcome model the HTTP gateway (or another agent) can receive ---------
class PublishOutcome(Model):
    request_id: str
    success: bool
    repo_url: Optional[str] = None
    error: Optional[str] = None

# --------- Message your other agent/app sends to THIS client to trigger a push ---------
# (updated: includes request_id + callback_address)
class PushDoc(Model):
    payload: Dict[str, Any]          # your JSON blob (format you shared)
    visibility: str = "private"
    request_id: str = ""             # gateway sets this (uuid)
    callback_address: Optional[str] = None  # gateway agent address (to send outcome)

# --------- Mapper: your JSON -> GithubPushRequest ---------
def _slugify(title: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9-_]+", "-", (title or "project").strip()).strip("-")
    return s[:90] or "project"

def build_push_request_from_doc(doc: Dict[str, Any], *, visibility: str = "private") -> GithubPushRequest:
    """
    Expects your format, e.g.:
    {
      "coding_related": true,
      "classification": {...},
      "research_titles": [...],
      "ideas": [{
        "title": "...",
        "approach": "...",
        "stack": "...",
        "documentation": "## README ...",
        "code_samples": [{"filename":"app.py","language":"python","content":"..."}]
      }],
      "count": 3
    }
    """
    ideas = doc.get("ideas") or []
    idea = ideas[0] if ideas else {}
    title = idea.get("title") or "project"
    readme_md = idea.get("documentation") or f"# {title}\n\n(Generated README)\n"

    files: List[GithubFile] = []
    for cs in (idea.get("code_samples") or []):
        fn = cs.get("filename") or "main.py"
        files.append(GithubFile(path=fn, content=cs.get("content") or ""))

    # hygiene files
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

# --------- Client agent that forwards to your self-hosted GitHub Agent ---------
# Set this to the address printed by github_agent.py
GITHUB_AGENT_ADDR = os.getenv("GITHUB_AGENT_ADDR", "").strip()

publisher_client = Agent(
    name="publisher-client",
    seed="hackathon-publisher-client-seed",
    port=8008,
    endpoint=["http://127.0.0.1:8008/submit"],
)

# Track pending pushes so we can route results back to the gateway
# key = repo_name → {"cb": callback_address, "rid": request_id}
PENDING: Dict[str, Dict[str, Any]] = {}

@publisher_client.on_event("startup")
async def announce(ctx: Context):
    ctx.logger.info(f"[publisher-client] Address: {publisher_client.address}")

    # Optional one-shot push (handy for quick CLI tests)
    doc_file = os.getenv("PUBLISH_DOC", "").strip()
    visibility = os.getenv("GITHUB_VISIBILITY", "private").strip()
    if doc_file and GITHUB_AGENT_ADDR:
        try:
            with open(doc_file, "r", encoding="utf-8") as f:
                doc = json.load(f)
            req = build_push_request_from_doc(doc, visibility=visibility or "private")
            # store a dummy pending record so the callback path won’t break (no callback on CLI)
            PENDING[req.repo_name] = {"cb": None, "rid": str(uuid.uuid4())}
            await ctx.send(GITHUB_AGENT_ADDR, req)
            ctx.logger.info(f"[publisher-client] Auto-push sent to {GITHUB_AGENT_ADDR} for repo {req.repo_name}")
        except Exception as e:
            ctx.logger.error(f"[publisher-client] Auto-push failed: {e}")

# Triggered by your backend/another agent on “Push code”
@publisher_client.on_message(PushDoc)
async def on_pushdoc(ctx: Context, sender: str, msg: PushDoc):
    if not GITHUB_AGENT_ADDR:
        ctx.logger.error("[publisher-client] GITHUB_AGENT_ADDR not set; cannot forward.")
        return

    req = build_push_request_from_doc(msg.payload, visibility=msg.visibility)
    # store callback + request id keyed by repo_name
    PENDING[req.repo_name] = {"cb": msg.callback_address, "rid": (msg.request_id or str(uuid.uuid4()))}

    await ctx.send(GITHUB_AGENT_ADDR, req)
    ctx.logger.info(f"[publisher-client] Sent GithubPushRequest to {GITHUB_AGENT_ADDR} for {req.repo_name}")

# Receive result from github_agent.py
@publisher_client.on_message(GithubPushResult)
async def on_github_result(ctx: Context, sender: str, res: GithubPushResult):
    # try to recover repo_name from repo_url, else fall back to a single pending entry
    repo_name = None
    if res.repo_url:
        repo_name = res.repo_url.rstrip("/").split("/")[-1]

    key = None
    if repo_name and repo_name in PENDING:
        key = repo_name
    elif len(PENDING) == 1:
        key = next(iter(PENDING))   # best-effort fallback for errors without URL

    if key:
        meta = PENDING.pop(key)
        cb, rid = meta["cb"], meta["rid"]
        if cb:
            await ctx.send(cb, PublishOutcome(
                request_id=rid, success=res.success, repo_url=res.repo_url, error=res.error
            ))

    # Existing logs/prints
    if res.success:
        ctx.logger.info(f"[publisher-client] ✅ GitHub pushed: {res.repo_url}")
        print({"pushed": True, "repo_url": res.repo_url})
    else:
        ctx.logger.error(f"[publisher-client] ❌ GitHub push failed: {res.error}")
        print({"pushed": False, "error": res.error})

# --------- CLI convenience (optional) ---------
def _parse_args():
    ap = argparse.ArgumentParser(description="Publisher Client Agent")
    ap.add_argument("--address", help="Your github_agent address (agent1...)", default=os.getenv("GITHUB_AGENT_ADDR", ""))
    ap.add_argument("--file", help="Path to JSON doc to push", default=os.getenv("PUBLISH_DOC", ""))
    ap.add_argument("--visibility", choices=["public", "private"], default=os.getenv("GITHUB_VISIBILITY", "private"))
    return ap.parse_args()

if __name__ == "__main__":
    args = _parse_args()
    if args.address and not os.getenv("GITHUB_AGENT_ADDR"):
        os.environ["GITHUB_AGENT_ADDR"] = args.address
    if args.file and not os.getenv("PUBLISH_DOC"):
        os.environ["PUBLISH_DOC"] = args.file
    print("publisher-client:", publisher_client.address)
    publisher_client.run()
