# Phase 0 Research: Password Health Score Chat

**Status**: Complete. All `NEEDS CLARIFICATION` items resolved below.

## R1. Hosting topology for the FastAPI agent

**Decision**: Deploy the FastAPI agent as a Vercel Python serverless function
co-located in the same Vercel project as the Next.js app, exposed under
`/api/agent/*`. The Next.js BFF calls it via an internal HTTPS request using
`process.env.AGENT_URL` (defaults to a same-origin path in production).

**Rationale**:
- The user explicitly chose Vercel, and Vercel supports Python serverless
  functions out of the box.
- One project, one deploy pipeline — keeps secrets (OpenAI key) and CORS rules
  in a single place.
- The agent is stateless and short-running (sub-3 s per call); the serverless
  cold-start trade-off is acceptable for an early product.

**Alternatives considered**:
- *Separate host (Fly.io / Render) for FastAPI*: more flexibility on long-lived
  connections, but adds a deploy target and a CORS surface for no current
  benefit.
- *Rewriting the agent in TypeScript* to consolidate on Node: rejected because
  Constitution I mandates Python + FastAPI for the backend.

## R2. Prisma in a mixed Python/TypeScript codebase

**Decision**: Use Prisma in TypeScript only, owned by the Next.js app. The
FastAPI agent has **no** database access at all.

**Rationale**:
- Prisma's TS client is the mature, first-class one. Prisma Client Python is
  community-maintained and not aligned with the user's "Prisma" instruction in
  spirit.
- A clean separation — Next.js owns persistence and identity; the agent owns
  scoring and recommendations — keeps the agent stateless and trivially
  testable.
- The agent's input is just `{ password_count, oldest_password_age_months }`;
  it doesn't need database context to score.

**Alternatives considered**:
- *Prisma Client Python on the agent*: rejected for maturity and to avoid
  schema-management duplication.
- *FastAPI accesses Postgres directly via SQLAlchemy*: rejected because
  schema-of-record would now live in Python while Prisma still owns migrations
  on the Next.js side — two sources of truth.

## R3. Session cookie strategy

**Decision**: Issue an HTTP-only, `SameSite=Lax`, `Secure` cookie named
`pmh_session` containing a 128-bit URL-safe random token (no PII). On the first
request without a cookie, the BFF generates a token, persists a `Visitor` row,
and sets the cookie with a 1-year `Max-Age`. The token is the join key for
score history.

**Rationale**:
- Encouraging tone (FR-009) → no sign-in wall.
- HTTP-only blocks JS access (XSS hygiene). `SameSite=Lax` blocks CSRF on
  cross-site POSTs while still allowing top-level navigation.
- 1-year expiry mirrors standard analytics-cookie lifetime; long enough to
  show meaningful improvement trends.
- Anonymous token is sufficient because there's no account to recover.

**Alternatives considered**:
- *Signed JWT*: unnecessary; we don't carry claims.
- *LocalStorage-only history*: rejected because the spec assumes server-side
  persistence (the data-model would otherwise be unused), and because clearing
  cookies/localStorage anyway is acknowledged in the spec as a graceful empty
  state.

## R4. Forcing structured JSON from the OpenAI Agents SDK

**Decision**: Define a single Pydantic model `AgentScoreResponse` and pass it
to the Agents SDK via `output_type=AgentScoreResponse`. The agent must emit
exactly that shape. The FastAPI route returns the validated Pydantic instance
serialised to JSON; if validation fails, the route maps to a friendly error
envelope (`code: AGENT_FORMAT_ERROR`).

**Rationale**:
- Constitution VII requires structured JSON. Using `output_type` forces the
  SDK to honour a JSON schema derived from Pydantic, eliminating prose drift.
- Pydantic gives validation for free on both directions: input from the BFF
  (`HealthCheckRequest`) and output from the model (`AgentScoreResponse`).

**Alternatives considered**:
- *Free-text + regex parsing*: rejected; brittle and violates Constitution VII.
- *Tool-call coercion*: equivalent rigor, but `output_type` is the SDK's
  idiomatic path and produces the same JSON-schema constraint.

## R5. Scoring formula (deterministic, simple, encouraging)

**Decision**: A pure function in `backend/src/agent/scoring.py`:

```text
score = round(clamp(
  100
  - 0.20 * max(0, password_count - 50)        # too many secrets is fatigue
  - 0.50 * max(0, oldest_password_age_months) # rotation pressure
  + bonus_for_few_recent(password_count, oldest_password_age_months),
  0, 100
))
```

