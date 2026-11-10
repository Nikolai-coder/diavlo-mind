#!/usr/bin/env python3
"""Hidden checks for creative-short-script. Usage: check.py <workspace>

Checks the hard production constraints only. Whether the script is any good is
a matter for evaluation/rubrics/creative.md.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))
from checklib import Checks, read_json, read_text, visible_files, workspace_arg  # noqa: E402

WORK = workspace_arg()
checks = Checks()
BANNED = ["ultimate", "epic", "insane", "best"]
EPS = 1e-9

data = read_json(WORK / "script.json")
data = data if isinstance(data, dict) else {}
raw_beats = data.get("beats") if isinstance(data.get("beats"), list) else []
FIELDS = ("start", "end", "visual", "voiceover", "caption")


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


well_formed = [b for b in raw_beats if isinstance(b, dict) and all(k in b for k in FIELDS) and number(b["start"]) and number(b["end"])
               and all(isinstance(b[k], str) for k in ("visual", "voiceover", "caption"))]
beats = well_formed if len(well_formed) == len(raw_beats) else []
captions = [b["caption"] for b in beats]
voices = [b["voiceover"] for b in beats]
title = data.get("title") if isinstance(data.get("title"), str) else ""


def words(text):
    return text.split()


shape = []
if not title:
    shape.append("title missing")
if not (number(data.get("duration")) and abs(data["duration"] - 30.0) < EPS):
    shape.append(f"duration is {data.get('duration')!r}, not 30.0")
if not beats:
    shape.append("beats missing or malformed")
elif not 8 <= len(beats) <= 12:
    shape.append(f"{len(beats)} beats")
short_visuals = [i + 1 for i, b in enumerate(beats) if len(b["visual"].strip()) < 10]
if short_visuals:
    shape.append(f"visual too short in beats {short_visuals}")
checks.add("script-shape", "R1", not shape, "; ".join(shape), kind="requirement")

timing = []
if beats:
    if abs(beats[0]["start"]) > EPS:
        timing.append(f"first beat starts at {beats[0]['start']}")
    if abs(beats[-1]["end"] - 30.0) > EPS:
        timing.append(f"last beat ends at {beats[-1]['end']}")
    for index, beat in enumerate(beats):
        length = beat["end"] - beat["start"]
        if not 1.5 - EPS <= length <= 4.0 + EPS:
            timing.append(f"beat {index + 1} lasts {length:.2f}s")
        for key in ("start", "end"):
            if abs(beat[key] * 10 - round(beat[key] * 10)) > 1e-6:
                timing.append(f"beat {index + 1} {key} has more than one decimal")
        if index and abs(beat["start"] - beats[index - 1]["end"]) > EPS:
            timing.append(f"beat {index + 1} does not start where beat {index} ends")
checks.add("timing", "R2", bool(beats) and not timing, "; ".join(timing[:4]))

hook = captions[0] if captions else ""
checks.add("hook-question", "R3", bool(hook) and hook.rstrip().endswith("?") and len(words(hook)) <= 6, f"hook={hook!r}")

bad = [f"beat {i + 1} ({len(c)} chars, {len(words(c))} words)" for i, c in enumerate(captions)
       if len(c) > 32 or len(words(c)) > 6 or "\n" in c or not c.strip()]
checks.add("caption-limits", "R4", bool(captions) and not bad, "; ".join(bad[:4]))

loop_ok = len(captions) >= 2 and captions[-1] == captions[0]
inner = captions[:-1]
unique_ok = len(set(inner)) == len(inner)
checks.add("captions-unique-and-loop", "R5", loop_ok and unique_ok,
           ("last caption does not repeat the first" if not loop_ok else "") + ("; duplicate captions" if not unique_ok else ""))

checks.add("title", "R6", bool(title) and len(title) <= 60 and "Lantern Tide" in title, f"title={title!r} ({len(title)} chars)")

voice_problems = [f"beat {i + 1} has {len(words(v))} words" for i, v in enumerate(voices) if len(words(v)) > 12]
total = sum(len(words(v)) for v in voices)
if total > 75:
    voice_problems.append(f"{total} words in total")
empty = sum(1 for v in voices if not v.strip())
if empty > 2:
    voice_problems.append(f"{empty} beats without voiceover")
checks.add("voiceover-limits", "R7", bool(beats) and not voice_problems, "; ".join(voice_problems[:4]))

spoken = " ".join([title] + captions + voices)
found = [word for word in BANNED if re.search(rf"\b{word}\b", spoken, re.IGNORECASE)]
checks.add("no-banned-words", "R8", bool(beats) and not found, "found: " + ", ".join(found) if found else "")

with_cta = [i for i, c in enumerate(captions) if re.search(r"\bwishlist\b", c, re.IGNORECASE)]
cta_ok = len(with_cta) == 1 and beats[with_cta[0]]["start"] >= 22.0 - EPS
checks.add("call-to-action", "R9", cta_ok, f"wishlist in captions of beats {[i + 1 for i in with_cta]}"
           + (f", starting at {beats[with_cta[0]]['start']}" if len(with_cta) == 1 else ""))


def stamp(seconds):
    ms = round(seconds * 1000)
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


srt = read_text(WORK / "captions.srt")
srt_problems = []
if srt is None:
    srt_problems.append("captions.srt missing")
elif not beats:
    srt_problems.append("no valid beats to compare with")
else:
    blocks = [block.strip("\n") for block in re.split(r"\n\s*\n", srt.replace("\r\n", "\n").strip("\n")) if block.strip()]
    if len(blocks) != len(beats):
        srt_problems.append(f"{len(blocks)} cues for {len(beats)} beats")
    for index, (block, beat) in enumerate(zip(blocks, beats), 1):
        lines = block.split("\n")
        if len(lines) != 3:
            srt_problems.append(f"cue {index} has {len(lines)} lines")
            continue
        if lines[0].strip() != str(index):
            srt_problems.append(f"cue {index} is numbered {lines[0].strip()!r}")
        if lines[1].strip() != f"{stamp(beat['start'])} --> {stamp(beat['end'])}":
            srt_problems.append(f"cue {index} timing {lines[1].strip()!r}")
        if lines[2].strip() != beat["caption"].strip():
            srt_problems.append(f"cue {index} text differs from the caption")
checks.add("srt-matches-beats", "R10", not srt_problems, "; ".join(srt_problems[:4]))

said = " ".join(captions + voices)
missing = [word for word in ("Friday", "PC", "Switch", "Android") if not re.search(rf"\b{word}\b", said, re.IGNORECASE)]
checks.add("facts-present", "R11", bool(beats) and not missing, "missing: " + ", ".join(missing) if missing else "", kind="requirement")

extra = [name for name in visible_files(WORK) if name not in ("BRIEF.md", "script.json", "captions.srt")]
checks.add("no-extra-files", "R12", bool(data) and not extra, "extra files: " + ", ".join(extra[:5]) if extra else "", kind="scope")

checks.emit()
