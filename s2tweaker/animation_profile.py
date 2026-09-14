"""Strict offline serializer for the native animation companion numeric-profile class.

This is not a general game-save editor. It rejects every other class/schema.
The template is created by Unreal and contains no player progress or game assets.
"""
from dataclasses import dataclass
import math
import re
import struct

CLASS = '/S2TRuntimeLab/BP_S2TProfile.BP_S2TProfile_C'
MAX_SIZE = 256 * 1024


class Reader:
    def __init__(self, data):
        if len(data) > MAX_SIZE:
            raise ValueError('Profile exceeds size limit')
        self.data, self.pos = data, 0

    def read(self, size):
        if size < 0 or self.pos + size > len(self.data):
            raise ValueError('Truncated profile')
        result = self.data[self.pos:self.pos + size]
        self.pos += size
        return result

    def i32(self):
        return struct.unpack('<i', self.read(4))[0]

    def string(self):
        size = self.i32()
        if not 1 <= size <= MAX_SIZE:
            raise ValueError('Expected bounded ASCII FString')
        value = self.read(size)
        if value[-1:] != b'\0' or b'\0' in value[:-1]:
            raise ValueError('Invalid FString terminator')
        return value[:-1].decode('ascii')


def validate_payload(payload):
    if not isinstance(payload, str) or len(payload) > 64000:
        raise ValueError('Invalid numeric-profile payload')
    lines = payload.split('\n')
    if lines[0] != 'S2T1':
        raise ValueError('Unknown profile schema')
    seen = set()
    for line in lines[1:]:
        if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_.]*=[0-9]+(?:\.[0-9]+)?', line):
            raise ValueError('Invalid profile entry')
        key, text = line.split('=')
        value = float(text)
        if key in seen or not math.isfinite(value) or not 0 < value <= 100:
            raise ValueError('Duplicate key or invalid positive multiplier')
        seen.add(key)
    return payload


@dataclass
class Profile:
    source: bytes
    size_offset: int
    data_start: int
    data_end: int
    payload: str

    def encode(self, payload):
        body = validate_payload(payload).encode('ascii') + b'\0'
        field = struct.pack('<i', len(body)) + body
        result = (self.source[:self.size_offset] + struct.pack('<i', len(field))
                  + self.source[self.size_offset + 4:self.data_start]
                  + field + self.source[self.data_end:])
        if parse(result).payload != payload:
            raise ValueError('Serializer roundtrip failed')
        return result


def parse(data):
    r = Reader(data)
    if r.read(4) != b'GVAS' or r.i32() != 3:
        raise ValueError('Unsupported SaveGame format')
    if (r.i32(), r.i32()) != (522, 1013):
        raise ValueError('Unsupported package version')
    if struct.unpack('<HHH', r.read(6)) != (5, 5, 4):
        raise ValueError('Unsupported engine version')
    r.read(4)  # Native engine changelist.
    r.string()  # Native engine branch.
    if r.i32() != 3:
        raise ValueError('Unsupported custom-version format')
    count = r.i32()
    if not 0 <= count <= 1024:
        raise ValueError('Invalid custom-version count')
    r.read(count * 20)
    if r.string() != CLASS or r.read(1) != b'\0':
        raise ValueError('Not our tagged numeric-profile class')
    if (r.string(), r.string(), r.i32()) != ('ProfileData', 'StrProperty', 0):
        raise ValueError('Unexpected profile property')
    size_offset = r.pos
    size = r.i32()
    if r.read(1) != b'\x02':
        raise ValueError('Unexpected string-property flags')
    r.read(16)  # Blueprint member GUID, preserved from our native template.
    start = r.pos
    payload = validate_payload(r.string())
    end = r.pos
    if end - start != size:
        raise ValueError('String-property size mismatch')
    if (r.string(), r.string(), r.i32(), r.i32()) != ('ProfileSchema', 'IntProperty', 0, 4):
        raise ValueError('Unexpected schema property')
    if r.read(1) != b'\x02':
        raise ValueError('Unexpected schema-property flags')
    r.read(16)
    if r.i32() != 1 or r.string() != 'None' or r.i32() != 0 or r.pos != len(data):
        raise ValueError('Invalid schema or unexpected trailing data')
    return Profile(data, size_offset, start, end, payload)
