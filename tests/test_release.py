"""The download includes only installable files and is reproducible."""

import ast
import hashlib
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
version = (ROOT / "VERSION").read_text().strip()
stem = "haunted-matrix-" + version
runtime_version = next(
    n.value.value
    for n in ast.parse((ROOT / "code.py").read_text()).body
    if isinstance(n, ast.Assign)
    and any(isinstance(t, ast.Name) and t.id == "VERSION" for t in n.targets)
)
assert runtime_version == version
with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
    archives = []
    for directory in (first, second):
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "tools/package_release.py"),
                "--output",
                directory,
            ],
            check=True,
        )
        archive = Path(directory) / (stem + "-install.zip")
        archives.append(archive.read_bytes())
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        assert (
            Path(directory) / "SHA256SUMS"
        ).read_text() == digest + "  " + archive.name + "\n"
        with zipfile.ZipFile(archive) as bundle:
            expected = {
                "code.py",
                "ambience.py",
                "transitions.py",
                "gallery.bin",
                "LICENSE",
                "INSTALL.txt",
            }
            assert set(bundle.namelist()) == {stem + "/" + name for name in expected}
            for name in expected - {"INSTALL.txt"}:
                assert bundle.read(stem + "/" + name) == (ROOT / name).read_bytes()
            assert bundle.testzip() is None
    assert archives[0] == archives[1]
print("PASS: deterministic install ZIP, exact runtime files, license and checksum.")
