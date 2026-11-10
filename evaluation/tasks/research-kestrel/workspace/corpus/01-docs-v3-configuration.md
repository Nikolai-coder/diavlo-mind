# Configuration (Kestrel DB 3.x documentation)

*Last updated 2025-11-04. Applies to 3.0 and later unless a version is stated.*

Kestrel DB reads `kestrel.toml` from the working directory. Every setting can also be given as an environment variable with the prefix `KESTREL_`.

## Network

| Setting | Default | Notes |
|---|---|---|
| `port` | `7411` | Changed from `7400` in 3.0. Environment: `KESTREL_PORT`. |
| `bind` | `127.0.0.1` | Use `0.0.0.0` to accept remote connections. |
| `cert` | *(none)* | Path to the TLS certificate. |

## Write path

| Setting | Default | Notes |
|---|---|---|
| `max_batch_size` | `500` | Maximum number of operations in one batch. |
| `fsync` | `always` | `always`, `interval` or `never`. |
| `flush_interval_ms` | `200` | Used when `fsync = interval`. |

## Logging

| Setting | Default | Notes |
|---|---|---|
| `log_level` | `info` | `debug`, `info`, `warn`, `error`. |
| `log_format` | `text` | `text` or `json`. |
