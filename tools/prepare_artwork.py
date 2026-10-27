"""Desktop-only gallery preparation; requires Pillow. Never touches the device.

Use --import-manifest PATH for [{"name": ..., "path": ...}] generated images.
Originals are preserved by the generation tool; workspace sources retain a
1024x512 JPEG suitable for adjusting these 64x32 display assets later.
"""

import argparse
import json
import struct
from pathlib import Path

from PIL import Image, ImageEnhance, ImageOps

ROOT = Path(__file__).resolve().parent.parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--import-manifest", type=Path)
args = parser.parse_args()
if args.import_manifest:
    for item in json.loads(args.import_manifest.read_text()):
        if not item.get("ok"):
            continue
        name = item["name"]
        if not name.replace("-", "").isalnum():
            raise ValueError("Invalid artwork filename")
        destination = ROOT / "artwork" / "sources" / (name + ".jpg")
        if destination.exists():
            continue
        source = Image.open(item["path"]).convert("RGB")
        source = ImageOps.fit(source, (1024, 512), method=Image.Resampling.LANCZOS)
        source.save(destination, quality=94)
for source in sorted((ROOT / "artwork" / "sources").iterdir()):
    if source.suffix.lower() not in (".png", ".jpg", ".jpeg"):
        continue
    image = ImageOps.fit(
        Image.open(source).convert("RGB"), (64, 32), method=Image.Resampling.LANCZOS
    )
    image = ImageEnhance.Sharpness(image).enhance(1.3)
    # A 256-color palette preserves shaded art while fitting the 2MB board.
    image = image.quantize(colors=256, method=Image.Quantize.MEDIANCUT)
    image.save(ROOT / "artwork" / (source.stem + ".bmp"))
    print(source.stem, "64x32 indexed BMP")

# One device file avoids FAT allocation overhead from 99 small bitmap files.
files = sorted((ROOT / "artwork").glob("*.bmp"))
with (ROOT / "gallery.bin").open("wb") as gallery:
    gallery.write(struct.pack("<4sHBB", b"HGR1", len(files), 64, 32))
    for path in files:
        image = Image.open(path)
        assert image.mode == "P" and image.size == (64, 32)
        palette = bytes(image.getpalette()[:768])
        gallery.write(palette.ljust(768, b"\0"))
        gallery.write(image.tobytes())
print("Packed", len(files), "pictures into gallery.bin")
