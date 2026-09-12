"""
devices.py — Сбор информации о подключённых устройствах: USB, принтеры, мониторы.
"""

import platform
from dataclasses import dataclass, asdict
from typing import List, Dict, Any

from .base import BaseCollector


@dataclass
class USBDevice:
    vendor_id: str
    product_id: str
    product_name: str


@dataclass
class Printer:
    name: str
    status: str
    is_default: bool


@dataclass
class Monitor:
    name: str
    width: int
    height: int


@dataclass
class DevicesInfo:
    usb_devices: List[Dict[str, Any]]
    printers: List[Dict[str, Any]]
    monitors: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class DevicesCollector(BaseCollector):
    def get(self) -> Dict[str, Any]:
        self.logger.debug("Collecting devices info")

        usb_devices = self._get_usb_devices()
        printers = self._get_printers()
        monitors = self._get_monitors()

        info = DevicesInfo(
            usb_devices=usb_devices,
            printers=printers,
            monitors=monitors,
        )

        self.logger.info(f"Devices: {len(usb_devices)} USB, {len(printers)} printers")
        return info.to_dict()

    def _get_usb_devices(self) -> List[Dict[str, Any]]:
        """Список USB-устройств."""
        devices = []
        try:
            import usb.core
            for dev in usb.core.find(find_all=True):
                try:
                    name = usb.util.get_string(dev, dev.iProduct) if dev.iProduct else "Unknown"
                except:
                    name = "Unknown"
                devices.append(asdict(USBDevice(
                    vendor_id=f"{dev.idVendor:04x}",
                    product_id=f"{dev.idProduct:04x}",
                    product_name=name,
                )))
        except ImportError:
            self.logger.warning("pyusb not installed, skipping USB devices")
        except Exception as e:
            self.logger.error(f"USB collection failed: {e}")
        return devices

    def _get_printers(self) -> List[Dict[str, Any]]:
        """Список принтеров (только Windows)."""
        if platform.system() != "Windows":
            return []

        printers = []
        try:
            import wmi
            c = wmi.WMI()
            for printer in c.Win32_Printer():
                printers.append(asdict(Printer(
                    name=printer.Name,
                    status=str(printer.PrinterStatus),
                    is_default=printer.Default,
                )))
        except ImportError:
            self.logger.warning("wmi not installed, skipping printers")
        except Exception as e:
            self.logger.error(f"Printer collection failed: {e}")
        return printers

    def _get_monitors(self) -> List[Dict[str, Any]]:
        """Список мониторов."""
        monitors = []
        try:
            from screeninfo import get_monitors
            for m in get_monitors():
                monitors.append(asdict(Monitor(
                    name=f"Monitor {m.width}x{m.height}",
                    width=m.width,
                    height=m.height,
                )))
        except ImportError:
            self.logger.warning("screeninfo not installed, skipping monitors")
        except Exception as e:
            self.logger.error(f"Monitor collection failed: {e}")
        return monitors