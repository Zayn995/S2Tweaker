"""A read-only preview of actual generated patches, with conservative baselines."""
from pathlib import PurePosixPath
from . import cfgparse, mod_library
from .tweaks import build_patches, build_root_files, input_ini, summarize


def base_file(path):
    if path.startswith("//") or path.startswith("Scripts/"):
        return None
    name = PurePosixPath(path)
    if ".cfg_patch_" in name.name:
        return str(name.parent / (name.name.split(".cfg_patch_", 1)[0] + ".cfg"))
    if str(name.parent) == ".":
        return None
    return str(name.parent) + ".cfg"


def describe_output(gd, settings, limit=400):
    patches = build_patches(gd, settings)
    resources = build_root_files(gd, settings)
    localized = {path: data for path, data in resources.items() if path.endswith(".locres")}
    ini = input_ini(settings)
    active = summarize(settings)
    lines = [f"Generated result for {settings.mod_name}",
             f"{len(active)} selection summaries · {len(patches)} config files"
             + (" · 1 input settings file" if ini else "")
             + (f" · {len(localized)} job translation files" if localized else ""), "",
             "This preview uses the current selection and installed game data.",
             "It does not install a mod or predict savegame/animation behavior.", ""]
    if not patches and ini is None:
        lines += ["No effective patch. The selection currently produces no game changes.",
                  "A factor on a zero base value or a dependent setting without its switch can have no effect.", ""]
    lines += ["Selected changes", *["• " + item for item in active], "", "Generated values: original → target"]
    roots, total, shown = {}, 0, 0
    cached_roots = {value.name: value for value in gd.__dict__.values()
                    if isinstance(value, cfgparse.CfgStruct)}
    for path, text in sorted(patches.items()):
        leaves = mod_library.patch_leaves(text)
        total += len(leaves)
        if shown >= limit:
            continue
        lines += ["", path]
        base = base_file(path)
        root = None
        if base:
            file = gd.dir / base
            root = cached_roots.get(str(file))
            # Do not parse the very large spawn archive just for a preview.
            if root is None and file.is_file() and file.stat().st_size < 5 * 1024 * 1024:
                if base not in roots:
                    roots[base] = gd._parse(base)
                root = roots[base]
        for leaf, value in leaves:
            if shown >= limit:
                break
            original = None
            if root is not None:
                original = (gd.resolve(root, leaf[0], ".".join(leaf[1:]))
                            if len(leaf) > 1 else root.get(leaf[0]))
            lines.append(f"  {'.'.join(leaf)}: {original if original is not None else '[new or unresolved base]'} → {value}")
            shown += 1
    if ini:
        lines += ["", "Input settings (whole INI file)", ini]
    if localized:
        lines += ["", "Supplementary job translations (experimental; game loading not yet verified)",
                  "Texts come from the current installation. Existing journal and stage identifiers are preserved."]
        lines += [f"  {path}: {len(data):,} bytes" for path, data in sorted(localized.items())]
    lines += ["", f"{total} generated value assignments; {shown} displayed.",
              "Unresolved bases are not assumed to be zero or vanilla. Use More options → Debug export for all patch files."]
    return "\n".join(lines)
