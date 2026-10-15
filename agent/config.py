"""
agent/config.py — Загрузка конфигурации агента из YAML.
"""

import yaml
import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)

def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """
    Загружает конфигурацию из YAML-файла.

    Если файл не найден — возвращает дефолтные настройки.
    """
    default_config = {
        "agent": {
            "interval": 5,
            "collectors": {
                "cpu": True,
                "memory": True,
                "disk": True,
                "network": True,
                "gpu": True,
                "devices": True,
                "system": True,
            },
            "retry": {
                "max_attempts": 3,
                "delay_seconds": 2,
            }
        },
        "server": {
            "url": "http://localhost:8000",
        },
        "thresholds": {
            "cpu_warning": 70,
            "cpu_critical": 90,
            "memory_warning": 80,
            "memory_critical": 95,
            "disk_warning": 80,
            "disk_critical": 95,
            "gpu_temp_warning": 75,
            "gpu_temp_critical": 85,
        }
    }

    path = Path(config_path)
    if not path.exists():
        logger.warning(f"Config file not found: {config_path}. Using defaults.")
        return default_config

    try:
        with open(path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        # Мерджим с дефолтами (чтобы не потерять поля, если в файле их нет)
        for section in default_config:
            if section not in config:
                config[section] = default_config[section]
            elif isinstance(default_config[section], dict):
                for key in default_config[section]:
                    if key not in config[section]:
                        config[section][key] = default_config[section][key]

        logger.info(f"Config loaded from {config_path}")
        return config

    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return default_config