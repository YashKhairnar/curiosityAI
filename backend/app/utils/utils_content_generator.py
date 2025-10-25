import os
import json
from flask import Flask, request, jsonify
from werkzeug.exceptions import HTTPException

import google.generativeai as genai


GEMINI_MODEL = os.getenv("GEMINI_MODEL")
API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel(GEMINI_MODEL)


def _safe_json(text: str, fallback):
    try:
        return json.loads(text)
    except Exception:
        return fallback


def classify_coding_related(summary: str):
    """Ask Gemini to classify: is this idea coding-related? Return JSON."""
    prompt = f"""
You are a JSON-only classifier.

Task:
Given a user "project idea/summary", determine if it is meant to be something about writing code.

Return ONLY a minified JSON object with keys:
- coding_related: boolean
- confidence: number between 0 and 1
- reasons: short string (max 200 chars)

User summary: {summary}
"""
    resp = model.generate_content(prompt)
    text = (resp.text or "").strip()
    return _safe_json(
        ''.join(text.split('\n')[1:-1]),
        {"coding_related": False, "confidence": 0.0, "reasons": "Unparseable response"}
    )


def generate_research_titles(summary: str, n: int = 5):
    """Always generate concise research proposal titles (array of strings)."""
    n = max(1, min(10, int(n)))
    prompt = f"""
Return ONLY a JSON array of {n} concise research proposal titles related to the following idea/summary.
Avoid duplicates; keep each under 90 characters.

Summary: {summary}
"""
    resp = model.generate_content(prompt)
    text = (resp.text or "").strip()
    parsed = _safe_json(text, [])
    if isinstance(parsed, list):
        return [str(x) for x in parsed][:n]
    return []


def generate_multi_code_and_docs(
    summary: str,
    preferred_stack,
    num_ideas: int
):
    """
    Ask Gemini to generate multiple project ideas (variants) with code + docs.
    Returns a list of idea objects.
    """
    num_ideas = max(1, min(5, int(num_ideas)))
    stack_hint = f"Preferred stack: {preferred_stack}" if preferred_stack else "Preferred stack: (none specified)"
    prompt = f"""
You are a senior software engineer. Produce STRICT JSON (no markdown fences, no commentary).

User summary: {summary}
{stack_hint}

Output: Return ONLY a JSON array with exactly {num_ideas} objects. Each object must match:
{{
  "title": "short, specific title for the project",
  "approach": "1-2 sentence description of how this idea/variant interprets the summary",
  "stack": "chosen tech stack (respect preference if given)",
  "code_samples": [
    {{"filename": "string", "language": "e.g. python, js", "content": "FULL file content"}}
  ],
  "documentation": "Markdown for a README that explains setup, usage, API/contracts, and limitations"
}}

Constraints:
- Each idea must be distinct (vary features, architecture, or stack).
- Keep filenames realistic (e.g., app.py, server.js, routes.py, Dockerfile).
- Ensure code and documentation match each other.
- Prefer minimal, runnable examples over pseudo-code.
- If the summary suggests a web API, include at least one endpoint example.
- Do NOT include backticks or additional commentary. Return only valid JSON.
"""
    resp = model.generate_content(prompt)
    text = (resp.text or "").strip()
    fallback = [{
        "title": "Generated Project",
        "approach": "Baseline interpretation of the summary.",
        "stack": preferred_stack or "Auto-selected by model",
        "code_samples": [],
        "documentation": "Documentation could not be parsed."
    }]
    ideas = _safe_json(text, fallback)
    # Basic sanitation to ensure list-of-dicts
    if not isinstance(ideas, list):
        ideas = fallback
    cleaned = []
    for idea in ideas[:num_ideas]:
        if not isinstance(idea, dict):
            continue
        cleaned.append({
            "title": idea.get("title", "Generated Project"),
            "approach": idea.get("approach", "Alternative interpretation."),
            "stack": idea.get("stack", preferred_stack or "Auto-selected by model"),
            "documentation": idea.get("documentation", "No documentation generated."),
            "code_samples": idea.get("code_samples", []),
        })
    return cleaned
