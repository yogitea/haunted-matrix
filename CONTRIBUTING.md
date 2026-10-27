# Contributing

Keep the installed player small, offline and compatible with its tested
CircuitPython 7 runtime. Avoid dependencies that cannot run on the M4.

- `code.py`, `ambience.py`, `transitions.py`: installed player.
- `gallery.bin`: packed generated artwork; do not edit by hand.
- `artwork/`: display previews and editing sources.
- `tools/`: desktop-only preparation and release packaging.
- `tests/`: standard-library checks plus an optional Pillow preview.

Run all five test scripts listed in the README before proposing a change.
Use `ruff check .` and `ruff format --check .` for style checks. Desktop-only
dependencies are in `requirements-dev.txt`; none are copied to the board.

When changing artwork, regenerate the packed gallery and keep the catalogue and
prompts consistent. Include only artwork you may redistribute. Never add device
backups, private configuration, credentials, original Adafruit splash images,
or generated Python caches.

Describe whether a change was tested only on the desktop or also on hardware.
Report the board, firmware and panel size for hardware testing. Do not claim
support for untested boards or firmware based on a successful desktop test.
