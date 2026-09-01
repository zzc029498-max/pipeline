# FrameForge Pipeline

A deliberately small, production-minded **3D asset validation and publishing pipeline**.
It is designed as a portfolio project for an animation pipeline engineering role: the
interesting part is not a giant UI, but a clean boundary between artist tools and reliable
pipeline logic.

## What it demonstrates

- **Python + PyQt6:** responsive artist-facing UI; validation runs off the UI thread.
- **3D pipeline awareness:** scene/texture discovery, naming policy and render-format hints.
- **Safe publishing:** immutable `v001` versions, staging plus atomic rename, SHA-256 manifest.
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
renames only after the payload and manifest are complete, so downstream consumers never see a
half-published asset. Every file is checksummed for traceability.

This prototype assumes one publisher per asset at a time. A production extension would reserve
versions through a database or lock service, store manifests centrally, and emit events to asset
management and render systems.
