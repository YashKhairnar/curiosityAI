import os
import json
import re
import time
import requests
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# pip install tavily-python
from tavily import TavilyClient

load_dotenv()
app = Flask(__name__)

ASI_KEY = os.getenv("ASI_LLM_KEY")
ASI_URL = os.getenv("ASI_LLM_API_URL", "https://api.asi1.ai/v1/chat/completions")
TAVILY_KEY = os.getenv("TAVILY_API_KEY")
TAVILY_TIMEOUT = float(os.getenv("TAVILY_TIMEOUT", "20"))  # seconds/network call
ASI_TIMEOUT = float(os.getenv("ASI_TIMEOUT", "60"))        # seconds total for ASI call

# Reuse connections (Keep-Alive)
SESSION = requests.Session()
TV: Optional[TavilyClient] = TavilyClient(api_key=TAVILY_KEY) if TAVILY_KEY else None

# ---------------------------
# Generic relevance heuristics
# ---------------------------
BLOCKLIST_BASE = {
    "x.com", "twitter.com", "facebook.com", "instagram.com", "tiktok.com",
    "pinterest.com", "reddit.com", "quora.com",
    "linktr.ee", "links.govdelivery.com", "bit.ly", "t.co"
}
SOFT_BLOCK = {"youtube.com", "www.youtube.com", "youtu.be"}
PRESS_HINTS = {"newsroom", "press", "media", "/news/", "/press/", "/investor", "investor."}
DOC_HINTS = {"docs.", "/docs", "/documentation", "/spec", "/standard", "ietf.org", "w3.org", "iso.org"}
ACADEMIC_HINTS = {"arxiv.org", "doi.org", ".edu"}
TOP_TIER_MEDIA = {
    "reuters.com", "apnews.com", "bbc.com", "bloomberg.com", "ft.com",
    "nytimes.com", "wsj.com", "theguardian.com", "nature.com", "science.org",
    "techcrunch.com", "theverge.com", "wired.com"
}

# ---------------------------
# Small utils
# ---------------------------
def _dedupe_preserve(seq: List[str]) -> List[str]:
    seen = set(); out = []
    for x in seq:
        if x not in seen:
            seen.add(x); out.append(x)
    return out

def _domain(url: str) -> str:
    try: return urlparse(url).netloc.lower()
    except Exception: return ""

def _normalize_url(url: str) -> str:
    try:
        u = urlparse(url)
        if not u.scheme.startswith("http"): return url
        q = [(k, v) for k, v in parse_qsl(u.query, keep_blank_values=True)
             if not k.lower().startswith(("utm_", "gclid", "fbclid", "mc_cid", "mc_eid"))]
        new_q = urlencode(q)
        path = u.path.rstrip("/") if u.path != "/" else u.path
        return urlunparse((u.scheme, u.netloc, path, u.params, new_q, ""))
    except Exception:
        return url

def _now_utc() -> datetime:
    return datetime.now(timezone.utc)

def _parse_date(val: Optional[str]) -> Optional[datetime]:
    if not val: return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%SZ", "%a, %d %b %Y %H:%M:%S %Z"):
        try:
            dt = datetime.strptime(val, fmt)
            if not dt.tzinfo: dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception: continue
    try: return datetime.fromisoformat(val.replace("Z", "+00:00"))
    except Exception: return None

def _extract_json(text: str) -> Any:
    try: return json.loads(text)
    except Exception: pass
    s = text.find("{"); e = text.rfind("}")
    if s != -1 and e != -1 and e > s:
        try: return json.loads(text[s:e+1])
        except Exception: pass
    return None

def _has_any(url: str, needles: set[str]) -> bool:
    u = url.lower()
    return any(n in u for n in needles)

