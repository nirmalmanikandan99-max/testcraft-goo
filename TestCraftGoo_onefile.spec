# -*- mode: python ; coding: utf-8 -*-
# Single-file (onefile) build: produces dist\TestCraftGoo.exe containing the
# whole app + bundled libraries. Use for distributing one file to users.
# Tracked in Git via LFS (the binary exceeds GitHub's 100 MB file limit).
from PyInstaller.utils.hooks import collect_all

datas = [
    ("app.py", "."),
    ("src", "src"),
    ("prompts", "prompts"),
    (".streamlit", ".streamlit"),
    ("venv/Lib/site-packages/streamlit/static", "streamlit/static"),
]
binaries = []
hiddenimports = []

for package in ("streamlit", "pypdf", "docx", "openpyxl", "ollama"):
    tmp_datas, tmp_binaries, tmp_hidden = collect_all(package)
    datas += tmp_datas
    binaries += tmp_binaries
    hiddenimports += tmp_hidden

a = Analysis(
    ["launcher.py"],
    pathex=[],
    binaries=binaries,
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
    name="TestCraftGoo",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    contents_directory=".",
    icon=None,
)
