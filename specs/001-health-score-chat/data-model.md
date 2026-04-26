# Phase 1 Data Model: Password Health Score Chat

**Owner**: Next.js application via Prisma. The FastAPI agent does **not** read
or write this database.

## Entities

### `Visitor`

A single browser-cookie identity. No PII; only the random session token.

| Field          | Type             | Notes                                            |
|----------------|------------------|--------------------------------------------------|
| `id`           | `String` (CUID)  | Primary key.                                     |
| `sessionToken` | `String` UNIQUE  | The 128-bit URL-safe value carried in `pmh_session`. |
| `createdAt`    | `DateTime`       | Server time; defaults to `now()`.                |
| `lastSeenAt`   | `DateTime`       | Updated on every `POST /api/checks`.             |

**Validation rules**
- `sessionToken` must be 22+ chars URL-safe base64. Generated server-side; never
  taken from user input.

**Indexes**
- Unique on `sessionToken`.

---

### `ScoreSubmission`

One completed health check.

| Field                       | Type                | Notes                                                    |
|-----------------------------|---------------------|----------------------------------------------------------|
| `id`                        | `String` (CUID)     | Primary key.                                             |
| `visitorId`                 | `String` (FK)       | References `Visitor.id`. Indexed.                        |
| `passwordCount`             | `Int`               | Validated 0 ≤ n ≤ 10000.                                 |
| `oldestPasswordAgeMonths`   | `Int`               | Validated 0 ≤ n ≤ 600 (50 years).                        |
| `score`                     | `Int`               | 0–100, computed by `scoring.py`.                         |
| `band`                      | `Enum(HEALTHY, OKAY, CRITICAL)` | Derived from `score` per spec thresholds.    |
| `recommendations`           | `Json`              | Array of `{ id, title }`, ≤ 5 items.                     |
| `createdAt`                 | `DateTime`          | Server time; immutable.                                  |

**Validation rules** (Constitution III)
- `passwordCount` integer, range `[0, 10000]`. Out of range → `INVALID_INPUT`.
- `oldestPasswordAgeMonths` integer, range `[0, 600]`. Out of range →
  `INVALID_INPUT`.
- `score` integer, range `[0, 100]`. Computed; never accepted from client.
- `band` MUST match the score per the formula in research.md §R5.
- `recommendations` length ≤ 5.

**Indexes**
- `(visitorId, createdAt DESC)` — primary access path for "list my history".
- Pruning trigger logic (research.md §R9) keeps at most 50 rows per visitor.

---

## Prisma Schema (target)

```prisma
generator client {
  provider = "prisma-client-js"
}

datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

enum Band {
  HEALTHY
  OKAY
  CRITICAL
}

model Visitor {
  id            String           @id @default(cuid())
  sessionToken  String           @unique
  createdAt     DateTime         @default(now())
  lastSeenAt    DateTime         @default(now())
  submissions   ScoreSubmission[]
}

model ScoreSubmission {
  id                       String   @id @default(cuid())
  visitor                  Visitor  @relation(fields: [visitorId], references: [id], onDelete: Cascade)
  visitorId                String
  passwordCount            Int
  oldestPasswordAgeMonths  Int
  score                    Int
  band                     Band
  recommendations          Json
  createdAt                DateTime @default(now())

  @@index([visitorId, createdAt(sort: Desc)])
}
```

## State / lifecycle

- Visitor is created lazily on the first `POST /api/checks` without a cookie.
- `ScoreSubmission` is append-only from the user's perspective. The pruning
  job (research.md §R9) deletes only the oldest rows beyond 50 per visitor; it
  is not part of the user-visible state machine.
- There is no "draft" state — partial chat answers (only one question
  answered) are kept in client memory until both are present. Spec edge case
  "user closes the app before answering the second" maps to "no row inserted".
