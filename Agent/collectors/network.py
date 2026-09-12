import psutil
from dataclasses import dataclass, asdict
from typing import List, Dict, Any

from .base import BaseCollector


@dataclass
class NetworkInterface:
    name: str
    ip_address: str
    mac_address: str
    is_up: bool


@dataclass
class NetworkIO:
    bytes_sent: int
    bytes_recv: int
    packets_sent: int
    packets_recv: int
    errin: int
    errout: int
    dropin: int
    dropout: int


@dataclass
class NetworkConnection:
    fd: int
    family: str
    type: str
    laddr: str
    raddr: str
    status: str
    pid: int


@dataclass
class NetworkInfo:
    interfaces: List[Dict[str, Any]]
    io: Dict[str, Any]
    connections_count: int
    connections: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class NetworkCollector(BaseCollector):
    def __init__(self, max_connections: int = 50):
        super().__init__()
        self.max_connections = max_connections

    def get(self) -> Dict[str, Any]:
        self.logger.debug("Collecting network metrics")

        # Интерфейсы
        interfaces = []
        for iface, addrs in psutil.net_if_addrs().items():
            ip_addr = ""
            mac_addr = ""
            for addr in addrs:
                if addr.family.name == 'AF_INET':
                    ip_addr = addr.address
                elif addr.family.name == 'AF_LINK':
                    mac_addr = addr.address

            stat = psutil.net_if_stats().get(iface)
            interfaces.append(asdict(NetworkInterface(
                name=iface,
                ip_address=ip_addr,
                mac_address=mac_addr,
                is_up=stat.isup if stat else False,
            )))

        # I/O
        nio = psutil.net_io_counters()
        io_data = asdict(NetworkIO(
            bytes_sent=nio.bytes_sent,
            bytes_recv=nio.bytes_recv,
            packets_sent=nio.packets_sent,
            packets_recv=nio.packets_recv,
            errin=nio.errin,
            errout=nio.errout,
            dropin=nio.dropin,
            dropout=nio.dropout,
        ))

        # Соединения (ограничиваем количество)
        connections = []
        try:
            conns = psutil.net_connections(kind='inet')[:self.max_connections]
            for conn in conns:
                laddr = f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else ""
                raddr = f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else ""
                connections.append(asdict(NetworkConnection(
                    fd=conn.fd,
                    family=conn.family.name,
                    type=conn.type.name,
                    laddr=laddr,
                    raddr=raddr,
                    status=conn.status,
                    pid=conn.pid or 0,
                )))
        except (psutil.AccessDenied, psutil.Error) as e:
            self.logger.warning(f"Cannot get connections: {e}")

        info = NetworkInfo(
            interfaces=interfaces,
            io=io_data,
            connections_count=len(connections),
            connections=connections,
        )

        self.logger.info(f"Network: {nio.bytes_sent} sent, {nio.bytes_recv} recv")
        return info.to_dict()