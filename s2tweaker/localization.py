"""Strict locres readers and byte-preserving native journal alias insertion.

No translations ship with the application. See JOB_LOCALIZATION_LOADING_FOLLOWUP.
"""
from collections import Counter
from collections.abc import Mapping
import struct

from ._cityhash import key_hash

MAGIC = bytes.fromhex("0e147475674a03fc4a15909dc3377f1b")


class ResourceError(ValueError):
    pass


def _parse_resource(raw):
    """Validate the resource and retain offsets needed to preserve source bytes."""
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
            text = value[:-unit].decode("utf-8" if unit == 1 else "utf-16-le")
        except UnicodeError as exc:
            raise ResourceError("Invalid localization string encoding.") from exc
        if "\0" in text:
            raise ResourceError("Embedded NUL in localization string.")
        return text

    offset = read("<q")
    total = count() if version == 3 else None
    records, identities, namespaces = [], set(), {}
    for _ in range(count()):
        namespace_hash = read("<I") if version == 3 else None
        namespace = string()
        if namespace in namespaces:
            raise ResourceError("Duplicate localization namespace.")
        count_at = pos
        entry_count = count()
        for _ in range(entry_count):
            hashed_key = read("<I") if version == 3 else None
            key = string()
            identity = namespace, key
            if identity in identities:
                raise ResourceError("Duplicate localization identity.")
            identities.add(identity)
            records.append((identity, read("<I"), read("<i"), hashed_key))
        namespaces[namespace] = (namespace_hash, count_at, entry_count, pos)
    if pos != offset or (total is not None and len(records) != total):
        raise ResourceError("Localization table size does not match its header.")
    strings, references, reference_offsets = [], [], []
    for _ in range(count()):
        strings.append(string())
        if version == 3:
            reference_offsets.append(pos)
            references.append(read("<i"))
    if pos != len(raw) or any(not 0 <= row[2] < len(strings) for row in records):
        raise ResourceError("Invalid localization string table.")
    if version == 3:
        counts = Counter(row[2] for row in records)
        if any(counts[i] != expected for i, expected in enumerate(references)):
            raise ResourceError("Localization string reference counts do not match.")
    return version, offset, records, strings, namespaces, references, reference_offsets


def read_resource(raw):
    """Return {(namespace, key): (source_hash, text)}; reject incomplete input."""
    _, _, records, strings, _, _, _ = _parse_resource(raw)
    return {identity: (source_hash, strings[index])
            for identity, source_hash, index, _ in records}


def _write_string(text):
    if not isinstance(text, str) or "\0" in text:
        raise ResourceError("Localization text must be a string without NUL.")
    try:
        if text.isascii():
            value = text.encode("ascii") + b"\0"
            return struct.pack("<i", len(value)) + value
        value = text.encode("utf-16-le") + b"\0\0"
        return struct.pack("<i", -len(value) // 2) + value
    except (UnicodeError, struct.error) as exc:
        raise ResourceError("Invalid localization string encoding or length.") from exc


def append_aliases(raw, namespace, aliases):
    """Add aliases to the native resource without rewriting existing records/text.

    Alias values name existing keys in this namespace. The existing pool slots
    are reused; version 3 reference counts advance accordingly. Neither source
    text hashes nor existing identity hashes are recalculated for serialization.
    """
    if not aliases:
        return raw
    if (not isinstance(namespace, str) or "\0" in namespace
            or not isinstance(aliases, Mapping)
            or any(not isinstance(k, str) or not k or "\0" in k
                   or not isinstance(v, str) or not v or "\0" in v
                   for k, v in aliases.items())):
        raise ResourceError("Invalid localization alias identity.")
    version, offset, records, _, namespaces, refs, ref_offsets = _parse_resource(raw)
    if namespace not in namespaces:
        raise ResourceError("Missing localization namespace for aliases.")
    ns_hash, count_at, entry_count, insert_at = namespaces[namespace]
    rows = {identity[1]: (source_hash, index, hashed_key)
            for identity, source_hash, index, hashed_key in records if identity[0] == namespace}
    if version == 3 and ns_hash != key_hash(namespace):
        raise ResourceError("Unsupported localization namespace hash.")
    additions = bytearray()
    increments = Counter()
    for alias, original in sorted(aliases.items()):
        if alias in rows or original not in rows:
            raise ResourceError(f"Unsupported localization alias identity: {alias} -> {original}")
        source_hash, index, hashed_key = rows[original]
        alias_bytes = _write_string(alias)
        if version == 3:
            if hashed_key != key_hash(original):
                raise ResourceError(f"Unsupported localization source key hash: {original}")
            additions += struct.pack("<I", key_hash(alias))
        additions += alias_bytes + struct.pack("<Ii", source_hash, index)
        increments[index] += 1
    patched = bytearray(raw)
    if entry_count + len(aliases) > 0xffffffff or len(records) + len(aliases) > 0xffffffff:
        raise ResourceError("Too many localization aliases.")
    struct.pack_into("<q", patched, 17, offset + len(additions))
    struct.pack_into("<I", patched, count_at, entry_count + len(aliases))
    if version == 3:
        struct.pack_into("<I", patched, 25, len(records) + len(aliases))
        for index, added in increments.items():
            if refs[index] + added > 0x7fffffff:
                raise ResourceError("Too many localization string references.")
            struct.pack_into("<i", patched, ref_offsets[index], refs[index] + added)
    return bytes(patched[:insert_at] + additions + patched[insert_at:])


def write_resource(namespace, entries):
    """Write only the supplied aliases in the locally verified Compact format."""
    rows = sorted(entries.items())
    table = bytearray(struct.pack("<I", 1) + _write_string(namespace) + struct.pack("<I", len(rows)))
    pool = bytearray(struct.pack("<I", len(rows)))
    for index, (key, (source_hash, text)) in enumerate(rows):
        if type(source_hash) is not int or not 0 <= source_hash <= 0xffffffff:
            raise ResourceError("Invalid localization source hash.")
        table += _write_string(key) + struct.pack("<Ii", source_hash, index)
        pool += _write_string(text)
    return MAGIC + b"\x01" + struct.pack("<q", 25 + len(table)) + table + pool
