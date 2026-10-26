"""Boundary tests for optional prerequisite provisioning, without network installs."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch
import zipfile

PATH = Path(__file__).resolve().parents[1] / "integrations/runtime_setup/setup.py"
spec = importlib.util.spec_from_file_location("zenith_runtime_setup", PATH)
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)


class RuntimeSetupTests(unittest.TestCase):
    def test_valid_zip_extracts_inside_owned_stage(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            archive = root / "node.zip"
            with zipfile.ZipFile(archive, "w") as packed:
                packed.writestr("node/node.exe", b"example")
            setup.extract_node(archive, root / "output", "node")
            self.assertEqual((root / "output/node/node.exe").read_bytes(), b"example")

    def test_valid_tar_extracts_inside_owned_stage(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            archive = root / "node.tar.gz"
            with tarfile.open(archive, "w:gz") as packed:
                member = tarfile.TarInfo("node/bin/node")
                member.size = 7
                packed.addfile(member, io.BytesIO(b"example"))
            setup.extract_node(archive, root / "output", "node")
            self.assertEqual((root / "output/node/bin/node").read_bytes(), b"example")

    def test_inspection_never_downloads_or_creates_root(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / "absent"
            out = io.StringIO()
            with patch.object(setup, "install") as install, contextlib.redirect_stdout(out):
                self.assertEqual(setup.main(["--root", str(root)]), 0)
            install.assert_not_called()
            self.assertFalse(root.exists())
            self.assertFalse(json.loads(out.getvalue())["install_requested"])

    def test_traversal_and_unexpected_roots_are_rejected(self):
        for name in ("../outside", "/outside", "node/../../outside", "other/file", "node/..\\outside", "node/C:/file"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                setup.safe_member(name, "node")

    def test_tar_symlink_escape_is_rejected_before_extraction(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            archive = root / "bad.tar.xz"
            with tarfile.open(archive, "w:xz") as packed:
                member = tarfile.TarInfo("node/link")
                member.type = tarfile.SYMTYPE
                member.linkname = "../../outside"
                packed.addfile(member)
            with self.assertRaises(ValueError):
                setup.extract_node(archive, root / "output", "node")
            self.assertFalse((root / "output").exists())

    def test_tar_special_files_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            archive = root / "bad.tar.gz"
            with tarfile.open(archive, "w:gz") as packed:
                member = tarfile.TarInfo("node/device")
                member.type = tarfile.CHRTYPE
                packed.addfile(member)
            with self.assertRaises(ValueError):
                setup.extract_node(archive, root / "output", "node")

    def test_zip_traversal_is_rejected_before_extraction(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            archive = root / "bad.zip"
            with zipfile.ZipFile(archive, "w") as packed:
                packed.writestr("node/../../outside", "bad")
            with self.assertRaises(ValueError):
                setup.extract_node(archive, root / "output", "node")
            self.assertFalse((root / "output").exists())

    def test_checksum_failure_never_extracts_or_installs(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with patch.object(setup.urllib.request, "urlopen", return_value=io.BytesIO(b"tampered")), patch.object(setup, "extract_node") as extract:
                with self.assertRaisesRegex(ValueError, "checksum"):
                    setup.node_install(root, "linux-x64")
            extract.assert_not_called()
            self.assertEqual(list(root.iterdir()), [])

    def test_unsupported_architecture_is_explicit(self):
        with patch.object(setup.platform, "system", return_value="Linux"), patch.object(setup.platform, "machine", return_value="riscv64"):
            with self.assertRaisesRegex(ValueError, "Unsupported"):
                setup.platform_key()

    def test_unowned_environment_is_not_mutated(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            sentinel = root / "preserve.txt"
            sentinel.write_text("keep")
            fake = type("Completed", (), {"stdout": "uv " + setup.PINS["uv"]})()
            with patch.object(setup.shutil, "which", return_value="uv"), patch.object(setup, "run", return_value=fake), patch.object(setup, "node_install") as node:
                with self.assertRaisesRegex(ValueError, "unowned"):
                    setup.install(root)
            node.assert_not_called()
            self.assertEqual(sentinel.read_text(), "keep")
            self.assertEqual(list(root.iterdir()), [sentinel])

    def test_nested_git_worktree_is_not_used_for_runtime_output(self):
        with tempfile.TemporaryDirectory() as folder:
            parent = Path(folder)
            (parent / ".git").write_text("gitdir: /some/worktree")
            root = parent / "nested" / "runtimes"
            fake = type("Completed", (), {"stdout": "uv " + setup.PINS["uv"]})()
            with patch.object(setup.shutil, "which", return_value="uv"), patch.object(setup, "run", return_value=fake):
                with self.assertRaisesRegex(ValueError, "outside all Git"):
                    setup.install(root)
            self.assertFalse(root.exists())

    def test_zip_source_without_git_metadata_is_also_protected(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "source"
            here = source / "integrations/runtime_setup"
            here.mkdir(parents=True)
            root = source / "generated-runtime"
            fake = type("Completed", (), {"stdout": "uv " + setup.PINS["uv"]})()
            with patch.object(setup, "HERE", here), patch.object(setup.shutil, "which", return_value="uv"), patch.object(setup, "run", return_value=fake), patch.object(setup, "node_install") as node:
                with self.assertRaisesRegex(ValueError, "outside all Git"):
                    setup.install(root)
            node.assert_not_called()
            self.assertFalse(root.exists())


if __name__ == "__main__":
    unittest.main()
