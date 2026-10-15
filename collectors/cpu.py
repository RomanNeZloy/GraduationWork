import platform
import psutil
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any

from .base import BaseCollector


@dataclass
class CPUInfo:
    physical_cores: int
    logical_cores: int
    usage_percent: float
    per_core_usage: List[float]
    frequency_current_mhz: Optional[float]
    frequency_min_mhz: Optional[float]
    frequency_max_mhz: Optional[float]
    load_avg: Optional[List[float]]
    temperature_c: Optional[Dict[str, float]]
    # Новые поля от LHM:
    voltage_v: Optional[float]  # Напряжение ядра
    power_w: Optional[float]  # Энергопотребление, Вт

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


class CPUCollector(BaseCollector):
    def __init__(self):
        super().__init__()
        self._lhm = None
        self._init_lhm()

    def _init_lhm(self):
        """Пытается инициализировать LHM на Windows."""
        if platform.system() == "Windows":
            try:
                from .lhm_monitor import LHMMonitor
                self._lhm = LHMMonitor('dlls')
                self.logger.info("LibreHardwareMonitorLib initialized")
            except Exception as e:
                self.logger.warning(f"LHM not available: {e}")

    def get(self) -> Dict[str, Any]:
        self.logger.debug("Collecting CPU metrics")

        # Базовая информация (psutil — всегда работает)
        physical = psutil.cpu_count(logical=False) or 0
        logical = psutil.cpu_count(logical=True) or 0
        usage = psutil.cpu_percent(interval=0.1)
        per_core = psutil.cpu_percent(interval=0.1, percpu=True)

        freq = psutil.cpu_freq()
        freq_current = freq.current if freq else None
        freq_min = freq.min if freq else None
        freq_max = freq.max if freq else None

        load_avg = None
        if platform.system() != "Windows":
            try:
                load_avg = list(psutil.getloadavg())
            except Exception:
                pass

        # Температура и дополнительные метрики
        temperature = None
        voltage = None
        power = None

        if self._lhm:
            # LHM доступен — берём всё из него
            temperature = self._lhm.get_cpu_temperature()

            voltages = self._lhm.get_cpu_voltage()
            if voltages:
                voltage = list(voltages.values())[0]

            powers = self._lhm.get_cpu_power()
            if powers:
                power = list(powers.values())[0]

        elif platform.system() == "Linux":
            # Linux — psutil
            try:
                temps = psutil.sensors_temperatures()
                if temps:
                    temperature = {}
                    for chip, entries in temps.items():
                        for entry in entries:
                            key = f"{chip}_{entry.label or 'sensor'}"
                            temperature[key] = entry.current
            except Exception:
                pass

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
            voltage_v=voltage,
            power_w=power,
        )

        self.logger.info(f"CPU: {usage}%, Temp: {temperature}, Power: {power}W")
        return info.to_dict()

    def __del__(self):
        """Освобождает ресурсы LHM при уничтожении объекта."""
        if self._lhm:
            self._lhm.close()