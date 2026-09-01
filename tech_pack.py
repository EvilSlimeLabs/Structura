"""Fold the Bedrock Technical Resource Pack into a generated Structura pack.

Both packs replace `entity/armor_stand.entity.json`, and a client entity file in
a resource pack **replaces** the vanilla one rather than merging with it. Between
two packs only the higher one in the player's list is read at all, so running
Structura and TechPack side by side silently loses whichever sits lower: either
the ghost blocks stop appearing, or every TechPack visualisation does. There is
no ordering that gives both.

Bundling is the way out. The two entity descriptions are merged into one file
and TechPack's supporting assets are copied in beside Structura's, so a single
pack drives both sets of features and the ordering question disappears. The
player then loads only the generated pack; keeping the standalone TechPack
applied as well re-creates the conflict.

The submodule is reference material at rest, so nothing here runs unless the
caller asks for it. When `be_tech_pack/` is absent -- a checkout without
submodules -- `available()` is False and the toggle has nothing to offer.
"""
import os
import shutil
import sys

import jsonc

SUBMODULE = "be_tech_pack"


def _root():
    """Where be_tech_pack/ lives, nearest first.

    A frozen build runs from a PyInstaller temp directory, so the copy that
    matters ships beside the executable -- the same lookup version.py does for
    the VERSION file, and the reason lookups/ and Vanilla_Resource_Pack/ are
    packaged next to the exe rather than inside it.
    """
    candidates = []
    if getattr(sys, "frozen", False):
        candidates.append(os.path.dirname(sys.executable))
    candidates.append(os.path.dirname(os.path.abspath(__file__)))
    candidates.append(os.getcwd())
    for directory in candidates:
        path = os.path.join(directory, SUBMODULE)
        if os.path.isfile(os.path.join(path, "entity", "armor_stand.entity.json")):
            return path
    return os.path.join(candidates[-1], SUBMODULE)


ROOT = _root()
ENTITY = os.path.join(ROOT, "entity", "armor_stand.entity.json")
MANIFEST = os.path.join(ROOT, "manifest.json")

## copied wholesale into the pack. Structura only ever writes entity/,
## models/entity/armor_stand.larger_render.geo.json, textures/entity/ and its
## own render_controllers file, so nothing here lands on top of its output --
## and the one file both projects ship, armor_stand.larger_render.geo.json, is
## byte for byte the same asset in both.
ASSET_DIRS = ("animation_controllers", "animations", "materials", "models",
              "particles", "render_controllers", "textures")

## the armor stand is merged rather than copied; the player entity has no
## Structura counterpart, so it goes in as it stands
ASSET_FILES = (os.path.join("entity", "player.entity.json"),)


def available():
    """Whether the submodule is checked out and carries what we need."""
    return os.path.isfile(ENTITY) and os.path.isdir(ROOT)


def version():
    """TechPack's own version, for the manifest description and the log."""
    if not os.path.isfile(MANIFEST):
        return "unknown"
    try:
        header = jsonc.load(MANIFEST).get("header", {})
        return ".".join(str(n) for n in header.get("version", [])) or "unknown"
    except Exception:
        return "unknown"


def description():
    """TechPack's client entity description, as data."""
    entity = jsonc.load(ENTITY)
    return entity["minecraft:client_entity"]["description"]


def copy_assets(work_dir):
    """Copy TechPack's assets into the pack tree. Returns what was written.

    Structura's own files are never overwritten. Any collision is reported
    rather than resolved silently, because a file that differs and gets skipped
    is the sort of thing that shows up much later as a missing texture.
    """
    written, skipped = 0, []
    for folder in ASSET_DIRS:
        source = os.path.join(ROOT, folder)
        if not os.path.isdir(source):
            continue
        for base, _dirs, files in os.walk(source):
            rel = os.path.relpath(base, ROOT)
            target = os.path.join(work_dir, rel)
            os.makedirs(target, exist_ok=True)
            for name in files:
                dest = os.path.join(target, name)
                if os.path.exists(dest):
                    skipped.append(os.path.join(rel, name).replace("\\", "/"))
                    continue
                shutil.copyfile(os.path.join(base, name), dest)
                written += 1

    for rel in ASSET_FILES:
        source = os.path.join(ROOT, rel)
        dest = os.path.join(work_dir, rel)
        if not os.path.isfile(source):
            continue
        if os.path.exists(dest):
            skipped.append(rel.replace("\\", "/"))
            continue
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copyfile(source, dest)
        written += 1

    return written, skipped
