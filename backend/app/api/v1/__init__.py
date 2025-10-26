from flask import Blueprint

bp = Blueprint("api_v1", __name__, url_prefix="/api/v1")

# Import routes after bp is defined to avoid circular imports
from . import echo, health, extractor, generator  # noqa: F401
