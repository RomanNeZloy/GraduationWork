"""
database/models.py — Логика работы с базой данных.
"""
import sqlite3
import logging
from typing import Dict, Any

from .schema import create_database

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Менеджер базы данных для мониторинга."""

    def __init__(self, db_path: str = "monitoring.db"):
        self.conn = create_database(db_path)
        self.cursor = self.conn.cursor()

    def close(self):
        """Закрывает подключение к БД."""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")

    def register_host(self, system_info: Dict[str, Any]) -> int:
        """Регистрирует хост в БД или обновляет время последнего подключения."""
        hostname = system_info.get("hostname", "unknown")

        # Проверяем, есть ли хост уже в БД
        self.cursor.execute("SELECT id FROM hosts WHERE hostname = ?", (hostname,))
        result = self.cursor.fetchone()

        if result:
            # Хост уже есть — обновляем last_seen
            host_id = result["id"]
            self.cursor.execute(
                "UPDATE hosts SET last_seen = CURRENT_TIMESTAMP WHERE id = ?",
                (host_id,)
            )
        else:
            # Новый хост — регистрируем
            self.cursor.execute(
                """
                INSERT INTO hosts (hostname, os_name, os_version, architecture, processor)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    hostname,
                    system_info.get("os_name"),
                    system_info.get("os_release"),  # в system.py мы использовали os_release
                    system_info.get("architecture"),
                    system_info.get("processor")
                )
            )
            host_id = self.cursor.lastrowid
            logger.info(f"Registered new host in DB: {hostname} (ID: {host_id})")

        self.conn.commit()
        return host_id

    def save_all_metrics(self, host_id: int, metrics: Dict[str, Any]):
        """Сохраняет все метрики из словаря в соответствующие таблицы."""
        try:
            # Сохраняем CPU
            cpu = metrics.get("cpu", {})
            if cpu:
                self.cursor.execute(
                    """
                    INSERT INTO metrics_cpu (host_id, usage_percent, physical_cores, logical_cores)
                    VALUES (?, ?, ?, ?)
                    """,
                    (host_id, cpu.get("usage_percent"), cpu.get("physical_cores"), cpu.get("logical_cores"))
                )

            # Сохраняем Memory
            mem = metrics.get("memory", {})
            if mem:
                self.cursor.execute(
                    """
                    INSERT INTO metrics_memory (host_id, total_gb, used_gb, percent)
                    VALUES (?, ?, ?, ?)
                    """,
                    (host_id, mem.get("total_gb"), mem.get("used_gb"), mem.get("percent"))
                )

            self.conn.commit()

        except Exception as e:
            logger.error(f"Failed to save metrics to DB: {e}")
            self.conn.rollback()