"""
server/storage.py — Хранилище последних метрик в памяти.

Зачем:
- БД хранит ВСЮ историю (для графиков)
- А для дашборда нужны только ПОСЛЕДНИЕ метрики каждого хоста
- Чтение из памяти в 1000 раз быстрее, чем из БД
"""

import logging
import threading
import time
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class MetricsStorage:
    """
    Хранилище последних метрик в памяти.

    Потокобезопасно (используется из нескольких HTTP-обработчиков).
    """

    def __init__(self, offline_threshold: int = 30):
        """
        Args:
            offline_threshold: Через сколько секунд хост считается оффлайн
        """
        self.offline_threshold = offline_threshold

        # {hostname: {metrics, last_seen, first_seen}}
        self._hosts: Dict[str, Dict[str, Any]] = {}

        # Блокировка для потокобезопасности
        self._lock = threading.RLock()

        logger.info(f"MetricsStorage initialized (offline threshold: {offline_threshold}s)")

    def update(self, hostname: str, metrics: Dict[str, Any]):
        """
        Обновляет метрики для хоста.

        Args:
            hostname: Имя хоста
            metrics: Словарь метрик
        """
        with self._lock:
            now = datetime.now()

            if hostname not in self._hosts:
                self._hosts[hostname] = {
                    "first_seen": now,
                    "last_seen": now,
                    "metrics": {},
                    "update_count": 0,
                }
                logger.info(f"New host registered: {hostname}")

            host_data = self._hosts[hostname]
            host_data["last_seen"] = now
            host_data["metrics"] = metrics
            host_data["update_count"] += 1

    def get_host(self, hostname: str) -> Optional[Dict[str, Any]]:
        """Получает данные конкретного хоста."""
        with self._lock:
            if hostname not in self._hosts:
                return None
            return self._hosts[hostname].copy()

    def get_all_hosts(self) -> List[Dict[str, Any]]:
        """Получает список всех хостов с их метриками."""
        with self._lock:
            result = []
            now = datetime.now()

            for hostname, data in self._hosts.items():
                last_seen = data["last_seen"]
                seconds_ago = (now - last_seen).total_seconds()

                # Определяем статус
                if seconds_ago > self.offline_threshold:
                    status = "offline"
                elif seconds_ago > self.offline_threshold / 2:
                    status = "stale"  # "подвисает"
                else:
                    status = "online"

                result.append({
                    "hostname": hostname,
                    "status": status,
                    "last_seen": last_seen,
                    "seconds_ago": round(seconds_ago, 1),
                    "first_seen": data["first_seen"],
                    "update_count": data["update_count"],
                    "metrics": data["metrics"],
                })

            # Сортируем: сначала онлайн, потом по имени
            result.sort(key=lambda x: (
                0 if x["status"] == "online" else (1 if x["status"] == "stale" else 2),
                x["hostname"]
            ))

            return result

    def get_stats(self) -> Dict[str, Any]:
        """Получает общую статистику."""
        with self._lock:
            hosts = self.get_all_hosts()

            online = sum(1 for h in hosts if h["status"] == "online")
            stale = sum(1 for h in hosts if h["status"] == "stale")
            offline = sum(1 for h in hosts if h["status"] == "offline")

            # Средние метрики по онлайн-хостам
            online_hosts = [h for h in hosts if h["status"] == "online"]

            avg_cpu = 0.0
            avg_ram = 0.0
            if online_hosts:
                cpus = [
                    h["metrics"].get("cpu", {}).get("usage_percent", 0)
                    for h in online_hosts
                ]
                rams = [
                    h["metrics"].get("memory", {}).get("percent", 0)
                    for h in online_hosts
                ]
                avg_cpu = sum(cpus) / len(cpus) if cpus else 0
                avg_ram = sum(rams) / len(rams) if rams else 0

            return {
                "total_hosts": len(hosts),
                "online": online,
                "stale": stale,
                "offline": offline,
                "avg_cpu": round(avg_cpu, 1),
                "avg_ram": round(avg_ram, 1),
            }

    def remove_host(self, hostname: str) -> bool:
        """Удаляет хост из хранилища."""
        with self._lock:
            if hostname in self._hosts:
                del self._hosts[hostname]
                logger.info(f"🗑️  Host removed: {hostname}")
                return True
            return False