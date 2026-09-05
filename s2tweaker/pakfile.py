"""Unreal-Pak-Dateien lesen und schreiben - in reinem Python, ohne repak.exe.

Warum es das gibt (05.09.2026)
------------------------------
Bis 1.22.0 erledigte das mitgelieferte repak.exe (Rust, von uns aus dem
Quelltext gebaut) das Entpacken der Spieldateien und das Packen der Mod.
Es war die einzige unsignierte ausfuehrbare Datei im Paket - und genau die
markierte Microsofts Machine-Learning-Erkennung am 05.09.2026 als
"Trojan:Win32/Wacatac.B!ml" bzw. "Bearfoos.A!ml", zweimal hintereinander,
fuer Binaerdateien, die sich nur im Zeitstempel unterschieden. Ein
unsigniertes Rust-Programm, das eine DLL per Namen laedt, ist fuer solche
Modelle ein verdaechtiges Muster, egal was es tut.

Dieses Modul ersetzt repak vollstaendig. Es braucht nur die Standard-
bibliothek: struct, zlib, hashlib, ctypes. Die proprietaere Oodle-DLL
(oo2core_9_win64.dll) wird - wie bisher - vom Nutzer einmal danebengelegt
und dann per ctypes geladen; heruntergeladen wird nichts (pakio.py).

Das Format
----------
Die Implementierung folgt dem Pak-Format von Unreal Engine 4/5, wie es
repak (https://github.com/trumank/repak, MIT OR Apache-2.0) liest und
schreibt. Verifiziert am 05.09.2026 gegen repak 0.2.3: eine von uns
geschriebene Mod-Pak hat denselben Index, dieselben Eintragskoepfe, Hashes
und Inhalte wie die von repak gepackte (nur die Reihenfolge der Datensaetze
unterscheidet sich - repak packt parallel und schreibt sie in zufaelliger
Reihenfolge, wir sortiert), repak liest unsere Paks, und die aus pakchunk0
und 27 fremden Mod-Paks entpackten Dateien sind byteidentisch mit denen,
die repak entpackt (tests/test_pakfile.py).

    [Datensatz je Datei: Eintragskopf + Rohdaten] ...
    [Index: Mount-Point, Anzahl, je Datei Pfad + Eintragskopf mit Offset]
    [Footer: Magic, Version, Index-Offset/-Groesse, SHA-1 des Index, ...]

Gelesen werden die Versionen 1 bis 11 (Spielpaks: 11, Mod-Paks: meist 8B),
mit Zlib, Gzip und Oodle als Kompression. Verschluesselte Paks und Zstd/LZ4
werden als klarer Fehler gemeldet (kommen bei S.T.A.L.K.E.R. 2 nicht vor).
Geschrieben wird immer Version 8B, unkomprimiert, Mount-Point ../../../ -
exakt die repak-Vorgaben, mit denen Mod-Paks im Spiel nachweislich laufen.
"""
from __future__ import annotations

import ctypes
import hashlib
import re
import struct
import zlib
from dataclasses import dataclass, field
from pathlib import Path

MAGIC = 0x5A6F12E1
MOUNT_POINT = "../../../"
STRIP_PREFIX = ("..", "..", "..")

# Kompressionsnamen im Footer (ab Version 8 als Text, davor feste Liste)
ZLIB, GZIP, OODLE, ZSTD, LZ4 = "Zlib", "Gzip", "Oodle", "Zstd", "LZ4"
_FIXED_COMPRESSION = [ZLIB, GZIP, OODLE]


class PakError(RuntimeError):
    """Pak unlesbar, unbekannte Version, verschluesselt, Eintrag fehlt ..."""


class OodleNeeded(PakError):
    """Ein Eintrag ist Oodle-komprimiert, aber es wurde keine DLL uebergeben."""


@dataclass(frozen=True)
class PakVersion:
    label: str          # V11, V8B, ...
    major: int          # im Footer gespeicherte Versionsnummer
    footer_size: int
    names: int          # Anzahl der 32-Byte-Kompressionsnamen im Footer
    compression_u8: bool = False   # nur V8A: Kompressionsindex als u8


def _footer_size(major: int, names: int) -> int:
    size = 4 + 4 + 8 + 8 + 20
    if major >= 7:
        size += 16          # encryption key guid
    if major >= 4:
        size += 1           # encrypted index flag
    if major == 9:
        size += 1           # frozen index flag
    return size + 32 * names


