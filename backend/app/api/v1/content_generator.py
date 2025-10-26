from flask import request, jsonify
from app.api.v1 import bp
from app.utils.utils_content_generator import classify_coding_related, generate_research_titles, generate_multi_code_and_docs
from app.agents.code_agent import generator


@bp.post("/content_generator")
def content_generator():
    """
    Body JSON:
    {
      "summary": "string (required)",
      "num_research_titles": 5       # optional, default 5, max 10
    }
    """
    data = request.get_json(silent=True) or {}
    summary = (data.get("summary") or "").strip()
    num_titles = int(data.get("num_research_titles") or 5)

    if not summary:
        return jsonify({"error": "Missing 'summary' in request body."}), 400

    # 1) Classify
    classification = classify_coding_related(summary)
    print('INFO:', classification.get('coding_related'))
    coding_related = bool(classification.get("coding_related"))
    confidence = float(classification.get("confidence") or 0.0)
    reasons = str(classification.get("reasons") or "")

    # 2) Always produce research proposal titles
    research_titles = generate_research_titles(summary, n=num_titles)

    result = {
        "coding_related": coding_related,
        "classification": {"confidence": confidence, "reasons": reasons},
        "research_titles": research_titles
    }

    # 3) Branch on coding-related
    if coding_related:
        ideas = generator.create_project(summary=summary)
        result.update({
            "ideas": ideas,               # list of idea objects
            "count": len(ideas)
        })
    else:
        result.update({
            "message": "The idea doesn't look primarily coding-related. No code/doc generated."
        })

    return jsonify(result), 200