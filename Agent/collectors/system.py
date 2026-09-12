import platform
import socket
import time
import psutil
from dataclasses import dataclass, asdict
from typing import Dict, Any, List

from .base import BaseCollector


@dataclass
class SystemInfo:
    hostname: str
    os_name: str
    os_release: str
    os_version: str
    architecture: str
    processor: str
    python_version: str
    boot_time: float
    uptime_seconds: float
    users: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SystemCollector(BaseCollector):
    def get(self) -> Dict[str, Any]:
        self.logger.debug("Collecting system info")

        # Пользователи
        users = [u.name for u in psutil.users()]

        info = SystemInfo(
            hostname=socket.gethostname(),
            os_name=platform.system(),
            os_release=platform.release(),
            os_version=platform.version(),
            architecture=platform.machine(),
            processor=platform.processor(),
            boot_time=psutil.boot_time(),
            uptime_seconds=time.time() - psutil.boot_time(),
            users=users,
        )

        self.logger.info(f"System: {info.hostname} ({info.os_name} {info.os_release})")
        return info.to_dict()