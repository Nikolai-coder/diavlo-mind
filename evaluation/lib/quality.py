"""Code-quality proxies for benchmark runs.

These are cheap, deterministic signals computed from the Python files a run
created or changed. They are proxies, not a judgement of design quality:
a high score means "nothing obviously wrong", not "good code".
"""
from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Dict, List, Optional

MARKERS = re.compile(r"#.*\b(TODO|FIXME|XXX|HACK)\b")


def _depth(node: ast.AST, level: int = 0) -> int:
    nested = (ast.If, ast.For, ast.While, ast.Try, ast.With, ast.AsyncFor, ast.AsyncWith)
    deepest = level
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        deepest = max(deepest, _depth(child, level + 1 if isinstance(child, nested) else level))
    return deepest


def analyse(files: List[Path]) -> Optional[Dict[str, object]]:
    """Return metrics and a 0..1 score for the given Python files, or None when there are none."""
    files = [path for path in files if path.suffix == ".py" and path.is_file()]
    if not files:
        return None
    syntax_errors = long_functions = bare_excepts = markers = 0
    lengths: List[int] = []
    deepest = 0
    for path in files:
        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except (SyntaxError, UnicodeDecodeError, OSError):
            syntax_errors += 1
            continue
        markers += len(MARKERS.findall(source))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                length = (node.end_lineno or node.lineno) - node.lineno + 1
                lengths.append(length)
                long_functions += length > 50
                deepest = max(deepest, _depth(node))
            elif isinstance(node, ast.ExceptHandler) and node.type is None:
                bare_excepts += 1
    score = 1.0
    if syntax_errors:
        score -= 0.5
    score -= min(0.3, 0.1 * long_functions)
    if deepest > 4:
        score -= 0.1
    score -= min(0.2, 0.1 * bare_excepts)
    score -= min(0.1, 0.05 * markers)
    return {
        "files": len(files),
        "syntax_errors": syntax_errors,
        "functions": len(lengths),
        "mean_function_lines": round(sum(lengths) / len(lengths), 1) if lengths else 0,
        "max_function_lines": max(lengths) if lengths else 0,
        "functions_over_50_lines": long_functions,
        "max_nesting_depth": deepest,
        "bare_excepts": bare_excepts,
        "todo_markers": markers,
        "score": round(max(0.0, score), 2),
    }
