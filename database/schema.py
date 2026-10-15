"""
database/schema.py — Создание структуры базы данных SQLite.
"""
import sqlite3
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def create_database(db_path: str = "monitoring.db") -> sqlite3.Connection:
    """Создаёт базу данных и все необходимые таблицы."""

    # Создаём файл БД, если его нет
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    # Подключаемся к БД
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # Чтобы результаты запросов были как словари

    cursor = conn.cursor()

    # 1. Таблица хостов (компьютеров)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS hosts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hostname TEXT NOT NULL UNIQUE,
            os_name TEXT,
            os_version TEXT,
            architecture TEXT,
            processor TEXT,
            first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 2. Таблица метрик CPU
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS metrics_cpu (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            host_id INTEGER NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            usage_percent REAL,
            physical_cores INTEGER,
            logical_cores INTEGER,
            FOREIGN KEY (host_id) REFERENCES hosts(id) ON DELETE CASCADE
        )
    """)

    # 3. Таблица метрик RAM
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS metrics_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            host_id INTEGER NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            total_gb REAL,
            used_gb REAL,
            percent REAL,
            FOREIGN KEY (host_id) REFERENCES hosts(id) ON DELETE CASCADE
        )
    """)

    # Создаём индексы для ускорения поиска по времени и хосту
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cpu_host ON metrics_cpu(host_id, timestamp)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_mem_host ON metrics_memory(host_id, timestamp)")

    conn.commit()
    logger.info(f"Database initialized at: {db_path}")

    return conn