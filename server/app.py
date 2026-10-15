"""
server/app.py — FastAPI-сервер для приёма метрик.

Эндпоинты:
- POST /api/metrics — приём метрик от агента
- GET  /api/health — проверка работоспособности
- GET  /api/hosts — список всех хостов
- GET  /api/hosts/{hostname} — метрики конкретного хоста
- GET  /api/stats — общая статистика
- DELETE /api/hosts/{hostname} — удалить хост
"""

import logging
from typing import Dict, Any
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from server.storage import MetricsStorage
from database.models import DatabaseManager

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════
#  Создание приложения
# ═══════════════════════════════════════════════════
app = FastAPI(
    title="Cluster Monitoring Server",
    description="Сервер для мониторинга работоспособности кластера рабочих мест",
    version="1.0.0",
)

# Глобальные объекты (инициализируются в startup)
storage: MetricsStorage = None
db: DatabaseManager = None


# ═══════════════════════════════════════════════════
#  События запуска и остановки
# ═══════════════════════════════════════════════════
@app.on_event("startup")
async def startup_event():
    """Инициализация при запуске сервера."""
    global storage, db

    if storage is None or db is None:
        raise RuntimeError("Storage or DB not initialized. Run via server_main.py")

    logger.info("=" * 60)
    logger.info("🚀 Monitoring Server started")
    logger.info("=" * 60)


@app.on_event("shutdown")
async def shutdown_event():
    """Очистка при остановке сервера."""
    if db:
        db.close()
    logger.info("Server stopped")


# ═══════════════════════════════════════════════════
#  Эндпоинты
# ═══════════════════════════════════════════════════
@app.get("/api/health")
async def health():
    """Проверка работоспособности сервера."""
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }


@app.post("/api/metrics")
async def receive_metrics(metrics: Dict[str, Any]):
    """
    Принимает метрики от агента.

    Это ГЛАВНЫЙ эндпоинт — сюда агенты шлют данные.
    """
    try:
        # 1. Извлекаем hostname
        system_info = metrics.get("system", {})
        hostname = system_info.get("hostname")

        if not hostname:
            raise HTTPException(
                status_code=400,
                detail="Missing 'system.hostname' in metrics"
            )

        # 2. Обновляем хранилище в памяти (для дашборда)
        storage.update(hostname, metrics)

        # 3. Сохраняем в БД (для истории) — в фоне, чтобы не блокировать
        try:
            host_id = db.register_host(system_info)
            db.save_all_metrics(host_id, metrics)
        except Exception as e:
            # Логируем, но не падаем — дашборд должен работать
            logger.error(f"Failed to save to database: {e}")

        return {
            "status": "ok",
            "hostname": hostname,
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/hosts")
async def list_hosts():
    """Список всех хостов с их текущими метриками."""
    return {"hosts": storage.get_all_hosts()}


@app.get("/api/hosts/{hostname}")
async def get_host(hostname: str):
    """Метрики конкретного хоста."""
    data = storage.get_host(hostname)
    if not data:
        raise HTTPException(status_code=404, detail="Host not found")
    return {"hostname": hostname, **data}


@app.get("/api/stats")
async def get_stats():
    """Общая статистика по кластеру."""
    return storage.get_stats()


@app.delete("/api/hosts/{hostname}")
async def delete_host(hostname: str):
    """Удаляет хост из хранилища."""
    if storage.remove_host(hostname):
        return {"status": "ok", "hostname": hostname}
    raise HTTPException(status_code=404, detail="Host not found")