import platform
import psutil
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any

from .base import BaseCollector


@dataclass
class CPUInfo:
    physical_cores: int
    logical_cores: int
    usage_percent: float                    # общая загрузка, %
    per_core_usage: List[float]             # загрузка по ядрам, %
    frequency_current_mhz: Optional[float]  # текущая частота, МГц
    frequency_min_mhz: Optional[float]      # минимальная частота, МГц
    frequency_max_mhz: Optional[float]      # максимальная частота, МГц
    load_avg: Optional[List[float]]         # средняя нагрузка (только Linux)
    temperature_c: Optional[Dict[str, float]]  # температура по сенсорам, °C

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CPUCollector(BaseCollector):
    def get(self) -> Dict[str, Any]:
        self.logger.debug("Collecting CPU metrics")

        # Базовая информация
        physical = psutil.cpu_count(logical=False) or 0
        logical = psutil.cpu_count(logical=True) or 0
        usage = psutil.cpu_percent(interval=0.1)
        per_core = psutil.cpu_percent(interval=0.1, percpu=True)

        # Частоты
        freq = psutil.cpu_freq()
        freq_current = freq.current if freq else None
        freq_min = freq.min if freq else None
        freq_max = freq.max if freq else None

        # Средняя нагрузка (только Linux/macOS)
        load_avg = None
        if platform.system() != "Windows":
            try:
                load_avg = list(psutil.getloadavg())
            except Exception as e:
                self.logger.warning(f"Cannot get load average: {e}")

        # Температура (Linux)
        temperature = None
        if platform.system() == "Linux":
            try:
                temps = psutil.sensors_temperatures()
                if temps:
                    temperature = {}
                    for chip, entries in temps.items():
                        for entry in entries:
                            key = f"{chip}_{entry.label or 'sensor'}"
                            temperature[key] = entry.current
            except Exception as e:
                self.logger.warning(f"Cannot get CPU temperature: {e}")

        info = CPUInfo(
            physical_cores=physical,
            logical_cores=logical,
            usage_percent=usage,
            per_core_usage=per_core,
            frequency_current_mhz=freq_current,
            frequency_min_mhz=freq_min,
            frequency_max_mhz=freq_max,
            load_avg=load_avg,
            temperature_c=temperature,
        )

        self.logger.info(f"CPU usage: {usage}%")
        return info.to_dict()