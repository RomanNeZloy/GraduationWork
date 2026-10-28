# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['server_main.py'],
    pathex=[],
    binaries=[],
    datas=[
        # Включаем папки и файлы, которые нужны серверу
        ('server', 'server'),
        ('database', 'database'),
        ('collectors', 'collectors'),
        ('config.yaml', '.'),
    ],
    hiddenimports=[
        # FastAPI и его зависимости
        'fastapi',
        'fastapi.applications',
        'fastapi.routing',
        'fastapi.middleware',
        'fastapi.middleware.cors',
        'fastapi.responses',
        'fastapi.websockets',

        # Starlette (основа FastAPI)
        'starlette',
        'starlette.applications',
        'starlette.routing',
        'starlette.middleware',
        'starlette.responses',
        'starlette.websockets',
        'starlette.status',

        # Pydantic (валидация данных)
        'pydantic',
        'pydantic.fields',
        'pydantic.main',

        # Uvicorn и его зависимости
        'uvicorn',
        'uvicorn.main',
        'uvicorn.config',
        'uvicorn.server',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.logging',

        # HTTP-библиотеки
        'httptools',
        'httpx',
        'anyio',
        'anyio._backends',
        'anyio._backends._asyncio',
        'sniffio',
        'h11',

        # Rich и его компоненты
        'rich',
        'rich.console',
        'rich.live',
        'rich.table',
        'rich.panel',
        'rich.layout',
        'rich.text',
        'rich.align',
        'rich.theme',
        'rich.color',
        'rich.style',
        'rich.markup',
        'rich._emoji_replace',
        'rich.emoji',
        'rich.columns',
        'rich.progress',
        'rich.spinner',
        'rich.logging',
        'rich.traceback',
        'rich.pretty',
        'pygments',
        'pygments.lexers',
        'pygments.lexers.python',
        'pygments.formatters',
        'commonmark',
        'mdit_py_emoji',

        # YAML
        'yaml',

        # SQLite (встроен, но на всякий случай)
        'sqlite3',
        'sqlite3.dbapi2',

        # Наши модули
        'server.app',
        'server.storage',
        'server.dashboard',
        'database.models',
        'database.schema',
        'collectors',
        'collectors.base',
        'collectors.cpu',
        'collectors.memory',
        'collectors.disk',
        'collectors.network',
        'collectors.system',
        'collectors.devices',
        'collectors.gpu',

        # Системные модули
        'asyncio',
        'threading',
        'socket',
        'json',
        'datetime',
        'pathlib',
        'typing',
        'logging',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'PIL',
        'cv2',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='MonitoringServer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # ВАЖНО: показывать консоль для дашборда
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Можно добавить иконку: icon='server_icon.ico'
)