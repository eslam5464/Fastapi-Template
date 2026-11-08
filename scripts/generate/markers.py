"""Whole-line feature-marker engine for the Copier template.

Strips ``FEATURE[<expr>]`` marked blocks (and standalone marker lines) from
generated projects, driven by the feature manifest in ``features.py``.

Marker styles (whole lines only; leading/trailing whitespace allowed):

    hash: ``# --- FEATURE[<expr>] START ---`` / ``# --- FEATURE[<expr>] END ---``
    html: ``<!-- --- FEATURE[<expr>] START --- -->`` / ``<!-- --- FEATURE[<expr>] END --- -->``

Expressions: a feature name, names joined only by ``|`` (any) or only by ``&``
(all); no parentheses, no whitespace around operators, no mixing. ``!name``
(single negated name) is allowed only in html-style files.
"""

from __future__ import annotations

import os
import re
import shutil
from pathlib import Path

import features

HASH = "hash"
HTML = "html"

_FEATURE_NAME = r"[A-Za-z_][A-Za-z0-9_]*"
_NAME_RE = re.compile(_FEATURE_NAME)
_NEGATED_RE = re.compile(r"!" + _FEATURE_NAME)
_OLD_STYLE_RE = re.compile(r"_(START|END) ---")

_MARKER_RE = {
    HASH: re.compile(r"[ \t]*# --- FEATURE\[(?P<expr>[^\]]+)\] (?P<side>START|END) ---[ \t]*"),
    HTML: re.compile(r"[ \t]*<!-- --- FEATURE\[(?P<expr>[^\]]+)\] (?P<side>START|END) --- -->[ \t]*"),
}

_HASH_SUFFIXES = frozenset({".py", ".toml", ".yml", ".yaml", ".ini", ".cfg", ".sh"})
_HTML_SUFFIXES = frozenset({".md", ".txt", ".html"})
_HASH_NAMES = frozenset({"Dockerfile", ".gitignore", ".dockerignore", ".env.example"})


class MarkerError(Exception):
    """Raised for any marker-related problem, with file:line context."""

    def __init__(self, path: str, line_no: int, message: str) -> None:
        super().__init__(f"{path}:{line_no}: {message}")
        self.path = path
        self.line_no = line_no
        self.message = message


def style_for(path: Path) -> str | None:
    """Marker comment style for a file, or None if the type is unsupported."""
    if path.name in _HASH_NAMES:
        return HASH
    suffix = path.suffix.lower()
    if suffix in _HASH_SUFFIXES:
        return HASH
    if suffix in _HTML_SUFFIXES:
        return HTML
    return None


def _parse_expr(expr: str, allow_not: bool, path: str, line_no: int) -> list[str]:
    """Validate an expression, returning its feature names (negation ignored)."""
    if "(" in expr or ")" in expr:
        raise MarkerError(path, line_no, f"parentheses are not allowed: {expr!r}")
    if "!" in expr:
        if not allow_not:
            raise MarkerError(path, line_no, f"'!' is only allowed in html-style files: {expr!r}")
        if not _NEGATED_RE.fullmatch(expr):
            raise MarkerError(path, line_no, f"only a single negated name is allowed: {expr!r}")
        return [expr[1:]]
    if "|" in expr and "&" in expr:
        raise MarkerError(path, line_no, f"cannot mix '|' and '&': {expr!r}")
    op = "|" if "|" in expr else ("&" if "&" in expr else None)
    parts = [expr] if op is None else expr.split(op)
    for part in parts:
        if not _NAME_RE.fullmatch(part):
            raise MarkerError(path, line_no, f"malformed expression: {expr!r}")
    return parts


def _eval_expr(expr: str, feature_flags: dict[str, bool], allow_not: bool, path: str, line_no: int) -> bool:
    names = _parse_expr(expr, allow_not, path, line_no)
    for name in names:
        if name not in feature_flags:
            raise MarkerError(path, line_no, f"unknown feature {name!r}: not in the feature map")
    if "!" in expr:
        value = not feature_flags[names[0]]
    elif "|" in expr:
        value = any(feature_flags[name] for name in names)
    elif "&" in expr:
        value = all(feature_flags[name] for name in names)
    else:
        value = feature_flags[names[0]]
    return value


