# Getting started with Kestrel DB in ten minutes

*Posted on 22 September 2024 on a personal blog.*

I have been playing with Kestrel DB for a few weeks and wanted to share a quick start.

Install the client, start the server and connect on the default port, which is **7400**:

```python
from kestrel.sync import Client

client = Client("localhost", 7400)
client.put("greeting", "hello")
```

The synchronous API in `kestrel.sync` is the simplest way in, and it is what I recommend for scripts.

A tip: batches can hold up to 1000 operations by default, so you rarely need to tune `max_batch_size`.

Kestrel DB is maintained by a small team at Northwind Labs, and they are quick to answer issues.
