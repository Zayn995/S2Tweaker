"""Parse GSC cfg text into a tree of CfgStruct nodes.

Reads vanilla data and inheritance attributes; s2tweaker.emit writes patches.
Example: Player : struct.begin {refurl=../BaseObj.cfg, refkey=Base}"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class CfgStruct:
    """A struct.begin/struct.end block with raw string values."""

    name: str
    attrs: str = ""  # Raw {...} attributes following struct.begin.
    values: dict[str, str] = field(default_factory=dict)
    children: dict[str, "CfgStruct"] = field(default_factory=dict)

    def attr_dict(self) -> dict[str, str]:
        """Parse {...} attributes, e.g. {"refkey": "[0]"}.

        Separators are semicolons or commas. Flags without '=' map to "true"."""
        result: dict[str, str] = {}
        for part in re.split(r"[;,]", self.attrs):
            part = part.strip()
            if not part:
                continue
            if "=" in part:
                k, _, v = part.partition("=")
                result[k.strip()] = v.strip()
            else:
                result[part] = "true"
        return result

    def get(self, path: str, default: str | None = None) -> str | None:
        """Read a value by path, e.g. get("VitalParams.MaxHP")."""
        parts = path.split(".")
        node: CfgStruct = self
        for part in parts[:-1]:
            child = node.children.get(part)
            if child is None:
                return default
            node = child
        return node.values.get(parts[-1], default)

    def find(self, name: str) -> "CfgStruct | None":
        """Recursively find the first child struct with this name."""
        if name in self.children:
            return self.children[name]
        for child in self.children.values():
            hit = child.find(name)
            if hit is not None:
                return hit
        return None

    def walk(self):
        """Yield all structs recursively, including self."""
        yield self
        for child in self.children.values():
            yield from child.walk()


# A trailing ':' occurs in AIGlobals.cfg ("AISettings : struct.begin:").
_STRUCT_BEGIN = re.compile(
    r"^(?P<name>[^=:]+?)\s*:\s*struct\.begin(?:\s*\{(?P<attrs>[^}]*)\})?\s*:?\s*$"
)
_KEY_VALUE = re.compile(r"^(?P<key>[^=:]+?)\s*=\s*(?P<value>.*)$")


def _strip_comment(line: str) -> str:
    # Strip // comments. GameData paths use single slashes; values containing
    # // are not expected in the supported input.
    idx = line.find("//")
    if idx >= 0:
        return line[:idx]
    return line


def parse(text: str, root_name: str = "<root>") -> CfgStruct:
    """Parse cfg text into a CfgStruct tree."""
    # Accept BOM and nonstandard whitespace.
    text = text.lstrip("﻿")
    # The shipped AIGlobals has a numeric assignment and struct.end on one
    # line (FleshMetal noise). Keep following materials at their actual level.
    text = re.sub(r"(?m)^([^\r\n=]+=[ \t]*[-+\d.eEfF%;]+)[ \t]+struct\.end[ \t]*$",
                  r"\1\nstruct.end", text)
    root = CfgStruct(root_name)
    stack: list[CfgStruct] = [root]

    for raw_line in text.splitlines():
        line = _strip_comment(raw_line).strip()
        if not line:
            continue

        if line == "struct.end":
            if len(stack) > 1:
                stack.pop()
            continue

        m = _STRUCT_BEGIN.match(line)
        if m:
            node = CfgStruct(m.group("name").strip(), (m.group("attrs") or "").strip())
            parent = stack[-1]
            # Handle duplicate names; indexed array keys [0], [1], ... are unique.
            key = node.name
            i = 1
            while key in parent.children:
                i += 1
                key = f"{node.name}#{i}"
            parent.children[key] = node
            stack.append(node)
            continue

        m = _KEY_VALUE.match(line)
        if m:
            stack[-1].values[m.group("key").strip()] = m.group("value").strip()
            continue

        # Ignore unknown lines to tolerate additional syntax.

    return root


def parse_file(path) -> CfgStruct:
    from pathlib import Path

    data = Path(path).read_bytes()
    # GameData cfg files use UTF-8, sometimes with a BOM.
    return parse(data.decode("utf-8-sig", errors="replace"), root_name=str(path))


def parse_number(value: str | None, default: float = 0.0) -> float:
    """Convert GSC numbers such as '24.f', '0.3f', '1000.f;' or '2%' to float.

    Accept trailing semicolons. '2%' returns 2.0, not 0.02."""
    if value is None:
        return default
    v = value.strip().rstrip(";").strip()
    if v.endswith("%"):
        v = v[:-1].strip()
    v = v.rstrip("fF").rstrip(".")
    try:
        return float(v)
    except ValueError:
        return default
