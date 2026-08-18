# AGENTS.md

## Cursor Cloud specific instructions

This is the **Donexto / HMS AI Assistant** monorepo (an email attention assistant). Relevant runnable services:

- `backend/` — FastAPI API (Python 3.12), served with `uvicorn main:app` on port `8000`.
- `frontend/` — Next.js 16 + React 19 app on port `3000`.
- `landing/donexto/` — static HTML deployed to Cloudflare Pages (no local server needed).
- `supabase/migrations/` — SQL migrations (not required to run the app locally).

Dependencies are installed by the startup update script: Python packages into `.venv/` (repo root) and frontend npm packages into `frontend/node_modules`.

### Running the backend
```bash
source .venv/bin/activate
cd backend
SUPABASE_URL="https://placeholder.supabase.co" SUPABASE_SECRET_KEY="placeholder-key" \
  uvicorn main:app --host 0.0.0.0 --port 8000
```
Non-obvious gotcha: several services (e.g. `app/services/oauth_storage.py`) instantiate a Supabase client **at import time**, so `SUPABASE_URL` and `SUPABASE_SECRET_KEY` must be set (even to placeholders) or the import raises `HTTPException 500: Faltan variables de Supabase`. This blocks both the server and the test suite. Placeholders are enough to boot and to exercise read-only endpoints (`/`, `/health`, `/docs`); Supabase/Google-backed features need real credentials. Data mutations are gated behind `HMS_DATA_MUTATIONS_ENABLED` (default `false`).

### Running the frontend
```bash
cd frontend
npm run dev:webpack   # next dev --webpack on 0.0.0.0:3000 (repo helper: ./hms start)
```
Non-obvious gotcha: `frontend/lib/supabase.ts` throws at module load if `NEXT_PUBLIC_SUPABASE_URL` or `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` are missing, which makes the dev server return **HTTP 500** on every page. Create `frontend/.env.local` (gitignored via `.env*`, so it is not committed and must be recreated per environment) with at least:
```
NEXT_PUBLIC_SUPABASE_URL=https://placeholder.supabase.co
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=placeholder-publishable-key
HMS_INTERNAL_API_BASE_URL=http://127.0.0.1:8000
```
The browser calls `/api/hms/*`, which `frontend/app/api/hms/[...path]/route.ts` proxies to `HMS_INTERNAL_API_BASE_URL` (defaults to `http://127.0.0.1:8000` when unset). Set it to the local backend for the full stack to work together.

### Lint / test
- Frontend lint: `cd frontend && npm run lint`. The codebase currently has pre-existing eslint errors (e.g. `components/MailboxConnectModal.tsx`); they are not from environment setup.
- Backend tests: `cd backend && SUPABASE_URL=... SUPABASE_SECRET_KEY=... python -m pytest` (needs the placeholder env vars above; `pytest` is installed into `.venv`).
