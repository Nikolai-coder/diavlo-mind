# Changelog

## 3.2.0 — 2026-02-10

- **Removed** the legacy synchronous client API `kestrel.sync`. It was deprecated in 3.0.0. Use `kestrel.aio`.
- **Changed** the minimum supported Python version to 3.11.
- **Changed** the default of `max_batch_size` from 500 to 250 to reduce tail latency. The configuration page will be updated.
- **Fixed** a crash when `log_format = json` was combined with `log_level = debug`.

## 3.1.0 — 2025-10-14

- **Added** `log_format = json`.
- **Added** the `kestrel doctor` command.
- **Changed** the minimum supported Python version to 3.10.

## 3.0.0 — 2025-06-30

- **Changed** the default port from 7400 to 7411.
- **Changed** the default of `max_batch_size` from 1000 to 500.
- **Deprecated** `kestrel.sync`. It keeps working in 3.0 and 3.1 and prints a warning.
- **Renamed** command-line flags; see the migration guide.
- Minimum supported Python version: 3.9.

## 2.8.0 — 2024-02-19

- Last release of the 2.x line.
