block_cipher = None

added_files = [
    ('barvocuc/ui', 'barvocuc/ui'),
    ('barvocuc/translations', 'barvocuc/translations'),
    ('barvocuc/media', 'barvocuc/media'),
    ('barvocuc/COPYING.html', 'barvocuc/'),
]


a = Analysis(
    ['gui_stub.py'],
    pathex=['.'],
    binaries=None,
    datas=added_files,
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        '_codecs_cn', '_codecs_hk', '_codecs_iso2022',
        '_codecs_jp', '_codecs_kr', '_codecs_tw', '_curses',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher
)


pyz = PYZ(a.pure, a.zipped_data)


exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='barvocuc-gui',
    debug=False,
    strip=False,
    upx=True,
    console=False,
)
