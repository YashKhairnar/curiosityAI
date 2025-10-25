import os
from dotenv import load_dotenv
import subprocess

def main():
    # Load environment variables from .env file
    load_dotenv()

    # Get the port number from environment variables or default to 8000
    port = os.getenv("PORT", "8000")

    print("✅ Environment variables loaded successfully.")
    print(f"🚀 Starting Flask server on http://localhost:{port}\n")

    # Start the Flask server
    subprocess.run(["python3", "wsgi.py"])

if __name__ == "__main__":
    main()
