"""Execute the actual palette fade; optional --preview needs Pillow."""

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("fade", ROOT / "transitions.py")
effect = importlib.util.module_from_spec(spec)
spec.loader.exec_module(effect)


class Clock:
    now = 0

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        assert seconds >= 0
        self.now += seconds


class Display:
    def __init__(self, group, clock, slow=False, interrupt=False):
        self.group, self.clock = group, clock
        self.frames = []
        self.slow = slow
        self.interrupt = interrupt

    def refresh(self, **kwargs):
        assert len(self.group) == 1
        self.frames.append(list(self.group[0].palette))
        if self.slow:
            self.clock.now += 0.06
        if self.interrupt and len(self.frames) == 10:
            raise KeyboardInterrupt
        return True


old_colors = [0x102030, 0xFE8040]
new_colors = [0x40C080, 0x123456, 0]
for slow, interrupt in ((False, False), (True, False), (False, True)):
    old = list(old_colors)
    new = list(new_colors)
    incoming = SimpleNamespace(palette=new)
    group = [SimpleNamespace(palette=old)]
    clock = Clock()
    display = Display(group, clock, slow, interrupt)
    effect.time = clock
    try:
        effect.play(group, incoming, display, old, old_colors, new, new_colors)
    except KeyboardInterrupt:
        assert interrupt
    assert old == old_colors and new == new_colors
    if not interrupt:
        assert group == [incoming] and len(display.frames) == 65
        assert display.frames[31] == [0, 0] and display.frames[32] == [0, 0, 0]
        assert display.frames[-1] == new_colors
        energy = [
            sum((c >> s) & 255 for c in frame for s in (0, 8, 16))
            for frame in display.frames
        ]
        assert all(a >= b for a, b in zip(energy[:31], energy[1:32]))
        assert all(a <= b for a, b in zip(energy[32:-1], energy[33:]))
        if not slow:
            assert abs(clock.now - 3.3) < 0.001
print("PASS: whole-frame fade, full-black midpoint, monotone brightness,")
print("      exact colors, slow-render tolerance and interruption cleanup.")

if "--preview" in sys.argv:
    from PIL import Image

    old = Image.open(ROOT / "artwork/haunted-house.bmp")
    new = Image.open(ROOT / "artwork/ghost-aurora.bmp")

    def colors(im):
        p = im.getpalette()
        return [(p[i] << 16) | (p[i + 1] << 8) | p[i + 2] for i in range(0, 768, 3)]

    a, b = colors(old), colors(new)
    ap, bp = list(a), list(b)
    old_tile = SimpleNamespace(palette=ap, pixels=list(old.tobytes()))
    new_tile = SimpleNamespace(palette=bp, pixels=list(new.tobytes()))
    group = [old_tile]
    frames = []

    class Preview:
        def refresh(self, **kwargs):
            tile = group[0]
            im = Image.new("RGB", (64, 32))
            im.putdata(
                [
                    (
                        (tile.palette[i] >> 16) & 255,
                        (tile.palette[i] >> 8) & 255,
                        tile.palette[i] & 255,
                    )
                    for i in tile.pixels
                ]
            )
            frames.append(im.resize((512, 256), Image.Resampling.NEAREST))
            return True

    effect.time = Clock()
    display = Preview()
    display.refresh()
    effect.play(group, new_tile, display, ap, a, bp, b)
    frames[0].save(
        ROOT / "transition-preview.gif",
        save_all=True,
        append_images=frames[1:],
        duration=[1000] + [50] * 32 + [300] + [50] * 31 + [1000],
        loop=0,
        disposal=2,
    )
    print("Saved transition-preview.gif")
