#!/usr/bin/env python3
"""
bin2cfg.py by joric, https://github.com/joric/stalker/wiki

Converts Stalker 2 ".bin" configs back into the human-readable ".cfg" text format.

* Based on JSON Converter by sdwvit: https://github.com/sdwvit/S2CfgToJSON
* Binary reader PR by thexii: https://github.com/sdwvit/S2CfgToJSON/pull/1

Usage:
    python3 bin2cfg.py input.cfg.bin [output.cfg]
    python3 bin2cfg.py some_directory [-o output_directory]

If output path is omitted for a single file, it defaults to replacing
".bin" suffix (input.cfg.bin -> input.cfg), or appending ".cfg" if
there's no ".bin" suffix to strip.

If the input path is a directory, every "*.cfg.bin" file found in it
(recursively) is converted. By default each converted ".cfg" file is
written right next to its source ".cfg.bin" file. Pass -o/--output-dir
to instead mirror the directory tree under a separate output root.

Updates:

* 2026-08-26: Preserved numeric literals, fixed float infinity, added progress

"""

from __future__ import annotations

import re
import shutil
import struct
import sys
from pathlib import Path
from typing import List, Optional, Tuple, Union

TAB = "   "  # 3 spaces, matches Struct.mts's `const TAB = "   "`
WILDCARD = "_wildcard"
KEYWORDS = ["refurl", "refkey", "bskipref", "bpatch"]
REMOVE_NODE = "removenode"


# --------------------------------------------------------------------------
# Node / Refs -- python stand-ins for the JS `Struct` / `Refs` classes
# --------------------------------------------------------------------------


class Refs:
    __slots__ = (
        "rawName",
        "refurl",
        "refkey",
        "bskipref",
        "bpatch",
        "isArray",
        "isRoot",
        "useAsterisk",
        "removenode",
    )

    def __init__(self):
        self.rawName: Optional[str] = None
        self.refurl: Optional[str] = None
        self.refkey: Optional[Union[str, int]] = None
        self.bskipref: Optional[bool] = None
        self.bpatch: Optional[bool] = None
        self.isArray: Optional[bool] = None
        self.isRoot: Optional[bool] = None
        self.useAsterisk: Optional[bool] = None
        self.removenode: Optional[bool] = None

    def to_string(self) -> str:
        parts = []
        for k in KEYWORDS:
            v = getattr(self, k)
            if v is None or v == "" or v is False:
                continue
            if v is True:
                parts.append(k)
            elif k == "refkey":
                parts.append(f"{k}={render_key_name(str(v), self.useAsterisk)}")
            else:
                parts.append(f"{k}={v}")
        return ";".join(parts)


class Node:
    """Python stand-in for a `Struct` instance (an ordered bag of fields)."""

    __slots__ = ("__internal__", "_data", "_raw_literals")

    def __init__(self, raw_name: str = ""):
        self.__internal__ = Refs()
        self.__internal__.rawName = raw_name.strip()
        self._data: dict = {}
        # Mirrors the JS port's hidden, non-enumerable RAW_LITERALS slot:
        # remembers the exact source text for numeric fields so re-rendering
        # doesn't normalize e.g. "35.0" -> "35" or "3.20" -> "3.2".
        self._raw_literals: dict = {}

    # dict-like helpers -----------------------------------------------
    def __setitem__(self, key, value):
        self._data[str(key)] = value

    def __getitem__(self, key):
        return self._data[str(key)]

    def __contains__(self, key):
        return str(key) in self._data

    def get(self, key, default=None):
        return self._data.get(str(key), default)

    def entries(self) -> List[Tuple[str, object]]:
        return list(self._data.items())

    def keys_count(self) -> int:
        return len(self._data)

    def remember_raw_literal(self, key: Union[str, int], raw: str) -> None:
        value = self._data.get(str(key))
        # Only worth keeping when rendering the number would not reproduce
        # the original text (e.g. plain "3.2" round-trips fine on its own).
        if not isinstance(value, float) or js_number_to_string(value) == raw:
            return
        self._raw_literals[str(key)] = raw

    # serialization -----------------------------------------------------
    def to_string(self) -> str:
        text = f"{self.__internal__.rawName} : " if self.__internal__.isRoot else ""
        text += "struct.begin"
        refs = self.__internal__.to_string()
        if refs:
            text += f" {{{refs}}}"
        text += "\n"

        rendered_lines = []
        for key, value in self.entries():
            name_already_rendered = isinstance(value, Node) and value.__internal__.isRoot
            use_asterisk = bool(self.__internal__.isArray and self.__internal__.useAsterisk)

            key_or_index = ""
            equals_or_colon = ""
            space_or_no_space = ""
            if not name_already_rendered:
                key_or_index = render_key_name(key, use_asterisk) + " "
                equals_or_colon = ":" if isinstance(value, Node) else "="
                space_or_no_space = "" if value == "" else " "

            if isinstance(value, Node) and value.__internal__.removenode:
                rendered_value = REMOVE_NODE
            elif isinstance(value, Node):
                rendered_value = value.to_string()
            else:
                rendered_value = render_literal(self, key, value)

            line = f"{key_or_index}{equals_or_colon}{space_or_no_space}{rendered_value}"
            rendered_lines.append(pad(line))

        text += "\n".join(rendered_lines)
        text += "\nstruct.end"
        return text


