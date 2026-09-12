"""
collectors — Модули для сбора метрик системы.
"""

from .cpu import CPUCollector
from .memory import MemoryCollector
from .disk import DiskCollector
from .network import NetworkCollector
from .system import SystemCollector
from .devices import DevicesCollector
from .gpu import GPUMonitor

__all__ = [
    'CPUCollector',
    'MemoryCollector',
    'DiskCollector',
    'NetworkCollector',
    'SystemCollector',
    'DevicesCollector',
    'GPUMonitor',
]