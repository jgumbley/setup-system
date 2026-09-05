import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import models


class ModelTests(unittest.TestCase):
    def manifest(self, root="/opt/models", path="vae/example.safetensors"):
        return json.dumps({"root": root, "models": [{"path": path,
            "url": "https://huggingface.co/example/resolve/commit/example.safetensors",
            "sha256": "a" * 64, "size": 20}]})

    def test_rejects_broad_or_escaping_clean_paths(self):
        for root, path in (("/", "vae/example.safetensors"),
                           ("/opt/models", "../example.safetensors"),
                           ("/opt/models", "/home/system/example.safetensors"),
                           ("/opt/models", "vae")):
            with self.subTest(root=root, path=path), patch.object(Path, "read_text", return_value=self.manifest(root, path)):
                with self.assertRaises(ValueError):
                    models.entries("manifest.json")

    def test_rejects_symlinked_destinations(self):
        with patch.object(Path, "read_text", return_value=self.manifest()), \
                patch.object(Path, "resolve", return_value=Path("/home/system/private.safetensors")):
            with self.assertRaises(ValueError):
                models.entries("manifest.json")

    def test_existing_corrupt_model_is_preserved(self):
        with tempfile.TemporaryDirectory(dir=".runtime") as directory:
            target = Path(directory) / "example.safetensors"
            target.write_bytes(b"old weights")
            item = {"size": 11, "sha256": "0" * 64}
            with self.assertRaises(RuntimeError):
                models.download(target, item)
            self.assertEqual(target.read_bytes(), b"old weights")

    def test_complete_verified_partial_is_promoted_without_network(self):
        content = b"verified model"
        item = {"size": len(content), "sha256": hashlib.sha256(content).hexdigest()}
        with tempfile.TemporaryDirectory(dir=".runtime") as directory:
            target = Path(directory) / "example.safetensors"
            target.with_suffix(".safetensors.part").write_bytes(content)
            with patch.object(models.subprocess, "run", side_effect=AssertionError("Unexpected download")):
                self.assertTrue(models.download(target, item))
                self.assertFalse(models.download(target, item))
            self.assertEqual(target.read_bytes(), content)


class WorkflowTests(unittest.TestCase):
    def test_native_graphs_have_valid_links_and_distilled_settings(self):
        for path in Path("workflows").glob("*-api.json"):
            with self.subTest(path=path):
                graph = json.loads(path.read_text())
                self.assertEqual(graph["1"]["inputs"]["unet_name"], "flux-2-klein-4b.safetensors")
                self.assertEqual(graph["8"]["inputs"]["steps"], 4)
                self.assertEqual(graph["10"]["inputs"]["cfg"], 1)
                for node in graph.values():
                    for value in node["inputs"].values():
                        if isinstance(value, list):
                            self.assertIn(value[0], graph)
                            self.assertIsInstance(value[1], int)
                if "reference" in path.name:
                    self.assertEqual(graph["17"]["class_type"], "ReferenceLatent")
                    self.assertEqual(graph["18"]["class_type"], "ReferenceLatent")


if __name__ == "__main__":
    unittest.main()
