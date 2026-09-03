# -*- mode: python ; coding: utf-8 -*-
# Builds the console executable, the twin of structura.spec's windowed one. It
# carries the same data with the interface libraries excluded. Driven by
# build.py, which runs the tests, freezes both specs and then zips the pair.
#
# The release is a **single self-contained executable**. Everything the program
# reads is packed inside it: the lookup tables, the trimmed vanilla resource
# pack, the parts of the TechPack submodule a generated pack needs,
# pyproject.toml, which holds the version, and the branding. It is unpacked at
# run time into the private folder PyInstaller points sys._MEIPASS at, and
# paths.py resolves every data read through there.
#
# A copy of any of those directories placed *beside* the executable still wins,
# because a bundle is read only. An edited lookup table dropped next to the exe
# takes effect without a rebuild, and paths.py finds it first.

import os

from PyInstaller.utils.hooks import collect_data_files

# --- Structura's own data --------------------------------------------------

## Source art and helper scripts that live in the data directories but have no
## business in a release. Kept in step with build.py.
SKIP_SUFFIXES = (".afphoto", ".xcf", ".psd", ".py", ".pyc")
SKIP_NAMES = {"easyItems.txt", "Thumbs.db", ".DS_Store"}

def tree(folder, into=None):
    """Every shippable file under `folder`, as PyInstaller (source, dest) pairs."""
    found = []
    into = into or folder
    for base, dirs, files in os.walk(folder):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for name in files:
            if name in SKIP_NAMES or name.lower().endswith(SKIP_SUFFIXES):
                continue
            source = os.path.join(base, name)
            target = os.path.join(into, os.path.relpath(base, folder))
            found.append((source, target))
    return found


## Structura's data lives inside the package, which is what makes the project
## pip installable; paths.py looks for it beside the executable, then in the
## bundle, then in the package, so unpacking it at the bundle root works.
## No window here, so no fonts and no pictures.
datas = []
for folder in ("lookups", "Vanilla_Resource_Pack"):
    source = os.path.join("structura", folder)
    if os.path.isdir(source):
        datas += tree(source, folder)

## pyproject.toml holds the version, and there is no installed distribution to
## read it out of once this is frozen, so the file itself comes along
datas += [("pyproject.toml", ".")]
## TechPack's assets, staged into the package by tools/stage_tech_pack.py so
## that a pip install carries them too. The submodule itself is not shipped.
if os.path.isdir(os.path.join("structura", "techpack")):
    datas += tree(os.path.join("structura", "techpack"), "techpack")

# --- library data ----------------------------------------------------------

## The command line build has no window, so none of the interface libraries
## nor the fonts they draw with are carried.
hiddenimports = []




a = Analysis(
    ['structura/cli/__main__.py'],
    ## the entry script lives inside the package it imports, so the tree
    ## above it has to be on the path for `import cli` to resolve
    pathex=[SPECPATH],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    ## The window and everything behind it. Nothing this entry point imports
    ## reaches `structura.ui`, because the language tables both halves need sit
    ## in the shared layer. This is a guard rather than a load-bearing list. If
    ## the interface ever creeps back into the command line's imports, the build
    ## fails here instead of quietly growing by six megabytes.
    excludes=['customtkinter', 'tkinterdnd2', 'darkdetect', 'structura.ui'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Structura-cli',
    icon='structura/images/pack_icon.ico',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
