"""
lhm_monitor.py — Прямой доступ к LibreHardwareMonitorLib через pythonnet.

Требования:
- pip install pythonnet
- .NET 6+ Runtime установлен
- Все DLL из LibreHardwareMonitor лежат в папке dlls/
"""

import os
import sys
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class LHMMonitor:
    """Монитор на базе LibreHardwareMonitorLib."""

    def __init__(self, dlls_dir: str = None):
        """
        Инициализация LHM с умным поиском папки dlls.
        """
        # 1. Если путь передан явно — используем его
        if dlls_dir is not None:
            potential_dir = os.path.abspath(dlls_dir)
        else:
            # 2. Умный поиск: поднимаемся вверх по папкам, пока не найдём dlls
            current_dir = os.path.dirname(os.path.abspath(__file__))
            potential_dir = None

            # Поднимаемся максимум на 5 уровней вверх (на случай глубокой вложенности типа Agent/collectors)
            for _ in range(5):
                test_dir = os.path.join(current_dir, "dlls")
                test_dll = os.path.join(test_dir, "LibreHardwareMonitorLib.dll")

                if os.path.exists(test_dir) and os.path.exists(test_dll):
                    potential_dir = test_dir
                    break

                # Поднимаемся на уровень выше
                current_dir = os.path.dirname(current_dir)

            # 3. Fallback: если не нашли относительно файла, ищем в текущей рабочей директории (cwd)
            if potential_dir is None:
                cwd_dlls = os.path.join(os.getcwd(), "dlls")
                if os.path.exists(cwd_dlls) and os.path.exists(os.path.join(cwd_dlls, "LibreHardwareMonitorLib.dll")):
                    potential_dir = cwd_dlls

        # 4. Финальная проверка
        if potential_dir is None or not os.path.exists(potential_dir):
            raise FileNotFoundError(
                f"Не удалось найти папку 'dlls' с LibreHardwareMonitorLib.dll.\n"
                f"Текущая рабочая директория: {os.getcwd()}\n"
                f"Директория файла: {os.path.dirname(os.path.abspath(__file__))}\n"
                f"Пожалуйста, создайте папку 'dlls' в корне проекта (GraduationWork) и поместите туда все .dll файлы."
            )

        dlls_dir = potential_dir
        main_dll = os.path.join(dlls_dir, "LibreHardwareMonitorLib.dll")

        logger.info(f"Using DLLs from: {dlls_dir}")

        # Добавляем папку в sys.path ДО импорта clr
        if dlls_dir not in sys.path:
            sys.path.insert(0, dlls_dir)
            logger.debug(f"Added to sys.path: {dlls_dir}")

        # Загружаем pythonnet и DLL (остальной код без изменений)
        try:
            import clr
        except ImportError as e:
            raise ImportError("pythonnet is not installed. Run: pip install pythonnet") from e

        try:
            clr.AddReference(main_dll)  # type: ignore
            logger.info(f"Loaded: {main_dll}")
        except Exception as e:
            raise RuntimeError(f"Failed to load LibreHardwareMonitorLib.dll: {e}") from e

        try:
            from LibreHardwareMonitor.Hardware import Computer  # type: ignore
            self._Computer = Computer
        except Exception as e:
            raise ImportError(f"Failed to import LibreHardwareMonitor classes: {e}") from e

        # Инициализация
        self.computer = self._Computer()
        self.computer.IsCpuEnabled = True
        self.computer.IsGpuEnabled = True
        self.computer.IsMemoryEnabled = True
        self.computer.IsMotherboardEnabled = True
        self.computer.IsStorageEnabled = True
        self.computer.IsNetworkEnabled = True
        self.computer.IsPsuEnabled = True
        self.computer.IsControllerEnabled = True
        self.computer.Open()

        logger.info("LHM initialized successfully")

    def close(self):
        """Закрывает доступ к датчикам."""
        if self.computer:
            self.computer.Close()
            logger.info("LHM closed")

    def get_all_sensors(self) -> List[Dict[str, Any]]:
        """Получает ВСЕ доступные сенсоры."""
        sensors = []

        for hardware in self.computer.Hardware:
            hardware.Update()

            for sensor in hardware.Sensors:
                if sensor.Value is not None:
                    sensors.append({
                        "hardware": str(hardware.Name),
                        "hardware_type": str(hardware.HardwareType),
                        "sensor_name": str(sensor.Name),
                        "sensor_type": str(sensor.SensorType),
                        "value": float(sensor.Value),
                        "min": float(sensor.Min) if sensor.Min is not None else None,
                        "max": float(sensor.Max) if sensor.Max is not None else None,
                    })

            for sub in hardware.SubHardware:
                sub.Update()
                for sensor in sub.Sensors:
                    if sensor.Value is not None:
                        sensors.append({
                            "hardware": str(sub.Name),
                            "hardware_type": str(sub.HardwareType),
                            "sensor_name": str(sensor.Name),
                            "sensor_type": str(sensor.SensorType),
                            "value": float(sensor.Value),
                            "min": float(sensor.Min) if sensor.Min is not None else None,
                            "max": float(sensor.Max) if sensor.Max is not None else None,
                        })

        return sensors

    def get_cpu_temperature(self) -> Dict[str, float]:
        """Получает температуру CPU."""
        return self._get_sensors_by_filter("Cpu", "Temperature")

    def get_cpu_load(self) -> Dict[str, float]:
        """Получает загрузку CPU."""
        return self._get_sensors_by_filter("Cpu", "Load")

    def get_cpu_power(self) -> Dict[str, float]:
        """Получает энергопотребление CPU."""
        return self._get_sensors_by_filter("Cpu", "Power")

    def get_cpu_voltage(self) -> Dict[str, float]:
        """Получает напряжение CPU."""
        return self._get_sensors_by_filter("Cpu", "Voltage")

    def get_gpu_temperature(self) -> Dict[str, float]:
        """Получает температуру GPU."""
        result = {}
        for gpu_type in ["GpuNvidia", "GpuAmd", "GpuIntel"]:
            result.update(self._get_sensors_by_filter(gpu_type, "Temperature"))
        return result

    def get_gpu_load(self) -> Dict[str, float]:
        """Получает загрузку GPU."""
        result = {}
        for gpu_type in ["GpuNvidia", "GpuAmd", "GpuIntel"]:
            result.update(self._get_sensors_by_filter(gpu_type, "Load"))
        return result

    def get_disk_temperatures(self) -> Dict[str, float]:
        """Получает температуру дисков."""
        return self._get_sensors_by_filter("Storage", "Temperature")

    def get_fan_speeds(self) -> Dict[str, float]:
        """Получает скорости вентиляторов."""
        return self._get_sensors_by_filter(None, "Fan")

    def _get_sensors_by_filter(
            self,
            hardware_type: Optional[str] = None,
            sensor_type: Optional[str] = None
    ) -> Dict[str, float]:
        """Фильтрует сенсоры по типу (регистронезависимо)."""
        result = {}

        # Приводим фильтры к нижнему регистру для надёжного поиска
        hw_filter = hardware_type.lower() if hardware_type else None
        sensor_filter = sensor_type.lower() if sensor_type else None

        for hardware in self.computer.Hardware:
            hardware.Update()
            hw_type_str = str(hardware.HardwareType).lower()
            hw_name_str = str(hardware.Name).lower()

            # Проверяем, подходит ли основное оборудование под фильтр
            is_main_match = (hw_filter is None) or (hw_filter in hw_type_str) or (hw_filter in hw_name_str)

            if is_main_match:
                for sensor in hardware.Sensors:
                    if sensor.Value is not None:
                        st_str = str(sensor.SensorType).lower()
                        if sensor_filter is None or sensor_filter in st_str:
                            key = f"{hardware.Name}_{sensor.Name}"
                            result[key] = float(sensor.Value)

            # Проверяем подчинённое оборудование (SubHardware)
            for sub in hardware.SubHardware:
                sub.Update()
                sub_type_str = str(sub.HardwareType).lower()
                sub_name_str = str(sub.Name).lower()

                is_sub_match = (hw_filter is None) or (hw_filter in sub_type_str) or (hw_filter in sub_name_str)

                if is_sub_match:
                    for sensor in sub.Sensors:
                        if sensor.Value is not None:
                            st_str = str(sensor.SensorType).lower()
                            if sensor_filter is None or sensor_filter in st_str:
                                key = f"{sub.Name}_{sensor.Name}"
                                result[key] = float(sensor.Value)

        return result