def eval_expr(expr: str, feature_flags: dict[str, bool], allow_not: bool) -> bool:
    """Evaluate a marker expression against a feature name -> on/off map."""
    return _eval_expr(expr, feature_flags, allow_not, "<expr>", 0)


def _body(line: str) -> str:
    if line.endswith("\r\n"):
        return line[:-2]
    if line.endswith("\n") or line.endswith("\r"):
        return line[:-1]
    return line


def _raise_near_miss(path: str, line_no: int, body: str, unsupported: bool) -> None:
    marker_like = (
        "FEATURE[" in body
        or _OLD_STYLE_RE.search(body) is not None
        or "TEMPLATE_SECTION_START" in body
        or "TEMPLATE_SECTION_END" in body
    )
    if marker_like:
        kind = "marker-like line in unsupported file type" if unsupported else "near-miss marker text"
        raise MarkerError(path, line_no, f"{kind}: {body.strip()!r}")


def process_text(text: str, feature_flags: dict[str, bool], style: str, path: str = "<text>") -> str:
    """Pure marker processing of one file's text. Returns the stripped text."""
    if style not in _MARKER_RE:
        raise ValueError(f"invalid style {style!r}: expected 'hash' or 'html'")
    lines = text.splitlines(keepends=True)
    allow_not = style == HTML
    stack: list[tuple[str, bool, int]] = []
    keep: list[bool] = []
    marker_seen = False
    for i, line in enumerate(lines):
        line_no = i + 1
        body = _body(line)
        match = _MARKER_RE[style].fullmatch(body)
        if match is None:
            _raise_near_miss(path, line_no, body, unsupported=False)
            keep.append(True if not stack else stack[-1][1])
            continue
        marker_seen = True
        expr, side = match.group("expr"), match.group("side")
        if side == "START":
            parent_keep = True if not stack else stack[-1][1]
            value = _eval_expr(expr, feature_flags, allow_not, path, line_no)
            stack.append((expr, parent_keep and value, line_no))
            keep.append(False)
        else:
            if not stack:
                raise MarkerError(path, line_no, "END marker without a matching START")
            start_expr, _, start_line_no = stack.pop()
            if expr != start_expr:
                raise MarkerError(
                    path,
                    line_no,
                    f"END expression {expr!r} does not match START expression {start_expr!r} on line {start_line_no}",
                )
            keep.append(False)
    if stack:
        start_expr, _, start_line_no = stack[-1]
        raise MarkerError(path, start_line_no, f"unclosed START marker for {start_expr!r}")
    if not marker_seen:
        return text
    stripped = _join_kept(lines, keep)
    if not stripped or all(line.strip() == "" for line in stripped):
        raise MarkerError(path, 0, "file became empty or whitespace-only after marker stripping")
    return "".join(stripped)


def _join_kept(lines: list[str], keep: list[bool]) -> list[str]:
    """Assemble kept lines, applying the blank-line max() rule at each removed span."""
    out: list[str] = []
    skip_blanks = 0
    i = 0
    n = len(lines)
    while i < n:
        if keep[i]:
            if skip_blanks > 0 and lines[i].strip() == "":
                skip_blanks -= 1
                i += 1
                continue
            skip_blanks = 0
            out.append(lines[i])
            i += 1
            continue
        j = i
        while j < n and not keep[j]:
            j += 1
        before = 0
        while before < len(out) and out[-1 - before].strip() == "":
            before += 1
        after = 0
        while j + after < n and keep[j + after] and lines[j + after].strip() == "":
            after += 1
        if after >= before:
            del out[len(out) - before :]
        else:
            skip_blanks = after
        i = j
    if lines and lines[-1].endswith(("\n", "\r")):
        while out and out[-1].strip() == "":
            out.pop()
    return out


