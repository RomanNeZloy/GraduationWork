"""
agent_main.py — Точка входа агента мониторинга.

Запуск:
    python agent_main.py                          # дефолтный конфиг
    python agent_main.py --config my_config.yaml  # свой конфиг
    python agent_main.py --server http://10.0.0.1:8000  # переопределить сервер
    python agent_main.py --interval 10            # переопределить интервал
"""
import sys
import os

# Добавляем корневую папку проекта в пути поиска Python
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import argparse
import logging
import time
import signal
from typing import Dict, Any

from agent.config import load_config
from agent.client import MonitoringClient
from collectors import (
    CPUCollector, MemoryCollector, DiskCollector,
    NetworkCollector, SystemCollector, DevicesCollector, GPUMonitor
)

# ═══════════════════════════════════════════════════
#  Глобальный флаг для graceful shutdown
# ═══════════════════════════════════════════════════
_running = True


def signal_handler(signum, frame):
    """Обработчик сигналов Ctrl+C и SIGTERM."""
    global _running
    print("\n⏹️  Stopping agent...")
    _running = False


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


# ═══════════════════════════════════════════════════
#  Сбор метрик
# ═══════════════════════════════════════════════════
class MetricsAggregator:
    """Агрегирует метрики со всех коллекторов."""

    def __init__(self, enabled_collectors: Dict[str, bool]):
        self.enabled = enabled_collectors
        self._collectors = {}
        self._gpu_monitor = None
        self._init_collectors()

    def _init_collectors(self):
        """Инициализирует только включённые коллекторы."""
        if self.enabled.get("cpu"):
            self._collectors["cpu"] = CPUCollector()
        if self.enabled.get("memory"):
            self._collectors["memory"] = MemoryCollector()
        if self.enabled.get("disk"):
            self._collectors["disk"] = DiskCollector()
        if self.enabled.get("network"):
            self._collectors["network"] = NetworkCollector(max_connections=50)
        if self.enabled.get("system"):
            self._collectors["system"] = SystemCollector()
        if self.enabled.get("devices"):
            self._collectors["devices"] = DevicesCollector()
        if self.enabled.get("gpu"):
            self._gpu_monitor = GPUMonitor()

    def collect_all(self) -> Dict[str, Any]:
        """Собирает все метрики."""
        metrics = {}

        for name, collector in self._collectors.items():
            try:
                metrics[name] = collector.safe_get()
            except Exception as e:
                logging.getLogger(__name__).error(f"Collector {name} failed: {e}")
                metrics[name] = {}

        # GPU отдельно
        if self._gpu_monitor:
            try:
                metrics["gpu"] = [g.to_dict() for g in self._gpu_monitor.get_gpus()]
            except Exception as e:
                logging.getLogger(__name__).error(f"GPU monitor failed: {e}")
                metrics["gpu"] = []

        return metrics


# ═══════════════════════════════════════════════════
#  Главный цикл
# ═══════════════════════════════════════════════════
def main():
    # Парсинг аргументов
    parser = argparse.ArgumentParser(description="Monitoring Agent")
    parser.add_argument("--config", default="config.yaml", help="Путь к конфигу")
    parser.add_argument("--server", help="URL сервера (переопределить)")
    parser.add_argument("--interval", type=int, help="Интервал сбора (сек)")
    parser.add_argument("--debug", action="store_true", help="Отладочные логи")
    parser.add_argument("--quiet", action="store_true", help="Только ошибки")
    args = parser.parse_args()

    # Настройка логирования
    if args.quiet:
        log_level = logging.ERROR
    elif args.debug:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S"
    )
    logger = logging.getLogger("Agent")

    # Загрузка конфига
    config = load_config(args.config)
    agent_cfg = config["agent"]

    # Переопределения из аргументов
    server_url = args.server or config.get("server", {}).get("url", "http://localhost:8000")
    interval = args.interval or agent_cfg["interval"]

    # Инициализация
    logger.info("=" * 60)
    logger.info("🚀 Monitoring Agent started")
    logger.info(f"   Server: {server_url}")
    logger.info(f"   Interval: {interval}s")
    logger.info("=" * 60)

    client = MonitoringClient(
        server_url=server_url,
        max_retries=agent_cfg["retry"]["max_attempts"],
        retry_delay=agent_cfg["retry"]["delay_seconds"]
    )

    aggregator = MetricsAggregator(agent_cfg["collectors"])

    # Проверка связи с сервером
    if client.ping():
        logger.info("✅ Server is reachable")
    else:
        logger.warning("⚠️  Server is not reachable (will retry)")

    # Главный цикл
    cycle = 0
    while _running:
        cycle += 1
        try:
            logger.debug(f"Cycle {cycle}: collecting metrics...")

            # 1. Сбор метрик
            metrics = aggregator.collect_all()

            # 2. Отправка на сервер
            success = client.send_metrics(metrics)

            if success:
                hostname = metrics.get("system", {}).get("hostname", "unknown")
                cpu = metrics.get("cpu", {}).get("usage_percent", 0)
                ram = metrics.get("memory", {}).get("percent", 0)
                logger.info(
                    f"✓ [{hostname}] CPU: {cpu:.1f}%, RAM: {ram:.1f}%"
                )
            else:
                logger.warning("✗ Failed to send metrics")

            # 3. Ждём следующий цикл
            time.sleep(interval)

        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"Main loop error: {e}", exc_info=True)
            time.sleep(interval)

    # Завершение
    logger.info("Agent stopped")
    client.close()


if __name__ == "__main__":
    main()