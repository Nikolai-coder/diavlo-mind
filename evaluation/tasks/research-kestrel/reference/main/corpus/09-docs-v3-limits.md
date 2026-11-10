# Limits (Kestrel DB 3.x documentation)

*Last updated 2026-02-12. Applies to 3.2.*

| Limit | Default | Configurable |
|---|---|---|
| Maximum client connections | 1024 | yes, `max_connections` |
| Maximum key size | 512 bytes | no |
| Maximum value size | 8 MiB | yes, `max_value_bytes` |
| Maximum databases per server | 64 | no |

Connections above the limit are refused with error `E_TOO_MANY_CONNECTIONS`.
