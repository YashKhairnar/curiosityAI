# 🛠️ Backend Developer Guide

This backend exposes a Flask API that uses **Google Gemini** to:
- Generate **multiple coding ideas** (each with code snippets + documentation) when the input is coding-related.
- Return **research proposal titles** for any topic.
- Politely say when an idea isn’t coding-related.

---

## 1️⃣ Project Structure
```bash
backend/
├─ app.py # Flask API
├─ startup.py # Loads .env and launches the server
├─ requirements.txt
├─ .env # ← provided to you; place here (do NOT commit)
└─ README.md
```


---

## 2️⃣ Prerequisites

- **Python 3.9+**
- **Google Gemini API Key** (from [Google AI Studio](https://aistudio.google.com/))

---

## 3️⃣ Setup & Run (Local)

1. Move into the backend folder:
```bash
cd backend
```

2. Create and activate a virtual environment:

```bash

python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
Place the provided .env file inside the backend/ folder.
```

4. Start the server using the startup script (loads .env automatically):

```bash
python startup.py
✅ Server runs at http://localhost:${PORT}   # default: http://localhost:8000
```


---

## 4️⃣ API Endpoints

🩺 A) Health Check: Verify the server and model configuration.
```bash
Method: GET
URL: /health
curl: curl -s http://localhost:8000/api/v1/health
```


💡 B) Generate Ideas / Code / Docs / Research Titles: Analyzes the summary, classifies if it’s coding-related, and:

 - If coding-related → returns N ideas with code + docs.
 - Always returns research proposal titles.

```bash
Method: POST
URL: /generate
curl: curl -s -X POST http://localhost:8000/api/v1/generate \
  -H "Content-Type: application/json" \
  -d '{
    "summary": "A REST API for tracking workouts with JWT auth and PostgreSQL",
    "preferred_stack": "Python Flask + SQLAlchemy",
    "num_ideas": 3,
    "num_research_titles": 5
  }'
```
Sample Response:
```bash
{
  "coding_related": true,
  "classification": {
    "confidence": 0.96,
    "reasons": "Mentions API, auth, database."
  },
  "research_titles": ["...", "...", "..."],
  "ideas": [
    {
      "title": "WorkoutLog API",
      "approach": "Flask service with JWT and SQLAlchemy models.",
      "stack": "Python Flask + SQLAlchemy",
      "documentation": "## README ...",
      "code_samples": [
        {"filename": "app.py", "language": "python", "content": "..."}
      ]
    }
  ],
  "count": 3
}
```
