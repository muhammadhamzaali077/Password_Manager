# Quickstart: Password Health Score Chat

A local-development walkthrough that gets the chat flow working end-to-end on a
laptop, then shows the smoke checks that prove the feature is healthy before
deploy.

## Prerequisites

- Node.js 20+ and pnpm (or npm)
- Python 3.12+ and `uv` (`pip install uv` if missing)
- A Neon Postgres database URL (free tier is fine)
- An OpenAI API key with access to `gpt-4o-mini`

## 1. Clone and install

```bash
# from repository root
cd frontend && pnpm install && cd ..
cd backend && uv sync && cd ..
```

## 2. Configure environment

`frontend/.env.local`:

```text
DATABASE_URL=postgres://...neon...
AGENT_URL=http://127.0.0.1:8000
SESSION_COOKIE_NAME=pmh_session
```

`backend/.env`:

```text
OPENAI_API_KEY=sk-...
ALLOWED_ORIGIN=http://localhost:3000
```

## 3. Apply the database schema

```bash
cd frontend
pnpm prisma migrate dev --name init
```

Confirm two tables exist in Neon: `Visitor`, `ScoreSubmission`.

## 4. Run both services

In two terminals:

```bash
# Terminal 1 — FastAPI agent
cd backend
uv run uvicorn agent.main:app --reload --port 8000

# Terminal 2 — Next.js
cd frontend
pnpm dev
```

Open `http://localhost:3000`.

## 5. Smoke test (manual, ~2 minutes)

1. **First check (US1)**: When prompted, answer "12" passwords and "18 months"
   for the oldest. Expect a single score card (yellow band ~ around 60), a
   list of ≤ 5 fixes, and an encouraging tone in the message above the card.
2. **Mobile (Constitution V)**: DevTools → device toolbar → iPhone SE
   (375 × 667). Repeat the flow; verify no horizontal scroll, all controls
   reachable, score card readable.
3. **Validation (Constitution III)**: Try `-3` for password count and `lots`
   for the oldest age. Expect a friendly clarification message — never a stack
   trace or framework error.
4. **History (US2)**: Refresh and run a *better* combo (e.g., 8 passwords, 3
   months). Expect the new card plus the previous score visible somewhere on
   the page, and an explicit acknowledgement of the improvement.
5. **Empty-history state**: Open an incognito window and run the first check.
   The history area should show a friendly first-time message, not an empty
   state.
6. **Structured JSON (Constitution VII)**: From DevTools Network, inspect
   `POST /api/checks` and the upstream `POST /agent/score`. Both responses
   must be valid JSON conforming to `contracts/bff-checks.schema.json` and
   `contracts/agent-score.schema.json` respectively.

## 6. Run automated checks

```bash
# Backend
cd backend
uv run pytest

# Frontend unit + component
cd ../frontend
pnpm test

# Frontend e2e (Playwright at 375 × 812)
pnpm exec playwright test --project=mobile
```

All three must pass before opening a PR.

## 7. Deploy

- Push to a feature branch; Vercel previews build automatically.
- Verify the smoke test (step 5) on the preview URL using a real phone before
  merging.
- Production deploys merge to `main` after PR approval.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Chat shows "Something went wrong on our side." | Agent unreachable or returned a non-conforming JSON. | Check FastAPI logs; confirm `OPENAI_API_KEY` is set; look for `AGENT_FORMAT_ERROR` in BFF logs. |
| Score is `null` or `NaN` on the card | BFF forwarded a non-2xx without mapping it to the friendly envelope. | Check `lib/errors.ts`; the BFF must always return `{ code, message }` on failure. |
| History is empty for a returning user | Cookie cleared, or third-party-cookie blocking. | Open the same incognito window again; cookies are first-party `SameSite=Lax`, but private modes may clear them. |
| Tests fail on `agent-score.schema.json` contract | The Pydantic model and the JSON schema drifted. | Regenerate and commit; the contract test should remain the gate. |
