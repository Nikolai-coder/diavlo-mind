# Questions about Kestrel DB

Kestrel DB is a fictional product. Nothing you may know from elsewhere applies: only the files in `corpus/` count.

## Rules

1. `corpus/00-SOURCES.md` says which files are official and which are community content, and gives their dates.
2. Official sources outrank community sources.
3. When official sources disagree, the most recent one wins.
4. If only community sources address a question and they agree, give their claim as the answer with confidence `unconfirmed`.
5. If no source settles a question, or community sources contradict each other with nothing official to decide, the answer is exactly `UNKNOWN` with confidence `unknown`.
6. Never fill a gap with a guess.

## Questions

- **Q1** — What is the default port in Kestrel DB 3.2?
- **Q2** — What is the default value of `max_batch_size` in Kestrel DB 3.2?
- **Q3** — Can an application running on Kestrel DB 3.2 use the `kestrel.sync` API? Answer `yes` or `no`.
- **Q4** — What is the minimum Python version required by Kestrel DB 3.2?
- **Q5** — What is the default value of the `snapshot_interval` setting in Kestrel DB 3.2?
- **Q6** — Who is the current lead maintainer of Kestrel DB?
- **Q7** — Which command-line flag replaces `--tls-cert` in version 3?
- **Q8** — What is the default maximum number of client connections in Kestrel DB 3.2?
- **Q9** — Does Kestrel DB 3.2 run on FreeBSD? Answer `yes` or `no`.

## Answer format

Write `answers.json` as one JSON object with a key for every question:

```json
{
  "Q1": {
    "answer": "the answer as a short string, or UNKNOWN",
    "sources": ["file names from corpus/ that support the answer"],
    "confidence": "confirmed | unconfirmed | unknown",
    "note": "optional: one sentence, for example which source was overruled and why"
  }
}
```

- `confirmed` — stated by an official source that is not overruled by a newer official one.
- `unconfirmed` — stated only by community sources.
- `unknown` — the answer is `UNKNOWN`.
- `sources` lists file names only, for example `03-changelog.md`. For an `UNKNOWN` answer it may be empty.
