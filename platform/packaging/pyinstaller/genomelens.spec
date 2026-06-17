# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

resource_dir = (Path(SPECPATH) / "../../resources").resolve()
datas = [(str(resource_dir), "resources")] if resource_dir.exists() else []

a = Analysis(
    ["../../src/genomelens/cli/main.py"],
    pathex=["../../src"],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="GenomeLens-runtime",
    console=True,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="GenomeLens",
)
