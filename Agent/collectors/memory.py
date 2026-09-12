import psutil
from dataclasses import dataclass, asdict
from typing import Dict, Any

from .base import BaseCollector


@dataclass
class MemoryInfo:
    total_gb: float
    available_gb: float
    used_gb: float
    percent: float
    swap_total_gb: float
    swap_used_gb: float
    swap_percent: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MemoryCollector(BaseCollector):
    def get(self) -> Dict[str, Any]:
        self.logger.debug("Collecting memory metrics")

        vm = psutil.virtual_memory()
        sw = psutil.swap_memory()

        info = MemoryInfo(
            total_gb=round(vm.total / (1024 ** 3), 2),
            available_gb=round(vm.available / (1024 ** 3), 2),
            used_gb=round(vm.used / (1024 ** 3), 2),
            percent=vm.percent,
            swap_total_gb=round(sw.total / (1024 ** 3), 2),
            swap_used_gb=round(sw.used / (1024 ** 3), 2),
            swap_percent=sw.percent,
        )

        self.logger.info(f"RAM usage: {vm.percent}%, Swap: {sw.percent}%")
        return info.to_dict()