# Reihenfolge = Probierreihenfolge beim Lesen (neueste zuerst), wie repak.
VERSIONS = [
    PakVersion("V11", 11, _footer_size(11, 5), 5),
    PakVersion("V10", 10, _footer_size(10, 5), 5),
    PakVersion("V9", 9, _footer_size(9, 5), 5),
    PakVersion("V8B", 8, _footer_size(8, 5), 5),
    PakVersion("V8A", 8, _footer_size(8, 4), 4, compression_u8=True),
    PakVersion("V7", 7, _footer_size(7, 0), 0),
    PakVersion("V6", 6, _footer_size(6, 0), 0),
    PakVersion("V5", 5, _footer_size(5, 0), 0),
    PakVersion("V4", 4, _footer_size(4, 0), 0),
    PakVersion("V3", 3, _footer_size(3, 0), 0),
    PakVersion("V2", 2, _footer_size(2, 0), 0),
    PakVersion("V1", 1, _footer_size(1, 0), 0),
]
V8B = VERSIONS[3]


@dataclass
class Entry:
    offset: int
    compressed: int
    uncompressed: int
    compression: int | None        # Index in die Kompressionsliste des Footers
    blocks: list[tuple[int, int]] | None = None
    flags: int = 0
    block_size: int = 0
    hash: bytes = b""

    @property
    def encrypted(self) -> bool:
        return bool(self.flags & 1)


# --- Lesehilfen -----------------------------------------------------------

class _Reader:
    """Kleiner Cursor ueber ein bytes-Objekt."""
    __slots__ = ("buf", "pos")

    def __init__(self, buf: bytes, pos: int = 0):
        self.buf, self.pos = buf, pos

    def take(self, n: int) -> bytes:
        if self.pos + n > len(self.buf):
            raise PakError("unexpected end of data")
        out = self.buf[self.pos:self.pos + n]
        self.pos += n
        return out

    def u8(self) -> int:
        return self.take(1)[0]

    def u32(self) -> int:
        return struct.unpack("<I", self.take(4))[0]

    def i32(self) -> int:
        return struct.unpack("<i", self.take(4))[0]

    def u64(self) -> int:
        return struct.unpack("<Q", self.take(8))[0]

    def string(self) -> str:
        """FString: i32 Laenge inkl. NUL; negativ = UTF-16LE."""
        n = self.i32()
        if n < 0:
            raw = self.take(-n * 2)
            text = raw.decode("utf-16-le", errors="replace")
        else:
            raw = self.take(n)
            text = raw.decode("utf-8", errors="replace")
        cut = text.find("\0")
        return text if cut < 0 else text[:cut]


