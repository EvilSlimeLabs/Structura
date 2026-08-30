"""Local release build.

Runs the tests, freezes structura.py with PyInstaller using structura.spec,
and assembles the release zip: the executable plus the data directories the
program reads at runtime.

    python build.py                 full build
    python build.py --skip-tests    freeze and package without running tests
    python build.py --skip-freeze   repackage the executable already in dist/

The version comes from the VERSION file, which is also copied into the zip so
the frozen program can read it back.
"""
import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import zipfile

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


def package(exe, release_version):
    zip_path = os.path.join(DIST, "Structura-%s.zip" % release_version)
    if os.path.isfile(zip_path):
        os.remove(zip_path)

    entries = [(exe, EXE_NAME)]
    for name in LOOSE_FILES:
        path = os.path.join(ROOT, name)
        if os.path.isfile(path):
            entries.append((path, name))
        else:
            print("   warning: %s is missing and will not ship" % name)
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

    print("\n>> packaging %d files (%d source-art files skipped)" % (len(entries), skipped))
    ## sorted entries and a fixed timestamp, so the archive layout is stable
    ## between builds and a diff of two releases is about content, not ordering.
    ## The frozen executable itself is not byte-reproducible.
    entries.sort(key=lambda e: e[1])
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for source, arcname in entries:
            info = zipfile.ZipInfo(arcname, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            with open(source, "rb") as f:
                archive.writestr(info, f.read())
    return zip_path


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--skip-tests", action="store_true",
                        help="do not run the unit tests first")
    parser.add_argument("--skip-freeze", action="store_true",
                        help="reuse the executable already in dist/")
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


if __name__ == "__main__":
    main()