# ---------------------------
# ASI1-mini planner (generic)
# ---------------------------
def plan_from_asi(text: str, max_queries: int = 6, max_domains: int = 8) -> Tuple[List[str], List[str], bool]:
    """Return (queries, preferred_domains, time_sensitive)."""
    if not ASI_KEY:
        return [text[:300]], [], True

    sys_prompt = f"""
You craft generic search plans for fact-checking across any topic.

Return STRICT JSON only (no markdown, no prose):
{{
  "time_sensitive": true,
  "queries": ["q1", "q2", "..."],
  "preferred_domains": ["official.example.com", "agency.gov", "org.edu"]
}}

Rules:
- Max {max_queries} queries, max {max_domains} domains.
- Prefer official/org sites (newsroom/press/investor/docs), .gov, .edu, standards bodies, reputable journals.
- Avoid social media and generic SEO blogs.
- Keep queries specific to entities, products, standards, and time frames.
"""
    payload = {
        "model": "asi1-mini",
        "messages": [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": text},
        ],
        "temperature": 0.2,
        "max_tokens": 750,
        "stream": False,
    }
    try:
        resp = SESSION.post(
            ASI_URL,
            headers={"Authorization": f"Bearer {ASI_KEY}", "Content-Type": "application/json"},
            json=payload,
            timeout=(10, ASI_TIMEOUT),
        )
        resp.raise_for_status()
        msg = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")
        parsed = _extract_json(msg) or {}
        queries = parsed.get("queries") if isinstance(parsed, dict) else None
        domains = parsed.get("preferred_domains") if isinstance(parsed, dict) else None
        time_sensitive = bool(parsed.get("time_sensitive", True)) if isinstance(parsed, dict) else True

        q = [str(x).strip() for x in (queries or []) if str(x).strip()]
        d = [str(x).lower().strip() for x in (domains or []) if str(x).strip()]

        q = q[:max_queries] or [text[:300]]
        d = [x for x in d if x][:max_domains]
        return q, d, time_sensitive
    except Exception:
        return [text[:300]], [], True

# ---------------------------
# Scoring (generic)
# ---------------------------
def _authority_score(domain: str, url: str, preferred_domains: List[str], mode: str) -> float:
    score = 0.0; u = url.lower()
    if domain in preferred_domains: score += 3.0
    if domain.endswith(".gov"): score += 2.6
    if domain.endswith(".edu"): score += 2.3
    if _has_any(u, PRESS_HINTS): score += 1.5
    if _has_any(u, DOC_HINTS): score += 1.3
    if _has_any(u, ACADEMIC_HINTS): score += 1.2
    if domain in TOP_TIER_MEDIA: score += 1.0
    if domain in BLOCKLIST_BASE: score -= 4.0
    if domain in SOFT_BLOCK: score -= 0.6
    if mode == "official_first" and (domain.endswith((".gov", ".edu")) or _has_any(u, PRESS_HINTS) or _has_any(u, DOC_HINTS)):
        score += 0.6
    elif mode == "media_first" and domain in TOP_TIER_MEDIA:
        score += 0.6
    return score

def _keyword_score(text: str, queries: List[str]) -> float:
    base = " ".join(queries[:2]).lower()
    tokens = {t for t in re.split(r"[^a-z0-9]+", base) if len(t) > 3}
    if not tokens: return 0.0
    t = text.lower()
    hits = sum(1 for tok in tokens if tok in t)
    return min(1.0, hits / (len(tokens) or 1))

def _recency_score(published: Optional[str]) -> float:
    if not published: return 0.3
    dt = _parse_date(published)
    if not dt: return 0.4
    days = max(0, (_now_utc() - dt).days)
    return max(0.0, 1.0 - (days / 365.0))

def rank_results(results: List[Dict[str, Any]], preferred_domains: List[str], queries: List[str], mode: str) -> List[Tuple[float, str, str]]:
    ranked = []
    for r in results:
        url = _normalize_url(str(r.get("url", "")).strip())
        if not url.startswith("http"): continue
        domain = _domain(url)
        title = (r.get("title") or "") + " " + (r.get("content") or r.get("snippet") or "")
        published = r.get("published_date") or r.get("date")
        score = (
            0.55 * _authority_score(domain, url, preferred_domains, mode) +
            0.25 * _recency_score(published) +
            0.20 * _keyword_score(title, queries)
        )
        # Penalize non-official PDFs (keeps .gov/.edu or preferred domains)
        if url.lower().endswith(".pdf") and (domain not in preferred_domains) and not (domain.endswith(".gov") or domain.endswith(".edu")):
            score -= 1.0
        ranked.append((score, url, domain))
    ranked.sort(key=lambda x: x[0], reverse=True)
    return ranked

