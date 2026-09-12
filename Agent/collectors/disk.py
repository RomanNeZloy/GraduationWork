import psutil
from dataclasses import dataclass, asdict
from typing import List, Dict, Any

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
        return asdict(self)


class DiskCollector(BaseCollector):
    def get(self) -> Dict[str, Any]:
        self.logger.debug("Collecting disk metrics")

        # Разделы
        partitions = []
        for part in psutil.disk_partitions(all=False):
            try:
                usage = psutil.disk_usage(part.mountpoint)
                partitions.append(DiskPartition(
                    device=part.device,
                    mountpoint=part.mountpoint,
                    fstype=part.fstype,
                    total_gb=round(usage.total / (1024 ** 3), 2),
                    used_gb=round(usage.used / (1024 ** 3), 2),
                    free_gb=round(usage.free / (1024 ** 3), 2),
                    percent=usage.percent,
                ).to_dict() if hasattr(DiskPartition, 'to_dict') else asdict(DiskPartition(
                    device=part.device,
                    mountpoint=part.mountpoint,
                    fstype=part.fstype,
                    total_gb=round(usage.total / (1024 ** 3), 2),
                    used_gb=round(usage.used / (1024 ** 3), 2),
                    free_gb=round(usage.free / (1024 ** 3), 2),
                    percent=usage.percent,
                )))
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