# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for PyRefactor."""

import sys
from pathlib import Path

# Get the project root
project_root = Path(SPECPATH)
src_path = project_root / "src"

# Analysis configuration
a = Analysis(
    [str(src_path / "pyrefactor" / "__main__.py")],
    pathex=[str(src_path)],
    binaries=[],
    datas=[
        (str(src_path / "pyrefactor" / "py.typed"), "pyrefactor"),
    ],
    hiddenimports=[
        "pyrefactor",
        "pyrefactor.analyzer",
        "pyrefactor.ast_visitor",
        "pyrefactor.config",
        "pyrefactor.models",
        "pyrefactor.reporter",
        "pyrefactor.detectors",
        "pyrefactor.detectors.boolean_logic",
        "pyrefactor.detectors.comparisons",
        "pyrefactor.detectors.complexity",
        "pyrefactor.detectors.context_manager",
        "pyrefactor.detectors.control_flow",
        "pyrefactor.detectors.dict_operations",
        "pyrefactor.detectors.duplication",
        "pyrefactor.detectors.loops",
        "pyrefactor.detectors.performance",
        "colorama",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "pytest",
        "hypothesis",
        "setuptools",
        "pip",
        "wheel",
        "distutils",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="PyRefactor",
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
    version="file_version_info.txt",
)

