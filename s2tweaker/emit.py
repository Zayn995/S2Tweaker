"""Erzeugt Patch-cfg-Dateien im bpatch-Format von S.T.A.L.K.E.R. 2.

Eine Patch-Datei ist eine NEUE cfg-Datei unterhalb von
Stalker2/Content/GameLite/GameData/, die per {bpatch} nur einzelne Werte
bestehender Prototypen ueberschreibt, z.B.:

    Player : struct.begin {bpatch}
       VitalParams : struct.begin {bpatch}
          MaxHP = 300
       struct.end
    struct.end
"""

from __future__ import annotations

INDENT = "   "


def _emit_struct(name: str, content: dict, depth: int, lines: list[str]) -> None:
    pad = INDENT * depth
    # "__attrs__" = zusaetzliche Struct-Attribute, z.B. refkey=Basis fuer einen
    # NEUEN Knoten, der von einem vorhandenen erbt ({refkey=X;bpatch},
    # sdwvit-Muster; seit 1.27.0 fuer die Pro-Fernrohr-Effekte)
    attrs = content.get("__attrs__")
    head = f"{attrs};bpatch" if attrs else "bpatch"
    lines.append(f"{pad}{name} : struct.begin {{{head}}}")
    for key, value in content.items():
        if key == "__attrs__":
            continue
        if isinstance(value, dict):
            _emit_struct(key, value, depth + 1, lines)
        else:
            # Leerer Wert (= Liste leeren, z.B. Upgrade-Sperren): "Key ="
            # ohne Leerzeichen dahinter, wie das Spiel es selbst schreibt
            lines.append(f"{pad}{INDENT}{key} = {value}".rstrip())
    lines.append(f"{pad}struct.end")


def emit_patch(patches: dict[str, dict]) -> str:
    """Patch-cfg-Text erzeugen.

    patches: {"Player": {"VitalParams": {"MaxHP": 300}}, "Boar": {...}}
    Verschachtelte dicts werden zu verschachtelten {bpatch}-Structs,
    alle anderen Werte zu `Key = Wert`-Zeilen (Wert wird str()-formatiert,
    der Aufrufer ist fuer das Format wie `0.3f` selbst verantwortlich).
    """
    lines: list[str] = []
    for name, content in patches.items():
        _emit_struct(name, content, 0, lines)
        lines.append("")
    return "\n".join(lines)


def fmt_float(x: float) -> str:
    """Float im GameData-Stil formatieren (ohne unnoetige Nullen)."""
    s = f"{x:.6f}".rstrip("0").rstrip(".")
    if "." not in s:
        s += ".0"
    return s
