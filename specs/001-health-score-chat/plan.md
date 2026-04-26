# Implementation Plan: Password Health Score Chat

**Branch**: `001-health-score-chat` | **Date**: 2026-04-26 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-health-score-chat/spec.md`

## Summary

Deliver a chat experience that asks the user two questions (password count, age
of the oldest password), computes a 0–100 health score, and returns a single
color-coded score card plus a short ordered fix list. History is persisted per
visitor (session cookie → Postgres row) so returning users can see whether they
are improving. Tone is encouraging across all bands.

Technical approach: Next.js 15 (TypeScript, Tailwind, shadcn/ui) on Vercel
serves the chat UI and the data layer (Prisma → Neon Postgres). A separate
Python FastAPI service hosts the agent, built on the OpenAI Agents SDK with
`gpt-4o-mini` and forced to return structured JSON via a Pydantic response
schema. The Next.js BFF owns input re-validation, session-cookie identity, and
persistence; the agent stays stateless.

## Technical Context

**Language/Version**:
- Frontend: TypeScript 5.x on Next.js 15 (App Router, Node 20 runtime)
- Backend: Python 3.12 (managed with `uv`)

**Primary Dependencies**:
- Frontend: Next.js 15, React 19, Tailwind CSS, shadcn/ui (Card, Progress,
  Button, Input, ScrollArea), Prisma Client, Zod (request validation)
- Backend: FastAPI, Pydantic v2, OpenAI Agents SDK (`openai-agents`), `httpx`
  (timeouts), `python-dotenv`

**Storage**: Neon Postgres (serverless), accessed exclusively from Next.js
through Prisma. The FastAPI agent has **no** database access — it is stateless.

**Testing**:
- Frontend: Vitest (unit), React Testing Library (component), Playwright (e2e
  including mobile viewport at 375 × 812)
- Backend: pytest, `pytest-asyncio`, `respx`/`httpx` mocks for the OpenAI client
- Contract: shared JSON schema fixtures consumed by both sides

**Target Platform**: Modern evergreen browsers on desktop and mobile. Mobile
viewport down to 375 px wide is a first-class target (Constitution V).

**Project Type**: Web application — `frontend/` (Next.js) + `backend/` (FastAPI
agent service). Plus `contracts/` for the shared schemas the two sides agree on.

**Performance Goals**:
- Chat round-trip (UI submit → score card visible): p95 ≤ 3.0 s on 4G.
- First contentful paint on mobile (Vercel edge cache hit): ≤ 1.5 s.
- Agent JSON response size: ≤ 4 KB (small list, no prose dump).

**Constraints**:
- Mobile-compatible at 375 px wide (Constitution V).
- All API responses are structured JSON (Constitution VII).
- All user-facing errors are friendly, never raw (Constitution IV).
- All input is validated server-side (Constitution III); a Pydantic model on
  FastAPI and a Zod schema on the Next.js BFF.
- Encouraging tone is enforced via the agent's system prompt and a static
  recommendation catalogue with human-tuned copy.
- Recommendations: at most 5 items per response.

**Scale/Scope**:
- Single user per browser (session cookie). No multi-tenant, no teams.
- Score history bounded to the most recent 50 submissions per visitor (older
  rows pruned on insert).
- Expected concurrent traffic: low (early product); design for a few hundred
  concurrent visitors, not thousands.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Compliance | Evidence |
|-----------|------------|----------|
| I. Defined Tech Stack | PASS | Next.js 15 + TS frontend, FastAPI + Python backend; no other frameworks introduced. |
| II. Function-Level Documentation | PASS | Codebase convention enforced in code review; ESLint `jsdoc/require-jsdoc` and a Ruff `D101/D103` ruleset will surface missing comments. |
| III. Strict Input Validation (NON-NEGOTIABLE) | PASS | Pydantic models on the FastAPI agent (`HealthCheckRequest`); Zod schemas on the Next.js BFF for the same payload before forwarding. |
| IV. Friendly, User-Facing Errors | PASS | Both services emit `{ "code": <stable_id>, "message": <user_safe_text> }` envelopes; agent system prompt forbids alarmist phrasing. |
| V. Mobile-Compatible by Default | PASS | Tailwind responsive design; Playwright e2e suite runs at 375 × 812; layout reviewed at 375 px. |
| VI. shadcn/ui for Cards and Progress Bars | PASS | Score card uses shadcn `Card`; the score readout uses shadcn `Progress`. No hand-rolled equivalents. |
| VII. Structured JSON from the Python Agent | PASS | Agent endpoints declare Pydantic response models; OpenAI Agents SDK is run with `response_format` constrained to the Pydantic schema. |

**Gate result**: PASS. No violations to justify; Complexity Tracking section
below remains empty.

## Project Structure

### Documentation (this feature)

```text
specs/001-health-score-chat/
├── plan.md              # This file
├── research.md          # Phase 0 output — decisions and rationales
├── data-model.md        # Phase 1 output — entities and Prisma model
├── quickstart.md        # Phase 1 output — local dev / smoke test guide
├── contracts/           # Phase 1 output — agent + BFF JSON schemas
│   ├── agent-score.schema.json
│   ├── bff-checks.schema.json
│   └── error-envelope.schema.json
├── checklists/
│   └── requirements.md
└── tasks.md             # (created later by /speckit.tasks)
```

### Source Code (repository root)

```text
backend/
├── pyproject.toml             # managed by uv
├── uv.lock
├── src/
│   └── agent/
│       ├── __init__.py
│       ├── main.py            # FastAPI app entrypoint + CORS
│       ├── routes/
│       │   └── score.py       # POST /agent/score
│       ├── schemas.py         # Pydantic request / response models
│       ├── prompts.py         # System prompt (encouraging tone)
│       ├── recommendations.py # Static catalogue + impact ranking
│       ├── scoring.py         # Pure scoring formula (deterministic)
│       └── errors.py          # Error envelope helpers
└── tests/
    ├── unit/
    │   ├── test_scoring.py
    │   └── test_recommendations.py
    ├── contract/
    │   └── test_agent_score_contract.py
    └── integration/
        └── test_score_route.py

