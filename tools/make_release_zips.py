"""Build player and source release ZIPs.

Player files are rooted at S2Tweaker.exe with _internal and README.txt.
Source files come from git ls-files, excluding release ZIPs, screenshots
and binaries. --dist selects an alternative portable build directory."""
import subprocess
import sys
import zipfile
from pathlib import Path

if __package__:
    from .public_files import validate_public_paths
else:
    from public_files import validate_public_paths

REPO = Path(__file__).resolve().parents[1]


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python tools/make_release_zips.py <version> "
                         "[--dist <path>]")
    version = sys.argv[1]
    app = REPO / "dist" / "S2Tweaker"
    if "--dist" in sys.argv:
        app = Path(sys.argv[sys.argv.index("--dist") + 1])
    if not (app / "S2Tweaker.exe").is_file():
        raise SystemExit(f"Application folder missing: {app} — run build.bat "
                         "first or specify --dist.")

    tracked = subprocess.run(["git", "ls-files", "-z"], cwd=REPO,
                             capture_output=True, text=True,
                             encoding="utf-8", check=True).stdout.rstrip("\0").split("\0")
    # Validate both inventories before creating either archive.
    validate_public_paths(tracked)
    player_files = sorted(path for path in app.rglob("*") if path.is_file())
    validate_public_paths(path.relative_to(app).as_posix() for path in player_files)
    # Exclude runtime binaries from the source archive.
    source_files = [f for f in tracked
                    if not f.endswith((".zip", ".exe", ".dll", ".pyd"))
                    and not f.startswith("release/screenshots")]

    out = REPO / "release"
    player = out / f"S2Tweaker_v{version}.zip"
    with zipfile.ZipFile(player, "w", zipfile.ZIP_DEFLATED) as z:
        for path in player_files:
            z.write(path, path.relative_to(app).as_posix())
        z.write(out / "README.txt", "README.txt")
    print(f"{player.name}: {player.stat().st_size:,} bytes")

    # Verify the player ZIP contains its root launcher and populated runtime.
    with zipfile.ZipFile(player) as z:
        names = z.namelist()
    assert "S2Tweaker.exe" in names, names[:10]
    internal = [n for n in names if n.startswith("_internal/")]
    assert len(internal) > 100, f"only {len(internal)} files in _internal/"
    assert "README.txt" in names, names[:10]
    # No updater script belongs in the player archive.
    assert "update.bat" not in names, "update.bat does not belong in the player ZIP"
    # Require the search-path file and launcher module; exclude network modules
    # and user data.
    assert any(n.startswith("python3") and n.endswith("._pth") for n in names), \
        "python3XX._pth missing; launcher would not find its code"
    assert "_internal/sitecustomize.py" in names, "Launcher module missing"
    verboten = [n for n in names if n.rsplit("/", 1)[-1].lower().startswith(
        ("_ssl", "_socket", "_hashlib", "libssl", "libcrypto", "sqlite3"))]
    assert not verboten, verboten
    reste = [n for n in names
             if n.split("/")[0] in ("settings.json", "editor.json", "pak_history",
                                      "cache", "output", "presets", "S2Tweaker_error.log")]
    assert not reste, reste
    print(f"Verification: S2Tweaker.exe + ._pth + {len(internal)} files in "
          "_internal/ + README, no updater/network modules/user data  OK")

    src = out / f"S2Tweaker_v{version}_source.zip"
    with zipfile.ZipFile(src, "w", zipfile.ZIP_DEFLATED) as z:
        for rel in source_files:
            z.write(REPO / rel, rel)
    print(f"{src.name}: {src.stat().st_size:,} bytes, "
          f"{len(source_files)} files")

    with zipfile.ZipFile(src) as z:
        names = z.namelist()
    forbidden = [n for n in names
                 if n.startswith(("vanilla/", "cache/", "dist/", "build/", "out/",
                                  "fremd mods/", "presets/", "pak_history/"))
                 or "oo2core" in n or n.endswith(("settings.json", "editor.json"))
                 or n.lower().endswith((".exe", ".dll", ".pyd"))]
    assert not forbidden, forbidden
    print("Verification: no vanilla/cache/dist/oo2core/settings files  OK")


if __name__ == "__main__":
    main()
