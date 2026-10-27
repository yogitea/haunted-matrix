"""Execute the release startup without board libraries or optional artwork."""

import ast
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
source = (ROOT / "code.py").read_text()
tree = ast.parse(source)
startup = ast.Module(
    body=[n for n in tree.body if not isinstance(n, ast.While)], type_ignores=[]
)


class Bitmap:
    def __init__(self, width, height, colors):
        self.pixels = [0] * (width * height)

    def __setitem__(self, xy, color):
        self.pixels[xy[1] * 64 + xy[0]] = color


class Palette(list):
    def __init__(self, size):
        super().__init__([0] * size)


class Display:
    def __init__(self, *args, **kwargs):
        self.group = None

    def show(self, group):
        self.group = group

    def refresh(self, **kwargs):
        return True


class ModernDisplay(Display):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.root_group = None


pins = (
    "R1",
    "G1",
    "B1",
    "R2",
    "G2",
    "B2",
    "ADDRA",
    "ADDRB",
    "ADDRC",
    "ADDRD",
    "CLK",
    "LAT",
    "OE",
)
fakes = dict(
    board=SimpleNamespace(**{"MTX_" + name: None for name in pins}),
    displayio=SimpleNamespace(
        release_displays=lambda: None,
        Bitmap=Bitmap,
        Palette=Palette,
        Group=list,
        TileGrid=lambda image, pixel_shader: SimpleNamespace(image=image),
    ),
    rgbmatrix=SimpleNamespace(RGBMatrix=lambda **kwargs: object()),
)


def board_open(path, *args, **kwargs):
    if path == "/gallery.bin":
        path = ROOT / "gallery.bin"
    return open(path, *args, **kwargs)


for display_class in (Display, ModernDisplay):
    fakes["framebufferio"] = SimpleNamespace(FramebufferDisplay=display_class)
    saved = {name: sys.modules.get(name) for name in fakes}
    sys.modules.update(fakes)
    try:
        ns = dict(open=board_open)
        exec(compile(startup, "startup", "exec"), ns)
        assert ns["WOLF_PATH"] is None
        assert ns["paths"] == list(range(99))
        assert ns["show_picture"](0)
        assert sum(ns["current_counts"]) == 2048
        packed = (ROOT / "gallery.bin").read_bytes()[8 : 8 + 2816]
        assert bytes(ns["group"][0].image.pixels) == packed[768:]
        if display_class is ModernDisplay:
            assert ns["display"].root_group is ns["group"]
        else:
            assert ns["display"].group is ns["group"]
    finally:
        for name, previous in saved.items():
            if previous is None:
                del sys.modules[name]
            else:
                sys.modules[name] = previous
print("PASS: default 99-picture startup and first rendering with both display APIs.")
