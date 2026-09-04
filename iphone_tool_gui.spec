# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['iphone_tool_gui.py'],
    pathex=[],
    binaries=[],
    datas=[('D:\\iphone_tool\\*.exe', '.'), ('D:\\iphone_tool\\*.dll', '.'), ('D:\\iphone_tool\\*.ipsw', '.'), ('D:\\iphone_tool\\*.png', '.'), ('D:\\iphone_tool\\*.ico', '.'), ('D:\\iphone_tool\\*.json', '.'), ('D:\\iphone_tool\\*.txt', '.')],
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
    name='iphone_tool_gui',
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
