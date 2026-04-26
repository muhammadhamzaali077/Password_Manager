# Feature Specification: Password Health Score Chat

**Feature Branch**: `001-health-score-chat`
**Created**: 2026-04-26
**Status**: Draft
**Input**: User description: "Build a chat app where the user tells the agent how many passwords they have and how old the oldest one is. The agent calculates a health score from 0 to 100 and shows it in a color coded card. Green is healthy, yellow is okay, red is critical. The agent gives a short list of what to fix first. It remembers past scores so the user can see if they are improving. The whole thing should feel encouraging not scary."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Get a health score and top fixes from a quick chat (Priority: P1)

A user opens the app and is greeted by a friendly agent in a chat interface.
The agent asks two questions: how many passwords they currently manage and
how old the oldest one is. After answering, the user sees a single
color-coded card with a 0–100 score (green = healthy, yellow = okay,
red = critical) and a short ordered list of fixes to tackle first. The
language stays warm and encouraging — even when the score is low.

**Why this priority**: This is the entire MVP. Without it, the product
delivers nothing. Anything else (history, repeat sessions, exports) only
matters once a user can complete one check end-to-end.

**Independent Test**: Open the app as a brand-new user, answer both
questions in the chat, and verify that within the same session a single
color-coded score card and a list of at most five prioritized fixes are
displayed, and that no message uses alarming or shaming language.

**Acceptance Scenarios**:

1. **Given** a new user has just opened the app, **When** the agent asks
   how many passwords they have and how old the oldest one is and the
   user answers both, **Then** the agent presents one card showing a
   numeric score from 0 to 100, the matching band color (green/yellow/
   red), and a short ordered list of recommended fixes.
2. **Given** the user has answered both questions, **When** the score
   falls in the red band, **Then** the agent's wording remains
   encouraging and constructive (no alarmist or shaming phrasing) and
   frames the fix list as next steps the user can take.
3. **Given** the user enters a non-numeric or implausible answer (e.g.,
   "lots", -3, 1,000,000), **When** they submit, **Then** the agent
   responds with a friendly clarification asking for a usable number,
   without scolding the user.

---

### User Story 2 - Track progress across past sessions (Priority: P2)

A user who has completed at least one health check before returns to the
app. They see (or can easily reach) their previous scores alongside
their newest one, so they can tell at a glance whether they are
improving. The agent acknowledges the change — celebrating gains and
gently encouraging momentum when scores have not improved yet.

**Why this priority**: Repeat use is what turns a one-shot novelty into
a habit. It also delivers on the explicit "remembers past scores so the
user can see if they are improving" requirement. It depends on US1 but
is independently testable once US1 is in place.

**Independent Test**: Complete two separate health checks in the same
browser at different times with deliberately different inputs. Verify
that the second session shows both the new score and the previous one
(at minimum the most recent prior score), and that the agent comments
on whether the user has improved, held steady, or slipped — always in
encouraging tone.

**Acceptance Scenarios**:

1. **Given** a returning user with at least one past score recorded,
   **When** they complete a new health check, **Then** the result view
   shows the new score and at least the most recent previous score so
   the user can compare them.
2. **Given** a returning user whose new score is higher than their last
   recorded score, **When** the result is presented, **Then** the agent
   includes a short congratulatory acknowledgement of the improvement.
3. **Given** a returning user whose new score is lower than their last
   recorded score, **When** the result is presented, **Then** the agent
   acknowledges the change in encouraging language and points to the
   top fix as a next step (no shaming).
4. **Given** a brand-new user with no prior score, **When** they finish
   their first check, **Then** the history view either is hidden or
   shows a friendly first-time message instead of an empty state.

---

### Edge Cases

- User enters `0` for password count — agent treats this as "you haven't
  started yet" and gently encourages them to add their first password,
  rather than calculating a misleading score.
- User enters an extremely large password count (e.g., > 10,000) — agent
  asks them to confirm rather than silently accepting an outlier.
- User enters `0` for oldest password age (a brand-new password) — agent
  treats this as a positive signal in the score calculation.
- User submits non-numeric input or a vague phrase ("a lot", "old") —
  agent responds with a friendly clarification (validation triggered).
- User answers one question and then closes the app before answering
  the second — partial answers are NOT saved to history; only completed
  checks are recorded.
- User has cleared their browser data — past scores are gone; the app
  treats them as a new user without error and without surfacing
  technical detail about why history is missing.
