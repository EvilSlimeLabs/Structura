# -*- mode: python ; coding: utf-8 -*-
# Driven by build.py, which runs the tests, freezes with this spec and then
# packages the executable together with lookups/ and Vanilla_Resource_Pack/.
# Those directories are read by relative path at runtime, so they ship beside
# the executable and are deliberately not listed in `datas`.


a = Analysis(
    ['structura.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
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
    icon='pack_icon.ico',
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
