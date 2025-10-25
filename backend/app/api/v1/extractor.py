from flask import request, jsonify
from app.api.v1 import bp
from app.utils.common import process_keywords

@bp.post("/extractor")
def extractor():
    """
    Accepts JSON and echoes it back with a server tag.
    No auth; allows any user.
    """
    payload = request.get_json(silent=True) or {}
    keywords = payload.get('keywords', [])
    max_results = payload.get('max_results', 10)

    records = process_keywords(keywords, max_results=max_results)

    return jsonify(
        ok=True,
        received=payload,
        server="flask-starter",
        records=records
    ), 200
