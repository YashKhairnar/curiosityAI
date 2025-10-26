# github_agent.py
from __future__ import annotations
from uagents import Agent, Context, Model
from typing import List, Optional, Dict, Any
import os, base64, aiohttp
import re, unicodedata
import sys, subprocess, argparse
from pathlib import Path

# ---------- Models (match publisher_client_agent) ----------
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
    owner: Optional[str] = None                # preferred owner/username
    token: Optional[str] = None                # per-request PAT (optional)
    metadata: Optional[Dict[str, Any]] = None

class GithubPushResult(Model):
    success: bool
    repo_url: Optional[str] = None
    error: Optional[str] = None

# ---------- Config (env defaults) ----------
ENV_GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "").strip()          # fallback PAT
ENV_GITHUB_USERNAME = os.getenv("GITHUB_USERNAME", "").strip()    # fallback owner

if not ENV_GITHUB_USERNAME:
    print("WARNING: GITHUB_USERNAME is not set; will require 'owner' in request if not provided.")

# ---------- Agent ----------
github_agent = Agent(
    name="github-agent",
    seed="hackathon-github-agent-seed",
    port=8010,
    endpoint=["http://127.0.0.1:8010/submit"],
)

# ---------- Helpers ----------
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

# ---------- GitHub API helpers ----------
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

# ---------- Message handler ----------
@github_agent.on_message(GithubPushRequest)
async def on_push(ctx: Context, sender: str, req: GithubPushRequest):
    # choose per-request creds or fall back to env
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
async def announce(ctx: Context):
    ctx.logger.info(f"[github-agent] Address: {github_agent.address}")

# ---------- Optional: launch publisher client + Flask gateway ----------
def start_stack_children():
    here = Path(__file__).resolve().parent
    pub_path = here / "publisher_client_agent.py"
    gw_path  = here / "ui_gateway_flask.py"
    if not pub_path.exists(): raise FileNotFoundError(pub_path)
    if not gw_path.exists():  raise FileNotFoundError(gw_path)

    # compute publisher address from its seed (must match that file)
    probe = Agent(name="publisher-client-probe", seed="hackathon-publisher-client-seed")
    publisher_addr = probe.address
    github_addr = github_agent.address

    env_pub = os.environ.copy()
    env_pub["GITHUB_AGENT_ADDR"] = github_addr
    pub_proc = subprocess.Popen([sys.executable, str(pub_path)], env=env_pub)

    env_gw = os.environ.copy()
    env_gw["PUBLISHER_CLIENT_ADDR"] = publisher_addr
    gw_proc = subprocess.Popen([sys.executable, str(gw_path)], env=env_gw)

    return pub_proc, gw_proc

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GitHub Agent (with optional stack launcher)")
    parser.add_argument("--stack", action="store_true", default=os.getenv("RUN_STACK", "0") == "1")
    args = parser.parse_args()

    print("github-agent:", github_agent.address)
    procs = []
    try:
        if args.stack:
            print("[stack] launching publisher client and Flask gateway…")
            procs = list(start_stack_children())
            print(f"[stack] publisher pid={procs[0].pid}  gateway pid={procs[1].pid}")
        github_agent.run()
    finally:
        for p in procs:
            try: p.terminate()
            except Exception: pass
        for p in procs:
            try: p.wait(timeout=5)
            except Exception: pass
