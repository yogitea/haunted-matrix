"""Detailed horror slideshow for MatrixPortal M4, CircuitPython 7."""

import gc
import os
import random
import struct

import board
import displayio
import framebufferio
import rgbmatrix

import ambience
import transitions

VERSION = "1.0.0"
HOLD_SECONDS = 15
GALLERY_FILE = "/gallery.bin"
RECORD_BYTES = 768 + 64 * 32
# Optional user-supplied 64x32, uncompressed 24-bit BMP. Not bundled.
# Example: WOLF_PATH = '/moon/splash-0.bmp'
WOLF_PATH = None

displayio.release_displays()
matrix = rgbmatrix.RGBMatrix(
    width=64,
    bit_depth=6,
    rgb_pins=[
        board.MTX_R1,
        board.MTX_G1,
        board.MTX_B1,
        board.MTX_R2,
        board.MTX_G2,
        board.MTX_B2,
    ],
    addr_pins=[board.MTX_ADDRA, board.MTX_ADDRB, board.MTX_ADDRC, board.MTX_ADDRD],
    clock_pin=board.MTX_CLK,
    latch_pin=board.MTX_LAT,
    output_enable_pin=board.MTX_OE,
)
display = framebufferio.FramebufferDisplay(matrix, auto_refresh=True)
group = displayio.Group()
if hasattr(display, "root_group"):
    display.root_group = group
else:
    display.show(group)
with open(GALLERY_FILE, "rb") as gallery:
    header = gallery.read(8)
if len(header) != 8:
    raise ValueError("Picture gallery header is incomplete")
magic, picture_count, width, height = struct.unpack("<4sHBB", header)
if magic != b"HGR1" or picture_count < 1 or width != 64 or height != 32:
    raise ValueError("Invalid picture gallery")
paths = []
if WOLF_PATH:
    try:
        os.stat(WOLF_PATH)
        paths.append(WOLF_PATH)
    except OSError:
        print("Optional picture not found:", WOLF_PATH)
paths.extend(range(picture_count))
current_palette = None
current_colors = None
current_counts = None


def show_picture(path):
    global current_palette, current_colors, current_counts
    gc.collect()
    if isinstance(path, str):
        with open(path, "rb") as source:
            data = source.read()
        if len(data) < 54 or data[:2] != b"BM":
            raise ValueError("Optional picture is not a valid BMP")
        offset = struct.unpack_from("<I", data, 10)[0]
        width, height = struct.unpack_from("<ii", data, 18)
        depth = struct.unpack_from("<H", data, 28)[0]
        compression = struct.unpack_from("<I", data, 30)[0]
        if (
            data[:2] != b"BM"
            or width != 64
            or abs(height) != 32
            or depth != 24
            or compression
        ):
            raise ValueError("Optional picture must be an uncompressed 64x32 RGB BMP")
        if len(data) < offset + 6144:
            raise ValueError("Optional picture data is incomplete")
        # Decode the original 24-bit BMP directly; CircuitPython 7's
        # OnDiskBitmap does not expose individual pixels to Python.
        image = displayio.Bitmap(64, 32, 2048)
        lookup = {}
        colors = []
        counts = []
        for y in range(32):
            for x in range(64):
                row = 31 - y if height > 0 else y
                position = offset + row * 192 + x * 3
                color = (
                    (data[position + 2] << 16)
                    | (data[position + 1] << 8)
                    | data[position]
                )
                if color not in lookup:
                    lookup[color] = len(colors)
                    colors.append(color)
                    counts.append(0)
                image[x, y] = lookup[color]
                counts[lookup[color]] += 1
        palette = displayio.Palette(len(colors))
        for i, color in enumerate(colors):
            palette[i] = color
        tile = displayio.TileGrid(image, pixel_shader=palette)
    else:
        with open(GALLERY_FILE, "rb") as gallery:
            gallery.seek(8 + path * RECORD_BYTES)
            record = gallery.read(RECORD_BYTES)
        if len(record) != RECORD_BYTES:
            raise ValueError("Incomplete gallery picture")
        counts = [0] * 256
        palette = displayio.Palette(256)
        colors = []
        for color in range(256):
            i = color * 3
            value = (record[i] << 16) | (record[i + 1] << 8) | record[i + 2]
            palette[color] = value
            colors.append(value)
        image = displayio.Bitmap(64, 32, 256)
        for y in range(32):
            for x in range(64):
                value = record[768 + y * 64 + x]
                image[x, y] = value
                counts[value] += 1
        tile = displayio.TileGrid(image, pixel_shader=palette)
    if len(group):
        transitions.play(
            group, tile, display, current_palette, current_colors, palette, colors
        )
    else:
        group.append(tile)
    refreshed = display.refresh(minimum_frames_per_second=0)
    current_palette, current_colors, current_counts = palette, colors, counts
    return refreshed


print("Haunted Matrix", VERSION, "—", len(paths), "pictures")
bag = []
last = None
while True:
    if not bag:
        bag = list(range(len(paths)))
        for i in range(len(bag) - 1, 0, -1):
            j = random.randrange(i + 1)
            bag[i], bag[j] = bag[j], bag[i]
        if last is None and paths[0] == WOLF_PATH:
            position = bag.index(0)
            bag[position], bag[-1] = bag[-1], bag[position]
        elif len(bag) > 1 and bag[-1] == last:
            bag[0], bag[-1] = bag[-1], bag[0]
    index = bag.pop()
    path = paths[index]
    show_picture(path)
    last = index
    print("Picture:", path)
    ambience.hold(current_palette, current_colors, current_counts, HOLD_SECONDS)
