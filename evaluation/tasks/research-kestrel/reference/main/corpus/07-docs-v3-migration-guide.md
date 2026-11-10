# Migrating from 2.x to 3.x

*Published 2025-06-30.*

## Client API

`kestrel.sync` is deprecated in 3.0 and will be removed in a later 3.x release. Move to the asynchronous client:

| 2.x | 3.x |
|---|---|
| `kestrel.sync.Client(host, port)` | `kestrel.aio.connect(host, port)` |
| `client.put(key, value)` | `await client.put(key, value)` |
| `client.batch(ops)` | `await client.batch(ops)` |

## Command-line flags

| 2.x flag | 3.x flag |
|---|---|
| `--tls-cert` | `--cert` |
| `--tls-key` | `--key` |
| `--listen-port` | `--port` |

The old flags are rejected by version 3 with an error that names the new flag.

## Configuration file

`tls_cert` in `kestrel.toml` becomes `cert`. The default port changes; see the configuration page.
