"""Check coherent color-family dimming and exact palette restoration."""

import ast
import gc
import importlib.util
import struct
import tempfile
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("ambience", ROOT / "ambience.py")
effects = importlib.util.module_from_spec(spec)
spec.loader.exec_module(effects)
colors = [0x000000, 0xB02010, 0x581008, 0x10B020, 0x808080, 0x0C0000]
counts = [200, 1000, 1000, 10, 200, 100]
family, weights = effects.select(colors, counts)
assert family == 0
assert weights[1] == weights[2] and weights[1] > 230
assert weights[0] == weights[3] == weights[4] == weights[5] == 0
assert abs(effects.weight(0xC86310, 0) - effects.weight(0xC86410, 0)) <= 3
palette = list(colors)
for strength in range(257):
    effects.apply(palette, colors, weights, strength)
    for old, new in zip(colors, palette):
        for shift in (0, 8, 16):
            a, b = (old >> shift) & 255, (new >> shift) & 255
            assert a * (256 - effects.MAX_DIM) // 256 <= b <= a
    assert palette[0] == colors[0] and palette[3:] == colors[3:]


class Clock:
    def __init__(self, palette, interrupt=False):
        self.now, self.frames = 0, []
        self.palette, self.interrupt = palette, interrupt

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        assert seconds >= 0
        self.frames.append(list(self.palette))
        self.now += seconds
        if self.interrupt and len(self.frames) == 3:
            raise KeyboardInterrupt


for interrupt in (False, True):
    palette = list(colors)
    clock = Clock(palette, interrupt)
    effects.time = clock
    try:
        effects.hold(palette, colors, counts, 2)
    except KeyboardInterrupt:
        assert interrupt
    assert palette == colors
    if not interrupt:
        assert len(clock.frames) == 16 and clock.now == 2
        assert clock.frames[0] == colors and clock.frames[4] != colors
        assert clock.frames[8] == colors and clock.frames[12] != colors
        assert (clock.frames[4][1] >> 16) < (colors[1] >> 16) * 0.35
        assert all(frame[3:] == colors[3:] for frame in clock.frames)
print("PASS: broad hue membership, near-shade coherence, dimming-only bounds,")
print("      unchanged unrelated/dark colors, timing and exact recovery.")

# Execute the actual loader against a synthetic 24-bit BMP in both row orders.
# This covers the older-firmware decoder without redistributing original art.


class TestBitmap:
    def __init__(self, width, height, count):
        self.data = [0] * (width * height)
        self.width = width

    def __setitem__(self, xy, value):
        self.data[xy[1] * self.width + xy[0]] = value


class TestPalette(list):
    def __init__(self, count):
        super().__init__([0] * count)


source = (ROOT / "code.py").read_text()
loader = next(
    n
    for n in ast.parse(source).body
    if isinstance(n, ast.FunctionDef) and n.name == "show_picture"
)
colors = [
    (x * 4 << 16) | (y * 8 << 8) | ((x ^ y) * 3 % 256)
    for y in range(32)
    for x in range(64)
]
for top_down in (False, True):
    pixels = bytearray()
    for y in range(32) if top_down else reversed(range(32)):
        for color in colors[y * 64 : (y + 1) * 64]:
            pixels.extend((color & 255, (color >> 8) & 255, color >> 16))
    header = struct.pack("<2sIHHI", b"BM", 6198, 0, 0, 54)
    header += struct.pack(
        "<IiiHHIIiiII", 40, 64, -32 if top_down else 32, 1, 24, 0, 6144, 0, 0, 0, 0
    )
    group = []
    ns = dict(
        gc=gc,
        struct=struct,
        group=group,
        current_file=None,
        last_transition=None,
        current_palette=None,
        current_colors=None,
        displayio=SimpleNamespace(
            Bitmap=TestBitmap,
            Palette=TestPalette,
            TileGrid=lambda bitmap, pixel_shader: SimpleNamespace(bitmap=bitmap),
        ),
        display=SimpleNamespace(refresh=lambda **kwargs: True),
    )
    exec(compile(ast.Module(body=[loader], type_ignores=[]), "loader", "exec"), ns)
    with tempfile.NamedTemporaryFile(suffix=".bmp") as f:
        f.write(header + pixels)
        f.flush()
        ns["show_picture"](f.name)
    decoded = [ns["current_colors"][index] for index in group[0].bitmap.data]
    assert decoded == colors
    assert ns["current_palette"] == ns["current_colors"]
print(
    "PASS: original-image decoder preserves all 2,048 RGB pixels in either BMP row order."
)
