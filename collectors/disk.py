import psutil
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional

from .base import BaseCollector


@dataclass
class DiskPartition:
    device: str
    mountpoint: str
    fstype: str
    total_gb: float
    used_gb: float
    free_gb: float
    percent: float
    # Новое поле:
    temperature_c: Optional[float] = None  # Температура диска, °C


@dataclass
class DiskIO:
    read_bytes: int
    write_bytes: int
    read_count: int
    write_count: int
    read_time_ms: int
    write_time_ms: int


@dataclass
class DiskInfo:
    partitions: List[Dict[str, Any]]
    io: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


class DiskCollector(BaseCollector):
    def __init__(self):
        super().__init__()
        self._lhm = None
        self._init_lhm()

    def _init_lhm(self):
        """Инициализирует LHM для температуры дисков."""
        import platform
        if platform.system() == "Windows":
            try:
                from .lhm_monitor import LHMMonitor
                self._lhm = LHMMonitor()
                self.logger.info("LibreHardwareMonitorLib initialized for disks")
            except Exception as e:
                self.logger.debug(f"LHM not available for disks: {e}")

    def get(self) -> Dict[str, Any]:
        self.logger.debug("Collecting disk metrics")

        # Разделы
        partitions = []
        disk_temps = self._get_disk_temperatures()

        for part in psutil.disk_partitions(all=False):
            try:
                usage = psutil.disk_usage(part.mountpoint)

                # Пытаемся найти температуру для этого диска
                temp = None
                device_name = part.device.replace(":", "").replace("\\", "").strip()
                if disk_temps:
                    # Ищем по имени устройства
                    for disk_name, disk_temp in disk_temps.items():
                        if device_name.lower() in disk_name.lower() or disk_name.lower() in device_name.lower():
                            temp = disk_temp
                            break

                partition = DiskPartition(
                    device=part.device,
                    mountpoint=part.mountpoint,
                    fstype=part.fstype,
                    total_gb=round(usage.total / (1024 ** 3), 2),
                    used_gb=round(usage.used / (1024 ** 3), 2),
                    free_gb=round(usage.free / (1024 ** 3), 2),
                    percent=usage.percent,
                    temperature_c=temp,
                )
                partitions.append(asdict(partition))

            except PermissionError:
                self.logger.warning(f"Permission denied for {part.mountpoint}")
                continue

        # I/O
        dio = psutil.disk_io_counters()
        io_data = asdict(DiskIO(
            read_bytes=dio.read_bytes,
            write_bytes=dio.write_bytes,
            read_count=dio.read_count,
            write_count=dio.write_count,
            read_time_ms=dio.read_time,
            write_time_ms=dio.write_time,
        ))

        info = DiskInfo(partitions=partitions, io=io_data)
        self.logger.info(f"Collected {len(partitions)} disk partitions")
        return info.to_dict()

    def _get_disk_temperatures(self) -> Optional[Dict[str, float]]:
        """Получает температуры дисков через LHM."""
        if not self._lhm:
            return None

        try:
            return self._lhm.get_disk_temperatures()
        except Exception as e:
            self.logger.warning(f"Failed to get disk temperatures: {e}")
            return None

    def __del__(self):
        """Освобождает ресурсы LHM."""
        if self._lhm:
            self._lhm.close()