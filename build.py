"""Local release build.

Runs the tests, freezes structura.py with PyInstaller using structura.spec,
and assembles the release zip: the executable plus the data directories the
program reads at runtime.

    python build.py                    full build
    python build.py --skip-tests       freeze and package without running tests
    python build.py --skip-freeze      repackage the executable already in dist/
    python build.py --update-package   also build the lookup update package

The update package is opt-in because this fork does not publish to the update
server; the output is kept so repointing it later does not mean rewriting the
packaging.

The version comes from the VERSION file, which is also copied into the zip so
the frozen program can read it back.
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile

import tech_pack
from datetime import date

import version

ROOT = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(ROOT, "build")
DIST = os.path.join(ROOT, "dist")
SPEC = os.path.join(ROOT, "structura.spec")
EXE_NAME = "Structura.exe" if os.name == "nt" else "Structura"

## Directories the program opens by relative path at runtime. They ship beside
## the executable rather than inside it: the code reads "lookups/..." and
## "Vanilla_Resource_Pack/..." from the working directory, and a --onefile
## bundle would unpack them somewhere else entirely.
DATA_DIRS = ["lookups", "Vanilla_Resource_Pack"]
LOOSE_FILES = ["VERSION", "LICENSE", "README.md"]

## The TechPack submodule ships beside the executable as well, so the bundle
## toggle works in a release, but only the folders a generated pack draws from.
## Its tests, tools, branding and documentation have no business in a release,
## and it is deliberately kept out of the update package -- the update server
## ships lookup drops, not somebody else's resource pack.
TECH_PACK_DIR = tech_pack.SUBMODULE
TECH_PACK_KEEP = tuple(sorted(set(tech_pack.ASSET_DIRS) | {"entity"}))
TECH_PACK_FILES = ("manifest.json", "LICENSE", "README.md")

## Source art and one-off helper scripts that live in the data directories but
## have no business in a release.
EXCLUDE_SUFFIXES = (".afphoto", ".xcf", ".py", ".psd")
EXCLUDE_NAMES = {"easyItems.txt", "test.py", "Thumbs.db", ".DS_Store"}


def run(cmd, what):
    print("\n>> %s" % what)
    print("   " + " ".join(cmd))
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode != 0:
        sys.exit("\nBuild stopped: %s failed (exit %d)" % (what, result.returncode))


def run_tests():
    run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-t", ".", "-v"],
        "unit tests")


def freeze():
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        sys.exit("Build stopped: PyInstaller is not installed.\n"
                 "  python -m pip install -r requirements-build.txt")
    for path in (BUILD, DIST):
        if os.path.isdir(path):
            shutil.rmtree(path)
    run([sys.executable, "-m", "PyInstaller", "--clean", "--noconfirm", SPEC],
        "PyInstaller")
    exe = os.path.join(DIST, EXE_NAME)
    if not os.path.isfile(exe):
        sys.exit("Build stopped: PyInstaller produced no %s" % EXE_NAME)
    return exe


def should_ship(path):
    name = os.path.basename(path)
    if name in EXCLUDE_NAMES or name.startswith("."):
        return False
    return not name.endswith(EXCLUDE_SUFFIXES)


def data_entries():
    """(source path, archive name) for everything under the data directories."""
    entries = []
    skipped = 0
    for data_dir in DATA_DIRS:
        root_dir = os.path.join(ROOT, data_dir)
        if not os.path.isdir(root_dir):
            sys.exit("Build stopped: %s is missing" % data_dir)
        for dirpath, dirnames, filenames in os.walk(root_dir):
            dirnames[:] = [d for d in dirnames if not d.startswith(".")]
            for filename in filenames:
                path = os.path.join(dirpath, filename)
                if not should_ship(path):
                    skipped += 1
                    continue
                entries.append((path, os.path.relpath(path, ROOT).replace("\\", "/")))
    return entries, skipped


def tech_pack_entries():
    """(source, archive name) for the parts of the TechPack submodule we ship.

    Missing is not fatal: a checkout without submodules still builds, and
    tech_pack.available() turns the toggle off at runtime.
    """
    root_dir = os.path.join(ROOT, TECH_PACK_DIR)
    if not os.path.isdir(root_dir):
        print("   warning: %s is missing; the built app will not offer the "
              "TechPack toggle" % TECH_PACK_DIR)
        return []
    entries = []
    for folder in TECH_PACK_KEEP:
        source = os.path.join(root_dir, folder)
        for dirpath, dirnames, filenames in os.walk(source):
            dirnames[:] = [d for d in dirnames if not d.startswith(".")]
            for filename in filenames:
                path = os.path.join(dirpath, filename)
                if not should_ship(path):
                    continue
                entries.append((path, os.path.relpath(path, ROOT).replace("\\", "/")))
    for filename in TECH_PACK_FILES:
        path = os.path.join(root_dir, filename)
        if os.path.isfile(path):
            entries.append((path, os.path.relpath(path, ROOT).replace("\\", "/")))
    return entries


def write_zip(zip_path, entries):
    """Sorted entries and a fixed timestamp, so the archive layout is stable
    between builds and a diff of two releases is about content, not ordering.
    The frozen executable itself is not byte-reproducible."""
    if os.path.isfile(zip_path):
        os.remove(zip_path)
    os.makedirs(os.path.dirname(zip_path), exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for source, arcname in sorted(entries, key=lambda e: e[1]):
            info = zipfile.ZipInfo(arcname, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            with open(source, "rb") as f:
                archive.writestr(info, f.read())
    return zip_path


def stamp_lookup_version():
    """The update server identifies a lookup drop by this string."""
    today = date.today()
    name = "update_package_%d-%d-%d" % (today.day, today.month, today.year)
    path = os.path.join(ROOT, "lookups", "lookup_version.json")
    with open(path, encoding="utf-8-sig") as f:
        data = json.load(f)
    data["version"] = name
    with open(path, "w", encoding="utf-8", newline="") as f:
        json.dump(data, f, indent=2)
    return name


def update_package():
    """The lookup tables and the vanilla pack, for the update server."""
    name = stamp_lookup_version()
    entries, _ = data_entries()
    path = write_zip(os.path.join(DIST, name + ".zip"), entries)
    print("\n>> update package: %s (%d files)" % (os.path.basename(path), len(entries)))
    return path


def package(exe, release_version):
    entries = [(exe, EXE_NAME)]
    for name in LOOSE_FILES:
        path = os.path.join(ROOT, name)
        if os.path.isfile(path):
            entries.append((path, name))
        else:
            print("   warning: %s is missing and will not ship" % name)
    data, skipped = data_entries()
    entries.extend(data)
    tech = tech_pack_entries()
    entries.extend(tech)

    print("\n>> packaging %d files (%d TechPack, %d source-art files skipped)"
          % (len(entries), len(tech), skipped))
    return write_zip(os.path.join(DIST, "Structura-%s.zip" % release_version), entries)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--skip-tests", action="store_true",
                        help="do not run the unit tests first")
    parser.add_argument("--skip-freeze", action="store_true",
                        help="reuse the executable already in dist/")
    parser.add_argument("--update-package", action="store_true",
                        help="also build the lookup update package for the update server")
    args = parser.parse_args()

    release_version = version.read()
    if release_version == version.FALLBACK:
        sys.exit("Build stopped: VERSION is missing or empty")
    print("Structura %s" % release_version)

    if not args.skip_tests:
        run_tests()

    if args.skip_freeze:
        exe = os.path.join(DIST, EXE_NAME)
        if not os.path.isfile(exe):
            sys.exit("Build stopped: --skip-freeze but dist/%s does not exist" % EXE_NAME)
    else:
        exe = freeze()

    zip_path = package(exe, release_version)
    digest = hashlib.sha256(open(zip_path, "rb").read()).hexdigest()
    print("\nBuilt %s" % os.path.relpath(zip_path, ROOT))
    print("  %.1f MB" % (os.path.getsize(zip_path) / 1024 / 1024))
    print("  sha256 %s" % digest)

    if args.update_package:
        update_package()


if __name__ == "__main__":
    main()
