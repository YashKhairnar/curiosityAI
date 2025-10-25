# github_agent.py
from __future__ import annotations
from uagents import Agent, Context, Model
from typing import List, Optional, Dict, Any
import os, base64, aiohttp, asyncio
import re, unicodedata  # <-- added

# ---------- Models (match your publisher_client_agent) ----------
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
    metadata: Optional[Dict[str, Any]] = None

class GithubPushResult(Model):
    success: bool
    repo_url: Optional[str] = None
    error: Optional[str] = None

# ---------- Config (env) ----------
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "").strip()          # fine-grained PAT with repo scope
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME", "").strip()    # your username or org

if not GITHUB_USERNAME:
    print("WARNING: GITHUB_USERNAME is not set; set it to your GitHub username or org.")

# ---------- Agent ----------
github_agent = Agent(
    name="github-agent",
    seed="hackathon-github-agent-seed",
    port=8010,
    endpoint=["http://127.0.0.1:8010/submit"],
)

# ---------- Helpers ----------
def _headers():
    return {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
    }

def safe_desc(text: str, limit: int = 140) -> str:
    """
    Produce a short, single-line description without control characters.
    GitHub rejects descriptions with newlines/control chars.
    """
    if not text:
        return ""
    text = text.splitlines()[0]                      # first line only
    text = re.sub(r'[\r\n\t]+', ' ', text)           # no newlines/tabs
    text = ''.join(ch for ch in text if unicodedata.category(ch)[0] != 'C')  # drop control chars
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:limit]

# ---------- GitHub API helpers ----------
async def gh_create_repo(session: aiohttp.ClientSession, owner: str, name: str, description: str, private: bool):
    """
    Create repo under user (POST /user/repos) or org (POST /orgs/{owner}/repos).
    Use auto_init=True so default branch exists and we can push files via Contents API.
    """
    if not owner:
        raise RuntimeError("Missing owner")
    payload = {
        "name": name,
        "description": description[:200] if description else "",
        "private": private,
        "auto_init": True,       # ensure default branch exists
    }
    if owner.lower() == GITHUB_USERNAME.lower():
        url = "https://api.github.com/user/repos"
    else:
        url = f"https://api.github.com/orgs/{owner}/repos"
    async with session.post(url, json=payload) as r:
        data = await r.json()
        if r.status == 201:
            return data
        # If repo exists, GitHub returns 422 with a message; treat as "ok, continue"
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
        payload["sha"] = sha  # update existing
    async with session.put(url, json=payload) as r:
        data = await r.json()
        if r.status not in (200, 201):
            raise RuntimeError(f"Put file failed [{r.status}]: {data}")

# ---------- Message handler ----------
@github_agent.on_message(GithubPushRequest)
async def on_push(ctx: Context, sender: str, req: GithubPushRequest):
    if not GITHUB_TOKEN or not GITHUB_USERNAME:
        await ctx.send(sender, GithubPushResult(success=False, error="Server missing GITHUB_TOKEN or GITHUB_USERNAME"))
        return

    owner = req.owner or GITHUB_USERNAME
    private = req.visibility != "public"
    repo = req.repo_name
    branch = req.branch or "main"

    try:
        async with aiohttp.ClientSession(headers=_headers()) as session:
            # 1) Create repo (or continue if it already exists)
            #    Use a clean, short description (approach from metadata, else README first line, else repo name)
            desc_source = (req.metadata or {}).get("approach") or (req.readme_md or repo)
            description = safe_desc(desc_source)
            await gh_create_repo(session, owner, repo, description, private)

            # 2) Ensure README.md and each file exist on the desired branch
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

if __name__ == "__main__":
    print("github-agent:", github_agent.address)
    github_agent.run()
