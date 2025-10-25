import os
from app import create_app

app = create_app()
PORT = os.getenv("PORT", 8000)

if __name__ == "__main__":
    port = int(os.getenv("PORT", PORT))
    app.run(host="0.0.0.0", port=port)
