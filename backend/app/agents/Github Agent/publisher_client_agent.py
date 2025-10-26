# publisher_client_agent.py
from __future__ import annotations
from uagents import Agent, Context, Model
from typing import List, Dict, Any, Optional
import os, re, json, argparse, uuid

# --------- Protocol (must match github_agent.py) ---------
class GithubFile(Model):
    path: str
    content: str

class GithubPushRequest(Model):
    repo_name: str
    visibility: str
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

# Message your UI gateway sends to THIS client
class PushDoc(Model):
    payload: Dict[str, Any]      # your JSON blob
    visibility: str = "private"
    request_id: str = ""
    callback_address: Optional[str] = None
    gh_owner: Optional[str] = None   # NEW
    gh_token: Optional[str] = None   # NEW

class PublishOutcome(Model):
    request_id: str
    success: bool
    repo_url: Optional[str] = None
    error: Optional[str] = None

# --------- Mapper: your JSON -> GithubPushRequest ---------
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

# --------- Client agent that forwards to your self-hosted GitHub Agent ---------
GITHUB_AGENT_ADDR = os.getenv("GITHUB_AGENT_ADDR", "").strip()

publisher_client = Agent(
    name="publisher-client",
    seed="hackathon-publisher-client-seed",
    port=8008,
    endpoint=["http://127.0.0.1:8008/submit"],
)

# Track pending pushes so we can route results back to gateway
PENDING: Dict[str, Dict[str, Any]] = {}   # repo_name -> {"cb": address, "rid": request_id}

@publisher_client.on_event("startup")
async def announce(ctx: Context):
    ctx.logger.info(f"[publisher-client] Address: {publisher_client.address}")

# Triggered by gateway “Push code”
@publisher_client.on_message(PushDoc)
async def on_pushdoc(ctx: Context, sender: str, msg: PushDoc):
    if not GITHUB_AGENT_ADDR:
        ctx.logger.error("[publisher-client] GITHUB_AGENT_ADDR not set; cannot forward.")
        return

    req = build_push_request_from_doc(msg.payload, visibility=msg.visibility)

    # attach credentials if provided (DO NOT LOG TOKENS)
    if msg.gh_owner:
        req.owner = msg.gh_owner.strip()
    if msg.gh_token:
        req.token = msg.gh_token.strip()

    rid = msg.request_id or str(uuid.uuid4())
    PENDING[req.repo_name] = {"cb": msg.callback_address, "rid": rid}

    await ctx.send(GITHUB_AGENT_ADDR, req)
    ctx.logger.info(f"[publisher-client] Sent GithubPushRequest to {GITHUB_AGENT_ADDR} for {req.repo_name}")

@publisher_client.on_message(GithubPushResult)
async def on_github_result(ctx: Context, sender: str, res: GithubPushResult):
    # best-effort repo name recovery
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

    # console signal for CLI users
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
    print("publisher-client:", publisher_client.address)
    publisher_client.run()
