"""A single whole-picture fade through black, for CircuitPython 7."""

import math
import time

FRAMES = 32
DURATION = 3.0
BLACK_HOLD = 0.3


def scale(palette, colors, level):
    for i, color in enumerate(colors):
        r = (((color >> 16) & 255) * level) >> 8
        g = (((color >> 8) & 255) * level) >> 8
        b = ((color & 255) * level) >> 8
        palette[i] = (r << 16) | (g << 8) | b


def play(group, incoming, display, old_palette, old_colors, new_palette, new_colors):
    """Fade every color together; swap pictures only while completely black."""
    try:
        for phase in range(2):
            if phase:
                time.sleep(BLACK_HOLD)
                scale(new_palette, new_colors, 0)
                group[0] = incoming
                display.refresh(minimum_frames_per_second=0)
            palette = new_palette if phase else old_palette
            colors = new_colors if phase else old_colors
            start = time.monotonic()
            for frame in range(1, FRAMES + 1):
                level = int((1 - math.cos(math.pi * frame / FRAMES)) * 128)
                scale(palette, colors, level if phase else 256 - level)
                display.refresh(minimum_frames_per_second=0)
                time.sleep(
                    max(0, start + DURATION * frame / (2 * FRAMES) - time.monotonic())
                )
    finally:
        scale(old_palette, old_colors, 256)
        scale(new_palette, new_colors, 256)
