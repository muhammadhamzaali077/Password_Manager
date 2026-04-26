<!--
SYNC IMPACT REPORT
==================
Version change: (template placeholders) -> 1.0.0
Bump rationale: Initial ratification. The prior file contained only template
placeholders; this is the first concrete adoption of the constitution, so the
version starts at 1.0.0 (not a PATCH/MINOR off an unset baseline).

Modified principles:
  - [PRINCIPLE_1_NAME] -> I. Defined Tech Stack
  - [PRINCIPLE_2_NAME] -> II. Function-Level Documentation
  - [PRINCIPLE_3_NAME] -> III. Strict Input Validation (NON-NEGOTIABLE)
  - [PRINCIPLE_4_NAME] -> IV. Friendly, User-Facing Errors
  - [PRINCIPLE_5_NAME] -> V. Mobile-Compatible by Default
  - (added)            -> VI. shadcn/ui for Cards and Progress Bars
  - (added)            -> VII. Structured JSON from the Python Agent

Added sections:
  - Technology Stack & UX Constraints (was [SECTION_2_NAME])
  - Development Workflow & Quality Gates (was [SECTION_3_NAME])

Removed sections: none

Templates requiring updates:
  - .specify/templates/plan-template.md       -> ✅ no change needed
    (Constitution Check gate is generic; per-feature plans now resolve it
    against the seven principles below.)
  - .specify/templates/spec-template.md       -> ✅ no change needed
    (Existing FR / edge-case sections already accommodate validation and
    error-messaging requirements.)
  - .specify/templates/tasks-template.md      -> ✅ no change needed
    (Sample task categories cover validation, error handling, and polish;
    no principle-driven task type was added or removed.)
  - .specify/templates/agent-file-template.md -> ✅ no change needed

Follow-up TODOs: none
-->

# Password Manager Health Check Constitution

## Core Principles

### I. Defined Tech Stack

The frontend MUST be built with Next.js using TypeScript. The backend MUST be
built with Python and FastAPI. No alternative frameworks or languages may be
introduced for the application's frontend or backend without an amendment to
this constitution.

Rationale: A single, agreed stack keeps the project understandable for every
contributor and avoids fragmenting infrastructure, tooling, and review
expertise across competing toolchains.

### II. Function-Level Documentation

Every function — across both the Next.js/TypeScript frontend and the FastAPI
Python backend — MUST carry a comment that explains its purpose. TypeScript
functions MUST have a JSDoc/TSDoc-style comment; Python functions MUST have
a docstring. Trivial getters and one-line lambdas are NOT exempt; if it is a
named function, it has a comment.

Rationale: This codebase is a security tool; reviewers need to know the
intent of every routine without reverse-engineering it from the body.

### III. Strict Input Validation (NON-NEGOTIABLE)

All user-supplied input MUST be validated. Validation MUST happen on the
backend (authoritative, e.g. via Pydantic models in FastAPI) and SHOULD also
happen at the frontend boundary for fast feedback. Invalid input MUST be
rejected before it reaches business logic. The backend MUST NOT trust any
client-side check.

Rationale: Password-manager health data is sensitive; un-validated input is
the most common path to injection, corruption, and information leaks.

### IV. Friendly, User-Facing Errors

Errors shown to the user MUST be plain-language and actionable. Raw
exception messages, stack traces, framework jargon, and internal identifiers
MUST NOT be surfaced to the UI. Backend errors MUST be mapped to a stable
error code plus a human-readable message before they leave the API.

Rationale: Most users are not engineers. A scary error makes them abandon
the health check; a clear one tells them what to do next.

### V. Mobile-Compatible by Default

Every page, flow, and component MUST be usable on a mobile viewport (down to
375px wide) without horizontal scrolling, clipped content, or unreachable
controls. Mobile is a first-class target, not an afterthought; a feature is
not "done" until it works on mobile.

Rationale: People most often check password-related concerns from the phone
they were just locked out on.

### VI. shadcn/ui for Cards and Progress Bars

Card and progress-bar UI MUST be implemented with shadcn/ui components.
Hand-rolled card or progress-bar components MUST NOT be introduced. Other
UI primitives MAY use shadcn/ui as well, but cards and progress bars are
mandatory.

Rationale: The health check leans heavily on score cards and progress
indicators; standardising those two component types keeps the look,
accessibility, and mobile behaviour consistent everywhere.

### VII. Structured JSON from the Python Agent

The Python (FastAPI) agent MUST always return structured JSON. Plain-text
bodies, HTML responses, and free-form strings inside `200 OK` payloads are
NOT permitted for application endpoints. Every response — success or error
— MUST conform to a documented JSON schema with named fields, so the
Next.js client can parse it deterministically.

Rationale: A typed contract between the agent and the frontend is what
makes input validation, friendly errors, and component rendering reliable
end to end.

## Technology Stack & UX Constraints

- **Frontend**: Next.js + TypeScript. Strict TypeScript MUST be enabled
  (`"strict": true` in `tsconfig.json`); `any` is discouraged and MUST be
  justified inline when used.
- **Backend**: Python + FastAPI. Request and response bodies MUST be
  defined as Pydantic models so that validation (Principle III) and the
  JSON contract (Principle VII) are enforced by the framework, not by ad
  hoc code.
- **UI components**: shadcn/ui is the default component library. Cards and
  progress bars MUST come from shadcn/ui (Principle VI).
- **Responsiveness**: Layouts MUST be tested at a 375px-wide viewport
  before a feature is considered complete (Principle V).
- **Error contract**: Every API error response MUST include at minimum a
  machine-readable `code` and a user-safe `message` field. The frontend
  MUST render `message` directly to the user (Principle IV).

## Development Workflow & Quality Gates

- **Constitution Check**: Every implementation plan MUST verify that its
  design respects the seven principles above before Phase 0 research and
  again after Phase 1 design. Violations MUST be recorded in the plan's
  Complexity Tracking table with explicit justification, or the plan MUST
  be revised.
- **Code review**: Reviewers MUST reject PRs that introduce a function
  without a comment/docstring, ship un-validated user input, surface raw
  errors to the UI, break the 375px mobile layout, replace shadcn/ui
  cards or progress bars with custom equivalents, or return non-JSON /
  unstructured responses from the FastAPI agent.
- **Definition of done**: A feature is done only when (a) backend
  validation is in place, (b) error responses are mapped to friendly
  messages, (c) the UI has been verified on a mobile viewport, and
  (d) every new function carries a comment.

## Governance

This constitution supersedes ad hoc conventions and informal agreements.
When a practice conflicts with this document, this document wins until it
is amended.

**Amendments**: Any change to this constitution MUST be proposed as a PR
that (a) updates this file, (b) updates the version line per the policy
below, (c) updates the Sync Impact Report comment at the top, and
(d) propagates the change into the dependent templates under
`.specify/templates/` where applicable.

**Versioning policy** (semantic):
- **MAJOR**: A principle is removed or redefined in a backward-incompatible
  way, or governance rules are materially weakened.
- **MINOR**: A new principle or section is added, or existing guidance is
  materially expanded.
- **PATCH**: Wording, clarifications, typo fixes, and other non-semantic
  refinements that do not change what is required.

**Compliance review**: At minimum, the Constitution Check in
`.specify/templates/plan-template.md` MUST be exercised on every feature
plan. Reviewers MAY also call out drift during code review at any time.

**Version**: 1.0.0 | **Ratified**: 2026-04-26 | **Last Amended**: 2026-04-26
