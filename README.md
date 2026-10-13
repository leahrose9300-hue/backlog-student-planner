# Backlog — Academic Recovery Planner

**You're not behind forever. You just need a way back.**

## Live demo
This public hackathon edition uses a separate, temporary in-memory SQLite database for each browser session. No sign-up, API key, or payment required. All demo data is reset when the session ends. **Do not enter sensitive personal information.**

## Local setup
```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Deploy
1. Upload `app.py`, `engine.py`, `storage.py`, `requirements.txt`, `.streamlit/config.toml`, and this README to a GitHub repository.
2. Open https://share.streamlit.io and create a new app using that repository's `main` branch and `app.py` entry point.
3. Check public URL in an incognito/private window.

## How it works
- `app.py`: interface with tasks, progress, Next Step and Comeback Engine.
- `engine.py`: deterministic workload calculations and priority/deadline scheduling.
- `storage.py`: task CRUD and SQLite schema.

## Known limitations
This edition is a disposable public demo, **not** a persistent account-based app. Data is temporary per session; server restarts or expired sessions lose progress. Session-bound databases are not intended for production use. Advanced multi-user accounts would require authentication and durable hosted storage.

## Demo storyline (5 minutes)
1. Describe overwhelmed student with recorded lectures and multiple deadlines.
2. Show sample backlog and enter a new task.
3. Show the recovery plan and explain capacity constraints.
4. Complete one Next Step session and show reduced workload.
5. Mark three days unavailable; reschedule and explore additional study hours.
6. Explain free student version, test demand for a premium analytics tier, and outline future account-backed university rollout.
