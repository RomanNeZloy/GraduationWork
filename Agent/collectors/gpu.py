
import logging
import platform
import subprocess
import shutil
from dataclasses import dataclass
from typing import List, Optional

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
#  Структура данных (единая для всех вендоров)
# ─────────────────────────────────────────────
@dataclass
class GPUInfo:
    id: int
    name: str
    vendor: str                              # "NVIDIA", "AMD", "Intel", "Unknown"
    load_percent: Optional[float] = None     # загрузка GPU, %
    memory_used_mb: Optional[int] = None     # использовано VRAM, МБ
    memory_total_mb: Optional[int] = None    # всего VRAM, МБ
    memory_percent: Optional[float] = None   # загрузка VRAM, %
    temperature_c: Optional[int] = None      # температура, °C
    driver_version: Optional[str] = None     # версия драйвера

    def to_dict(self) -> dict:
        """Сериализация для отправки на сервер."""
        return {k: v for k, v in self.__dict__.items() if v is not None}


# ─────────────────────────────────────────────
#  Главный класс
# ─────────────────────────────────────────────
class GPUMonitor:
    def __init__(self):
        self._backend = self._detect_backend()
        logger.info(f"GPU backend selected: {self._backend}")

    # ── Определение бэкенда ──────────────────
    def _detect_backend(self) -> str:
        """
        Последовательно пробуем библиотеки от «лучшей» к «худшей».
        Первый рабочий вариант побеждает.
        """

        # 1) NVIDIA через GPUtil
        try:
            import GPUtil
            if GPUtil.getGPUs():
                return "nvidia_gputil"
        except Exception as e:
            logger.debug(f"GPUtil unavailable: {e}")

        # 2) NVIDIA через pynvml (официальный NVML)
        try:
            import pynvml
            pynvml.nvmlInit()
            if pynvml.nvmlDeviceGetCount() > 0:
                return "nvidia_pynvml"
        except Exception as e:
            logger.debug(f"pynvml unavailable: {e}")

        # 3) AMD через amdsmi (официальный ROCm SMI)
        try:
            import amdsmi
            amdsmi.amdsmi_init()
            if amdsmi.amdsmi_get_processor_handles():
                return "amd_amdsmi"
        except Exception as e:
            logger.debug(f"amdsmi unavailable: {e}")

        # 4) AMD через CLI-утилиту rocm-smi
        if self._cmd_exists("rocm-smi"):
            return "amd_rocm_smi"

        # 5) NVIDIA через CLI-утилиту nvidia-smi (последний шанс для NVIDIA)
        if self._cmd_exists("nvidia-smi"):
            return "nvidia_smi"

        # 6) Fallback: WMI (Windows) или lspci (Linux)
        if platform.system() == "Windows":
            return "wmi_fallback"
        return "linux_fallback"

    @staticmethod
    def _cmd_exists(cmd: str) -> bool:
        return shutil.which(cmd) is not None

    # ── Публичный метод ──────────────────────
    def get_gpus(self) -> List[GPUInfo]:
        """Возвращает список всех обнаруженных GPU."""
        dispatch = {
            "nvidia_gputil":   self._via_gputil,
            "nvidia_pynvml":   self._via_pynvml,
            "amd_amdsmi":      self._via_amdsmi,
            "amd_rocm_smi":    self._via_rocm_smi,
            "nvidia_smi":      self._via_nvidia_smi,
            "wmi_fallback":    self._via_wmi,
            "linux_fallback":  self._via_lspci,
        }
        handler = dispatch.get(self._backend, self._via_wmi)
        try:
            return handler()
        except Exception as e:
            logger.error(f"GPU collection failed ({self._backend}): {e}")
            return []

    # ── NVIDIA: GPUtil ───────────────────────
    def _via_gputil(self) -> List[GPUInfo]:
        import GPUtil
        result = []
        for g in GPUtil.getGPUs():
            result.append(GPUInfo(
                id=g.id,
                name=g.name,
                vendor="NVIDIA",
                load_percent=round(g.load * 100, 1),
                memory_used_mb=g.memoryUsed,
                memory_total_mb=g.memoryTotal,
                memory_percent=round(g.memoryUtil * 100, 1),
                temperature_c=g.temperature,
            ))
        return result

    # ── NVIDIA: pynvml ───────────────────────
    def _via_pynvml(self) -> List[GPUInfo]:
        import pynvml
        result = []
        for i in range(pynvml.nvmlDeviceGetCount()):
            h = pynvml.nvmlDeviceGetHandleByIndex(i)
            name = pynvml.nvmlDeviceGetName(h)
            if isinstance(name, bytes):
                name = name.decode()
            util = pynvml.nvmlDeviceGetUtilizationRates(h)
            mem = pynvml.nvmlDeviceGetMemoryInfo(h)
            temp = pynvml.nvmlDeviceGetTemperature(h, pynvml.NVML_TEMPERATURE_GPU)
            drv = pynvml.nvmlSystemGetDriverVersion()
            if isinstance(drv, bytes):
                drv = drv.decode()
            result.append(GPUInfo(
                id=i,
                name=name,
                vendor="NVIDIA",
                load_percent=util.gpu,
                memory_used_mb=mem.used // (1024 ** 2),
                memory_total_mb=mem.total // (1024 ** 2),
                memory_percent=round(mem.used / mem.total * 100, 1),
                temperature_c=temp,
                driver_version=drv,
            ))
        return result

    # ── AMD: amdsmi ──────────────────────────
    def _via_amdsmi(self) -> List[GPUInfo]:
        import amdsmi
        result = []
        handles = amdsmi.amdsmi_get_processor_handles()
        for i, h in enumerate(handles):
            name = amdsmi.amdsmi_get_gpu_asic_info(h)["market_name"]
            util = amdsmi.amdsmi_get_gpu_activity(h)["gfx_activity"]
            vram = amdsmi.amdsmi_get_gpu_vram_usage(h)
            temp = amdsmi.amdsmi_get_temp_metric(
                h, amdsmi.AmdSmiTemperatureType.JUNCTION,
                amdsmi.AmdSmiTemperatureMetric.CURRENT
            ) // 1000  # миллиградусы → градусы
            result.append(GPUInfo(
                id=i,
                name=name,
                vendor="AMD",
                load_percent=util,
                memory_used_mb=vram["vram_used"] // (1024 ** 2),
                memory_total_mb=vram["vram_total"] // (1024 ** 2),
                memory_percent=round(vram["vram_used"] / vram["vram_total"] * 100, 1),
                temperature_c=temp,
            ))
        return result

    # ── AMD: rocm-smi (CLI) ──────────────────
    def _via_rocm_smi(self) -> List[GPUInfo]:
        """Парсим JSON-вывод rocm-smi."""
        import json
        raw = subprocess.check_output(
            ["rocm-smi", "--showuse", "--showmemuse", "--showtemp", "--json"],
            text=True, stderr=subprocess.DEVNULL
        )
        data = json.loads(raw)
        result = []
        for key, val in data.items():
            if not key.startswith("card"):
                continue
            gpu_id = int(key.replace("card", ""))
            result.append(GPUInfo(
                id=gpu_id,
                name=f"AMD GPU {gpu_id}",
                vendor="AMD",
                load_percent=float(val.get("GPU use (%)", 0)),
                memory_percent=float(val.get("GPU memory use (%)", 0)),
                temperature_c=int(float(val.get("Temperature (Sensor edge) (C)", 0))),
            ))
        return result

    # ── NVIDIA: nvidia-smi (CLI) ─────────────
    def _via_nvidia_smi(self) -> List[GPUInfo]:
        """Парсим CSV-вывод nvidia-smi."""
        raw = subprocess.check_output([
            "nvidia-smi",
            "--query-gpu=index,name,utilization.gpu,memory.used,memory.total,"
            "temperature.gpu,driver_version",
            "--format=csv,noheader,nounits"
        ], text=True)
        result = []
        for line in raw.strip().splitlines():
            parts = [p.strip() for p in line.split(",")]
            mem_used = int(parts[3])
            mem_total = int(parts[4])
            result.append(GPUInfo(
                id=int(parts[0]),
                name=parts[1],
                vendor="NVIDIA",
                load_percent=float(parts[2]),
                memory_used_mb=mem_used,
                memory_total_mb=mem_total,
                memory_percent=round(mem_used / mem_total * 100, 1),
                temperature_c=int(parts[5]),
                driver_version=parts[6],
            ))
        return result

    # ── Fallback: WMI (Windows) ──────────────
    def _via_wmi(self) -> List[GPUInfo]:
        """Базовая информация через WMI. Нет нагрузки в реальном времени."""
        import wmi
        c = wmi.WMI()
        result = []
        for i, vc in enumerate(c.Win32_VideoController()):
            vendor = "Unknown"
            name_lower = (vc.Name or "").lower()
            if "nvidia" in name_lower:
                vendor = "NVIDIA"
            elif "amd" in name_lower or "radeon" in name_lower:
                vendor = "AMD"
            elif "intel" in name_lower:
                vendor = "Intel"
            vram_mb = int(vc.AdapterRAM or 0) // (1024 ** 2) if vc.AdapterRAM else None
            result.append(GPUInfo(
                id=i,
                name=vc.Name or "Unknown GPU",
                vendor=vendor,
                memory_total_mb=vram_mb,
                driver_version=vc.DriverVersion,
            ))
        return result

    # ── Fallback: lspci (Linux) ──────────────
    def _via_lspci(self) -> List[GPUInfo]:
        """Базовая информация через lspci. Только название."""
        raw = subprocess.check_output(
            ["lspci"], text=True, stderr=subprocess.DEVNULL
        )
        result = []
        gpu_id = 0
        for line in raw.splitlines():
            if "VGA" in line or "3D" in line or "Display" in line:
                name = line.split(": ", 1)[-1] if ": " in line else line
                vendor = "Unknown"
                nl = name.lower()
                if "nvidia" in nl:
                    vendor = "NVIDIA"
                elif "amd" in nl or "radeon" in nl:
                    vendor = "AMD"
                elif "intel" in nl:
                    vendor = "Intel"
                result.append(GPUInfo(id=gpu_id, name=name, vendor=vendor))
                gpu_id += 1
        return result