# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for PyRefactor.

Generate ``file_version_info.txt`` before building:
  python scripts/generate_file_version_info.py
"""

from pathlib import Path

# Get the project root
project_root = Path(SPECPATH)
src_path = project_root / "src"
pyproject_path = project_root / "pyproject.toml"

# Analysis configuration
a = Analysis(
    [str(project_root / "scripts" / "pyinstaller_entry.py")],
    pathex=[str(src_path)],
    binaries=[],
    datas=[
        (str(src_path / "pyrefactor" / "py.typed"), "pyrefactor"),
        (str(pyproject_path), "."),
    ],
    hiddenimports=[
        "pyrefactor",
        "pyrefactor.analyzer",
        "pyrefactor.ast_visitor",
        "pyrefactor.config",
        "pyrefactor.models",
        "pyrefactor.reporter",
        "pyrefactor.json_reporter",
        "pyrefactor._version",
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
    upx=False,
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

