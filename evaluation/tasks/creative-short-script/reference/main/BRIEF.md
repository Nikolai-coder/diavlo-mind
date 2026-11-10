# Brief: launch short for "Lantern Tide"

*Lantern Tide* is a cosy puzzle game by a two-person studio. You guide paper lanterns down a river at night by redirecting the current; each level is a single screen. It launches this **Friday** on **PC**, **Switch** and **Android**.

We need a vertical video script of exactly 30 seconds for the launch. One idea only: *the river does the moving, you only bend it*. Tone: calm and curious. The video will loop, so the ending must lead back into the opening.

## Deliverable 1 — `script.json`

```json
{
  "title": "…",
  "duration": 30.0,
  "beats": [
    {"start": 0.0, "end": 2.5, "visual": "what we see", "voiceover": "what is said", "caption": "on-screen text"}
  ]
}
```

Rules (a *word* is anything separated by spaces):

- **Timing.** Between 8 and 12 beats. The first starts at `0.0`, the last ends at `30.0`, and each beat starts exactly where the previous one ends. Every beat lasts at least 1.5 and at most 4.0 seconds. Times have at most one decimal place.
- **Hook.** The first beat's caption is a question (it ends with `?`) of at most 6 words.
- **Captions.** Each caption is a single line of at most 32 characters and at most 6 words. All captions are different from each other, with one exception: the last beat's caption repeats the first beat's caption exactly, so the loop closes.
- **Title.** At most 60 characters, and it contains `Lantern Tide`.
- **Voiceover.** At most 12 words per beat and at most 75 words in total. The voiceover may be an empty string in at most two beats.
- **Visual.** Every beat describes what is on screen in at least 10 characters.
- **Facts.** The script must say that the game launches on Friday, and must name all three platforms. Captions or voiceover both count.
- **Call to action.** The word `wishlist` appears in exactly one caption, and that beat starts at `22.0` or later.
- **Banned words.** Our style guide forbids `ultimate`, `epic`, `insane` and `best`, in any capitalisation, anywhere in the title, captions or voiceover.

## Deliverable 2 — `captions.srt`

A SubRip file with one cue per beat, in order. Cue numbers start at 1. Each cue's time range equals the beat's start and end, written as `HH:MM:SS,mmm --> HH:MM:SS,mmm`, and the cue text is the beat's caption. Cues are separated by one blank line.
