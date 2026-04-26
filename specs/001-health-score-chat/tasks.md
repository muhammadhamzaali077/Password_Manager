---

description: "Task list for Password Health Score Chat (feature 001)"
---

# Tasks: Password Health Score Chat

**Input**: Design documents from `/specs/001-health-score-chat/`
**Prerequisites**: plan.md (✓), spec.md (✓), research.md (✓), data-model.md (✓), contracts/ (✓), quickstart.md (✓)

**Tests**: Test tasks ARE included because the plan (research.md §R8) committed
to a testing strategy and Constitution VII relies on a contract test to prevent
schema drift. If you don't want them, strike each task with a `[P]` `tests/`
path before running `/speckit.implement`.

**Organization**: Tasks are grouped by user story so each can be implemented
and shipped independently.

## Format: `[ID] [P?] [Story] Description with file path`

- **[P]**: Different files, no dependencies on incomplete tasks → safe to run in parallel.
- **[Story]**: `[US1]` or `[US2]`. Setup, Foundational, and Polish phases have no story label.
- File paths are absolute relative to the repo root (`frontend/`, `backend/`, `specs/`).

## Path Conventions

This is a **web application** (Option 2 in plan.md):

- **Frontend (Next.js 15 + TS)**: `frontend/`
- **Backend (FastAPI + Python, uv)**: `backend/`
- **Shared contracts**: `specs/001-health-score-chat/contracts/` (source of truth)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Bring the two empty apps into existence and wire up tooling.

- [X] T001 Create the top-level project layout per plan.md `Project Structure` (create `frontend/`, `backend/`, and a repo-root `.gitignore` covering `node_modules/`, `.next/`, `__pycache__/`, `.venv/`, `.env*`, `dist/`, `.pytest_cache/`, `playwright-report/`)
- [ ] T002 Initialize the Next.js 15 app with TypeScript, Tailwind CSS, and the App Router in `frontend/` (run `pnpm create next-app@latest frontend --ts --tailwind --app --no-src-dir=false`; commit the resulting `frontend/package.json`, `frontend/tsconfig.json` with `"strict": true`, `frontend/tailwind.config.ts`, `frontend/postcss.config.js`)
- [ ] T003 [P] Install and configure shadcn/ui in `frontend/` and generate the `Card`, `Progress`, `Button`, `Input`, and `ScrollArea` primitives into `frontend/src/components/ui/`
- [ ] T004 [P] Initialize the FastAPI agent skeleton with `uv` in `backend/` (`uv init`; declare Python 3.12; add `fastapi`, `uvicorn[standard]`, `pydantic>=2`, `openai-agents`, `httpx`, `python-dotenv`, `respx`, `pytest`, `pytest-asyncio` in `backend/pyproject.toml`; run `uv sync` so `backend/uv.lock` is committed)
- [X] T005 [P] Configure ESLint with `eslint-plugin-jsdoc` and the `jsdoc/require-jsdoc` rule for all named functions in `frontend/.eslintrc.json` (Constitution II)
- [X] T006 [P] Enable Ruff `D101`, `D103` (missing docstring) rules and Black-compatible formatting in `backend/pyproject.toml` under `[tool.ruff]` (Constitution II)
- [X] T007 [P] Add Vitest + React Testing Library to `frontend/` (`frontend/vitest.config.ts`, `frontend/tests/setup.ts`)
- [X] T008 [P] Add Playwright to `frontend/` and define a `mobile` project at viewport 375×812 in `frontend/playwright.config.ts` (Constitution V)
- [X] T009 [P] Add pytest config + `respx` HTTP mock fixtures in `backend/pyproject.toml` (`[tool.pytest.ini_options]` with `asyncio_mode = "auto"`)
- [X] T010 Create environment templates `frontend/.env.local.example` (with `DATABASE_URL`, `AGENT_URL`, `SESSION_COOKIE_NAME`) and `backend/.env.example` (with `OPENAI_API_KEY`, `ALLOWED_ORIGIN`) per quickstart.md §2

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Persistence, identity, validation, and the JSON-contract layer that every story depends on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T011 Add Prisma to `frontend/` (`pnpm add -D prisma`, `pnpm add @prisma/client`, run `pnpm prisma init`); set the `postgresql` provider and `DATABASE_URL` env binding in `frontend/prisma/schema.prisma`
- [X] T012 Author the Prisma schema in `frontend/prisma/schema.prisma`: `enum Band { HEALTHY OKAY CRITICAL }`, `model Visitor`, `model ScoreSubmission` with the `@@index([visitorId, createdAt(sort: Desc)])` exactly as specified in `data-model.md`
- [ ] T013 Generate and apply the initial migration with `pnpm prisma migrate dev --name init` from `frontend/`; commit `frontend/prisma/migrations/`
- [X] T014 [P] Create the Prisma singleton in `frontend/src/lib/prisma.ts` (single `PrismaClient` instance reused across hot reloads)
- [X] T015 [P] Implement session-cookie helpers in `frontend/src/lib/session.ts` per research R3: `getOrCreateVisitor(req, res)` issues a 22+ char URL-safe random token, sets cookie `pmh_session` with `HttpOnly; Secure; SameSite=Lax; Max-Age=31536000`; reuses on subsequent requests
- [X] T016 [P] Implement the friendly error envelope helper in `frontend/src/lib/errors.ts` exporting `toEnvelope(code, message)` and a mapper `friendlyMessageFor(code)`; covers `INVALID_INPUT`, `AGENT_TIMEOUT`, `AGENT_FORMAT_ERROR`, `RATE_LIMITED`, `INTERNAL_ERROR` per `contracts/error-envelope.schema.json` (Constitution IV)
- [X] T017 [P] Copy `specs/001-health-score-chat/contracts/*.schema.json` to `frontend/src/contracts/` and `backend/src/agent/contracts/` so both runtimes can load them at boot for the contract tests
- [X] T018 [P] Create the FastAPI app entrypoint in `backend/src/agent/main.py` with CORS that allows only `ALLOWED_ORIGIN`; mount routes from `backend/src/agent/routes/`
- [X] T019 [P] Implement the error envelope helper in `backend/src/agent/errors.py` exporting `error_response(code, message, status)` returning `JSONResponse({"code": ..., "message": ...}, status_code=status)` (Constitution IV + VII)
- [X] T020 [P] Define Pydantic v2 models in `backend/src/agent/schemas.py`: `Band` (str enum), `Recommendation`, `HealthCheckRequest`, `AgentScoreResponse`, mirroring `specs/001-health-score-chat/contracts/agent-score.schema.json` (Constitution III + VII)

