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


def _emit_struct(name: str, content: dict, depth: int, lines: list[str],
                 plain: bool = False) -> None:
    pad = INDENT * depth
    # "__attrs__" = zusaetzliche Struct-Attribute, z.B. refkey=Basis fuer einen
    # NEUEN Knoten, der von einem vorhandenen erbt ({refkey=X;bpatch},
    # sdwvit-Muster; seit 1.27.0 fuer die Pro-Fernrohr-Effekte)
    attrs = content.get("__attrs__")
    # "__new__" = ein Knoten, den es in Vanilla NICHT gibt (seit 1.33.0 fuer
    # die zusaetzlichen Quest-Knoten). Ein neuer Top-Level-Name wird vom
    # Spiel angehaengt (docs/SPEC.md par. 0) - dabei darf KEIN {bpatch}
    # stehen, sonst soll er etwas zusammenfuehren, das es nicht gibt.
    # Innerhalb eines neuen Knotens sind auch alle Kinder neu - sie duerfen
    # ebenfalls kein {bpatch} tragen (so schreibt es auch die Vorlage, Nexus
    # 2638). Darum wird das Kennzeichen nach unten durchgereicht.
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