def render_literal(parent: "Node", key: str, value):
    """Port of Struct.mts's renderLiteral(): prefer the original source text
    for a numeric field when it still holds the value that was parsed from
    it (a reassigned field renders its new value instead)."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        raw = parent._raw_literals.get(str(key))
        if raw is not None and parse_value(raw) == value:
            return raw
        return js_number_to_string(value)
    return value


def pad(text: str) -> str:
    return TAB + re.sub(r"\n+", f"\n{TAB}", text)


def js_number_to_string(value: float) -> str:
    """Mimic JS's `${number}` template interpolation for floats."""
    if value != value:  # NaN
        return "NaN"
    if value == float("inf"):
        return "Infinity"
    if value == float("-inf"):
        return "-Infinity"
    if value == int(value) and abs(value) < 1e21:
        return str(int(value))
    # JS uses the shortest round-trippable representation; Python's repr()
    # for floats does the same since 3.1.
    return repr(value)


# --------------------------------------------------------------------------
# key / value helpers (ports of parseKey / parseValue / renderKeyName /
# renderStructName from Struct.mts)
# --------------------------------------------------------------------------


def js_parse_int(s: str) -> Optional[int]:
    """Mimic JS parseInt(): parses a leading (optionally signed) integer,
    ignoring any trailing non-numeric characters. Returns None for NaN."""
    m = re.match(r"^\s*([+-]?\d+)", s)
    if not m:
        return None
    return int(m.group(1))


def is_number(ref: Union[str, int]) -> bool:
    if isinstance(ref, int):
        return True
    parsed = js_parse_int(str(ref))
    return parsed is not None


def extract_key_from_brackets(key: str) -> str:
    m = re.search(r"\[(.+)]", key)
    if m:
        return m.group(1)
    return ""


def render_key_name(key: Union[str, int], use_asterisk: Optional[bool] = None) -> str:
    key = str(key)
    if key.startswith("_"):
        return render_key_name(key[1:], use_asterisk)
    if "*" in key or use_asterisk:
        return "[*]"
    if "_dupe_" in key:
        return render_key_name(key[: key.index("_dupe_")])
    if is_number(key):
        return f"[{js_parse_int(key)}]"
    return key


def parse_key(key: str, parent: Node, index: int) -> Union[str, int]:
    norm_key: Union[str, int] = key
    if key.startswith("[") and key.endswith("]"):
        parent.__internal__.isArray = True
        norm_key = extract_key_from_brackets(key)
        if norm_key == "*":
            parent.__internal__.useAsterisk = True
            return parent.keys_count()
        if norm_key in parent:
            return f"{norm_key}_dupe_{index}"
        return norm_key
    if norm_key in parent:
        return f"{norm_key}_dupe_{index}"
    return norm_key


_VALUE_RE = re.compile(r"^(-?)(\d*)\.?(\d*)f?$")


def parse_value(value: str) -> Union[str, float, bool]:
    if value in ("true", "false"):
        return value == "true"
    m = _VALUE_RE.match(value)
    if m:
        minus, first, second = m.group(1), m.group(2), m.group(3)
        if first or second:
            sign = "-" if minus else ""
            whole = first or "0"
            frac = f".{second}" if second else ""
            try:
                return float(f"{sign}{whole}{frac}")
            except ValueError:
                pass
    return value


def assign_field(parent: Node, raw_key: str, value, index: int, raw: Optional[str] = None) -> None:
    key = parse_key(raw_key, parent, index)
    parent[key] = value
    if raw is not None:
        parent.remember_raw_literal(key, raw)


def is_empty_nested_struct(node: Node) -> bool:
    return (
        len(node.entries()) == 0
        and not node.__internal__.refkey
        and not node.__internal__.refurl
        and not node.__internal__.bpatch
        and not node.__internal__.bskipref
    )


