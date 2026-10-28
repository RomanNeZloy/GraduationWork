"""
agent/client.py — HTTP-клиент для отправки метрик на сервер.
"""

import logging
import time
from typing import Dict, Any, Optional

import requests
from requests.exceptions import RequestException, Timeout, ConnectionError

logger = logging.getLogger(__name__)


class MonitoringClient:
    """HTTP-клиент для отправки метрик на сервер мониторинга."""

    def __init__(
            self,
            server_url: str = "http://localhost:8000",
            timeout: int = 10,
            max_retries: int = 3,
            retry_delay: float = 2.0
    ):
        """
        Args:
            server_url: URL сервера
            timeout: Таймаут запроса в секундах
            max_retries: Максимальное количество попыток
            retry_delay: Задержка между попытками в секундах
        """
        self.server_url = server_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Создаём сессию для переиспользования соединения
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "MonitoringAgent/1.0"
        })

        logger.info(f"Client initialized: server={self.server_url}")

    def send_metrics(self, metrics: Dict[str, Any]) -> bool:
        """
        Отправляет метрики на сервер с повторными попытками.

        Args:
            metrics: Словарь метрик от collect_all_metrics()

        Returns:
            bool: True если успешно, False если все попытки провалились
        """
        url = f"{self.server_url}/api/metrics"

        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.session.post(
                    url,
                    json=metrics,
                    timeout=self.timeout
                )

                # Успех
                if response.status_code == 200:
                    logger.debug(f"Metrics sent successfully (attempt {attempt})")
                    return True

                # Ошибка сервера — пробуем ещё
                if response.status_code >= 500:
                    logger.warning(
                        f"Server error {response.status_code} "
                        f"(attempt {attempt}/{self.max_retries})"
                    )
                else:
                    # Ошибка клиента (4xx) — нет смысла повторять
                    logger.error(
                        f"Client error {response.status_code}: "
                        f"{response.text}"
                    )
                    return False

            except Timeout:
                logger.warning(
                    f"Timeout connecting to server "
                    f"(attempt {attempt}/{self.max_retries})"
                )

            except ConnectionError:
                logger.warning(
                    f"Cannot connect to server "
                    f"(attempt {attempt}/{self.max_retries})"
                )

            except RequestException as e:
                logger.error(f"Request failed: {e}")
                return False

            # Ждём перед следующей попыткой (с экспоненциальной задержкой)
            if attempt < self.max_retries:
                delay = self.retry_delay * (2 ** (attempt - 1))
                logger.debug(f"Retrying in {delay:.1f}s...")
                time.sleep(delay)

        logger.error(f"All {self.max_retries} attempts failed")
        return False

    def ping(self) -> bool:
        """
        Проверяет доступность сервера.
        Returns:
            bool: True если сервер отвечает
        """
        try:
            response = self.session.get(
                f"{self.server_url}/api/health",
                timeout=3
            )
            return response.status_code == 200
        except Exception:
            return False

    def close(self):
        """Закрывает сессию."""
        self.session.close()