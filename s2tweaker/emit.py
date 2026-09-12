"""Emit S.T.A.L.K.E.R. 2 bpatch cfg files.

New files under Stalker2/Content/GameLite/GameData/ override selected values
of existing prototypes using {bpatch} on the affected structs."""

from __future__ import annotations

INDENT = "   "


def _emit_struct(name: str, content: dict, depth: int, lines: list[str],
                 plain: bool = False) -> None:
    pad = INDENT * depth
    # __attrs__ adds struct attributes, e.g. refkey=Base for inherited scope
    # effects using the {refkey=X;bpatch} pattern documented by sdwvit.
    attrs = content.get("__attrs__")
    # __new__ identifies nodes absent from vanilla (e.g. additional quest nodes).
    # New top-level names are appended without {bpatch}; see docs/SPEC.md.
    # Their descendants must also omit {bpatch}, so propagate this flag down.
    plain = plain or bool(content.get("__new__"))
    if plain:
        head = attrs or ""
    else:
        head = f"{attrs};bpatch" if attrs else "bpatch"
    lines.append(f"{pad}{name} : struct.begin" + (f" {{{head}}}" if head else ""))
    for key, value in content.items():
        if key in ("__attrs__", "__new__"):
            continue
        if isinstance(value, dict):
            _emit_struct(key, value, depth + 1, lines, plain)
        else:
            # An empty value clears a list: emit 'Key =' without trailing whitespace.
            lines.append(f"{pad}{INDENT}{key} = {value}".rstrip())
    lines.append(f"{pad}struct.end")


def emit_patch(patches: dict[str, dict]) -> str:
    """Emit patch cfg text from nested dictionaries.

    Example: {"Player": {"VitalParams": {"MaxHP": 300}}}.
    Nested dictionaries become structs; other values become Key = value lines.
    Callers supply any required GSC suffixes, such as '0.3f'."""
    lines: list[str] = []
    for name, content in patches.items():
        _emit_struct(name, content, 0, lines)
        lines.append("")
    return "\n".join(lines)


def fmt_float(x: float) -> str:
    """Format a float in GameData style without unnecessary trailing zeros."""
    s = f"{x:.6f}".rstrip("0").rstrip(".")
    if "." not in s:
        s += ".0"
    return s