# --------------------------------------------------------------------------
# Binary reader (port of binCfgParser.mjs)
# --------------------------------------------------------------------------


class BinaryCursor:
    def __init__(self, data: bytes):
        self.bytes = data
        self.position = 0

    @property
    def length(self) -> int:
        return len(self.bytes)

    def ensure_available(self, length: int) -> None:
        if self.position + length > self.length:
            raise ValueError("Unexpected end of binary cfg data.")

    def read_byte(self) -> int:
        self.ensure_available(1)
        value = self.bytes[self.position]
        self.position += 1
        return value

    def read_int32(self) -> int:
        self.ensure_available(4)
        value = struct.unpack_from("<i", self.bytes, self.position)[0]
        self.position += 4
        return value

    def read_uint32(self) -> int:
        self.ensure_available(4)
        value = struct.unpack_from("<I", self.bytes, self.position)[0]
        self.position += 4
        return value

    def read_bytes(self, length: int) -> bytes:
        self.ensure_available(length)
        start = self.position
        self.position += length
        return self.bytes[start:self.position]


def get_binary_string(index: int, string_pool: List[str]) -> str:
    if 1 <= index <= len(string_pool):
        return string_pool[index - 1]
    return ""


def read_binary_header(reader: BinaryCursor) -> List[str]:
    reader.read_uint32()  # version
    string_count = reader.read_int32()
    string_pool: List[str] = []
    reader.read_uint32()  # reserved

    for _ in range(string_count - 1):
        if reader.position + 4 > reader.length:
            break
        length = reader.read_int32()
        if length == 0:
            reader.position -= 4
            break
        if length < 0:
            length = abs(length)
            string_bytes = reader.read_bytes(length * 2)
            string_pool.append(string_bytes[:-2].decode("utf-16-le"))
            continue
        string_bytes = reader.read_bytes(length)
        if len(string_bytes) > 1:
            string_pool.append(string_bytes[:-1].decode("utf-8"))
        else:
            string_pool.append("")

    return string_pool


def skip_post_pool_padding(reader: BinaryCursor) -> None:
    if reader.position + 9 <= reader.length:
        reader.read_uint32()
        reader.read_uint32()
        reader.read_byte()


class BinaryBlock:
    __slots__ = ("values", "last_byte", "position")

    def __init__(self, values: List[int], last_byte: int, position: int):
        self.values = values
        self.last_byte = last_byte
        self.position = position


def read_binary_cfg_config(reader: BinaryCursor, pool_size: int) -> BinaryBlock:
    position = reader.position
    values: List[int] = []

    while reader.position + 4 <= reader.length:
        value = reader.read_int32()
        if value <= 0:
            break
        if value > pool_size:
            reader.position -= 4
            break
        values.append(value)

    last_byte = reader.read_byte()
    return BinaryBlock(values, last_byte, position)


def read_binary_link_pair(reader: BinaryCursor) -> Tuple[str, Optional[str]]:
    parent_length = reader.read_int32()
    parent_bytes = reader.read_bytes(parent_length)
    parent_name = parent_bytes[:-1].decode("utf-8")

    ref_length = reader.read_int32()
    ref_path: Optional[str] = None
    if ref_length > 0:
        ref_bytes = reader.read_bytes(ref_length)
        ref_path = ref_bytes[:-1].decode("utf-8")

    return parent_name, ref_path


def read_binary_struct(reader: BinaryCursor, string_pool: List[str]) -> Node:
    block = read_binary_cfg_config(reader, len(string_pool))
    name = get_binary_string(block.values[1], string_pool) if len(block.values) > 1 else ""
    node = Node(name)

    if block.last_byte > 0 and block.last_byte in (1, 5, 7):
        parent_name, ref_path = read_binary_link_pair(reader)
        if block.last_byte in (1, 7):
            node.__internal__.refkey = parent_name
            if ref_path:
                node.__internal__.refurl = ref_path

    fields_count = reader.read_int32()
    for current_field in range(fields_count):
        field_block = read_binary_cfg_config(reader, len(string_pool))
        if len(field_block.values) <= 1:
            continue

        field_name = get_binary_string(field_block.values[0], string_pool)
        n_values = len(field_block.values)
        if n_values == 2:
            reader.position = field_block.position
            nested = read_binary_struct(reader, string_pool)
            assign_field(
                node,
                field_name,
                "" if is_empty_nested_struct(nested) else nested,
                current_field,
            )
        elif n_values in (3, 4):
            raw_value = get_binary_string(field_block.values[2], string_pool).strip()
            assign_field(node, field_name, parse_value(raw_value), current_field, raw=raw_value)

    return node


