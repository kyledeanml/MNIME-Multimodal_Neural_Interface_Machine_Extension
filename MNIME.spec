# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from PyInstaller.utils.hooks import collect_all

if not os.path.exists('version_info.txt'):
    with open('version_info.txt', 'w') as f:
        f.write('''VSVersionInfo(
  ffi=FixedFileInfo(filevers=(1, 0, 0, 0), prodvers=(1, 0, 0, 0), mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040904B0', [
        StringStruct('CompanyName', 'MNIME'), StringStruct('FileDescription', 'MNIME Desktop'),
        StringStruct('FileVersion', '1.0.0'), StringStruct('InternalName', 'MNIME'),
        StringStruct('OriginalFilename', 'MNIME.exe'), StringStruct('ProductName', 'MNIME'),
        StringStruct('ProductVersion', '1.0.0')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)''')

datas = [('MN.ico', '.'), ('models', 'models')]
binaries = []
hiddenimports = [
    'pymupdf',
    'pypdf',
    'PIL',
    'PIL.Image',
    'PIL.ImageDraw',
    'pdf2docx',
    'docx',
    'PyQt6',
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'PyQt6.QtNetwork',
    'PyQt6.QtPrintSupport',
    'core',
    'core.app_icon',
    'core.file_item',
    'core.nlp_engine',
    'core.pdf_engine',
    'core.print_engine',
    'core.search_engine',
    'core.windows_integration',
    'core.worker',
    'ui',
    'ui.action_bar',
    'ui.carousel_view',
    'ui.cursor_fx',
    'ui.document_viewer',
    'ui.file_card',
    'ui.file_dialog',
    'ui.icons',
    'ui.image_editor',
    'ui.main_window',
    'ui.merge_particles',
    'ui.minimize_animation',
    'ui.nlp_view',
    'ui.output_view',
    'ui.pdf_editor',
    'ui.reader_dialog',
    'ui.nerds',
    'ui.tabs_bar',
]

for pkg in ['pymupdf', 'pdf2docx', 'pypdf', 'langchain', 'langchain_community', 'sentence_transformers', 'faiss', 'llama_cpp']:
    try:
        pkg_datas, pkg_binaries, pkg_hiddenimports = collect_all(pkg)
        datas += pkg_datas
        binaries += pkg_binaries
        hiddenimports += pkg_hiddenimports
    except Exception:
        pass

a = Analysis(
    ['MNIME.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'tensorflow', 'nltk', 'IPython', 'spacy', 'torchvision'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='MNIME',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['MN.ico'],
    version='version_info.txt',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='MNIME',
)