Score thresholds (from spec Assumptions):
- Healthy (green): `score >= 80`
- Okay (yellow): `50 <= score < 80`
- Critical (red): `score < 50`

**Rationale**:
- Deterministic (FR-003 plus spec Assumption "score formula is deterministic
  for given inputs"): the same inputs always produce the same score, so the
  user can validate progress.
- Two coefficients, both interpretable: oldest-password age dominates because
  rotation is the highest-impact lever; sheer count contributes after a
  reasonable threshold.
- Computed in code, not in the LLM. The LLM is responsible only for tone and
  recommendation phrasing; the score is auditable.

**Alternatives considered**:
- *Letting the LLM compute the score*: rejected — non-deterministic and
  un-auditable.
- *Multi-factor formula with weak/reused/MFA flags*: rejected for now; the
  spec's MVP captures only two inputs.

## R6. Recommendation catalogue and ranking

**Decision**: A static catalogue in `backend/src/agent/recommendations.py`
with ~8–12 entries, each tagged with `(impact_weight, applies_when)`. The
agent reads the catalogue, filters by `applies_when(inputs, score)`, sorts by
`impact_weight` desc, takes the top 5, and includes them verbatim in the JSON
response. The LLM is not asked to invent recommendations — only to wrap them
in encouraging copy at the message level.

**Rationale**:
- Determinism + reviewability: a security-sensitive list of "what to do next"
  shouldn't drift between runs.
- Tone (FR-009) is enforced once, in the catalogue copy, and verified by tests.

**Alternatives considered**:
- *LLM-generated recommendations*: rejected — risks hallucinating advice and
  breaking the 5-item cap.

## R7. Validation duplication: BFF and agent

**Decision**: The Next.js BFF re-validates the inbound JSON with a Zod schema
(`HealthCheckRequest.zod.ts`) before forwarding to the agent, which validates
again with Pydantic. Both schemas are generated from the same JSON Schema in
`specs/001-health-score-chat/contracts/agent-score.schema.json`.

**Rationale**:
- Constitution III: backend is authoritative; client checks aren't trusted.
  The BFF's check protects the agent (fewer wasted LLM calls); the agent's
  check is the system of record.
- One JSON Schema → both bindings ⇒ no drift between the two validation
  layers.

**Alternatives considered**:
- *Backend-only validation*: works, but wastes an LLM call on garbage input.

## R8. Testing strategy

**Decision**:
- Frontend: Vitest for utilities and React Testing Library for components;
  Playwright for the chat flow at the 375 × 812 viewport.
- Backend: pytest with `pytest-asyncio`; a contract test that loads
  `agent-score.schema.json` and asserts that `AgentScoreResponse.model_json_schema()`
  is a superset (so the schema and Pydantic model can't drift); a deterministic
  unit test for `scoring.py`; an integration test for the route with the
  OpenAI client mocked via `respx`.
- Tone-review check: a small lint test in the backend that runs each
  recommendation copy through a forbidden-words list (e.g., "stupid", "fail",
  "danger", "hacked").

**Rationale**:
- Mobile (Constitution V) needs an enforcement gate, hence the 375 × 812
  Playwright viewport.
- A contract test pinned to the JSON Schema prevents Constitution VII drift.

## R9. Pruning history

**Decision**: On each `POST /api/checks`, after inserting the new row, the
BFF runs `DELETE FROM ScoreSubmission WHERE visitorId = $1 AND id NOT IN (...)`
to retain the most recent 50 submissions per visitor. This keeps page-load
fast for long-time users and bounds storage.

**Rationale**: 50 entries is well above the threshold needed to perceive a
trend (typical user runs the check ≤ once a week) and stays small enough to
render in one shadcn card without virtualisation.

## R10. Error envelope shape

**Decision**: Every non-2xx response from both services follows:

```json
{ "code": "STABLE_UPPER_SNAKE", "message": "User-safe sentence." }
```

Reserved codes: `INVALID_INPUT`, `AGENT_TIMEOUT`, `AGENT_FORMAT_ERROR`,
`RATE_LIMITED`, `INTERNAL_ERROR`. The frontend renders `message` directly to
the chat surface (Constitution IV); the `code` is only used for analytics and
client-side branching.

**Rationale**: A two-field envelope is the smallest contract that satisfies
Constitution IV and Constitution VII at once.