def read_binary_cfg(data: bytes) -> List[Node]:
    reader = BinaryCursor(data)
    if reader.length < 12:
        return []

    string_pool = read_binary_header(reader)
    skip_post_pool_padding(reader)

    roots: List[Node] = []
    while reader.position < reader.length:
        if reader.position + 16 > reader.length:
            break
        childs_count = reader.read_int32()
        for _ in range(childs_count):
            root = read_binary_struct(reader, string_pool)
            root.__internal__.isRoot = True
            roots.append(root)

    return roots


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def convert(input_path: Path, output_path: Path, *, verbose: bool = True) -> Tuple[int, int]:
    """Converts one .cfg.bin file to text. Returns (num_roots, output_char_count)."""
    data = input_path.read_bytes()
    roots = read_binary_cfg(data)
    text = "\n".join(root.to_string() for root in roots)
    output_path.write_text(text, encoding="utf-8")
    if verbose:
        print(f"Parsed {len(roots)} root struct(s).")
        print(f"Wrote {output_path} ({len(text)} chars).")
    return len(roots), len(text)


def default_output_path(input_path: Path) -> Path:
    name = input_path.name
    if name.endswith(".cfg.bin"):
        return input_path.with_name(name[: -len(".bin")])
    if input_path.suffix == ".bin":
        return input_path.with_suffix("")
    return input_path.with_suffix(input_path.suffix + ".cfg")


def find_bin_files(root: Path) -> List[Path]:
    return sorted(p for p in root.rglob("*.cfg.bin") if p.is_file())


def _format_size(num_bytes: int) -> str:
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f}{unit}" if unit == "B" else f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}GB"


def _progress_line(done: int, total: int, failed: int, size_bytes: int, current: str) -> str:
    width = len(str(total))
    pct = (done / total * 100) if total else 100.0
    prefix = f"[{done:>{width}}/{total}] {pct:5.1f}%  failed:{failed}  {_format_size(size_bytes):>7}  "
    term_width = shutil.get_terminal_size((100, 20)).columns
    room = max(term_width - len(prefix) - 1, 10)
    if len(current) > room:
        current = "…" + current[-(room - 1):]
    return prefix + current


def convert_directory(input_dir: Path, output_dir: Optional[Path]) -> int:
    bin_files = find_bin_files(input_dir)
    total = len(bin_files)
    if total == 0:
        print(f"No *.cfg.bin files found under {input_dir}")
        return 0

    print(f"Found {total} *.cfg.bin file(s) under {input_dir}")
    term_width = shutil.get_terminal_size((100, 20)).columns
    ok = 0
    failed = 0
    is_tty = sys.stdout.isatty()

    for i, bin_path in enumerate(bin_files, start=1):
        rel = bin_path.relative_to(input_dir)
        if output_dir is None:
            out_path = default_output_path(bin_path)
        else:
            out_path = output_dir / default_output_path(rel)
            out_path.parent.mkdir(parents=True, exist_ok=True)

        size_bytes = bin_path.stat().st_size
        line = _progress_line(i, total, failed, size_bytes, str(rel))
        if is_tty:
            sys.stdout.write("\r" + line.ljust(term_width))
            sys.stdout.flush()
        else:
            print(line)

        try:
            convert(bin_path, out_path, verbose=False)
            ok += 1
        except Exception as exc:  # keep going on a per-file parse error
            failed += 1
            if is_tty:
                sys.stdout.write("\r" + " " * term_width + "\r")
            print(f"FAILED: {bin_path} ({exc})", file=sys.stderr)

    if is_tty:
        sys.stdout.write("\r" + " " * term_width + "\r")
    print(f"Done. {ok} converted, {failed} failed, {total} total.")
    return 1 if failed else 0


def main(argv: List[str]) -> int:
    if not argv:
        print(__doc__)
        return 1

    output_dir: Optional[Path] = None
    positional: List[str] = []
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg in ("-o", "--output-dir"):
            if i + 1 >= len(argv):
                print(f"{arg} requires a directory argument", file=sys.stderr)
                return 1
            output_dir = Path(argv[i + 1])
            i += 2
            continue
        positional.append(arg)
        i += 1

    if not positional:
        print(__doc__)
        return 1

    input_path = Path(positional[0])
    if not input_path.exists():
        print(f"Input path not found: {input_path}", file=sys.stderr)
        return 1

    if input_path.is_dir():
        return convert_directory(input_path, output_dir)

    output_path = Path(positional[1]) if len(positional) > 1 else default_output_path(input_path)
    convert(input_path, output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