def _write_string(value: str) -> bytes:
    if value == "" or value.isascii():
        return struct.pack("<I", len(value) + 1) + value.encode("ascii") + b"\0"
    data = value.encode("utf-16-le")
    return struct.pack("<i", -(len(data) // 2 + 1)) + data + b"\0\0"


def _entry_size(version: PakVersion, compression: int | None, block_count: int) -> int:
    """Groesse des Eintragskopfs vor den Rohdaten (repak: get_serialized_size)."""
    size = 8 + 8 + 8 + (1 if version.compression_u8 else 4)
    if version.major == 1:
        size += 8           # timestamp
    size += 20              # hash
    if compression is not None:
        size += 4 + 16 * block_count
    size += 1               # flags
    if version.major >= 3:
        size += 4           # block size
    return size


def _read_entry(r: _Reader, version: PakVersion) -> Entry:
    offset = r.u64()
    compressed = r.u64()
    uncompressed = r.u64()
    comp = r.u8() if version.compression_u8 else r.u32()
    compression = None if comp == 0 else comp - 1
    if version.major == 1:
        r.u64()             # timestamp
    digest = r.take(20)
    blocks = None
    if version.major >= 3 and compression is not None:
        blocks = [(r.u64(), r.u64()) for _ in range(r.u32())]
    flags = r.u8() if version.major >= 3 else 0
    block_size = r.u32() if version.major >= 3 else 0
    return Entry(offset, compressed, uncompressed, compression, blocks,
                 flags, block_size, digest)


def _read_encoded_entry(r: _Reader, version: PakVersion) -> Entry:
    """Kompakte Eintraege des Index ab Version 10 (repak: read_encoded)."""
    bits = r.u32()
    comp = (bits >> 23) & 0x3F
    compression = None if comp == 0 else comp - 1
    encrypted = bool(bits & (1 << 22))
    block_count = (bits >> 6) & 0xFFFF
    block_size = bits & 0x3F
    block_size = r.u32() if block_size == 0x3F else block_size << 11

    def var_int(bit: int) -> int:
        return r.u32() if bits & (1 << bit) else r.u64()

    offset = var_int(31)
    uncompressed = var_int(30)
    compressed = uncompressed if compression is None else var_int(29)
    base = _entry_size(version, compression, block_count)
    blocks = None
    if block_count == 1 and not encrypted:
        blocks = [(base, base + compressed)]
    elif block_count > 0:
        blocks = []
        index = base
        for _ in range(block_count):
            size = r.u32()
            blocks.append((index, index + size))
            if encrypted:
                size = (size + 15) & ~15
            index += size
    return Entry(offset, compressed, uncompressed, compression, blocks,
                 int(encrypted), block_size)


# --- Lesen ----------------------------------------------------------------

class PakFile:
    """Eine Pak lesen: Index beim Oeffnen, Eintraege bei Bedarf.

        with PakFile(path) as pak:
            for name in pak.files():
                data = pak.read(name)

    `oodle`: Callable(comp: bytes, raw_len: int) -> bytes, wird nur fuer
    Oodle-komprimierte Eintraege gebraucht (pakio.oodle_decompressor)."""

    def __init__(self, path: Path | str, oodle=None):
        self.path = Path(path)
        self._oodle = oodle
        self._fh = open(self.path, "rb")
        try:
            self._load()
        except Exception:
            self._fh.close()
            raise

    def __enter__(self) -> "PakFile":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def close(self) -> None:
        if self._fh is not None:
            self._fh.close()
            self._fh = None

    # -- Index ------------------------------------------------------------

    def _load(self) -> None:
        self._fh.seek(0, 2)
        total = self._fh.tell()
        errors = []
        for version in VERSIONS:
            if version.footer_size > total:
                continue
            self._fh.seek(total - version.footer_size)
            try:
                footer = self._parse_footer(self._fh.read(version.footer_size), version)
            except PakError as exc:
                errors.append(f"{version.label}: {exc}")
                continue
            self.version = version
            self.index_offset, index_size, self.encrypted_index, self.compression = footer
            break
        else:
            raise PakError("not a pak file (no valid footer): "
                           + "; ".join(errors[:3]))
        if self.encrypted_index:
            raise PakError("encrypted index - this tool does not support encrypted paks")
        self._fh.seek(self.index_offset)
        index = _Reader(self._fh.read(index_size))
        self.mount_point = index.string()
        count = index.u32()
        self.entries: dict[str, Entry] = {}
        if self.version.major >= 10:
            self._load_index_v10(index)
        else:
            for _ in range(count):
                name = index.string()
                self.entries[name] = _read_entry(index, self.version)

    def _parse_footer(self, raw: bytes, version: PakVersion):
        r = _Reader(raw)
        if version.major >= 7:
            r.take(16)                       # encryption key guid
        encrypted = bool(r.u8()) if version.major >= 4 else False
        magic = r.u32()
        if magic != MAGIC:
            raise PakError(f"bad magic {magic:#x}")
        major = r.u32()
        if major != version.major:
            raise PakError(f"footer says version {major}")
        index_offset = r.u64()
        index_size = r.u64()
        r.take(20)                           # index hash
        if version.major == 9:
            r.u8()                           # frozen index
        names = []
        for _ in range(version.names):
            text = r.take(32).split(b"\0", 1)[0].decode("ascii", errors="replace")
            names.append(text or None)
        if version.major < 8:
            names += _FIXED_COMPRESSION
        return index_offset, index_size, encrypted, names

    def _load_index_v10(self, index: _Reader) -> None:
        index.u64()                          # path hash seed
        if index.u32():                      # path hash index (nicht gebraucht)
            index.u64(); index.u64(); index.take(20)
        directories = None
        if index.u32():                      # full directory index
            fdi_offset = index.u64()
            fdi_size = index.u64()
            index.take(20)
            self._fh.seek(fdi_offset)
            fdi = _Reader(self._fh.read(fdi_size))
            directories = []
            for _ in range(fdi.u32()):
                dir_name = fdi.string()
                files = []
                for _ in range(fdi.u32()):
                    files.append((fdi.string(), fdi.i32()))
                directories.append((dir_name, files))
        encoded = _Reader(index.take(index.u32()))
        plain = [_read_entry(index, self.version) for _ in range(index.u32())]
        if directories is None:
            raise PakError("pak has no full directory index")
        for dir_name, files in directories:
            prefix = dir_name[1:] if dir_name.startswith("/") else dir_name
            for file_name, location in files:
                if location >= 0:
                    encoded.pos = location
                    entry = _read_encoded_entry(encoded, self.version)
                else:
                    entry = plain[-location - 1]
                self.entries[prefix + file_name] = entry

    # -- Zugriff ----------------------------------------------------------

    def files(self) -> list[str]:
        """Alle Eintragspfade (relativ zum Mount-Point), sortiert wie repak."""
        return sorted(self.entries)

    def full_path(self, name: str) -> str:
        """Mount-Point + Eintrag, z.B. ../../../Stalker2/Content/..."""
        if name.startswith("/"):
            return name
        if self.mount_point and not self.mount_point.endswith("/"):
            return self.mount_point + "/" + name
        return self.mount_point + name

    def stripped(self, name: str) -> str:
        """Pfad ohne das fuehrende ../../../ (repak: --strip-prefix)."""
        parts = [p for p in self.full_path(name).split("/") if p not in ("", ".")]
        if tuple(parts[:3]) != STRIP_PREFIX:
            raise PakError(f"path {self.full_path(name)!r} is not under {MOUNT_POINT}")
        return "/".join(parts[3:])

    def compression_of(self, name: str) -> str | None:
        entry = self.entries[name]
        if entry.compression is None:
            return None
        try:
            return self.compression[entry.compression]
        except IndexError:
            raise PakError(f"{name}: compression slot {entry.compression} unknown")

    def uses_oodle(self, names=None) -> bool:
        names = self.entries if names is None else names
        return any((self.compression_of(n) or "").lower() == "oodle" for n in names)

    def read(self, name: str) -> bytes:
        entry = self.entries.get(name)
        if entry is None:
            raise PakError(f"no such entry: {name}")
        if entry.encrypted:
            raise PakError(f"{name}: encrypted entries are not supported")
        self._fh.seek(entry.offset)
        head = self._fh.read(_entry_size(self.version, entry.compression,
                                         len(entry.blocks or ())))
        # Der Kopf vor den Daten wiederholt den Index-Eintrag; seine Laenge
        # bestimmt, wo die Daten beginnen (repak liest ihn genauso).
        r = _Reader(head)
        _read_entry(r, self.version)
        data_offset = entry.offset + r.pos
        self._fh.seek(data_offset)
        data = self._fh.read(entry.compressed)
        if len(data) != entry.compressed:
            raise PakError(f"{name}: truncated pak")
        method = self.compression_of(name)
        if method is None:
            return data
        # Blockgrenzen: ab Version 5 relativ zum Eintrag, davor absolut.
        if entry.blocks:
            base = data_offset - entry.offset if self.version.major >= 5 else data_offset
            ranges = [(start - base, end - base) for start, end in entry.blocks]
        else:
            ranges = [(0, len(data))]
        method_l = method.lower()
        if method_l == "zlib":
            return b"".join(zlib.decompress(data[a:b]) for a, b in ranges)
        if method_l == "gzip":
            return b"".join(zlib.decompress(data[a:b], 16 + zlib.MAX_WBITS)
                            for a, b in ranges)
        if method_l == "oodle":
            if self._oodle is None:
                raise OodleNeeded(f"{name} is Oodle-compressed")
            chunk = entry.uncompressed if len(ranges) == 1 else entry.block_size
            out = bytearray()
            remaining = entry.uncompressed
            for a, b in ranges:
                raw_len = min(chunk, remaining)
                out += self._oodle(data[a:b], raw_len)
                remaining -= raw_len
            if len(out) != entry.uncompressed:
                raise PakError(f"{name}: Oodle produced {len(out)} of "
                               f"{entry.uncompressed} bytes")
            return bytes(out)
        raise PakError(f"{name}: compression {method!r} is not supported")


# --- Oodle per ctypes -----------------------------------------------------

def load_oodle(dll: Path | str):
    """OodleLZ_Decompress der DLL als Python-Funktion (comp, raw_len) -> bytes.

    Signatur wie in repaks oodle_loader: fuzzSafe=1, checkCRC=1,
    threadPhase=3 (alles). Rueckgabe 0 heisst: Daten kaputt oder falsche DLL."""
    lib = ctypes.CDLL(str(dll))
    fn = lib.OodleLZ_Decompress
    fn.restype = ctypes.c_ssize_t
    fn.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_size_t,
                   ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_void_p,
                   ctypes.c_size_t, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
                   ctypes.c_size_t, ctypes.c_int]
    try:
        quiet = lib.OodleCore_Plugins_SetPrintf
        quiet.restype = None
        quiet.argtypes = [ctypes.c_void_p]
        quiet(None)                      # Oodle-Logausgaben abschalten
    except AttributeError:
        pass

    def decompress(comp: bytes, raw_len: int) -> bytes:
        if raw_len == 0:
            return b""
        src = (ctypes.c_char * len(comp)).from_buffer_copy(comp)
        dst = (ctypes.c_char * raw_len)()
        got = fn(src, len(comp), dst, raw_len, 1, 1, 0, None, 0, None, None, None, 0, 3)
        if got != raw_len:
            raise PakError(f"Oodle decompression failed ({got} of {raw_len} bytes)")
        return dst.raw

    decompress.library = lib
    return decompress


# --- Schreiben ------------------------------------------------------------

def write_pak(out_path: Path | str, files: list[tuple[str, bytes]],
              mount_point: str = MOUNT_POINT) -> Path:
    """Pak Version 8B, unkomprimiert, schreiben. `files` = [(pfad, bytes)]
    in der Reihenfolge, in der die Datensaetze liegen sollen; der Index ist
    - wie bei repak - nach Pfad sortiert."""
    out_path = Path(out_path)
    records: dict[str, tuple[int, int, bytes]] = {}
    with open(out_path, "wb") as fh:
        for name, data in files:
            digest = hashlib.sha1(data).digest()
            offset = fh.tell()
            fh.write(struct.pack("<QQQI", 0, len(data), len(data), 0))
            fh.write(digest)
            fh.write(b"\0" + struct.pack("<I", 0))
            fh.write(data)
            records[name] = (offset, len(data), digest)
        index = bytearray(_write_string(mount_point))
        index += struct.pack("<I", len(records))
        for name in sorted(records):
            offset, size, digest = records[name]
            index += _write_string(name)
            index += struct.pack("<QQQI", offset, size, size, 0) + digest
            index += b"\0" + struct.pack("<I", 0)
        index_offset = fh.tell()
        fh.write(index)
        fh.write(b"\0" * 16)                           # encryption key guid
        fh.write(b"\0")                                # encrypted index: no
        fh.write(struct.pack("<II", MAGIC, V8B.major))
        fh.write(struct.pack("<QQ", index_offset, len(index)))
        fh.write(hashlib.sha1(index).digest())
        fh.write(b"\0" * (32 * V8B.names))             # keine Kompression
    return out_path


def pack_dir(staging: Path | str, out_path: Path | str,
             mount_point: str = MOUNT_POINT) -> Path:
    """Einen Ordner packen wie `repak pack`: alle Dateien rekursiv, Pfade
    relativ zum Ordner mit '/', Datensaetze in Pfadkomponenten-Reihenfolge."""
    staging = Path(staging)
    if not staging.is_dir():
        raise PakError(f"input is not a directory: {staging}")
    paths = [p for p in staging.rglob("*") if p.is_file()]
    rel = {p: p.relative_to(staging).as_posix() for p in paths}
    paths.sort(key=lambda p: tuple(rel[p].split("/")))
    return write_pak(out_path, [(rel[p], p.read_bytes()) for p in paths], mount_point)


# --- Include-Muster (repak: -i, glob mit literalem '/') ---------------------

def glob_regex(pattern: str) -> re.Pattern:
    """Glob -> Regex: '*' und '?' laufen nicht ueber '/', '**' schon,
    '[...]' wie in fnmatch ('[[]' = literales '[')."""
    out, i = [], 0
    while i < len(pattern):
        ch = pattern[i]
        if ch == "*":
            if pattern[i:i + 2] == "**":
                out.append(".*")
                i += 2
                continue
            out.append("[^/]*")
        elif ch == "?":
            out.append("[^/]")
        elif ch == "[":
            j = pattern.find("]", i + 1)
            if j < 0:
                out.append(re.escape(ch))
            else:
                body = pattern[i + 1:j]
                if body.startswith("!"):
                    body = "^" + body[1:]
                body = body.replace("\\", "\\\\").replace("[", "\\[")
                out.append("[" + body + "]")
                i = j
        else:
            out.append(re.escape(ch))
        i += 1
    return re.compile("".join(out) + r"\Z")


def matches(patterns: list[re.Pattern], stripped: str) -> bool:
    """Trifft ein Muster den Pfad oder einen seiner Ordner (mit oder ohne
    Schraegstrich am Ende)? Genau die Regel von `repak unpack -i`."""
    candidates = [stripped]
    parts = stripped.split("/")
    for n in range(len(parts) - 1, 0, -1):
        folder = "/".join(parts[:n])
        candidates += [folder, folder + "/"]
    return any(p.match(c) for p in patterns for c in candidates)