**Checkpoint**: Database is migrated, both apps boot, the JSON contract types exist on each side.

---

## Phase 3: User Story 1 - Get a health score and top fixes from a quick chat (Priority: P1) 🎯 MVP

**Goal**: A new user opens the app, answers two chat questions, and sees a single
color-coded score card plus ≤ 5 prioritized fixes — all in encouraging copy.

**Independent Test**: As a brand-new visitor (incognito), submit `password_count = 12`
and `oldest_password_age_months = 18`. Within the same session a card shows a
0–100 score, the matching band color, and a fix list of ≤ 5 items; no message
contains alarmist or shaming language. (Spec acceptance scenarios US1.1–US1.3.)

### Tests for User Story 1

> Write these tests **first**, ensure they fail before implementation.

- [X] T021 [P] [US1] Contract test in `backend/tests/contract/test_agent_score_contract.py` — load `specs/001-health-score-chat/contracts/agent-score.schema.json` and assert that `AgentScoreResponse.model_json_schema()` is a structural superset (Constitution VII drift gate)
- [X] T022 [P] [US1] Table-driven unit test for the scoring formula in `backend/tests/unit/test_scoring.py` — assert deterministic `(password_count, oldest_password_age_months) → score, band` covering all three bands and the boundary values 0, 50, 80, 100 (research R5)
- [X] T023 [P] [US1] Unit test for the recommendation ranker in `backend/tests/unit/test_recommendations.py` — assert `len(items) <= 5`, items returned in descending impact order, every `title` passes the forbidden-words check (`"stupid"`, `"fail"`, `"danger"`, `"hacked"`, `"shame"`)
- [X] T024 [P] [US1] Integration test in `backend/tests/integration/test_score_route.py` — `POST /agent/score` with the OpenAI client mocked via `respx`; assert response status 200 and JSON body conforms to `agent-score.schema.json` Response definition; assert error envelope on bad input, on upstream timeout, and on upstream non-conforming output
- [X] T025 [P] [US1] Component test in `frontend/tests/unit/score-card.test.tsx` — render `<ScoreCard>` with each band; assert the shadcn `Progress` value matches the score, the card color class matches the band, and ≤ 5 recommendations render

### Implementation for User Story 1

