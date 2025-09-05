# Frontend (Next.js)

This is an optional React/Next.js UI that enhances the visualization of similar projects.

## Prerequisites
- Node.js 18+
- Backend running at http://127.0.0.1:8000 (FastAPI in this repo)
- Ensure backend CORS allows http://localhost:3000 (set `CORS_ORIGINS` in `.env` if needed)

## Setup

```
cd frontend
npm install
npm run dev
```

Open http://localhost:3000 in your browser.

## Features
- Text prediction (query_text) and big, clean estimate display
- Similar projects as responsive cards with similarity bars
- "Show this month's actual" button that reads a 60-month randomized schedule (same logic as static UI) and fetches initial budget for the current month from the backend

## Notes
- The schedule is kept in `localStorage` under key `pg_overview_schedule_v1`
- API endpoints used:
  - `POST /v1/budget/predict`
  - `GET /v1/events/ids`
  - `GET /v1/events/meta?budget_id=...`
