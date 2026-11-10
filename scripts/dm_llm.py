#!/usr/bin/env python3
"""Minimal multi-provider text completion client for DIAVLO MIND scripts.

One function, `complete(spec, system, messages)`, over several back ends,
using only the Python standard library. Tools are deliberately not used:
the orchestrator exchanges plain text, so every chat-capable model works.

Model spec:  <provider>:<model>

    anthropic:<model-id>          Claude API, POST /v1/messages
    openai:<model-id>             OpenAI Chat Completions
    openai-responses:<model-id>   OpenAI Responses API
    gemini:<model-id>             Gemini API generateContent
    compatible:<model-id>         Any OpenAI-compatible server (set DM_OPENAI_BASE_URL)
    claude-cli:<alias-or-id>      Local Claude Code CLI, `claude -p`, no API key needed
    cmd:<label>                   Any command that reads a prompt on stdin (set DM_CMD)
    mock:<path-to-json>           Scripted responses, for tests

Environment:
    ANTHROPIC_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY (or GOOGLE_API_KEY)
    DM_ANTHROPIC_BASE_URL, DM_OPENAI_BASE_URL, DM_GEMINI_BASE_URL   override endpoints
    DM_ANTHROPIC_VERSION      anthropic-version header (default 2026-10-21)
    DM_ANTHROPIC_AUTH         "bearer" (default) or "x-api-key"
    DM_CMD                    command line for the cmd provider
    DM_HTTP_TIMEOUT           seconds (default 600)

Sampling parameters (temperature, top_p, top_k) are never sent: several
current APIs reject or ignore them. Wire formats were checked against the
vendors' documentation in November 2026; see adapters/ for sources.

CLI:  python dm_llm.py <spec> "prompt" [--system "..."]
"""
from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional

DEFAULT_MAX_TOKENS = 8192
RETRY_STATUS = {408, 409, 425, 429, 500, 502, 503, 504, 529}


class LLMError(Exception):
    """A provider call failed in a way the caller should see."""


def parse_spec(spec: str) -> tuple:
    if ":" not in spec:
        raise LLMError(f"model spec must look like provider:model, got {spec!r}")
    provider, model = spec.split(":", 1)
    provider = provider.strip().lower()
    if provider not in PROVIDERS:
        raise LLMError(f"unknown provider {provider!r}; choose one of {', '.join(sorted(PROVIDERS))}")
    if not model.strip():
        raise LLMError(f"model name missing in {spec!r}")
    return provider, model.strip()


def _timeout() -> float:
    return float(os.environ.get("DM_HTTP_TIMEOUT", "600"))


def _post_json(url: str, headers: Dict[str, str], body: dict, retries: int = 3) -> dict:
    data = json.dumps(body).encode("utf-8")
    last = "no attempt made"
    for attempt in range(retries + 1):
        request = urllib.request.Request(url, data=data, method="POST")
        request.add_header("Content-Type", "application/json")
        for key, value in headers.items():
            request.add_header(key, value)
        try:
            with urllib.request.urlopen(request, timeout=_timeout()) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:600]
            last = f"HTTP {exc.code} from {url}: {detail}"
            if exc.code not in RETRY_STATUS or attempt == retries:
                raise LLMError(last) from exc
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            last = f"cannot reach {url}: {exc}"
            if attempt == retries:
                raise LLMError(last) from exc
        except json.JSONDecodeError as exc:
            raise LLMError(f"{url} returned a non-JSON body: {exc}") from exc
        time.sleep(min(2 ** attempt, 20))
    raise LLMError(last)


def _key(*names: str) -> str:
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    raise LLMError(f"set {' or '.join(names)} to use this provider")


def _result(text: str, input_tokens: Optional[int], output_tokens: Optional[int],
            cost_usd: Optional[float] = None) -> dict:
    return {"text": text, "input_tokens": input_tokens, "output_tokens": output_tokens, "cost_usd": cost_usd}


def flatten(system: str, messages: List[dict]) -> str:
    """Single-prompt form for back ends that take one block of text."""
    parts = []
    if system:
        parts.append(f"[SYSTEM INSTRUCTIONS]\n{system}")
    if len(messages) == 1 and messages[0]["role"] == "user":
        parts.append(messages[0]["content"])
    else:
        for message in messages:
            parts.append(f"[{message['role'].upper()}]\n{message['content']}")
    return "\n\n".join(parts)


# --------------------------------------------------------------------------
# Providers
# --------------------------------------------------------------------------

