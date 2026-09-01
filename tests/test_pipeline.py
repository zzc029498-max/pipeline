import json
import tempfile
import unittest
from pathlib import Path

from anim_pipeline.models import Asset, Severity
from anim_pipeline.service import PipelineService


def make_asset(tmp_path: Path, name: str = "red_panda") -> Asset:
    source = tmp_path / "source"
    source.mkdir()
    (source / "model.usda").write_text("#usda 1.0\n", encoding="utf-8")
    (source / "fur.exr").write_bytes(b"texture")
    return Asset("movie", "character", name, source)


class PipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_valid_asset_can_publish(self) -> None:
        asset = make_asset(self.root)
        service = PipelineService(self.root / "published")
        self.assertEqual(service.inspect(asset), [])
        result = service.publish(asset, "first look")
        manifest = json.loads(result.manifest.read_text(encoding="utf-8"))
        self.assertEqual(result.version, 1)
        self.assertEqual(manifest["asset"], "movie/character/red_panda")
        self.assertTrue(manifest["files"][0]["sha256"])

    def test_versions_are_immutable_and_increment(self) -> None:
        asset = make_asset(self.root)
        service = PipelineService(self.root / "published")
        self.assertEqual(service.publish(asset).version, 1)
        self.assertEqual(service.publish(asset).version, 2)

    def test_bad_name_blocks_publish(self) -> None:
        asset = make_asset(self.root, "Red Panda")
        service = PipelineService(self.root / "published")
        findings = service.inspect(asset)
        self.assertTrue(any(f.severity == Severity.ERROR for f in findings))
        with self.assertRaisesRegex(ValueError, "snake_case"):
            service.publish(asset)


if __name__ == "__main__":
    unittest.main()
