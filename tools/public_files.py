"""Reject private workspace material before publishing repository or ZIP content."""
from pathlib import PurePosixPath
import subprocess


PRIVATE_DIRS = frozenset({
    ".agents", ".claude", ".codex", ".codex-remote-attachments",
    ".git", "out", "vanilla", "cache", "presets", "pak_history",
    "output", "fremd mods", "build", "dist",
})
PRIVATE_NAMES = frozenset({
    "agents.md", "claude.md", "handover.md", "roadmap.md", "testprotokoll.md",
    "ingame_runtime_research.md",
    "settings.json", "editor.json", "s2tweaker_error.log",
    "nexus_replies.txt", "defender_false_positive.txt", "zillya_false_positive.txt",
    "signpath_application.txt", "issue_6_antwort.txt",
})


def is_private_path(name: str) -> bool:
    """Match local-only files at any depth, including Windows-style ZIP paths."""
    path = PurePosixPath(name.replace("\\", "/").lower())
    return (
        bool(PRIVATE_DIRS.intersection(path.parts))
        or path.name in PRIVATE_NAMES
        or path.name.startswith(("oo2core", "nexus_support_email"))
    )


def validate_public_paths(names) -> None:
    """Fail before writing an archive or uploading a build containing private data."""
    rejected = sorted(str(name) for name in names if is_private_path(str(name)))
    if rejected:
        raise ValueError("Private files cannot be published:\n" + "\n".join(rejected))


if __name__ == "__main__":
    import sys
    from pathlib import Path

    if len(sys.argv) > 1:
        root = Path(sys.argv[1])
        if not root.is_dir():
            raise SystemExit(f"Publication directory does not exist: {root}")
        validate_public_paths(path.relative_to(root).as_posix()
                              for path in root.rglob("*") if path.is_file())
    else:
        root = Path(__file__).resolve().parents[1]
        files = subprocess.check_output(["git", "ls-files", "-z"], cwd=root)
        validate_public_paths(name for name in files.decode("utf-8").split("\0") if name)
    print("Public file check passed.")
