import os

class BaseConfig:
    SECRET_KEY = os.getenv("SECRET_KEY", "change-me")
    JSON_SORT_KEYS = False
    JSONIFY_PRETTYPRINT_REGULAR = False
    PROPAGATE_EXCEPTIONS = True
    # CORS (allow all origins since you said “allow any user”)
    CORS_RESOURCES = {r"/*": {"origins": "*"}}

class DevelopmentConfig(BaseConfig):
    DEBUG = True

class ProductionConfig(BaseConfig):
    DEBUG = False

def get_config():
    env = os.getenv("FLASK_ENV", "production").lower()
    if env == "development":
        return DevelopmentConfig
    return ProductionConfig
