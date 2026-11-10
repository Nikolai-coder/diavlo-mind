# Notification service — design

## Context

Product teams need one service to notify users by email, SMS and push (R1). The service must respect per-user preferences and quiet hours (R2), never deliver twice for the same idempotency key (R3), retry failures with backoff and keep a replayable dead-letter store (R4), stay under each provider's rate limit (R5), keep an audit trail per notification (R6), hand 99% of non-held notifications to a provider within 60 seconds at 50 per second (R7), and show operators queue depth, failure rates and the oldest pending age (R8).

Three constraints shape everything: one Linux VM with 4 vCPU and 8 GB (C1), PostgreSQL as the only storage with no broker (C2), and a team of two Python developers (C3). The drivers are therefore: durability and exactly-once intake inside PostgreSQL, a shared rate limit across worker processes, and as few moving parts as possible.

Capacity check for R7: a provider call takes roughly 200 ms, so one sender handles 5 per second. Four dispatcher processes with eight sender threads each give about 160 per second, three times the target. With a one-second polling interval, hand-off happens within a few seconds. Assumption: the channel mix stays inside the provider limits; if more than 10 SMS per second arrive for a 10-per-second provider, R5 wins and the SMS backlog grows, which R8 makes visible.

## Components

| Component | Responsibility | Depends on | Covers |
|---|---|---|---|
| `api` | Validates requests and stores each one exactly once per idempotency key | store, audit | R1, R3 |
| `scheduler` | Applies preferences and quiet hours to decide when a notification is due | store, audit | R2 |
| `dispatcher` | Claims due notifications, sends them, schedules retries or dead-letters | store, rate-limiter, channel-adapters, audit | R1, R4, R7 |
| `rate-limiter` | Token bucket per provider, shared by all dispatcher processes | store | R5 |
| `channel-adapters` | One provider call per channel; classifies outcomes | — | R1 |
| `store` | PostgreSQL schema and the queries that claim work | — | R3, R4 |
| `audit` | Append-only state-change log, queryable by notification id | store | R6 |
| `ops-console` | Metrics, dead-letter inspection and replay | store, audit | R4, R8 |

The dependency graph is a tree rooted in `store`; nothing depends on `api`, `dispatcher` or `ops-console`, so there are no cycles. Each component runs inside one of five systemd services (one API, four dispatchers; the scheduler and the ops console are modules of the API process).

## Data flow

1. **Intake.** A caller posts a notification with an idempotency key. In one transaction `api` inserts the row with `ON CONFLICT DO NOTHING` on the unique key and writes the first audit entry. A repeated key returns the original id and inserts nothing (R3).
2. **Scheduling.** In the same transaction `scheduler` reads the user's preferences. A disabled channel ends the notification as `suppressed`. Otherwise it sets `due_at`: now, or the end of quiet hours unless the request is urgent (R2).
3. **Dispatch.** Each dispatcher polls `claim_due`, which selects pending rows with `due_at <= now` using `FOR UPDATE SKIP LOCKED` and marks them `sending`. For each row it asks `rate-limiter` for a permit (R5), calls the adapter, and records the outcome.
4. **Outcome.** Success marks the row `delivered`. A transient failure sets `due_at` to now plus `30s × 2^attempt` with jitter; after the fifth attempt, or on a permanent failure, the row moves to `dead_letters` (R4). Every transition goes through `audit.record` in the same transaction (R6).
5. **Operations.** `ops-console` reads aggregate queries for the three metrics (R8) and replays a dead letter by inserting a fresh pending row linked to the original (R4).

Failure of the database stops intake with a 503 and stops dispatch without changing any row. Failure of a provider affects only its channel: its rows back off while other channels continue.

## Interfaces

- **`POST /notifications`** (api, external callers). Input: idempotency_key, user_id, channel, template, params, urgent. Output: 202 with the id, or 200 with the original id for a repeated key. Errors: 400 invalid payload, 503 database unavailable.
- **`claim_due(limit, now)`** (store → dispatcher). Returns locked, due rows marked `sending`. Error: database unavailable, in which case no state changes.
- **`acquire(provider, permits)`** (rate-limiter → dispatcher). Returns permits granted and the wait until the next one. Errors: unknown provider; database unavailable, which grants zero permits.
- **`send(notification)`** (channel-adapters → dispatcher). Returns a provider message id. Errors: `TransientError`, `PermanentError`, `ProviderRateLimited`.
- **`record(id, from, to, detail)`** (audit → all writers). Written in the caller's transaction; a failure rolls the state change back.
- **`GET /ops/metrics`, `POST /ops/dead-letters/{id}/replay`** (ops-console, operators). Errors: 404 unknown dead letter, 409 already replayed.

## Decisions

- **D1 — Queue.** A PostgreSQL table claimed with `FOR UPDATE SKIP LOCKED`, instead of LISTEN/NOTIFY alone or an external broker. C2 rules the broker out; the table is durable and comfortably handles the load. Cost: polling delay and vacuuming. Revisit above roughly 500 per second or with more than one host.
- **D2 — Rate limit.** A token-bucket row per provider in PostgreSQL, instead of an in-process limiter or fixed sleeps. Several processes share one limit, so the state must be shared. Cost: one short transaction per batch. Revisit if lock contention shows in measurements.
- **D3 — Idempotency.** A unique index with `ON CONFLICT DO NOTHING`, instead of check-then-insert or payload hashing. Only the database makes concurrent duplicates collide. Cost: keys need a retention job.
- **D4 — Processes.** One API process and four dispatcher processes under systemd, instead of a single asyncio process or Celery. It fits C1 and is simple for the team in C3. Cost: capacity changes are manual.

## Risks

- **Queue bloat** slows polling → partial index, nightly archiving; validated by a two-hour load test at 50 per second.
- **Provider outage** causes a retry storm → backoff with jitter and a per-channel circuit breaker; validated by fault injection on one adapter.
- **Crash between provider accept and commit** could duplicate → the notification id is the provider idempotency token and `sending` rows are reconciled on restart; validated by a kill -9 test.
- **Time-zone mistakes** in quiet hours → IANA zones and UTC arithmetic; validated by daylight-saving unit tests.

## Test strategy

- **Unit:** quiet-hours calculation including daylight-saving changes (R2); backoff schedule and the five-attempt cut-off (R4); token-bucket arithmetic (R5).
- **Integration with a real PostgreSQL:** fifty concurrent requests with one idempotency key produce one row and one delivery (R3); two dispatchers never claim the same row; every state change has an audit row (R6).
- **Contract:** each adapter against a fake provider for success, transient, permanent and rate-limited answers (R1).
- **Load:** 50 per second for two hours; assert p99 hand-off under 60 seconds and providers never above their limits (R5, R7).
- **Operational:** metrics match direct SQL counts (R8); a dead letter can be replayed exactly once (R4); the whole service restarts cleanly on the single VM (C1) using only PostgreSQL (C2) and the Python tool chain (C3).
