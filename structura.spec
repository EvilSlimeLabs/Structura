# -*- mode: python ; coding: utf-8 -*-
# Builds the windowed executable. Driven by build.py, which runs the tests,
# freezes with this spec and structura_cli.spec, and then zips both.
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
#
# Also listed here is library data the program never names itself and so cannot
# find by path. CustomTkinter loads its colour themes and widget fonts from JSON
# inside its own package, and tkinterdnd2 loads a compiled tkdnd library.

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
datas = []
for folder in ("lookups", "Vanilla_Resource_Pack", "fonts", "images"):
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

datas += collect_data_files("customtkinter")
hiddenimports = ["customtkinter", "darkdetect"]

# Dropping files onto the window is a convenience, not a requirement: if
# tkinterdnd2 is not installed the window still opens and the add button still
# works, so a missing package must not stop the build.
try:
    datas += collect_data_files("tkinterdnd2")
    hiddenimports.append("tkinterdnd2")
except Exception:
    pass


a = Analysis(
    ['structura/__main__.py'],
    ## the entry script lives inside the package it imports, so the tree above
    ## it has to be on the path for `import structura` to resolve
    pathex=[SPECPATH],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='Structura',
    icon='structura/images/pack_icon.ico',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
