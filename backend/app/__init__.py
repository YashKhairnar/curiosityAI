import os
from flask import Flask, jsonify
from .config import get_config
from .extensions import init_logging, init_cors
from .api.v1 import bp as api_v1_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(get_config())

    # Extensions
    init_logging(app)
    init_cors(app)

    # Blueprints
    app.register_blueprint(api_v1_bp)

    # Health root (optional convenience)
    @app.get("/")
    def root():
        return jsonify(app="flask-starter", version="v1"), 200

    # Error handlers (keep responses consistent)
    @app.errorhandler(404)
    def not_found(err):
        return jsonify(error="not_found", message="Resource not found"), 404

    @app.errorhandler(400)
    def bad_request(err):
        return jsonify(error="bad_request", message="Bad request"), 400

    @app.errorhandler(Exception)
    def internal_error(err):
        app.logger.exception("Unhandled exception")
        return jsonify(error="internal_error", message="Something went wrong"), 500

    return app
