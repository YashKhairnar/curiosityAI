from flask import request, jsonify
from app.api.v1 import bp

@bp.post("/echo")
def echo():
    """
    Accepts JSON and echoes it back with a server tag.
    No auth; allows any user.
    """
    payload = request.get_json(silent=True) or {}
    return jsonify(
        ok=True,
        received=payload,
        server="flask-starter"
    ), 200