def _is_excluded(rel: str, prefixes: tuple[str, ...]) -> bool:
    for prefix in prefixes:
        if prefix.endswith("/"):
            if rel == prefix[:-1] or rel.startswith(prefix):
                return True
        elif rel == prefix or rel.startswith(prefix + "/"):
            return True
    return False


def _iter_files(root: Path):
    """Yield (Path, forward-slash repo-relative path) for files under root."""
    excludes = features.SCAN_EXCLUDE
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = Path(dirpath).relative_to(root).as_posix()
        base = "" if rel_dir == "." else rel_dir
        pruned = []
        for d in sorted(dirnames):
            candidate = f"{base}/{d}" if base else d
            if not _is_excluded(candidate, excludes):
                pruned.append(d)
        dirnames[:] = pruned
        for filename in sorted(filenames):
            rel = f"{base}/{filename}" if base else filename
            if _is_excluded(rel, excludes):
                continue
            yield Path(dirpath) / filename, rel


def _read_text(path: Path) -> str | None:
    """File text, or None for files that are not scannable (binary/NUL)."""
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if b"\0" in data:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None


def _scan_near_miss(text: str, rel: str, unsupported: bool) -> None:
    for i, line in enumerate(text.splitlines(keepends=True)):
        _raise_near_miss(rel, i + 1, _body(line), unsupported=unsupported)


def _remove_empty_parents(directory: Path, root: Path) -> None:
    """Remove `directory` and its parents while they are empty, stopping at `root`.

    A PATHS deletion can leave its folder empty (e.g. docs/integrations/ once
    its only guide is gone); git does not track empty folders, so neither
    should the generated project.
    """
    root = root.resolve()
    current = directory.resolve()
    while current != root and root in current.parents and current.is_dir() and not any(current.iterdir()):
        current.rmdir()
        current = current.parent


def apply(root: Path, feature_flags: dict[str, bool]) -> list[Path]:
    """Apply marker stripping and PATHS deletion to a generated project tree.

    Returns the files whose content the marker pass rewrote, so the caller can
    re-normalise them (e.g. import sorting) afterwards.
    """
    root = Path(root)
    changed: list[Path] = []
    for rel in features.PATHS:
        if not (root / rel).exists():
            raise MarkerError(rel, 0, "PATHS entry does not exist under root")
    for rel, expr in features.PATHS.items():
        if not _eval_expr(expr, feature_flags, allow_not=False, path=rel, line_no=0):
            target = root / rel
            if not target.exists():
                # Already gone with a deleted parent folder (e.g. a firestore-only
                # test file inside the firebase test package).
                continue
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
            _remove_empty_parents(target.parent, root)
    for path, rel in _iter_files(root):
        text = _read_text(path)
        if text is None:
            continue
        style = style_for(path)
        if style is None:
            _scan_near_miss(text, rel, unsupported=True)
            continue
        stripped = process_text(text, feature_flags, style, rel)
        if stripped != text:
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(stripped)
            changed.append(path)
    for path, rel in _iter_files(root):
        text = _read_text(path)
        if text is None:
            continue
        style = style_for(path)
        if style is None:
            continue
        for i, line in enumerate(text.splitlines(keepends=True)):
            assert _MARKER_RE[style].fullmatch(_body(line)) is None, f"{rel}:{i + 1}: marker line survived processing"
    return changed


def used_features(root: Path) -> set[str]:
    """Feature names used in any marker expression or PATHS expression under root."""
    root = Path(root)
    used: set[str] = set()
    for rel, expr in features.PATHS.items():
        used.update(_parse_expr(expr, allow_not=True, path=rel, line_no=0))
    for path, rel in _iter_files(root):
        text = _read_text(path)
        if text is None:
            continue
        style = style_for(path)
        if style is None:
            continue
        for i, line in enumerate(text.splitlines(keepends=True)):
            match = _MARKER_RE[style].fullmatch(_body(line))
            if match is not None:
                used.update(_parse_expr(match.group("expr"), allow_not=True, path=rel, line_no=i + 1))
    return used
