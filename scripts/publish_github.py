#!/usr/bin/env python3
"""Publish this folder as a GitHub repository that people can install from.

    python scripts/publish_github.py                  # every step, into <your account>/diavlo-mind, public
    python scripts/publish_github.py --dry-run        # print every step and command, change nothing
    python scripts/publish_github.py --private
    python scripts/publish_github.py --steps prepare  # only rewrite URLs, rebuild, validate, test, package

Needs git and the GitHub CLI (gh) signed in: `gh auth login`.

Steps, in order. Each one can be repeated safely:

    prepare    put the account name where the owner placeholder is, rebuild the prompt tiers, run the
               validator (release mode), the unit tests and the benchmark self-test, build the archives
    commit     commit whatever changed (on the first run: the initial commit)
    create     create the repository on GitHub if it does not exist yet
    push       push the main branch
    metadata   set description, topics, features and issue labels from .github/repo-metadata.json
    release    create release v<VERSION> with the archives from dist/ (skipped when it exists)

Commits made by this script use your GitHub no-reply address unless you pass --identity git,
so your private e-mail address does not end up in a public history.

Python 3.9+, standard library only.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parent.parent
OWNER_TOKEN = "__GITHUB_OWNER__"
DEFAULT_REPO = "diavlo-mind"
STEPS = ["prepare", "commit", "create", "push", "metadata", "release"]
# Files that mention the placeholder on purpose (they look for it or replace it).
KEEP_TOKEN = {"scripts/validate.py", "scripts/publish_github.py"}
SKIP_PARTS = {".git", "dist", "__pycache__", "runs", ".pytest_cache", ".diavlo-mind", "node_modules"}
LABELS = [
    ("framework-failure", "d73a4a", "A model following the framework did the wrong thing"),
    ("benchmark-result", "0e8a16", "A benchmark run on some model or environment"),
    ("proposal", "1d76db", "Proposed change to rules, procedures, agents, prompts or tasks"),
]
OWNER_RE = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?")
REPO_RE = re.compile(r"[A-Za-z0-9._-]{1,100}")


class PublishError(Exception):
    """A step could not be completed; the message says what to do next."""


class Runner:
    """Runs commands, or only prints them in a dry run."""

    def __init__(self, dry_run: bool) -> None:
        self.dry_run = dry_run
        self.planned: List[str] = []

    @staticmethod
    def show(command: Sequence[str]) -> str:
        return " ".join(part if re.fullmatch(r"[\w@%+=:,./-]+", part) else json.dumps(part, ensure_ascii=False)
                        for part in command)

    def read(self, command: Sequence[str], cwd: Path = ROOT) -> Tuple[int, str, str]:
        """Run a command that changes nothing. Runs even in a dry run."""
        try:
            done = subprocess.run(list(command), cwd=str(cwd), capture_output=True, text=True,
                                  encoding="utf-8", errors="replace")
        except FileNotFoundError:
            return 127, "", f"{command[0]}: program not found"
        return done.returncode, done.stdout.strip(), done.stderr.strip()

    def change(self, command: Sequence[str], cwd: Path = ROOT, ok_if: Sequence[str] = ()) -> bool:
        """Run a command that changes something. Returns False when it failed in a way listed in ok_if."""
        line = self.show(command)
        self.planned.append(line)
        print(f"    $ {line}")
        if self.dry_run:
            return True
        try:
            done = subprocess.run(list(command), cwd=str(cwd), capture_output=True, text=True,
                                  encoding="utf-8", errors="replace")
        except FileNotFoundError as exc:
            raise PublishError(f"{command[0]}: program not found") from exc
        if done.returncode == 0:
            return True
        output = (done.stderr.strip() or done.stdout.strip())
        if any(marker.lower() in output.lower() for marker in ok_if):
            return False
        raise PublishError(f"command failed (exit {done.returncode}): {line}\n{output[-1500:]}")


# --------------------------------------------------------------------------
# Pure helpers (unit-tested)
# --------------------------------------------------------------------------

def project_files(root: Path) -> List[Path]:
    """Every file that belongs to the project, without git internals, caches and build output."""
    out = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if path.is_file() and not any(part in SKIP_PARTS for part in relative.parts):
            out.append(path)
    return out


def replace_owner(root: Path, owner: str, repo: str = DEFAULT_REPO, previous_owner: Optional[str] = None,
                  write: bool = True) -> List[str]:
    """Replace the owner placeholder (or a previous owner's repository path) in every text file.

    Returns the relative paths that contain something to replace. Binary files and the files in
    KEEP_TOKEN are left alone. Line endings are preserved byte for byte.
    """
    changed = []
    pairs = [(f"{OWNER_TOKEN}/{DEFAULT_REPO}", f"{owner}/{repo}"), (OWNER_TOKEN, owner)]
    if previous_owner and previous_owner != owner:
        pairs.append((f"{previous_owner}/{DEFAULT_REPO}", f"{owner}/{repo}"))
    for path in project_files(root):
        relative = path.relative_to(root).as_posix()
        if relative in KEEP_TOKEN:
            continue
        raw = path.read_bytes()
        if b"\0" in raw[:8192]:
            continue
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            continue
        new = text
        for old, replacement in pairs:
            new = new.replace(old, replacement)
        if new != text:
            changed.append(relative)
            if write:
                path.write_bytes(new.encode("utf-8"))
    return changed


def written_owner(root: Path) -> Optional[str]:
    """The account name currently written in the files (from the plugin manifest), or None while the placeholder is there."""
    try:
        manifest = json.loads((root / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    match = re.search(r"github\.com/([^/\s]+)/", str(manifest.get("repository", "")))
    if not match or match.group(1) == OWNER_TOKEN:
        return None
    return match.group(1)


def changelog_section(text: str, version: str) -> str:
    """The body of the CHANGELOG entry for one version, without its heading."""
    match = re.search(rf"(?ms)^## \[{re.escape(version)}\][^\n]*\n(.*?)(?=^## \[|\Z)", text)
    return match.group(1).strip() if match else ""


def load_metadata(root: Path) -> dict:
    data = json.loads((root / ".github" / "repo-metadata.json").read_text(encoding="utf-8"))
    topics = data.get("topics", [])
    if len(topics) > 20:
        raise PublishError("repo-metadata.json lists more than 20 topics; GitHub accepts at most 20")
    bad = [t for t in topics if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,49}", t)]
    if bad:
        raise PublishError(f"invalid topic name(s): {', '.join(bad)} (lowercase letters, digits and hyphens, at most 50 characters)")
    if len(data.get("description", "")) > 350:
        raise PublishError("the repository description is longer than 350 characters")
    return data


def release_notes(root: Path, version: str, owner: str, repo: str) -> str:
    body = changelog_section((root / "CHANGELOG.md").read_text(encoding="utf-8"), version)
    install = (
        "## Install\n\n"
        "```bash\n"
        f"git clone https://github.com/{owner}/{repo}\n"
        f"cd {repo}\n"
        "python scripts/install.py claude-code      # or: codex | gemini-cli | antigravity | agents\n"
        "```\n\n"
        f"**Windows, one click:** download `DIAVLO-MIND-Setup.bat` and double-click it. It installs Python 3.9+ "
        "for your user if it is missing, downloads this release and installs DIAVLO MIND in every AI tool it finds.\n\n"
        "`DIAVLO-MIND-FABLE-EDITION.zip` is the whole project. `diavlo-mind.zip` is the skill alone, "
        "for hosts where you upload a skill archive. Checksums are in `SHA256SUMS.txt`.\n"
    )
    return f"{install}\n{body}\n" if body else install


# --------------------------------------------------------------------------
# Steps
# --------------------------------------------------------------------------

def step_prepare(run: Runner, owner: str, repo: str, previous_owner: Optional[str], skip_tests: bool) -> None:
    previous_owner = previous_owner or written_owner(ROOT)  # a copy published before carries its old account name
    if previous_owner and previous_owner != owner:
        print(f"    the files name the account {previous_owner}; it will be replaced by {owner}")
    hits = replace_owner(ROOT, owner, repo, previous_owner, write=not run.dry_run)
    verb = "would be updated" if run.dry_run else "updated"
    print(f"    owner name: {len(hits)} file(s) {verb}" + (f" ({', '.join(hits[:5])}{', …' if len(hits) > 5 else ''})" if hits else ""))
    py = sys.executable
    run.change([py, "scripts/build_prompts.py"])
    run.change([py, "scripts/validate.py", "--release"])
    if not skip_tests:
        run.change([py, "-m", "unittest", "discover", "-s", "tests"])
        run.change([py, "evaluation/selftest.py"])
    run.change([py, "scripts/package.py"])


def noreply_identity(login: str, user_id: str) -> Tuple[str, str]:
    """Author name and GitHub no-reply address of an account."""
    return login, f"{user_id}+{login}@users.noreply.github.com"


def commit_identity(run: Runner, mode: str) -> List[str]:
    """Extra git arguments that set the author of the commit."""
    if mode == "git":
        code, name, _ = run.read(["git", "config", "user.name"])
        code2, email, _ = run.read(["git", "config", "user.email"])
        if code or code2 or not name or not email:
            raise PublishError("git has no user.name / user.email configured; set them, or use --identity noreply")
        return []
    if run.dry_run:  # do not look anything up for a preview
        return ["-c", "user.name=<your login>", "-c", "user.email=<id>+<login>@users.noreply.github.com"]
    code, answer, _ = run.read(["gh", "api", "user", "--jq", '.login + " " + (.id|tostring)'])
    parts = answer.split()
    if code or len(parts) != 2 or not parts[1].isdigit():
        raise PublishError("could not read your GitHub account (is gh signed in?); try --identity git")
    name, email = noreply_identity(parts[0], parts[1])
    return ["-c", f"user.name={name}", "-c", f"user.email={email}"]


def step_commit(run: Runner, identity: str, message: Optional[str], version: str) -> None:
    if not (ROOT / ".git").exists():
        run.change(["git", "init"])
        run.change(["git", "symbolic-ref", "HEAD", "refs/heads/main"])
        first = True
    else:
        code, _, _ = run.read(["git", "rev-parse", "--verify", "HEAD"])
        first = code != 0
    run.change(["git", "add", "-A"])
    if not run.dry_run:
        code, status, _ = run.read(["git", "status", "--porcelain"])
        if not status:
            print("    nothing to commit")
            return
    text = message or (f"DIAVLO MIND {version}: Fable Edition" if first else f"Prepare {version} for publication")
    run.change(["git", *commit_identity(run, identity), "commit", "-m", text])
    if first:
        run.change(["git", "branch", "-M", "main"])


def step_create(run: Runner, slug: str, private: bool, description: str) -> None:
    if run.dry_run:  # a preview never goes to the network
        print("    (skipped when the repository already exists)")
    else:
        code, _, _ = run.read(["gh", "repo", "view", slug, "--json", "name"])
        if code == 0:
            print(f"    {slug} already exists")
            return
    created = run.change(["gh", "repo", "create", slug, "--private" if private else "--public", "--description", description],
                         ok_if=("already exists",))
    if not created:
        print(f"    {slug} already exists")


def step_push(run: Runner, slug: str) -> None:
    url = f"https://github.com/{slug}.git"
    code, current, _ = run.read(["git", "remote", "get-url", "origin"])
    if code != 0:
        run.change(["git", "remote", "add", "origin", url])
    elif current.rstrip("/") not in (url, url[:-4]):
        problem = (f"the remote 'origin' points to {current}, not to {url}. "
                   f"Change it with: git remote set-url origin {url}")
        if not run.dry_run:
            raise PublishError(problem)
        print(f"    note: {problem}")
    try:
        run.change(["git", "push", "-u", "origin", "main"])
    except PublishError as exc:
        raise PublishError(f"{exc}\nIf git asked for a password, run `gh auth setup-git` once and repeat with "
                           "--steps push,metadata,release") from exc


def step_metadata(run: Runner, slug: str, meta: dict) -> None:
    features = meta.get("features", {})
    command = ["gh", "repo", "edit", slug, "--description", meta["description"]]
    if meta.get("homepage"):
        command += ["--homepage", meta["homepage"]]
    for flag, key in (("--enable-issues", "issues"), ("--enable-wiki", "wiki"), ("--enable-projects", "projects"),
                      ("--enable-discussions", "discussions")):
        if key in features:
            command.append(f"{flag}={'true' if features[key] else 'false'}")
    for topic in meta.get("topics", []):
        command += ["--add-topic", topic]
    run.change(command)
    for name, color, description in LABELS:
        run.change(["gh", "label", "create", name, "--repo", slug, "--color", color, "--description", description, "--force"])


def step_release(run: Runner, slug: str, meta: dict, version: str) -> None:
    tag = f"v{version}"
    owner, repo = slug.split("/", 1)
    if run.dry_run:
        print("    (skipped when the release already exists)")
    else:
        code, _, _ = run.read(["gh", "release", "view", tag, "--repo", slug, "--json", "tagName"])
        if code == 0:
            print(f"    release {tag} already exists")
            return
    release = meta.get("release", {})
    assets = [ROOT / name for name in release.get("assets", [])]
    missing = [a.relative_to(ROOT).as_posix() for a in assets if not a.is_file()]
    if missing and not run.dry_run:
        raise PublishError(f"missing release file(s): {', '.join(missing)}. Run the prepare step (or python scripts/package.py) first")
    title = release.get("title", "DIAVLO MIND {version}").replace("{version}", version)
    scratch = Path(tempfile.mkdtemp(prefix="dm-release-"))
    try:
        notes = scratch / "notes.md"
        notes.write_text(release_notes(ROOT, version, owner, repo), encoding="utf-8")
        run.change(["gh", "release", "create", tag, "--repo", slug, "--target", "main", "--title", title,
                    "--notes-file", str(notes), *[str(a) for a in assets]])
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def utf8_stdio() -> None:
    """Write UTF-8 regardless of the platform's default encoding (Windows pipes use a legacy code page)."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def parse_steps(text: Optional[str]) -> List[str]:
    if not text:
        return list(STEPS)
    chosen = [part.strip() for part in text.split(",") if part.strip()]
    unknown = [step for step in chosen if step not in STEPS]
    if unknown:
        raise PublishError(f"unknown step(s): {', '.join(unknown)}. Choose from: {', '.join(STEPS)}")
    return [step for step in STEPS if step in chosen]  # always in the canonical order


def main(argv: Optional[List[str]] = None) -> int:
    utf8_stdio()
    parser = argparse.ArgumentParser(description="Publish this folder as a GitHub repository.",
                                     epilog="Steps: " + ", ".join(STEPS))
    parser.add_argument("--owner", help="GitHub account or organisation (default: the account gh is signed in as)")
    parser.add_argument("--repo", default=DEFAULT_REPO, help=f"repository name (default: {DEFAULT_REPO}; the skill folder keeps the name diavlo-mind either way)")
    parser.add_argument("--private", action="store_true", help="create a private repository (default: public)")
    parser.add_argument("--steps", help="comma-separated subset of the steps (default: all)")
    parser.add_argument("--previous-owner", help="when republishing a copy: the account name currently written in the files "
                                                 "(default: read from .claude-plugin/plugin.json)")
    parser.add_argument("--identity", choices=["noreply", "git"], default="noreply",
                        help="author of the commit: your GitHub no-reply address (default) or git's configured identity")
    parser.add_argument("--message", help="commit message (default: a standard one)")
    parser.add_argument("--skip-tests", action="store_true", help="in the prepare step, skip unit tests and the benchmark self-test")
    parser.add_argument("--dry-run", action="store_true", help="print the steps and commands without changing anything")
    args = parser.parse_args(argv)
    run = Runner(args.dry_run)

    try:
        steps = parse_steps(args.steps)
        needs_git = bool({"commit", "push"} & set(steps))
        needs_gh = bool({"create", "metadata", "release"} & set(steps)) or (not args.owner) or \
            ("commit" in steps and args.identity == "noreply")
        if needs_git and not shutil.which("git"):
            raise PublishError("git is not installed or not on PATH")
        if needs_gh and not shutil.which("gh") and not (args.dry_run and args.owner):
            raise PublishError("the GitHub CLI (gh) is not installed: https://cli.github.com then `gh auth login`")
        owner = args.owner
        if not owner:
            code, owner, error = run.read(["gh", "api", "user", "--jq", ".login"])
            if code != 0 or not owner:
                raise PublishError("gh is not signed in. Run `gh auth login`, or pass --owner <account> with --dry-run to preview.\n" + error[-300:])
        if not OWNER_RE.fullmatch(owner):
            raise PublishError(f"not a valid GitHub account name: {owner!r}")
        if not REPO_RE.fullmatch(args.repo):
            raise PublishError(f"not a valid repository name: {args.repo!r}")
        slug = f"{owner}/{args.repo}"
        version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
        meta = load_metadata(ROOT)
        visibility = "private" if args.private else "public"
        print(f"Publishing DIAVLO MIND {version} to https://github.com/{slug} ({visibility})"
              + (" — dry run, nothing will change" if args.dry_run else ""))

        for step in steps:
            print(f"\n[{step}]")
            if step == "prepare":
                step_prepare(run, owner, args.repo, args.previous_owner, args.skip_tests)
            elif step == "commit":
                step_commit(run, args.identity, args.message, version)
            elif step == "create":
                step_create(run, slug, args.private, meta["description"])
            elif step == "push":
                step_push(run, slug)
            elif step == "metadata":
                step_metadata(run, slug, meta)
            elif step == "release":
                step_release(run, slug, meta, version)
    except PublishError as exc:
        print(f"\nerror: {exc}", file=sys.stderr)
        return 1

    print("\n" + ("Dry run complete: nothing was changed." if args.dry_run else "Done."))
    print(f"Repository: https://github.com/{slug}")
    if not args.dry_run and "metadata" in steps and meta.get("social_preview"):
        print(f"One manual step is left, because GitHub has no command for it: open\n"
              f"  https://github.com/{slug}/settings  →  Social preview  →  Edit  →  upload {meta['social_preview']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