- User performs many checks in quick succession — only completed
  checks count toward history; rapid duplicate submissions do not
  inflate the trend line.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST greet the user in a chat interface and ask,
  in plain language, (a) how many passwords they currently have and
  (b) how old the oldest password is.
- **FR-002**: System MUST accept and validate both inputs before
  computing a score; non-numeric, negative, or implausibly large values
  MUST be rejected with a friendly retry message.
- **FR-003**: System MUST compute a single health score in the range
  0–100 from the two inputs, where a higher score reflects better
  password hygiene (more recent oldest password, reasonable count).
- **FR-004**: System MUST classify each score into exactly one of three
  bands: Healthy (green), Okay (yellow), Critical (red).
- **FR-005**: System MUST display the score and band together in a
  single card whose color matches the band.
- **FR-006**: System MUST display, alongside the score card, a short
  ordered list of no more than five recommended fixes, ordered by
  estimated impact (most impactful first).
- **FR-007**: System MUST persist each completed check (inputs, score,
  band, timestamp) so it can be shown later as part of the user's
  history.
- **FR-008**: System MUST display past scores to returning users so
  they can see whether they are improving across sessions.
- **FR-009**: System MUST phrase all user-facing messages —
  including those reporting Critical (red) scores or rejecting invalid
  input — in encouraging, non-alarming, non-shaming language.
- **FR-010**: System MUST allow the user to start a fresh health check
  at any time without having to clear history or restart the app.
- **FR-011**: System MUST acknowledge improvement explicitly when a new
  score exceeds the user's most recent prior score, and MUST frame a
  decline as a next step rather than a failure.
- **FR-012**: System MUST present a graceful, friendly empty state for
  first-time users (no past scores) and for users whose history is no
  longer available.

### Key Entities *(include if feature involves data)*

- **Score Submission**: A single completed health check. Captures the
  user's reported password count, the user's reported age of the oldest
  password, the computed score (0–100), the resulting band
  (Healthy / Okay / Critical), the prioritized list of fixes shown,
  and the timestamp the check was completed.
- **Score History**: The ordered collection of Score Submissions
  belonging to one user (scoped per browser by default — see
  Assumptions). Used to show progress over time and to compare a new
  submission to the most recent prior submission.
- **Recommendation**: A single actionable fix suggested by the agent
  (e.g., "rotate the oldest password", "stop reusing passwords across
  sites"). Each recommendation has a short user-facing title and an
  impact ranking that determines its position in the fix list.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A first-time user can go from opening the app to seeing
  their score card and fix list in under 60 seconds.
- **SC-002**: 100% of result screens display the score, the matching
  band color, and a fix list of no more than five items.
- **SC-003**: In tone-review checks, at least 90% of agent messages
  across all bands (Healthy, Okay, Critical) are rated "encouraging"
  or "supportive" — and 0% are rated "alarming" or "shaming" — by
  reviewers.
- **SC-004**: At least 90% of returning users in usability testing can
  locate their previous score next to their new score without external
  help.
- **SC-005**: After three completed sessions, at least 95% of users in
  usability testing can correctly state whether their score went up,
  down, or stayed the same versus their previous session.
- **SC-006**: No user-facing error or validation message in the
  experience contains raw technical content (stack traces, internal
  identifiers, framework jargon).

## Assumptions

- **History is persisted per browser by default**: Score history is
  stored locally in the user's browser so that no sign-in is required.
  If the user clears their browser data or uses a different device,
  their history will not appear there. This keeps the experience
  friction-free and on-tone (encouraging, not gated).
- **Default score bands**: In the absence of a stronger signal, the
  bands are Healthy ≥ 80, Okay 50–79, Critical < 50. These thresholds
  are tunable later without changing the contract of this spec.
- **"Oldest password age"** is captured as a duration the user can
  express naturally (e.g., "6 months", "3 years"); the agent
  interprets the value into a normalized internal unit before scoring.
- **Recommendation catalogue**: The set of possible fixes is a small
  fixed catalogue of common best-practice tips (rotate old passwords,
  remove reuse, enable MFA, replace weak passwords, etc.). The agent
  selects up to five items per session, ordered by estimated impact
  given the user's inputs. The exact catalogue contents are an
  implementation concern and not fixed by this spec.
- **Score formula is deterministic for given inputs**: The same
  (password count, oldest age) pair always yields the same score and
  band, so a user can validate progress meaningfully across sessions.
- **Single-user, no multi-tenant or shared state**: Each browser is
  treated as one user; no accounts, no team / shared views in this
  feature.
