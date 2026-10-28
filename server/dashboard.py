"""
server/dashboard.py — консольный дашборд на базе rich.

Обновляется в реальном времени, показывает:
- Статистику по кластеру (онлайн/оффлайн)
- Таблицу со всеми хостами и их метриками
- Цветовую индикацию проблем
"""

import time
import threading
from datetime import datetime
from typing import Optional

from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.text import Text
from rich.console import Console
from rich.align import Align

from server.storage import MetricsStorage


class Dashboard:

    def __init__(self, storage: MetricsStorage, refresh_rate: float = 1.0, thresholds: Optional[dict] = None):
        """
        Args:
            storage: Хранилище метрик
            refresh_rate: Частота обновления (сек)
            thresholds: Пороги для цветовой индикации
        """
        self.storage = storage
        self.refresh_rate = refresh_rate
        self.console = Console()

        # Пороги по умолчанию
        self.thresholds = thresholds or {
            "cpu_warning": 70,
            "cpu_critical": 90,
            "memory_warning": 80,
            "memory_critical": 95,
            "disk_warning": 80,
            "disk_critical": 95,
            "gpu_temp_warning": 75,
            "gpu_temp_critical": 85,
        }

        self._running = False

    def start(self):
        """Запускает дашборд в отдельном потоке."""
        self._running = True
        thread = threading.Thread(target=self._run, daemon=True)
        thread.start()
        return thread

    def stop(self):
        """Останавливает дашборд."""
        self._running = False

    def _run(self):
        """Главный цикл обновления."""
        with Live(
                self._render(),
                console=self.console,
                refresh_per_second=1 / self.refresh_rate,
                screen=True
        ) as live:
            while self._running:
                live.update(self._render())
                time.sleep(self.refresh_rate)

    def _render(self) -> Layout:
        """Создаёт полную разметку дашборда."""
        layout = Layout()

        layout.split_column(
            Layout(self._render_header(), name="header", size=3),
            Layout(self._render_stats(), name="stats", size=5),
            Layout(self._render_hosts_table(), name="hosts"),
            Layout(self._render_footer(), name="footer", size=3),
        )

        return layout

    def _render_header(self) -> Panel:
        """Заголовок дашборда."""
        title = Text()
        title.append("  ", style="bold")
        title.append("CLUSTER MONITORING DASHBOARD", style="bold cyan")
        title.append("  ", style="bold")

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        subtitle = Text(f"Last update: {now}", style="dim")

        return Panel(
            Align.center(title),
            subtitle=subtitle,
            border_style="cyan",
        )

    def _render_stats(self) -> Panel:
        """Панель со статистикой кластера."""
        stats = self.storage.get_stats()

        # Цвет для счётчиков
        online_color = "green" if stats["online"] > 0 else "red"
        stale_color = "yellow" if stats["stale"] > 0 else "dim"
        offline_color = "red" if stats["offline"] > 0 else "dim"

        # Цвет для средних значений
        avg_cpu_color = self._get_load_color(
            stats["avg_cpu"],
            self.thresholds["cpu_warning"],
            self.thresholds["cpu_critical"]
        )
        avg_ram_color = self._get_load_color(
            stats["avg_ram"],
            self.thresholds["memory_warning"],
            self.thresholds["memory_critical"]
        )

        content = Text()
        content.append(" CLUSTER: ", style="bold")
        content.append(f"{stats['total_hosts']} hosts  ", style="white")
        content.append("│  ", style="dim")

        content.append("🟢 Online: ", style="bold")
        content.append(f"{stats['online']}  ", style=online_color)
        content.append("│  ", style="dim")

        content.append("🟡 Stale: ", style="bold")
        content.append(f"{stats['stale']}  ", style=stale_color)
        content.append("│  ", style="dim")

        content.append("🔴 Offline: ", style="bold")
        content.append(f"{stats['offline']}  ", style=offline_color)
        content.append("\n")

        content.append(" AVERAGES: ", style="bold")
        content.append("CPU: ", style="dim")
        content.append(f"{stats['avg_cpu']:5.1f}%  ", style=avg_cpu_color)
        content.append("│  RAM: ", style="dim")
        content.append(f"{stats['avg_ram']:5.1f}%", style=avg_ram_color)

        return Panel(content, border_style="blue")

    def _render_hosts_table(self) -> Table:
        """Таблица со всеми хостами."""
        table = Table(
            title="  HOSTS",
            expand=True,
            show_lines=True,
            border_style="bright_black",
        )

        # Колонки
        table.add_column("Status", justify="center", width=4)
        table.add_column("Hostname", style="cyan", width=20)
        table.add_column("OS", width=12)
        table.add_column("CPU", justify="right", width=8)
        table.add_column("RAM", justify="right", width=8)
        table.add_column("Disk", justify="right", width=10)
        table.add_column("GPU", justify="right", width=10)
        table.add_column("Temp", justify="right", width=8)
        table.add_column("Last seen", justify="right", width=10)

        hosts = self.storage.get_all_hosts()

        if not hosts:
            table.add_row(
                "—", "—", "—", "—", "—", "—", "—", "—", "—"
            )
            return table

        for host in hosts:
            metrics = host.get("metrics", {})
            status = host["status"]

            # Статус (эмодзи)
            if status == "online":
                status_icon = "[green]●[/]"
            elif status == "stale":
                status_icon = "[yellow]◐[/]"
            else:
                status_icon = "[red]○[/]"

            # Имя хоста
            hostname = host["hostname"]

            # ОС
            sys_info = metrics.get("system", {})
            os_name = sys_info.get("os_name", "—")
            os_version = sys_info.get("os_release", "")
            os_str = f"{os_name} {os_version}".strip() or "—"

            # CPU
            cpu_data = metrics.get("cpu", {})
            cpu_val = cpu_data.get("usage_percent")
            if cpu_val is not None:
                cpu_color = self._get_load_color(
                    cpu_val,
                    self.thresholds["cpu_warning"],
                    self.thresholds["cpu_critical"]
                )
                cpu_str = f"[{cpu_color}]{cpu_val:5.1f}%[/]"
            else:
                cpu_str = "[dim]—[/]"

            # RAM
            mem_data = metrics.get("memory", {})
            ram_val = mem_data.get("percent")
            ram_used = mem_data.get("used_gb")
            ram_total = mem_data.get("total_gb")
            if ram_val is not None:
                ram_color = self._get_load_color(
                    ram_val,
                    self.thresholds["memory_warning"],
                    self.thresholds["memory_critical"]
                )
                ram_str = f"[{ram_color}]{ram_val:5.1f}%[/]\n[dim]{ram_used:.1f}/{ram_total:.1f}G[/]"
            else:
                ram_str = "[dim]—[/]"

            # Disk (максимальная заполненность)
            disk_data = metrics.get("disk", {})
            partitions = disk_data.get("partitions", [])
            if partitions:
                max_disk = max(partitions, key=lambda p: p.get("percent", 0))
                disk_val = max_disk.get("percent", 0)
                disk_dev = max_disk.get("device", "")
                disk_color = self._get_load_color(
                    disk_val,
                    self.thresholds["disk_warning"],
                    self.thresholds["disk_critical"]
                )
                disk_str = f"[{disk_color}]{disk_val:5.1f}%[/]\n[dim]{disk_dev}[/]"
            else:
                disk_str = "[dim]—[/]"

            # GPU
            gpu_data = metrics.get("gpu", [])
            if gpu_data:
                # Берём самую загруженную GPU
                main_gpu = max(
                    gpu_data,
                    key=lambda g: g.get("load_percent", 0) or 0
                )
                gpu_name = main_gpu.get("name", "—")
                gpu_load = main_gpu.get("load_percent")
                gpu_temp = main_gpu.get("temperature_c")

                if gpu_load is not None:
                    gpu_str = f"{gpu_load:5.1f}%"
                else:
                    gpu_str = "—"

                # Обрезаем длинное имя
                if len(gpu_name) > 15:
                    gpu_name = gpu_name[:12] + "..."

                gpu_str = f"{gpu_str}\n[dim]{gpu_name}[/]"
            else:
                gpu_str = "[dim]—[/]"

            # Температура CPU
            temp_data = cpu_data.get("temperature_c")
            if temp_data and isinstance(temp_data, dict):
                max_temp = max(temp_data.values())
                temp_color = self._get_temp_color(
                    max_temp,
                    self.thresholds.get("gpu_temp_warning", 75),
                    self.thresholds.get("gpu_temp_critical", 85)
                )
                temp_str = f"[{temp_color}]{max_temp:4.0f}°C[/]"
            elif temp_data and isinstance(temp_data, (int, float)):
                temp_str = f"{temp_data:4.0f}°C"
            else:
                temp_str = "[dim]—[/]"

            # Last seen
            last_seen = host["seconds_ago"]
            if last_seen < 60:
                last_str = f"{last_seen:.0f}s ago"
            elif last_seen < 3600:
                last_str = f"{last_seen / 60:.1f}m ago"
            else:
                last_str = f"{last_seen / 3600:.1f}h ago"

            table.add_row(
                status_icon,
                hostname,
                os_str,
                cpu_str,
                ram_str,
                disk_str,
                gpu_str,
                temp_str,
                last_str,
            )

        return table

    def _render_footer(self) -> Panel:
        """Подвал с подсказками."""
        text = Text()
        text.append(" ", style="bold")
        text.append("Legend: ", style="bold")
        text.append("🟢 Online ", style="green")
        text.append("(< 15s)  │  ", style="dim")
        text.append("◐ Stale ", style="yellow")
        text.append("(< 30s)  │  ", style="dim")
        text.append("○ Offline ", style="red")
        text.append("(> 30s)", style="dim")
        text.append("     ")
        text.append("Press Ctrl+C to stop", style="dim italic")

        return Panel(
            Align.center(text),
            border_style="bright_black",
        )

    def _get_load_color(self, value: float, warning: float, critical: float) -> str:
        """Возвращает цвет для значения нагрузки."""
        if value >= critical:
            return "red bold"
        elif value >= warning:
            return "yellow"
        return "green"

    def _get_temp_color(self, value: float, warning: float, critical: float) -> str:
        """Возвращает цвет для температуры."""
        if value >= critical:
            return "red bold"
        elif value >= warning:
            return "yellow"
        return "cyan"