"""Local release build.

Runs the tests, freezes structura.py with PyInstaller using structura.spec, and
writes the release: a **single self-contained executable**, and a zip of it for
places that will not carry a bare .exe. Nothing has to be extracted alongside it
-- the lookup tables, the vanilla pack and the TechPack assets are all inside.

    python build.py                    full build
    python build.py --skip-tests       freeze and package without running tests
    python build.py --skip-freeze      repackage the executable already in dist/
    python build.py --update-package   also build the lookup update package

The update package is opt-in because this fork does not publish to the update
server; the output is kept so repointing it later does not mean rewriting the
packaging.

The version comes from the VERSION file, which is packed into the executable so
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

import paths
from datetime import date

import version

ROOT = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(ROOT, "build")
DIST = os.path.join(ROOT, "dist")
SPEC = os.path.join(ROOT, "structura.spec")
EXE_NAME = "Structura.exe" if os.name == "nt" else "Structura"

## Directories the program reads at runtime. They are packed *inside*
## the executable -- see structura.spec -- so nothing here ships beside it any
## more. The list is still needed because the update package is built from it.
DATA_DIRS = list(paths.DATA_DIRS)
LOOSE_FILES = ["LICENSE", "README.md"]

## The TechPack submodule is packed into the executable by structura.spec, which
## keeps its own list of the folders a generated pack draws from. It is
## deliberately kept out of the update package -- the update server ships lookup
## drops, not somebody else's resource pack.

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
    """The release: the executable, and a zip of it.

    The executable is self-contained, so the zip exists only because some
    browsers and chat clients refuse a bare .exe download. Extracting it gives
    you the program, not a folder you have to keep together -- which is the
    whole point of the self-contained packaging.

    The licence travels with the binary because it has to; nothing else does.
    """
    entries = [(exe, EXE_NAME)]
    for name in LOOSE_FILES:
        path = os.path.join(ROOT, name)
        if os.path.isfile(path):
            entries.append((path, name))
        else:
            print("   warning: %s is missing and will not ship" % name)

    print("\n>> packaging the executable (%.1f MB) and %d loose files"
          % (os.path.getsize(exe) / 1024 / 1024, len(entries) - 1))
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
    if args.update_package:
        update_package()

    digest = hashlib.sha256(open(zip_path, "rb").read()).hexdigest()
    print("\nBuilt %s" % os.path.relpath(exe, ROOT))
    print("      %s" % os.path.relpath(zip_path, ROOT))
    print("  %.1f MB zipped" % (os.path.getsize(zip_path) / 1024 / 1024))
    print("  sha256 %s" % digest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
