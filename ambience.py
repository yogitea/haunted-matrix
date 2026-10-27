"""Dim a broad hue family together, with fixed smooth membership per picture."""

import math
import random
import time

NAMES = ("red", "yellow", "green", "cyan", "blue", "violet")
FPS = 8
MAX_DIM = 179  # 70% peak reduction for strongly matching color regions.
CYCLES = 2


def weight(color, family):
    r, g, b = (color >> 16) & 255, (color >> 8) & 255, color & 255
    hi, lo = max(r, g, b), min(r, g, b)
    chroma = hi - lo
    if not chroma or hi <= 16:
        return 0
    if hi == r:
        hue = ((g - b) * 256 // chroma) % 1536
    elif hi == g:
        hue = 512 + (b - r) * 256 // chroma
    else:
        hue = 1024 + (r - g) * 256 // chroma
    distance = abs(hue - family * 256)
    distance = min(distance, 1536 - distance)
    if distance >= 384:
        return 0
    # Soft hue boundaries, with no binary palette-entry membership changes.
    hue_weight = (
        1 if distance <= 128 else (1 + math.cos(math.pi * (distance - 128) / 256)) / 2
    )
    saturation = min(1, 2 * chroma / hi)
    darkness = min(1, (hi - 16) / 32)
    return int(256 * hue_weight * saturation * darkness)


def select(colors, counts):
    scores = []
    for family in range(6):
        scores.append(
            sum(weight(color, family) * count for color, count in zip(colors, counts))
        )
    best = max(scores)
    if best == 0:
        return None, [0] * len(colors)
    candidates = [i for i, score in enumerate(scores) if score >= best * 0.7]
    family = candidates[random.randrange(len(candidates))]
    return family, [weight(color, family) for color in colors]


def apply(palette, colors, weights, strength):
    for i, color in enumerate(colors):
        # All channels use the same multiplier: hue and shading stay coherent.
        # A color region dims by at most 70%; it is never switched off.
        level = 256 - (weights[i] * strength * MAX_DIM // 65536)
        r = (((color >> 16) & 255) * level) >> 8
        g = (((color >> 8) & 255) * level) >> 8
        b = ((color & 255) * level) >> 8
        palette[i] = (r << 16) | (g << 8) | b


def hold(palette, colors, counts, seconds):
    family, weights = select(colors, counts)
    print("Dim color region:", NAMES[family] if family is not None else "none")
    start = time.monotonic()
    frame = 0
    try:
        while True:
            elapsed = time.monotonic() - start
            if elapsed >= seconds:
                break
            # Two slow, clearly visible cycles per picture; fixed color regions.
            strength = int(
                (1 - math.cos(2 * math.pi * CYCLES * elapsed / seconds)) * 128
            )
            apply(palette, colors, weights, strength)
            frame += 1
            time.sleep(
                max(0, min(start + seconds, start + frame / FPS) - time.monotonic())
            )
    finally:
        for i, color in enumerate(colors):
            palette[i] = color
