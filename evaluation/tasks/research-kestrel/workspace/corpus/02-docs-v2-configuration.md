# Configuration (Kestrel DB 2.x documentation — archived)

*Archived 2024-02-19. This page describes version 2.8 and is no longer maintained.*

## Network

| Setting | Default |
|---|---|
| `port` | `7400` |
| `bind` | `127.0.0.1` |
| `tls_cert` | *(none)* |

## Write path

| Setting | Default |
|---|---|
| `max_batch_size` | `1000` |
| `fsync` | `always` |

Version 2.8 requires Python 3.8 or later for the client library.
