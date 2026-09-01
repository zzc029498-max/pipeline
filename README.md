# FrameForge Pipeline

A deliberately small, production-minded **3D asset validation and publishing pipeline**.
FrameForge explores a simple idea: artist tools should feel lightweight while the machinery
behind them stays predictable, traceable, and safe. Its focus is the clean boundary between
the creative workflow and reliable pipeline logic.

## Features

- **Python + PyQt6:** responsive artist-facing UI; validation runs off the UI thread.
- **3D pipeline awareness:** scene/texture discovery, naming policy and render-format hints.
- **Safe publishing:** immutable versions, cross-process locking, staging plus atomic rename.
- **Traceability:** deterministic manifest with size and streaming SHA-256 for every file.
- **Code craft:** typed domain models, injectable validation rules, headless CLI and tests.

```text
artist source ──▶ concurrent validators ──▶ publish gate ──▶ v001/
                                                           ├── manifest.json
                                                           └── payload/
```

## Try it

Python 3.10+ is enough for the CLI and tests. The GUI additionally needs PyQt6.

```bash
python -m anim_pipeline.cli demo/source/dragon --name dragon
python -m anim_pipeline.cli demo/source/dragon --name dragon \
  --publish --publish-root demo/published --comment "model approved"

python -m pip install -e '.[gui,dev]'
frameforge-gui
python -m unittest discover -s tests -v
```

The demo deliberately uses a tiny USDA scene and EXR placeholder so it can be published
immediately. In a studio, rules can be injected for Maya/USD metadata, frame ranges, color
spaces, texture resolution, or farm compatibility without changing the publisher.

## Design decisions

Validation and publishing do not import Qt. That keeps business logic usable from DCC apps,
CI, a render farm, or the command line. Publishing copies into a hidden staging directory and
validates that exact copy before an atomic rename, so downstream consumers never see a
half-published or differently validated asset. An OS-managed file lock gives concurrent
publishers unique versions and is automatically released if a process exits.

For a distributed production, the local lock can be replaced by database-backed version
reservation while keeping the same publishing API. Manifests can also be stored centrally or
emitted as events to asset-management and render systems.
