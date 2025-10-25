from flask import jsonify
from app.api.v1 import bp

@bp.get("/health")
def health():
    return jsonify(status="ok"), 200
