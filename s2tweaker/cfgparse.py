"""Parser fuer das GSC-cfg-Format von S.T.A.L.K.E.R. 2.

Format (Beispiel):

    Player : struct.begin {refurl=../BaseObj.cfg, refkey=Base}
       VitalParams : struct.begin
          MaxHP = 100
       struct.end
    struct.end

Der Parser liest eine cfg-Datei in einen Baum aus CfgStruct-Knoten.
Er dient nur zum LESEN der Vanilla-Werte; geschrieben werden eigene
Patch-Dateien ueber s2tweaker.emit.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class CfgStruct:
    """Ein struct.begin/struct.end-Block; Werte sind Strings (roh)."""

    name: str
    attrs: str = ""  # Inhalt der {...}-Klammer hinter struct.begin, roh
    values: dict[str, str] = field(default_factory=dict)
    children: dict[str, "CfgStruct"] = field(default_factory=dict)

    def attr_dict(self) -> dict[str, str]:
        """{...}-Attribute hinter struct.begin als dict, z.B. {"refkey": "[0]"}.

        Trennzeichen ist ';' (auch ',' kommt vor); Eintraege ohne '='
        (z.B. "bpatch") bekommen den Wert "true".
        """
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
        """Wert per Pfad holen, z.B. get("VitalParams.MaxHP")."""
        parts = path.split(".")
        node: CfgStruct = self
        for part in parts[:-1]:
            child = node.children.get(part)
            if child is None:
                return default
            node = child
        return node.values.get(parts[-1], default)

    def find(self, name: str) -> "CfgStruct | None":
        """Rekursiv den ersten Kind-Struct mit diesem Namen finden."""
        if name in self.children:
            return self.children[name]
        for child in self.children.values():
            hit = child.find(name)
            if hit is not None:
                return hit
        return None

    def walk(self):
        """Alle Structs rekursiv liefern (inkl. self)."""
        yield self
        for child in self.children.values():
            yield from child.walk()


# Trailing ':' kommt in AIGlobals.cfg vor ("AISettings : struct.begin:")
_STRUCT_BEGIN = re.compile(
    r"^(?P<name>[^=:]+?)\s*:\s*struct\.begin(?:\s*\{(?P<attrs>[^}]*)\})?\s*:?\s*$"
)
_KEY_VALUE = re.compile(r"^(?P<key>[^=:]+?)\s*=\s*(?P<value>.*)$")


def _strip_comment(line: str) -> str:
    # Kommentare beginnen mit // (Strings mit // in Werten sind in GameData
    # praktisch nicht vorhanden; Pfade nutzen einzelne Slashes).
    idx = line.find("//")
    if idx >= 0:
        return line[:idx]
    return line


def parse(text: str, root_name: str = "<root>") -> CfgStruct:
    """cfg-Text in einen CfgStruct-Baum parsen."""
    # BOM und exotische Whitespaces tolerieren
    text = text.lstrip("﻿")
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
            # Doppelte Namen (kommt bei Arrays nicht vor, [0], [1] sind eindeutig)
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

        # Unbekannte Zeile: ignorieren (robust bleiben)

    return root


def parse_file(path) -> CfgStruct:
    from pathlib import Path

    data = Path(path).read_bytes()
    # GameData-cfgs sind UTF-8 (teils mit BOM)
    return parse(data.decode("utf-8-sig", errors="replace"), root_name=str(path))


def parse_number(value: str | None, default: float = 0.0) -> float:
    """GSC-Zahlenliterale wie '24.f', '0.3f', '100', '1000.f;', '2%' nach float.

    Trailing ';' (AIGlobals.cfg) und '%'-Literale werden toleriert;
    '2%' liefert 2.0 (Prozentzahl, NICHT 0.02)."""
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
