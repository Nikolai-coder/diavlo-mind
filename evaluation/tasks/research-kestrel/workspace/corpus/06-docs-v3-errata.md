# Documentation errata (Kestrel DB 3.x)

*Published 2026-04-02.*

The following statements in the version 3 documentation are wrong and will be corrected in the next documentation release.

1. **Configuration page, `max_batch_size`.** The page gives the default as `500`. Since 3.2.0 the default is `250`.
2. **Configuration page, `flush_interval_ms`.** The description should read "used when `fsync = interval`"; an older revision said "used when `fsync = always`".