def _merge_domain_diverse(ranked: List[Tuple[float, str, str]], k: int, block_social: bool) -> List[str]:
    out: List[str] = []; seen_domains: set[str] = set()
    for _, url, dom in ranked:
        if block_social and (dom in BLOCKLIST_BASE): continue
        if url in out: continue
        if dom not in seen_domains:
            out.append(url); seen_domains.add(dom)
        if len(out) >= k: return out
    for _, url, dom in ranked:
        if block_social and (dom in BLOCKLIST_BASE): continue
        if url in out: continue
        out.append(url)
        if len(out) >= k: break
    return out

# ---------------------------
# Tavily search (fast + parallel + early stop)
# ---------------------------
def _tv_search_call(q: str, *, include_domains=None, exclude_domains=None, days=365, search_depth="advanced", stype="general", max_results=8):
    # Use the global client; Tavily client does per-call timeouts internally via httpx defaults.
    # We just rely on Tavily's backend; if you want per-call timeouts here, wrap with threads and timeouts.
    return TV.search(
        q,
        max_results=max_results,
        search_depth=search_depth,
        include_raw_content=False,     # was True — turning off speeds things up a lot
        include_answer=False,
        include_images=False,
        include_domains=include_domains,
        exclude_domains=exclude_domains,
        days=days,
        search_type=stype,
    )

def tavily_best_links(
    queries: List[str],
    preferred_domains: List[str],
    max_links: int,
    days: int,
    mode: str,
    include_domains: Optional[List[str]] = None,
    exclude_domains: Optional[List[str]] = None,
    search_depth: str = "advanced",
    time_sensitive: bool = True,
    fast: bool = False,
    budget_ms: Optional[int] = None,
) -> List[str]:
    if TV is None: return []
    start = time.monotonic()
    def time_left() -> float:
        if budget_ms is None: return 1e9
        return max(0.0, (budget_ms / 1000.0) - (time.monotonic() - start))

    # Fast mode tweaks
    if fast:
        search_depth = "basic"
        days = min(days, 120 if time_sensitive else 365)
        per_query = 4
        # use fewer queries if we have a lot
        queries = queries[:max(3, min(len(queries), 4))]
    else:
        per_query = 8

    blocklist = set(BLOCKLIST_BASE)
    if exclude_domains:
        blocklist.update([d.lower() for d in exclude_domains])

    raw: List[Dict[str, Any]] = []
    dom_focus = [d for d in (preferred_domains or []) if d] + [d for d in (include_domains or []) if d]
    dom_focus = [d.lower() for d in dom_focus if d.lower() not in blocklist][:12]
    stype = "news" if time_sensitive else "general"

    # Helper to add results & early stop
    def extend_results(res):
        items = res.get("results", []) if isinstance(res, dict) else []
        for it in items:
            u = str(it.get("url", "")).strip()
            if u.startswith("http"):
                raw.append(it)

    # PASS 1: preferred domains (in parallel)
    if dom_focus and time_left() > 0.05:
        with ThreadPoolExecutor(max_workers=min(8, len(queries))) as ex:
            futs = [
                ex.submit(_tv_search_call, q,
                          include_domains=dom_focus, exclude_domains=None,
                          days=days, search_depth=search_depth, stype=stype, max_results=per_query)
                for q in queries
            ]
            for f in as_completed(futs, timeout=None):
                if budget_ms is not None and time_left() <= 0.0:
                    break
                try:
                    res = f.result(timeout=TAVILY_TIMEOUT)
                    extend_results(res)
                except Exception:
                    continue
                # Early stop if we already have enough unique URLs
                if len({_normalize_url(str(i.get("url",""))) for i in raw}) >= max_links * 2:
                    break

    # PASS 2: broader (parallel), only if we still need more
    if time_left() > 0.05 and len(raw) < max_links * 2:
        with ThreadPoolExecutor(max_workers=min(8, len(queries))) as ex:
            futs = [
                ex.submit(_tv_search_call, q,
                          include_domains=None, exclude_domains=list(blocklist),
                          days=days, search_depth=search_depth, stype=stype, max_results=per_query)
                for q in queries
            ]
            for f in as_completed(futs, timeout=None):
                if budget_ms is not None and time_left() <= 0.0:
                    break
                try:
                    res = f.result(timeout=TAVILY_TIMEOUT)
                    extend_results(res)
                except Exception:
                    continue
                if len({_normalize_url(str(i.get("url",""))) for i in raw}) >= max_links * 3:
                    break

    # Dedupe & rank
    seen = set(); unique: List[Dict[str, Any]] = []
    for item in raw:
        u = _normalize_url(str(item.get("url","")).strip())
        if not u.startswith("http"): continue
        if u in seen: continue
        seen.add(u); unique.append(item)

    ranked = rank_results(unique, preferred_domains, queries, mode)
    block_social = True
    out = _merge_domain_diverse(ranked, k=max_links, block_social=block_social)
    return out[:max_links]

