"""
base.py — Базовый класс для всех коллекторов метрик.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseCollector(ABC):
    """Абстрактный базовый класс для всех коллекторов."""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def get(self) -> Dict[str, Any]:
        """
        Собирает метрики и возвращает их в виде словаря.
        Должен быть переопределён в каждом коллекторе.
        """
        pass

    def safe_get(self) -> Dict[str, Any]:
        """
        Безопасная обёртка над get() с обработкой ошибок.
        Возвращает пустой словарь в случае исключения.
        """
        try:
            return self.get()
        except Exception as e:
            self.logger.error(f"Collection failed: {e}", exc_info=True)
            return {}