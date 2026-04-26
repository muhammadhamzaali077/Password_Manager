# Password Manager Health Check

A friendly chat that asks two questions — how many passwords you have and how
old the oldest one is — and returns a 0–100 health score in a color-coded
card with a short list of fixes. History is tracked per-browser so you can see
yourself improving.

## Apps in this repo

- **`frontend/`** — Next.js 15 + TypeScript + Tailwind + shadcn/ui, deployed
  on Vercel. Owns the chat UI, the BFF API routes, and the Prisma → Neon
  Postgres data layer.
- **`backend/`** — Python 3.12 FastAPI agent managed with `uv`, using the
  OpenAI Agents SDK with `gpt-4o-mini` and structured-JSON responses. Stateless.

## Quickstart

See [`specs/001-health-score-chat/quickstart.md`](specs/001-health-score-chat/quickstart.md)
for the local-development walkthrough and smoke tests. In short:

```bash
# Backend
cd backend && uv sync && uv run uvicorn agent.main:app --reload --port 8000

# Frontend (new terminal)
cd frontend && pnpm install && pnpm prisma migrate dev --name init && pnpm dev
```

Open <http://localhost:3000>.

## Environment variables

`frontend/.env.local`:

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | Neon Postgres connection string. |
| `AGENT_URL` | Base URL of the FastAPI agent (default `http://127.0.0.1:8000`). |
| `SESSION_COOKIE_NAME` | Name of the visitor cookie (default `pmh_session`). |

`backend/.env`:

| Variable | Purpose |
|----------|---------|
| `OPENAI_API_KEY` | Required for the OpenAI Agents SDK. |
| `ALLOWED_ORIGIN` | CORS origin for the Next.js app (e.g. `http://localhost:3000`). |

## Constitution

This project follows
[`.specify/memory/constitution.md`](.specify/memory/constitution.md). Highlights:

- Strict input validation on the backend (Pydantic) and at the BFF (Zod).
- Friendly user-facing errors only — never raw stack traces.
- Mobile-first (every flow works at 375 px wide).
- shadcn/ui for cards and progress bars.
- The Python agent always returns structured JSON.
