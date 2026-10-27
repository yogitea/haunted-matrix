"""Desktop-only slideshow checks; uses the Python standard library."""

import argparse
import ast
import hashlib
import random
import struct
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--expected-pictures", type=int, default=99)
args = parser.parse_args()
count = args.expected_pictures
ROOT = Path(__file__).resolve().parent.parent
source = (ROOT / "code.py").read_text()
compile(source, "code.py", "exec")
files = sorted((ROOT / "artwork").glob("*.bmp"))
assert len(files) == count
signatures = set()
for path in files:
    data = path.read_bytes()
    signatures.add(hashlib.sha256(data).hexdigest())
    assert data[:2] == b"BM"
    width, height = struct.unpack_from("<ii", data, 18)
    depth = struct.unpack_from("<H", data, 28)[0]
    compression = struct.unpack_from("<I", data, 30)[0]
    offset = struct.unpack_from("<I", data, 10)[0]
    assert (width, height, depth, compression) == (64, 32, 8, 0), path
    assert len(data) == offset + 64 * 32
    assert len(set(data[offset:])) > 32
assert len(signatures) == len(files), "Duplicate pictures"
# Verify the packed device file preserves every palette and pixel exactly.
packed = (ROOT / "gallery.bin").read_bytes()
magic, entries, width, height = struct.unpack_from("<4sHBB", packed)
assert (magic, entries, width, height) == (b"HGR1", len(files), 64, 32)
assert len(packed) == 8 + len(files) * 2816
for index, path in enumerate(files):
    data = path.read_bytes()
    offset = struct.unpack_from("<I", data, 10)[0]
    record = packed[8 + index * 2816 : 8 + (index + 1) * 2816]
    expected_palette = bytes(
        value
        for i in range(256)
        for value in (data[54 + i * 4 + 2], data[54 + i * 4 + 1], data[54 + i * 4])
    )
    expected_pixels = b"".join(
        data[offset + y * 64 : offset + (y + 1) * 64] for y in reversed(range(32))
    )
    assert record[:768] == expected_palette, path
    assert record[768:] == expected_pixels, path
# Exercise both fresh installation and optional-picture shuffle paths.
loop = next(n for n in ast.parse(source).body if isinstance(n, ast.While))
selection = ast.Module(body=loop.body[:3], type_ignores=[])
code = compile(selection, "selection", "exec")
for optional in (False, True):
    paths = (["wolf"] if optional else []) + list(range(len(files)))
    ns = dict(
        random=random.Random(29),
        paths=paths,
        WOLF_PATH="wolf" if optional else None,
        bag=[],
        last=None,
    )
    played = []
    for _ in range(len(paths) * 100):
        exec(code, ns)
        played.append(ns["index"])
        ns["last"] = ns["index"]
    if optional:
        assert played[0] == 0
    assert all(a != b for a, b in zip(played, played[1:]))
    assert all(
        len(set(played[i : i + len(paths)])) == len(paths)
        for i in range(0, len(played), len(paths))
    )
print("PASS: 99 bundled pictures, exact packed pixels and palettes,")
print("      100 shuffle rounds each with and without an optional picture.")