# ---------------------------
# Flask endpoint
# ---------------------------
@app.post("/references")
def references():
    """
    Body JSON:
    {
      "text": "string",                # REQUIRED
      "max_references": 6,             # optional
      "days": 365,                     # optional recency window
      "mode": "official_first",        # "official_first" | "balanced" | "media_first"
      "include_domains": ["..."],      # optional hard include
      "exclude_domains": ["..."],      # optional hard exclude
      "search_depth": "advanced",      # "basic" | "advanced"
      "fast": true,                    # speed-first settings
      "budget_ms": 2500                # optional overall time budget (approx)
    }
    """
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 415

    data = request.get_json(silent=True) or {}
    text = data.get("text") or data.get("data") or data.get("content") or ""
    if not isinstance(text, str) or not text.strip():
        return jsonify({"error": "Missing 'text' in request body"}), 400
    if not ASI_KEY or not TAVILY_KEY:
        return jsonify({"error": "Missing API keys. Set ASI_LLM_KEY and TAVILY_API_KEY in .env"}), 500

    # Params
    try: max_refs = max(1, int(data.get("max_references", 6)))
    except Exception: max_refs = 6
    try: days = int(data.get("days", 365))
    except Exception: days = 365
    mode = str(data.get("mode", "official_first")).lower()
    if mode not in {"official_first", "balanced", "media_first"}: mode = "official_first"
    include_domains = [d.lower() for d in data.get("include_domains", []) if isinstance(d, str)]
    exclude_domains = [d.lower() for d in data.get("exclude_domains", []) if isinstance(d, str)]
    search_depth = str(data.get("search_depth", "advanced"))
    if search_depth not in {"basic", "advanced"}: search_depth = "advanced"
    fast = bool(data.get("fast", False))
    budget_ms = None
    if "budget_ms" in data:
        try: budget_ms = max(500, int(data["budget_ms"]))  # min 0.5s
        except Exception: budget_ms = None

    # Fewer queries in fast mode
    q_cap = 4 if fast else max_refs if max_refs >= 3 else 3
    queries, preferred_domains, time_sensitive = plan_from_asi(text.strip(), max_queries=q_cap)

    links = tavily_best_links(
        queries=queries,
        preferred_domains=preferred_domains,
        max_links=max_refs,
        days=days,
        mode=mode,
        include_domains=include_domains,
        exclude_domains=exclude_domains,
        search_depth=search_depth,
        time_sensitive=time_sensitive,
        fast=fast,
        budget_ms=budget_ms,
    )
    return jsonify({"links": links}), 200

@app.get("/health")
def health():
    return jsonify({"ok": True}), 200

if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    app.run(host=host, port=port, debug=os.getenv("FLASK_DEBUG", "0") == "1")
