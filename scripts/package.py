#!/usr/bin/env python3
"""Build the release archives into dist/.

    dist/DIAVLO-MIND-FABLE-EDITION.zip   whole project, top folder DIAVLO-MIND/
    dist/diavlo-mind.zip                 lean skill for upload (claude.ai, ChatGPT, Skills API),
                                         top folder diavlo-mind/ with SKILL.md directly inside
    dist/SHA256SUMS.txt

    python scripts/package.py

Archives are deterministic for a given tree (sorted entries, fixed timestamps).
Python 3.9+, standard library only.
"""
from __future__ import annotations

import hashlib
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import List

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
SKIP_PARTS = {".git", "dist", "__pycache__", "runs", ".pytest_cache", ".diavlo-mind", ".DS_Store"}
LEAN_DIRS = ["agents", "workflows", "prompts", "memory", "adapters"]
LEAN_FILES = ["SKILL.md", "README.md", "LICENSE", "VERSION"]
LEAN_SCRIPTS = ["dm_state.py", "dm_packet.py", "dm_schema.py", "select_mode.py", "dm_llm.py", "dm_orchestrate.py"]
FIXED_TIME = (2026, 1, 1, 0, 0, 0)


def tracked_files() -> List[Path]:
    """Files to ship: git's view when available, otherwise a filtered walk."""
    try:
        out = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard"], cwd=str(ROOT),
                             capture_output=True, text=True, check=True).stdout
        files = [ROOT / line for line in out.splitlines() if line.strip()]
    except (OSError, subprocess.CalledProcessError):
        files = [p for p in ROOT.rglob("*") if p.is_file()]
    keep = []
    for path in files:
        relative = path.relative_to(ROOT)
        if not path.is_file() or any(part in SKIP_PARTS for part in relative.parts) or path.suffix == ".pyc":
            continue
        keep.append(path)
    return sorted(keep)


def lean_files() -> List[Path]:
    chosen = [ROOT / name for name in LEAN_FILES if (ROOT / name).is_file()]
    chosen += [ROOT / "scripts" / name for name in LEAN_SCRIPTS]
    everything = tracked_files()
    for folder in LEAN_DIRS:
        chosen += [p for p in everything if p.relative_to(ROOT).parts[0] == folder]
    return sorted(set(chosen))


def write_zip(target: Path, top: str, files: List[Path]) -> None:
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            name = f"{top}/{path.relative_to(ROOT).as_posix()}"
            info = zipfile.ZipInfo(name, FIXED_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o755 if path.suffix == ".py" else 0o644) << 16
            archive.writestr(info, path.read_bytes())


def verify(target: Path, top: str) -> int:
    with zipfile.ZipFile(target) as archive:
        bad = archive.testzip()
        if bad:
            raise SystemExit(f"error: corrupt entry {bad} in {target.name}")
        names = archive.namelist()
    if f"{top}/SKILL.md" not in names:
        raise SystemExit(f"error: {target.name} has no {top}/SKILL.md")
    if any(not name.startswith(top + "/") for name in names):
        raise SystemExit(f"error: {target.name} has entries outside {top}/")
    return len(names)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def utf8_stdio() -> None:
    """Write UTF-8 regardless of the platform's default encoding (Windows pipes use a legacy code page)."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def main() -> int:
    utf8_stdio()
    DIST.mkdir(exist_ok=True)
    builds = [
        (DIST / "DIAVLO-MIND-FABLE-EDITION.zip", "DIAVLO-MIND", tracked_files()),
        (DIST / "diavlo-mind.zip", "diavlo-mind", lean_files()),
    ]
    sums = []
    for target, top, files in builds:
        write_zip(target, top, files)
        count = verify(target, top)
        digest = sha256(target)
        sums.append(f"{digest}  {target.name}")
        print(f"{target.relative_to(ROOT).as_posix()}: {count} files, {target.stat().st_size / 1024:.0f} KB, sha256 {digest[:16]}…")
    (DIST / "SHA256SUMS.txt").write_text("\n".join(sums) + "\n", encoding="utf-8")
    print(f"{(DIST / 'SHA256SUMS.txt').relative_to(ROOT).as_posix()} written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
