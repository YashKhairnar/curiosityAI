import logging
import os
from flask_cors import CORS

def init_logging(app):
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )
    handler.setFormatter(formatter)
    app.logger.handlers.clear()
    app.logger.addHandler(handler)
    app.logger.setLevel(level)
    # Silence overly noisy loggers if desired:
    logging.getLogger("werkzeug").setLevel(level)

def init_cors(app):
    CORS(app, resources=app.config.get("CORS_RESOURCES"))