- [X] T026 [P] [US1] Implement the deterministic scoring formula in `backend/src/agent/scoring.py` exporting `compute_score(password_count, oldest_password_age_months) -> tuple[int, Band]` per research R5
- [X] T027 [P] [US1] Implement the recommendation catalogue + ranker in `backend/src/agent/recommendations.py` (8–12 entries with `id`, `title`, `impact_weight`, `applies_when(inputs, score, band) -> bool`); export `pick_recommendations(...) -> list[Recommendation]` returning ≤ 5, sorted by impact desc (research R6)
- [X] T028 [P] [US1] Define the encouraging-tone system prompt and the user-message template in `backend/src/agent/prompts.py` (forbid alarmist phrasing; instruct the model to emit only the JSON shape, not prose) (FR-009 + Constitution IV)
- [X] T029 [US1] Implement the `POST /agent/score` route in `backend/src/agent/routes/score.py`: validate body against `HealthCheckRequest`, call the OpenAI Agents SDK with `gpt-4o-mini` and `output_type=AgentScoreResponse`, override the model's score/band/recommendations with deterministic values from T026 + T027, return the validated `AgentScoreResponse`; on error map to envelopes (`INVALID_INPUT`, `AGENT_TIMEOUT`, `AGENT_FORMAT_ERROR`, `INTERNAL_ERROR`) (depends on T020, T026, T027, T028, T019)
- [X] T030 [US1] Mount the score route in `backend/src/agent/main.py` and wire the `OPENAI_API_KEY` + `ALLOWED_ORIGIN` env loading (depends on T018, T029)
- [X] T031 [P] [US1] Implement the Zod request schema in `frontend/src/lib/validation.ts` mirroring `bff-checks.schema.json` `PostChecksRequest` (integers, ranges 0–10000 and 0–600); export `parsePostChecksRequest(input): PostChecksRequest` (Constitution III)
- [X] T032 [P] [US1] Implement the typed agent client in `frontend/src/lib/agent-client.ts` exporting `requestScore(payload): Promise<AgentScoreResponse>`; uses `process.env.AGENT_URL`, sets a 5 s timeout, validates the response shape against the contract before returning (Constitution VII)
- [X] T033 [US1] Implement the `POST /api/checks` BFF route in `frontend/src/app/api/checks/route.ts`: read/issue session cookie via T015, Zod-validate via T031, forward to `requestScore`, persist a `ScoreSubmission` via Prisma, prune to the 50 newest rows for that visitor (research R9), return the BFF response shape from `bff-checks.schema.json#/definitions/ScoreSubmission` (depends on T011–T017, T031, T032)
- [X] T034 [P] [US1] Build `<ScoreCard>` in `frontend/src/components/score/ScoreCard.tsx` using shadcn `Card` + `Progress`; the card border / accent color is bound to band (`HEALTHY` → green, `OKAY` → yellow, `CRITICAL` → red); renders the score, the agent's `message`, and the ordered recommendation list (Constitution VI)
- [X] T035 [P] [US1] Build the chat surface in `frontend/src/components/chat/` — `ChatPane.tsx`, `MessageList.tsx`, `PromptInput.tsx`; ask the two questions in sequence, accept natural-language answers for the oldest-password age and normalize to integer months client-side, submit on second answer
- [X] T036 [US1] Wire the chat page in `frontend/src/app/page.tsx`: render `<ChatPane>`, on submit call `POST /api/checks`, render `<ScoreCard>` with the response. Mobile-first layout (Tailwind responsive utilities, no horizontal scroll at 375 px) (depends on T033, T034, T035; Constitution V)
- [X] T037 [US1] Friendly error rendering in `frontend/src/app/page.tsx` and `frontend/src/components/chat/MessageList.tsx`: any non-2xx response from `/api/checks` is rendered using `friendlyMessageFor(code)` from T016; raw text and error codes never reach the UI surface (Constitution IV)

**Checkpoint**: User Story 1 is fully functional and independently testable on desktop and at 375 × 812 mobile. MVP-ready.

---

## Phase 4: User Story 2 - Track progress across past sessions (Priority: P2)

**Goal**: A returning visitor sees their new score next to past scores and gets
encouraging copy that explicitly acknowledges improvement, hold, or slip.

**Independent Test**: From the same browser, complete two checks at different
times with deliberately different inputs. The second view shows both the new
score and at least the most recent prior score, and the agent's wording
explicitly acknowledges whether the user improved (US2.2), held steady, or
slipped (US2.3) — always in encouraging tone.

### Tests for User Story 2

