"""Build a reproducible, board-ready ZIP without private or development files."""

import argparse
import hashlib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNTIME = ("code.py", "ambience.py", "transitions.py", "gallery.bin")
INSTALL = """Haunted Matrix

Copy gallery.bin, ambience.py and transitions.py to the CIRCUITPY drive root.
Copy code.py last. Keep the panel connected to its normal power supply.
Back up your previous startup program before replacing it.

99 generated pictures are bundled. No Wi-Fi or external libraries are needed.
The optional Adafruit wolf image is NOT included. See the repository README
for hardware requirements, optional artwork, settings and troubleshooting.

https://github.com/yogitea/haunted-matrix
"""


def build(output):
    version = (ROOT / "VERSION").read_text().strip()
    if not version or any(c not in "0123456789." for c in version):
        raise ValueError("Invalid release version")
    output.mkdir(parents=True, exist_ok=True)
    stem = "haunted-matrix-" + version
    archive = output / (stem + "-install.zip")
    files = {name: (ROOT / name).read_bytes() for name in RUNTIME}
    files["LICENSE"] = (ROOT / "LICENSE").read_bytes()
    files["INSTALL.txt"] = INSTALL.encode()
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_STORED) as bundle:
        for name, data in sorted(files.items()):
            entry = zipfile.ZipInfo(stem + "/" + name, (2026, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_STORED
            entry.external_attr = 0o100644 << 16
            entry.create_system = 3
            bundle.writestr(entry, data)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    (output / "SHA256SUMS").write_text(digest + "  " + archive.name + "\n")
    print(archive.name, archive.stat().st_size, "bytes")
    return archive


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    build(parser.parse_args().output)