frontend/
├── package.json
├── prisma/
│   └── schema.prisma
├── src/
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx                # Chat page (mobile-first)
│   │   └── api/
│   │       ├── checks/
│   │       │   └── route.ts        # POST: persist + forward to agent
│   │       └── history/
│   │           └── route.ts        # GET: list past scores for cookie
│   ├── components/
│   │   ├── chat/
│   │   │   ├── ChatPane.tsx
│   │   │   ├── MessageList.tsx
│   │   │   └── PromptInput.tsx
│   │   ├── score/
│   │   │   ├── ScoreCard.tsx       # shadcn Card + Progress
│   │   │   └── HistoryList.tsx
│   │   └── ui/                     # shadcn-generated primitives
│   ├── lib/
│   │   ├── prisma.ts
│   │   ├── session.ts              # cookie issue / read
│   │   ├── agent-client.ts         # typed fetch to backend
│   │   ├── validation.ts           # Zod schemas
│   │   └── errors.ts               # friendly error mapper
│   └── styles/
│       └── globals.css
└── tests/
    ├── unit/                       # Vitest
    │   └── score-card.test.tsx
    └── e2e/                        # Playwright
        └── chat-flow.spec.ts
```

**Structure Decision**: Web application (Option 2). Two top-level apps,
`frontend/` and `backend/`, deployed independently. Next.js is deployed as a
Vercel project; the FastAPI agent is deployed as a separate Vercel Python
serverless function under the same project (decision recorded in research.md
§ Hosting). The contracts folder under the spec directory is the source of
truth for the JSON schemas that bridge them.

## Complexity Tracking

> Constitution Check passed with no violations; this section is intentionally empty.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| _none_    | _n/a_      | _n/a_                               |
