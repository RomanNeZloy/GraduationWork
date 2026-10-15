"""
server_main.py — Точка входа сервера мониторинга.

Запуск:
    python server_main.py                          # дефолтный конфиг
    python server_main.py --port 9000              # другой порт
    python server_main.py --no-dashboard           # без дашборда
    python server_main.py --refresh 2              # обновление каждые 2 сек
"""
import sys
import os

# Добавляем корневую папку проекта в пути поиска Python
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

"""
server_main.py — Точка входа сервера мониторинга.
ИСПРАВЛЕНО: правильная передача storage между FastAPI и Dashboard.
"""

import argparse
import logging
import signal
import sys
import threading

import uvicorn

from server.storage import MetricsStorage
from database.models import DatabaseManager

# ═══════════════════════════════════════════════════
#  Глобальные объекты (ОДИН экземпляр на всё приложение)
# ═══════════════════════════════════════════════════
_storage: MetricsStorage = None
_db: DatabaseManager = None
_dashboard = None
_running = True


def signal_handler(signum, frame):
    """Обработчик Ctrl+C."""
    global _running
    print("\n⏹️  Stopping server...")
    _running = False
    if _dashboard:
        _dashboard.stop()


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


# ═══════════════════════════════════════════════════
#  Главный запуск
# ═══════════════════════════════════════════════════
def main():
    global _storage, _db, _dashboard

    # Парсинг аргументов
    parser = argparse.ArgumentParser(description="Monitoring Server")
    parser.add_argument("--host", default="0.0.0.0", help="Хост для слушания")
    parser.add_argument("--port", type=int, default=8000, help="Порт")
    parser.add_argument("--db", default="monitoring.db", help="Путь к БД")
    parser.add_argument("--no-dashboard", action="store_true", help="Без дашборда")
    parser.add_argument("--refresh", type=float, default=1.0, help="Частота обновления дашборда")
    parser.add_argument("--debug", action="store_true", help="Отладочные логи")
    args = parser.parse_args()

    # Настройка логирования
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S"
    )
    logger = logging.getLogger("Server")

    # Загружаем конфиг
    import yaml
    from pathlib import Path

    config = {}
    config_path = Path("config.yaml")
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}

    server_cfg = config.get("server", {})
    thresholds = config.get("thresholds", {})

    # ═══════════════════════════════════════════════════
    #  Инициализация глобальных объектов
    # ═══════════════════════════════════════════════════
    _storage = MetricsStorage(
        offline_threshold=server_cfg.get("offline_threshold", 30)
    )
    _db = DatabaseManager(args.db)

    # ═══════════════════════════════════════════════════
    #  Инжектим в FastAPI app
    # ═══════════════════════════════════════════════════
    import server.app as app_module
    app_module.storage = _storage
    app_module.db = _db

    logger.info("=" * 60)
    logger.info("🚀 Monitoring Server")
    logger.info(f"   URL: http://{args.host}:{args.port}")
    logger.info(f"   Docs: http://{args.host}:{args.port}/docs")
    logger.info(f"   Database: {args.db}")
    logger.info("=" * 60)

    # Запускаем дашборд в отдельном потоке
    if not args.no_dashboard:
        from server.dashboard import Dashboard
        _dashboard = Dashboard(
            storage=_storage,  # ← Передаём ТОТ ЖЕ экземпляр storage
            refresh_rate=args.refresh,
            thresholds=thresholds
        )
        _dashboard.start()
        logger.info("📊 Dashboard started")

    # Запускаем FastAPI-сервер
    try:
        from server.app import app
        uvicorn.run(
            app,
            host=args.host,
            port=args.port,
            log_level="warning" if not args.debug else "info",
            access_log=False
        )
    except KeyboardInterrupt:
        pass
    finally:
        if _dashboard:
            _dashboard.stop()
        if _db:
            _db.close()
        logger.info("Server stopped")


if __name__ == "__main__":
    main()