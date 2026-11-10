# Brief: notification service

A small SaaS company wants one internal service that every product team calls to notify users. Design it.

## Requirements

- **R1** — Deliver notifications through three channels: email, SMS and push.
- **R2** — Each user has per-channel preferences and quiet hours. A notification that arrives during quiet hours is held and delivered when they end, unless it is marked urgent.
- **R3** — A request that repeats an idempotency key already seen must never cause a second delivery.
- **R4** — A failed delivery is retried with exponential backoff, at most 5 attempts. After that the notification goes to a dead-letter store that operators can inspect and replay.
- **R5** — Each provider has a rate limit (for example 10 SMS per second). The service must never exceed it.
- **R6** — Every state change of a notification is recorded in an audit log that can be queried by notification id.
- **R7** — At a load of 50 notifications per second, 99% of notifications that are not held must be handed to a provider within 60 seconds.
- **R8** — Operators can see queue depth, failure rate per channel and the age of the oldest pending notification.

## Constraints

- **C1** — It runs on a single Linux VM with 4 vCPU and 8 GB of RAM. No managed cloud services and no container orchestrator.
- **C2** — PostgreSQL is the only storage. The team already operates it. No additional datastore and no message broker.
- **C3** — Two developers maintain it, and they write Python only.

## Out of scope

Template editing, marketing campaigns, and the provider accounts themselves.
