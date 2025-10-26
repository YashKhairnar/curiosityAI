import os
from app import create_app

app = create_app()

if __name__ == "__main__":
    # Use FLASK_PORT from environment, defaulting to 9000
    port = int(os.getenv("FLASK_PORT", 9000))
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    
    print(f"🚀 Starting Flask server on {host}:{port}")
    app.run(host=host, port=port, debug=debug)
