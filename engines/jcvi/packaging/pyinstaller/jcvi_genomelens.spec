# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all

ortools_datas, ortools_binaries, ortools_hiddenimports = collect_all("ortools")

a = Analysis(
    ["../../src/jcvi_genomelens/cli.py"],
    pathex=["../../src"],
    binaries=ortools_binaries,
    datas=[("../../src/jcvi", "jcvi"), *ortools_datas],
    hiddenimports=ortools_hiddenimports,
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
    a.binaries,
    a.datas,
    [],
    name="jcvi-genomelens",
    console=True,
)
