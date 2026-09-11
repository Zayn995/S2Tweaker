"""Strict readers for installed locres formats 1/3 and a Compact alias writer.

No translations ship with the application. See JOB_LOCALIZATION_ASSETS_RESEARCH.
"""
from collections import Counter
import struct

MAGIC = bytes.fromhex("0e147475674a03fc4a15909dc3377f1b")


class ResourceError(ValueError):
    pass


def read_resource(raw):
    """Return {(namespace, key): (source_hash, text)}; reject incomplete input."""
    if len(raw) < 29 or raw[:16] != MAGIC or raw[16] not in (1, 3):
        raise ResourceError("Unsupported localization resource format (expected Compact 1 or optimized 3).")
    version, pos = raw[16], 17

    def read(fmt):
        nonlocal pos
        size = struct.calcsize(fmt)
        if size > len(raw) - pos:
            raise ResourceError("Truncated localization resource.")
        value = struct.unpack_from(fmt, raw, pos)[0]
        pos += size
        return value

    def count():
        value = read("<I")
        if value > len(raw) // 4:
            raise ResourceError("Invalid localization entry count.")
        return value

    def string():
        nonlocal pos
        length = read("<i")
        if not length:
            return ""
        size, unit = (length, 1) if length > 0 else (-length * 2, 2)
        if size > len(raw) - pos:
            raise ResourceError("Truncated localization string.")
        value = raw[pos:pos + size]
        pos += size
        if value[-unit:] != b"\0" * unit:
            raise ResourceError("Unterminated localization string.")
        try:
            return value[:-unit].decode("utf-8" if unit == 1 else "utf-16-le")
        except UnicodeError as exc:
            raise ResourceError("Invalid localization string encoding.") from exc

    offset = read("<q")
    total = count() if version == 3 else None
    records, identities = [], set()
    for _ in range(count()):
        if version == 3:
            read("<I")  # Serialized key hashes belong to the engine's algorithm.
        namespace = string()
        for _ in range(count()):
            if version == 3:
                read("<I")
            key = string()
            identity = namespace, key
            if identity in identities:
                raise ResourceError("Duplicate localization identity.")
            identities.add(identity)
            records.append((identity, read("<I"), read("<i")))
    if pos != offset or (total is not None and len(records) != total):
        raise ResourceError("Localization table size does not match its header.")
    strings, references = [], []
    for _ in range(count()):
        strings.append(string())
        if version == 3:
            references.append(read("<i"))
    if pos != len(raw) or any(not 0 <= row[2] < len(strings) for row in records):
        raise ResourceError("Invalid localization string table.")
    if version == 3:
        counts = Counter(row[2] for row in records)
        if any(counts[i] != expected for i, expected in enumerate(references)):
            raise ResourceError("Localization string reference counts do not match.")
    return {identity: (source_hash, strings[index]) for identity, source_hash, index in records}


def write_resource(namespace, entries):
    """Write only the supplied aliases in the locally verified Compact format."""
    def string(text):
        if not isinstance(text, str) or "\0" in text:
            raise ResourceError("Localization text must be a string without NUL.")
        if text.isascii():
            value = text.encode("ascii") + b"\0"
            return struct.pack("<i", len(value)) + value
        value = text.encode("utf-16-le") + b"\0\0"
        return struct.pack("<i", -len(value) // 2) + value

    rows = sorted(entries.items())
    table = bytearray(struct.pack("<I", 1) + string(namespace) + struct.pack("<I", len(rows)))
    pool = bytearray(struct.pack("<I", len(rows)))
    for index, (key, (source_hash, text)) in enumerate(rows):
        if type(source_hash) is not int or not 0 <= source_hash <= 0xffffffff:
            raise ResourceError("Invalid localization source hash.")
        table += string(key) + struct.pack("<Ii", source_hash, index)
        pool += string(text)
    return MAGIC + b"\x01" + struct.pack("<q", 25 + len(table)) + table + pool