def _anthropic(model: str, system: str, messages: List[dict], max_tokens: Optional[int]) -> dict:
    base = os.environ.get("DM_ANTHROPIC_BASE_URL", "https://api.anthropic.com").rstrip("/")
    key = _key("ANTHROPIC_API_KEY")
    headers = {"anthropic-version": os.environ.get("DM_ANTHROPIC_VERSION", "2026-10-21")}
    if os.environ.get("DM_ANTHROPIC_AUTH", "bearer").lower() == "x-api-key":
        headers["x-api-key"] = key
    else:
        headers["Authorization"] = f"Bearer {key}"
    body = {"model": model, "max_tokens": max_tokens or DEFAULT_MAX_TOKENS, "messages": messages}
    if system:
        body["system"] = system
    data = _post_json(f"{base}/v1/messages", headers, body)
    text = "".join(block.get("text", "") for block in data.get("content", []) if block.get("type") == "text")
    usage = data.get("usage", {})
    input_tokens = sum(usage.get(k) or 0 for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"))
    if data.get("stop_reason") == "refusal" and not text:
        raise LLMError("the model declined the request (stop_reason: refusal)")
    return _result(text, input_tokens, usage.get("output_tokens"))


def _openai_chat(model: str, system: str, messages: List[dict], max_tokens: Optional[int],
                 compatible: bool = False) -> dict:
    if compatible:
        base = os.environ.get("DM_OPENAI_BASE_URL")
        if not base:
            raise LLMError("set DM_OPENAI_BASE_URL (for example http://localhost:11434/v1) for the compatible provider")
        key = os.environ.get("DM_OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY") or "not-needed"
    else:
        base = os.environ.get("DM_OPENAI_BASE_URL", "https://api.openai.com/v1")
        key = _key("OPENAI_API_KEY")
    chat = []
    if system:
        chat.append({"role": "system" if compatible else "developer", "content": system})
    chat += messages
    body = {"model": model, "messages": chat}
    if max_tokens:
        body["max_tokens" if compatible else "max_completion_tokens"] = max_tokens
    data = _post_json(f"{base.rstrip('/')}/chat/completions", {"Authorization": f"Bearer {key}"}, body)
    try:
        text = data["choices"][0]["message"].get("content") or ""
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMError(f"unexpected chat completion shape: {str(data)[:300]}") from exc
    usage = data.get("usage") or {}
    return _result(text, usage.get("prompt_tokens"), usage.get("completion_tokens"))


def _openai_responses(model: str, system: str, messages: List[dict], max_tokens: Optional[int]) -> dict:
    base = os.environ.get("DM_OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    key = _key("OPENAI_API_KEY")
    body = {"model": model, "input": [{"role": m["role"], "content": m["content"]} for m in messages]}
    if system:
        body["instructions"] = system
    if max_tokens:
        body["max_output_tokens"] = max_tokens
    data = _post_json(f"{base}/responses", {"Authorization": f"Bearer {key}"}, body)
    chunks = []
    for item in data.get("output", []):
        if item.get("type") != "message":
            continue
        for part in item.get("content", []):
            if part.get("type") == "output_text":
                chunks.append(part.get("text", ""))
    usage = data.get("usage") or {}
    return _result("".join(chunks), usage.get("input_tokens"), usage.get("output_tokens"))


def _gemini(model: str, system: str, messages: List[dict], max_tokens: Optional[int]) -> dict:
    base = os.environ.get("DM_GEMINI_BASE_URL", "https://generativelanguage.googleapis.com").rstrip("/")
    key = _key("GEMINI_API_KEY", "GOOGLE_API_KEY")
    contents = [
        {"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]}
        for m in messages
    ]
    body: dict = {"contents": contents}
    if system:
        body["system_instruction"] = {"parts": [{"text": system}]}
    if max_tokens:
        body["generationConfig"] = {"maxOutputTokens": max_tokens}
    data = _post_json(f"{base}/v1beta/models/{model}:generateContent", {"x-goog-api-key": key}, body)
    candidates = data.get("candidates") or []
    if not candidates:
        raise LLMError(f"Gemini returned no candidates: {str(data.get('promptFeedback', data))[:300]}")
    parts = (candidates[0].get("content") or {}).get("parts") or []
    text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
    usage = data.get("usageMetadata") or {}
    output = (usage.get("candidatesTokenCount") or 0) + (usage.get("thoughtsTokenCount") or 0)
    return _result(text, usage.get("promptTokenCount"), output or None)


def _claude_cli(model: str, system: str, messages: List[dict], max_tokens: Optional[int]) -> dict:
    binary = shutil.which("claude")
    if not binary:
        raise LLMError("the `claude` command was not found on PATH (install Claude Code or pick another provider)")
    command = [binary, "-p", "--output-format", "json", "--model", model, "--tools", "",
               "--no-session-persistence", "--safe-mode",
               "--system-prompt", system or "You are a helpful assistant."]
    prompt = flatten("", messages)
    try:
        run = subprocess.run(command, input=prompt, capture_output=True, text=True,
                             encoding="utf-8", timeout=_timeout())
    except subprocess.TimeoutExpired as exc:
        raise LLMError(f"claude -p timed out after {_timeout():.0f}s") from exc
    try:
        data = json.loads(run.stdout)
    except json.JSONDecodeError as exc:
        raise LLMError(f"claude -p did not return JSON (exit {run.returncode}): {(run.stdout or run.stderr)[:400]}") from exc
    if data.get("is_error"):
        raise LLMError(f"claude -p reported an error: {str(data.get('result'))[:400]}")
    usage = data.get("usage") or {}
    input_tokens = sum(usage.get(k) or 0 for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"))
    return _result(data.get("result") or "", input_tokens, usage.get("output_tokens"), data.get("total_cost_usd"))


def _cmd(model: str, system: str, messages: List[dict], max_tokens: Optional[int]) -> dict:
    template = os.environ.get("DM_CMD")
    if not template:
        raise LLMError("set DM_CMD to a command that reads a prompt on stdin and prints the reply")
    # Windows resolves quoting itself when given the whole command line; elsewhere split it.
    command = template if os.name == "nt" else shlex.split(template)
    try:
        run = subprocess.run(command, input=flatten(system, messages), capture_output=True, text=True,
                             encoding="utf-8", timeout=_timeout())
    except FileNotFoundError as exc:
        raise LLMError(f"DM_CMD program not found: {template}") from exc
    except subprocess.TimeoutExpired as exc:
        raise LLMError(f"DM_CMD timed out after {_timeout():.0f}s") from exc
    if run.returncode != 0:
        raise LLMError(f"DM_CMD exited with {run.returncode}: {run.stderr[:400]}")
    return _result(run.stdout, None, None)


def _mock(model: str, system: str, messages: List[dict], max_tokens: Optional[int]) -> dict:
    """Scripted replies from a JSON file: {"responses": [...], "cursor": 0}.

    Each response is a string, or {"contains": "<text>", "text": "<reply>"} to
    assert that the prompt contains a marker. Calls are appended to "<file>.calls".
    """
    path = Path(model)
    try:
        script = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LLMError(f"mock script {path} unreadable: {exc}") from exc
    cursor = script.get("cursor", 0)
    responses = script.get("responses", [])
    if cursor >= len(responses):
        raise LLMError(f"mock script {path} exhausted after {cursor} call(s)")
    entry = responses[cursor]
    prompt = flatten(system, messages)
    if isinstance(entry, dict):
        marker = entry.get("contains")
        if marker and marker not in prompt:
            raise LLMError(f"mock call {cursor}: prompt does not contain {marker!r}")
        text = entry["text"]
    else:
        text = entry
    script["cursor"] = cursor + 1
    path.write_text(json.dumps(script, indent=2), encoding="utf-8")
    with open(str(path) + ".calls", "a", encoding="utf-8") as log:
        log.write(json.dumps({"call": cursor, "system": system, "messages": messages}) + "\n")
    return _result(text, len(prompt) // 4, len(text) // 4, 0.0)


PROVIDERS = {
    "anthropic": _anthropic,
    "openai": _openai_chat,
    "openai-responses": _openai_responses,
    "gemini": _gemini,
    "compatible": lambda model, system, messages, max_tokens: _openai_chat(model, system, messages, max_tokens, compatible=True),
    "claude-cli": _claude_cli,
    "cmd": _cmd,
    "mock": _mock,
}


def complete(spec: str, system: str, messages: List[dict], max_tokens: Optional[int] = None) -> dict:
    """Run one completion. Returns text, token counts (when known), cost (when known) and timing."""
    provider, model = parse_spec(spec)
    for message in messages:
        if message.get("role") not in ("user", "assistant") or not isinstance(message.get("content"), str):
            raise LLMError("messages must be a list of {'role': 'user'|'assistant', 'content': str}")
    started = time.time()
    result = PROVIDERS[provider](model, system, messages, max_tokens)
    result.update({"provider": provider, "model": model, "seconds": round(time.time() - started, 2)})
    if not result["text"].strip():
        raise LLMError(f"{spec} returned an empty reply")
    return result


def utf8_stdio() -> None:
    """Write UTF-8 regardless of the platform's default encoding (Windows pipes use a legacy code page)."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def main(argv: Optional[List[str]] = None) -> int:
    utf8_stdio()
    parser = argparse.ArgumentParser(description="Send one prompt to a model (smoke test for a provider setup).")
    parser.add_argument("spec", help="provider:model, e.g. claude-cli:haiku")
    parser.add_argument("prompt")
    parser.add_argument("--system", default="")
    parser.add_argument("--max-tokens", type=int)
    parser.add_argument("--json", action="store_true", help="print the full result as JSON")
    args = parser.parse_args(argv)
    try:
        result = complete(args.spec, args.system, [{"role": "user", "content": args.prompt}], args.max_tokens)
    except LLMError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(result["text"])
        print(f"[{result['provider']}:{result['model']} in={result['input_tokens']} out={result['output_tokens']} "
              f"cost={result['cost_usd']} {result['seconds']}s]", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