- [ ] T038 [P] [US2] Component test in `frontend/tests/unit/history-list.test.tsx` — render `<HistoryList>` with empty data (assert friendly first-time copy, no empty grid), one entry, and many entries; assert chronological order (newest first) and band color classes
- [ ] T039 [P] [US2] Playwright e2e test in `frontend/tests/e2e/chat-flow.spec.ts` (run under the `mobile` project): perform check #1 (12, 18), reload, perform check #2 (8, 3), assert the second view contains both scores and an "improved" acknowledgement; runs at 375 × 812 (Constitution V + spec SC-005)

### Implementation for User Story 2

- [X] T040 [P] [US2] In `frontend/src/app/api/checks/route.ts`, before insert, query the most recent prior `ScoreSubmission` for the visitor and include `previous_score` (or `null`) in the BFF response per `bff-checks.schema.json#/definitions/ScoreSubmission` (depends on T033)
- [X] T041 [US2] Implement the `GET /api/history` BFF route in `frontend/src/app/api/history/route.ts`: read the session cookie via T015, return the visitor's last 50 submissions (`id, score, band, created_at`) as `bff-checks.schema.json#/definitions/GetHistoryResponse`; if there is no cookie, return `{ "history": [] }` (Constitution VII; spec FR-012 empty state)
- [X] T042 [P] [US2] Build `<HistoryList>` in `frontend/src/components/score/HistoryList.tsx`: shadcn-styled list of past scores with band color dots, newest first, with a friendly first-time message when empty; mobile-friendly layout
- [X] T043 [US2] Wire history into the chat page: load `GET /api/history` on mount, append the latest entry after each successful check, render `<HistoryList>` adjacent to / below `<ScoreCard>` so both fit at 375 px (depends on T036, T041, T042)
- [X] T044 [US2] Add the improvement / decline acknowledgement to `frontend/src/app/page.tsx` and / or `frontend/src/components/score/ScoreCard.tsx`: when the BFF response includes a non-null `previous_score`, render an encouraging line above or beneath the card (`+N points since last time` for gains, `next step: <top fix>` for declines, neutral copy for ties) (depends on T040, T036; spec FR-011)

**Checkpoint**: User Stories 1 AND 2 both work independently on mobile and desktop.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect both stories, deploy readiness, and constitutional gate enforcement.

- [X] T045 [P] Add a tone-review unit test in `backend/tests/unit/test_tone.py`: every entry in `recommendations.py`, every line of the system prompt in `prompts.py`, and the `friendlyMessageFor` map (read via a JSON fixture exported from the frontend at build time) is asserted to contain none of the forbidden words `["stupid", "fail", "danger", "hacked", "shame", "idiot"]` and to use second-person encouraging phrasing (Constitution IV + spec SC-003)
- [ ] T046 [P] Add structured request logging (request id, status, error code only) without leaking input values to logs in both `backend/src/agent/main.py` (FastAPI middleware) and `frontend/src/app/api/checks/route.ts` (Constitution IV)
- [ ] T047 [P] Add a per-cookie rate limit (token bucket: 30 requests / 10 minutes) in `frontend/src/app/api/checks/route.ts`; on overflow return the `RATE_LIMITED` envelope (Constitution IV; future-proofing the recommendation flood case)
- [X] T048 [P] Configure Vercel deployment in `vercel.json` at the repo root: Next.js project from `frontend/`, Python serverless functions from `backend/src/agent/`, route `/agent/*` to the FastAPI handler; declare environment variables `DATABASE_URL`, `OPENAI_API_KEY`, `AGENT_URL`, `SESSION_COOKIE_NAME`, `ALLOWED_ORIGIN` (research R1)
- [ ] T049 [P] Run `quickstart.md` §5 smoke checks against a Vercel preview from a real iPhone-sized viewport (375 × 667) and confirm: no horizontal scroll, all controls reachable, validation feedback friendly, structured-JSON conformance in DevTools Network (Constitution V + VII verification)
- [X] T050 Add a repository-root `README.md` linking to `specs/001-health-score-chat/quickstart.md` and listing the env vars; one paragraph per app
- [ ] T051 Run all three test suites end-to-end in CI order: `cd backend && uv run pytest`, `cd frontend && pnpm test`, `cd frontend && pnpm exec playwright test --project=mobile`; all green is required to mark the feature complete

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — can start immediately.
- **Phase 2 (Foundational)**: Depends on Phase 1 — BLOCKS all user stories.
- **Phase 3 (US1)**: Depends on Phase 2.
- **Phase 4 (US2)**: Depends on Phase 2 AND parts of Phase 3 (T033, T036). May start once US1 has a working `POST /api/checks` and a working chat page; can ship behind US1 in the same release.
- **Phase 5 (Polish)**: Depends on Phase 3 (and Phase 4 if shipped).

