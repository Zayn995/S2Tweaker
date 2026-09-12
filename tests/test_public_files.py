"""Keep private workspace material out of repository and release archives."""
from pathlib import Path
import subprocess
import sys
import unittest
from tempfile import TemporaryDirectory
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.public_files import validate_public_paths
from tools import make_release_zips


class PublicFilesTests(unittest.TestCase):
    def test_public_sources_and_localization_are_allowed(self):
        validate_public_paths([
            "README.md", "docs/SPEC.md", "s2tweaker/localization.py",
            "tests/test_job_localization.py", "release/README.txt",
            "_internal/s2tweaker/gui.py", "S2Tweaker.exe",
        ])

    def test_private_material_is_rejected_at_any_depth(self):
        for name in [
            "CLAUDE.md", "docs/AGENTS.md", "HANDOVER.md", "docs/ROADMAP.md",
            "docs/INGAME_RUNTIME_RESEARCH.md",
            ".agents/skills/add-tweak/SKILL.md", ".claude/settings.json",
            ".codex-remote-attachments/photo.jpg", "out/notes.md",
            "release/NEXUS_SUPPORT_EMAIL_NACHTRAG4.txt", "cache/GameData.cfg",
            "vanilla/Game.locres", "tools/oo2core_9_win64.dll.123.part",
            "_internal/CLAUDE.md", "_internal\\.CODEX\\notes.md",
            "settings.json", "editor.json", "presets/personal.json",
        ]:
            with self.subTest(name=name), self.assertRaises(ValueError):
                validate_public_paths(["README.md", name])

    def test_actual_tracked_paths_are_public(self):
        root = Path(__file__).resolve().parents[1]
        if not (root / ".git").exists():
            self.skipTest("Source archive has no Git index")
        names = subprocess.check_output(["git", "ls-files", "-z"], cwd=root)
        validate_public_paths(n for n in names.decode("utf-8").split("\0") if n)

    def test_zip_builder_checks_both_inventories_before_writing(self):
        for private_source, private_player in [(True, False), (False, True), (False, False)]:
            with self.subTest(source=private_source, player=private_player), TemporaryDirectory() as folder:
                root = Path(folder)
                app = root / "portable"
                internal = app / "_internal"
                internal.mkdir(parents=True)
                (app / "S2Tweaker.exe").write_bytes(b"launcher fixture")
                (app / "python312._pth").write_text("_internal\n", encoding="utf-8")
                (internal / "sitecustomize.py").write_text("# Launcher fixture\n", encoding="utf-8")
                for index in range(101):
                    (internal / f"runtime_{index}.txt").write_text("fixture", encoding="utf-8")
                if private_player:
                    (internal / "CLAUDE.md").write_text("Private note", encoding="utf-8")
                (root / "release").mkdir()
                (root / "release" / "README.txt").write_text("Player instructions", encoding="utf-8")
                (root / "README.md").write_text("Public documentation", encoding="utf-8")
                tracked = ["README.md", "release/README.txt"]
                if private_source:
                    (root / "CLAUDE.md").write_text("Private note", encoding="utf-8")
                    tracked.append("CLAUDE.md")
                result = subprocess.CompletedProcess([], 0, "\0".join(tracked) + "\0")
                argv = ["make_release_zips.py", "test", "--dist", str(app)]
                with patch.object(make_release_zips, "REPO", root), \
                        patch.object(sys, "argv", argv), \
                        patch.object(make_release_zips.subprocess, "run", return_value=result):
                    if private_source or private_player:
                        with self.assertRaisesRegex(ValueError, "Private files cannot be published"):
                            make_release_zips.main()
                        self.assertEqual(list((root / "release").glob("*.zip")), [])
                    else:
                        make_release_zips.main()
                        with zipfile.ZipFile(root / "release/S2Tweaker_vtest_source.zip") as archive:
                            self.assertEqual(set(archive.namelist()), set(tracked))
                            self.assertEqual(archive.read("README.md"), b"Public documentation")
                        with zipfile.ZipFile(root / "release/S2Tweaker_vtest.zip") as archive:
                            validate_public_paths(archive.namelist())
                            self.assertIn("_internal/sitecustomize.py", archive.namelist())


if __name__ == "__main__":
    unittest.main()
