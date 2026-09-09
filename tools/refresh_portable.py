"""Assemble a source update using an existing, byte-identical portable runtime.

No executable patching, compilation, downloads, GUI starts or directory deletion.
The destination must be new. Its binary inventory must match the base exactly.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def binaries(directory):
    return {str(path.relative_to(directory)).replace("\\", "/"): digest(path)
            for path in directory.rglob("*")
            if path.is_file() and path.suffix.lower() in (".exe", ".dll", ".pyd")}


def refresh(base, output, expected_starter_sha):
    base, output = Path(base).resolve(), Path(output).resolve()
    if output.exists() or output == base or base in output.parents:
        raise ValueError("Choose a new output directory outside the base runtime.")
    starter = base / "S2Tweaker.exe"
    if not starter.is_file() or digest(starter) != expected_starter_sha.lower():
        raise ValueError("Base starter does not match the required SHA-256.")
    if not (base / "_internal" / "sitecustomize.py").is_file():
        raise ValueError("Base is not an existing S2Tweaker portable build.")
    before = binaries(base)

    def ignore(directory, names):
        skip = {name for name in names if name == "__pycache__" or name.endswith(".pyc")}
        directory = Path(directory).resolve()
        if directory == base:
            skip |= {"settings.json", "editor.json", "cache", "output", "pak_history", "presets", "error.log", "README.txt"}
        if directory == base / "_internal":
            skip.add("s2tweaker")
        return skip

    shutil.copytree(base, output, ignore=ignore)
    shutil.copytree(ROOT / "s2tweaker", output / "_internal" / "s2tweaker",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    shutil.copytree(ROOT / "assets", output / "_internal" / "assets", dirs_exist_ok=True)
    shutil.copy2(ROOT / "tools" / "launcher.py", output / "_internal" / "sitecustomize.py")
    after = binaries(output)
    if before != after or digest(starter) != expected_starter_sha.lower():
        raise ValueError("Binary inventory changed; this output must not be shipped.")
    own_sources = {str(path.relative_to(ROOT / "s2tweaker")): digest(path)
                   for path in (ROOT / "s2tweaker").glob("*.py")}
    shipped_sources = {str(path.relative_to(output / "_internal" / "s2tweaker")): digest(path)
                       for path in (output / "_internal" / "s2tweaker").glob("*.py")}
    if own_sources != shipped_sources:
        raise ValueError("The shipped application sources differ from the workspace.")
    report = {"starter_sha256": digest(output / "S2Tweaker.exe"),
              "all_binaries_unchanged": True, "binary_count": len(after),
              "binaries": after, "source_files": own_sources,
              "gui_started": False, "signature_check": "Run separately on Windows."}
    (output.parent / "runtime_integrity.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Prepared {output}: {len(after)} unchanged binaries; {len(own_sources)} source files.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--expected-starter-sha", required=True)
    args = parser.parse_args()
    refresh(args.base, args.output, args.expected_starter_sha)
