# TripTrack

A lightweight Kivy app for logging commute trips (to/from work) and exporting the data as CSV.
Runs on desktop for development and packages as an Android APK via Buildozer.

## Features

- Log trips with one tap — records date, direction, start/end time, and duration
- Edit or delete any logged trip
- Export all trips to a CSV file (`date,direction,duration_minutes,notes`)
- No ads, no tracking, no cloud — data stays on your device
- Readable source code, suitable for learning Kivy + Python mobile development

## Prerequisites

- Python 3.9 or newer
- [uv](https://docs.astral.sh/uv/) (recommended) **or** pip
- For Android builds: Linux/WSL + [Buildozer](https://buildozer.readthedocs.io/)

## Getting Started

### Install dependencies

**With uv (recommended):**

```bash
uv sync
```

**With pip:**

```bash
pip install kivy>=2.3.0
```

### Run on desktop

```bash
uv run python main.py
```

Or with plain Python:

```bash
python main.py
```

The app opens a Kivy window. Trip data is saved to `trips.json` in the project directory.

### Run tests

```bash
uv run pytest tests/ -v
```

All tests are in `tests/test_storage.py` and cover the storage layer end-to-end.

## Build for Android

> Requires Linux or WSL with Buildozer installed.

```bash
pip install buildozer
buildozer android debug
```

The signed debug APK will be placed in `bin/`. Transfer it to your device and install with:

```bash
adb install bin/*.apk
```

On Android, trip data is written to the app's private storage directory (no permissions required).

## License

GNU General Public License v3.0 — see [LICENSE](LICENSE) for details.

## Contributing

Contributions welcome. Fork the repo, make your changes, and open a pull request.
