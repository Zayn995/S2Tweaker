"""Binary-format regressions using invented data; no game assets required."""
from pathlib import Path
import struct
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from s2tweaker import vendor_bin2cfg as binary


def ints(*values):
    return struct.pack('<' + 'i' * len(values), *values)


def fstring(value):
    raw = value.encode('utf-8') + b'\0'
    return ints(len(raw)) + raw


def fixture(version):
    """Same two roots in V1/V2, nested array, references and exact literals.

    Wire records: string IDs, zero, optional V2 source ID, flags;
    structs then carry any inheritance link followed by their child count.
    The source ID deliberately names a path, not a field or value.
    """
    pool = ['Base', 'SID', 'Amount', '35.0', 'Derived', 'Entries', '[0]',
            'EExample::Value', 'GameData/Invented.cfg']
    source = ints(9) if version == 2 else b''
    def record(*ids, flags=0, location=source):
        return ints(*ids, 0) + location + bytes([flags])
    outer = ints(0, 0) + (ints(0) if version == 2 else b'') + b'\0'
    first = (record(1, 1) + ints(2) + record(2, 2, 1) +
             record(3, 3, 4))
    nested = (record(6, 6, location=ints(0) if version == 2 else b'') +
              ints(1) + record(7, 7, 8))
    second = (record(5, 5, flags=7) + fstring('Base') +
              fstring('Invented.cfg') + ints(1) + nested)
    return (ints(version, len(pool) + 1, 0) + b''.join(map(fstring, pool)) +
            outer + ints(2) + first + second)


EXPECTED = '''Base : struct.begin
   SID = Base
   Amount = 35.0
struct.end
Derived : struct.begin {refurl=Invented.cfg;refkey=Base}
   Entries : struct.begin
      [0] = EExample::Value
   struct.end
struct.end'''


class BinaryCfgVersions(unittest.TestCase):
    def test_both_versions_preserve_roots_values_nested_arrays_and_links(self):
        for version in (1, 2):
            with self.subTest(version=version):
                roots = binary.read_binary_cfg(fixture(version))
                self.assertEqual(len(roots), 2)
                self.assertEqual('\n'.join(n.to_string() for n in roots).strip(), EXPECTED)

    def test_stream_uses_its_own_version_when_interleaved(self):
        old = binary.iter_binary_cfg(fixture(1))
        new = binary.iter_binary_cfg(fixture(2))
        self.assertEqual(next(old).to_string(), next(new).to_string())
        self.assertEqual(next(new).to_string(), next(old).to_string())
        self.assertEqual(list(old), [])
        self.assertEqual(list(new), [])

    def test_unknown_versions_fail_explicitly_instead_of_silent_garbage(self):
        for version in (0, 3, 999):
            with self.subTest(version=version), self.assertRaisesRegex(
                    ValueError, f'Unsupported binary cfg version {version}'):
                binary.read_binary_cfg(ints(version) + fixture(2)[4:])

    def test_truncated_v2_metadata_and_flags_are_rejected(self):
        for tail in (b'', ints(1), ints(1) + ints(1), ints(1, 1, 0),
                     ints(1, 1, 0) + b'\x01\x00', ints(1, 1, 0, 1)):
            reader = binary.BinaryCursor(tail)
            reader.version = 2
            with self.subTest(tail=tail), self.assertRaises(ValueError):
                binary.read_binary_cfg_config(reader, 9)

    def test_truncated_outer_block_is_rejected(self):
        for version in (1, 2):
            with self.subTest(version=version), self.assertRaises(ValueError):
                binary.read_binary_cfg(ints(version, 1, 0) + b'\0' * 8)

    def test_empty_nested_struct_does_not_consume_following_sibling(self):
        for version in (1, 2):
            data = fixture(version)
            # An independently encoded root with an empty child and a scalar.
            reader = binary.BinaryCursor(data)
            pool = binary.read_binary_header(reader)
            extra = ints(0) if version == 2 else b''
            block = lambda *ids: ints(*ids, 0) + extra + b'\0'
            empty_then_scalar = (block(1, 1) + ints(2) + block(6, 6) +
                                 ints(0) + block(3, 3, 4))
            cursor = binary.BinaryCursor(empty_then_scalar)
            cursor.version = version
            root = binary.read_binary_struct(cursor, pool)
            self.assertEqual(root.get('Entries'), '')
            self.assertEqual(root.get('Amount'), 35.0)
            self.assertEqual(cursor.position, cursor.length)


if __name__ == '__main__':
    unittest.main()