### User Story Dependencies

- **US1 (P1, MVP)**: Self-contained once Foundational is done; delivers value on its own.
- **US2 (P2)**: Builds on US1's BFF route (T033) and the chat page (T036). T040 modifies the same file as T033 — sequence them.

### Within Each User Story

- Tests (where included) MUST be written and FAIL before the corresponding implementation tasks.
- Models and contracts (Phase 2) before services (Phase 3 implementation).
- Services before route handlers; route handlers before UI wiring.
- Backend deterministic logic (`scoring`, `recommendations`) before the route that consumes it.

### Parallel Opportunities

- All `[P]` tasks within Phase 1 can run in parallel (frontend init, backend init, tooling).
- All `[P]` tasks within Phase 2 can run in parallel once T011–T013 (Prisma) finish.
- All `[P]` US1 test tasks (T021–T025) can run in parallel; same for US1 implementation tasks T026–T028, T031–T032, T034–T035.
- US2 test tasks T038–T039 can run in parallel; T040 and T042 can run in parallel.
- Polish tasks T045–T049 can run in parallel.

---

## Parallel Example: User Story 1

```bash
# Launch all US1 test tasks together (after Phase 2 is done):
Task: "Contract test in backend/tests/contract/test_agent_score_contract.py"     # T021
Task: "Unit test for scoring in backend/tests/unit/test_scoring.py"              # T022
Task: "Unit test for recommendations in backend/tests/unit/test_recommendations.py"  # T023
Task: "Integration test in backend/tests/integration/test_score_route.py"        # T024
Task: "Component test in frontend/tests/unit/score-card.test.tsx"                # T025

# Launch parallel US1 implementation tasks:
Task: "Scoring formula in backend/src/agent/scoring.py"                          # T026
Task: "Recommendation catalogue in backend/src/agent/recommendations.py"         # T027
Task: "System prompt in backend/src/agent/prompts.py"                            # T028
Task: "Zod schema in frontend/src/lib/validation.ts"                             # T031
Task: "Agent client in frontend/src/lib/agent-client.ts"                         # T032
Task: "ScoreCard component in frontend/src/components/score/ScoreCard.tsx"       # T034
Task: "Chat surface in frontend/src/components/chat/"                            # T035
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 (Setup) — T001–T010.
2. Complete Phase 2 (Foundational) — T011–T020.
3. Complete Phase 3 (US1) — T021–T037.
4. **STOP and VALIDATE**: Run the smoke test from `quickstart.md` §5 steps 1–3
   and the test suite from §6. Verify a brand-new visitor can complete the
   flow on mobile in under 60 seconds (SC-001) with friendly tone (SC-003).
5. Deploy to a Vercel preview (T048) and re-validate on a real phone (T049).
   Ship — this is a viable MVP.

### Incremental Delivery

1. Phase 1 + Phase 2 → foundation ready.
2. Phase 3 (US1) → MVP ships. Encouraging tone + score + fix list.
3. Phase 4 (US2) → progress tracking ships. Returning users see growth.
4. Phase 5 (Polish) → tone-review test, rate limiting, structured logging,
   final mobile pass.

### Parallel Team Strategy

With two or three contributors:

- **Backend track** (one dev): T004, T006, T009 in setup → T018–T020 in
  Foundational → T021–T024, T026–T030 in US1.
- **Frontend track** (one dev): T002, T003, T005, T007, T008 in setup →
  T011–T017 in Foundational → T025, T031–T037 in US1, then T038–T044 in US2.
- **Polish / DevOps track** (third dev or shared): T010 → T045–T051.

---

## Notes

- `[P]` = different files, no dependencies on incomplete tasks.
- `[Story]` label maps each task to the user story it serves; setup,
  foundational, and polish tasks have no story label.
- Tests for a given story must be in place and failing before the matching
  implementation tasks; this also ensures the contract test (T021) catches
  any drift between `AgentScoreResponse` and `agent-score.schema.json`.
- Commit after each task or each logical group; with no commits yet on
  branch `001-health-score-chat`, T001's commit will become the baseline.
- Stop at any checkpoint to validate independently (`quickstart.md` §5).
- Avoid: mixing US2 logic into the US1 BFF before T033 is settled (the file
  is modified by both T033 and T040).
