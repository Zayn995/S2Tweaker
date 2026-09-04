"""Baut tools/repak.exe aus dem Quellcode — OHNE Download-Funktion.

    python tools/build_repak.py            -> tools/repak.exe
    python tools/build_repak.py --out <pfad>
    python tools/build_repak.py --keep     (Quellbaum stehen lassen)

Braucht Rust (rustup.rs). Dauert ~20 Sekunden.

WARUM
-----
Bis 04.09.2026 lag hier die fertige repak.exe vom Upstream-Release. Die
hat zwei Eigenschaften, die wir nicht wollen:

1. Sie laedt die proprietaere Oodle-DLL bei Bedarf SELBST aus dem Netz
   nach und laedt sie dann als nativen Code. Ein Programm, das zur
   Laufzeit eine Bibliothek herunterlaedt und ausfuehrt, ist genau das
   Verhaltensmuster, auf das die ML-Heuristiken der Virenscanner
   anspringen — und die Freigabe auf Nexus scheiterte an solchen
   Fehlalarmen. Ausserdem prueft repaks eigener Download TLS gegen
   EINGEBAUTE Mozilla-Roots statt gegen den Windows-Zertifikatsspeicher;
   hinter AV-/Proxy-HTTPS-Inspektion schlaegt er fehl (Bugreport foxce,
   31.08.2026).
2. Sie ist ein fertiges Fremdbinaerteil im Release. Fuer die Zusage
   „alles stammt aus diesem oeffentlichen Quellcode" (Nexus, SignPath)
   ist das die letzte Luecke.

Dieses Skript loest beides: es baut repak selbst und entfernt dabei die
Download-Funktion aus `oodle_loader`. Danach KANN das Programm gar nicht
mehr herunterladen — die Funktion ist nicht abgeschaltet, sie ist nicht
vorhanden, samt HTTP-/TLS-Stack (`ureq`). Oodle-Unterstuetzung bleibt:
liegt die DLL da, wird sie benutzt; fehlt sie, kommt ein klarer Fehler,
und S2Tweaker erklaert dem Nutzer, woher er sie bekommt.

repak ist MIT ODER Apache-2.0 — Aendern und Ausliefern ist erlaubt. Dass
es ein VERAENDERTER Build ist, steht in THIRD_PARTY_LICENSES.txt.
"""
import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
REPAK_URL = "https://github.com/trumank/repak.git"
REPAK_TAG = "v0.2.3"          # Version, gegen die S2Tweaker getestet ist

# --- Der Eingriff: fetch_oodle() laedt nichts mehr nach -------------------
OLD_FETCH = """fn fetch_oodle() -> Result<std::path::PathBuf> {
    let oodle_path = std::env::current_exe()?.with_file_name(OODLE_PLATFORM.name);
    if !oodle_path.exists() {
        let buffer = ureq::get(&url()).call()?.into_body().read_to_vec()?;
        check_hash(&buffer)?;
        std::fs::write(&oodle_path, buffer)?;
    }"""
NEW_FETCH = """fn fetch_oodle() -> Result<std::path::PathBuf> {
    // S2Tweaker-Build: NIEMALS herunterladen. Siehe tools/build_repak.py.
    let oodle_path = std::env::current_exe()?.with_file_name(OODLE_PLATFORM.name);
    if !oodle_path.exists() {
        return Err(Error::Missing {
            path: oodle_path.display().to_string(),
            url: url(),
        });
    }"""

OLD_ERR = """    #[error("ureq error {0:?}")]
    Ureq(Box<ureq::Error>),"""
NEW_ERR = """    #[error("Oodle library not found at {path} - this build never downloads \
it, put the file there yourself (source: {url})")]
    Missing { path: String, url: String },"""

OLD_FROM = """impl From<ureq::Error> for Error {
    fn from(value: ureq::Error) -> Self {
        Self::Ureq(value.into())
    }
}
"""

OLD_DEP = '\nureq = "3.1"'


def patch(src: Path) -> None:
    """Download-Weg entfernen. Jede Ersetzung wird geprueft — schlaegt eine
    fehl, hat sich repak geaendert und der Eingriff muss nachgezogen
    werden, statt still etwas anderes zu bauen."""
    lib = src / "oodle_loader" / "src" / "lib.rs"
    text = lib.read_text(encoding="utf-8")
    for old, new, what in ((OLD_FETCH, NEW_FETCH, "fetch_oodle()"),
                           (OLD_ERR, NEW_ERR, "Fehlertyp"),
                           (OLD_FROM, "", "From<ureq::Error>")):
        if old not in text:
            raise SystemExit(
                f"repak {REPAK_TAG}: {what} sieht anders aus als erwartet — "
                "tools/build_repak.py muss angepasst werden.")
        text = text.replace(old, new, 1)
    if "ureq" in text:
        raise SystemExit("ureq wird noch benutzt — Eingriff unvollstaendig.")
    lib.write_text(text, encoding="utf-8")

    cargo = src / "oodle_loader" / "Cargo.toml"
    ctext = cargo.read_text(encoding="utf-8")
    if OLD_DEP not in ctext:
        raise SystemExit("ureq-Abhaengigkeit nicht gefunden — Eingriff pruefen.")
    cargo.write_text(ctext.replace(OLD_DEP, "", 1), encoding="utf-8")
    print("  Download-Funktion und HTTP-Stack entfernt")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(REPO / "tools" / "repak.exe"))
    ap.add_argument("--keep", action="store_true",
                    help="Quellbaum nicht loeschen (zum Nachsehen)")
    args = ap.parse_args()

    if shutil.which("cargo") is None:
        raise SystemExit("cargo fehlt — Rust installieren (https://rustup.rs).")

    work = Path(tempfile.mkdtemp(prefix="s2t_repak_"))
    src = work / "repak"
    try:
        print(f"Hole repak {REPAK_TAG} ...")
        subprocess.run(["git", "clone", "--quiet", "--depth", "1",
                        "--branch", REPAK_TAG, REPAK_URL, str(src)],
                       check=True)
        patch(src)
        print("Baue (cargo release) ...")
        subprocess.run(["cargo", "build", "--release", "-p", "repak_cli"],
                       cwd=src, check=True)
        built = src / "target" / "release" / "repak.exe"
        if not built.is_file():
            built = src / "target" / "release" / "repak"
        if not built.is_file():
            raise SystemExit("Build lief durch, aber es gibt keine Binaerdatei.")
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(built, out)
        print(f"\nFertig: {out} ({out.stat().st_size:,} Bytes)")
    finally:
        if args.keep:
            print(f"Quellbaum bleibt: {src}")
        else:
            shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
