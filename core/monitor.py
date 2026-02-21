"""Affinity — Surveillance système en temps réel (thread background)."""

import threading
import time
from collections import deque

import psutil


class SystemMonitor:
    """Thread de collecte des métriques toutes les 3 secondes."""

    def __init__(self, callback, interval: float = 3):
        self.callback = callback
        self.interval = interval
        self.running = True
        self._thread = None
        self._prev_net = None
        self._prev_time = time.time()
        self.cpu_history = deque(maxlen=100)
        self.ram_history = deque(maxlen=100)
        self.disk_history = deque(maxlen=100)

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self.running = False
        if self._thread:
            self._thread.join(timeout=5)

    def _get_cpu_temp(self) -> float:
        try:
            temps = psutil.sensors_temperatures()
            for name in ("coretemp", "k10temp", "zenpower"):
                if name in temps and temps[name]:
                    return temps[name][0].current
        except Exception:
            pass
        return 0

    def _get_ssid(self) -> str:
        try:
            import subprocess
            r = subprocess.run(
                ["iwgetid", "-r"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            return (r.stdout or "").strip() or "Câble Ethernet"
        except Exception:
            return "Réseau"

    def _get_local_ip(self) -> str:
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "—"

    def _run(self) -> None:
        self._prev_net = psutil.net_io_counters()
        self._prev_time = time.time()
        while self.running:
            try:
                cpu = psutil.cpu_percent(interval=None)
                ram = psutil.virtual_memory()
                disk = psutil.disk_usage("/")
                net = psutil.net_io_counters()
                now = time.time()
                dt = max(0.01, now - self._prev_time)
                dl_speed = (net.bytes_recv - self._prev_net.bytes_recv) / dt / 1024 / 1024
                ul_speed = (net.bytes_sent - self._prev_net.bytes_sent) / dt / 1024 / 1024
                self._prev_net = net
                self._prev_time = now
                cpu_temp = self._get_cpu_temp()
                self.cpu_history.append(cpu)
                self.ram_history.append(ram.percent)
                self.disk_history.append(disk.percent)
                metrics = {
                    "cpu_percent": cpu,
                    "cpu_temp": cpu_temp,
                    "cpu_history": list(self.cpu_history),
                    "ram_used_gb": ram.used / 1e9,
                    "ram_total_gb": ram.total / 1e9,
                    "ram_percent": ram.percent,
                    "ram_history": list(self.ram_history),
                    "disk_percent": disk.percent,
                    "disk_used_gb": disk.used / 1e9,
                    "disk_total_gb": disk.total / 1e9,
                    "disk_free_gb": disk.free / 1e9,
                    "disk_history": list(self.disk_history),
                    "net_dl_mbs": dl_speed,
                    "net_ul_mbs": ul_speed,
                    "net_ssid": self._get_ssid(),
                    "local_ip": self._get_local_ip(),
                    "uptime_seconds": time.time() - psutil.boot_time(),
                }
                self.callback(metrics)
            except Exception:
                pass
            for _ in range(int(self.interval * 10)):
                if not self.running:
                    return
                time.sleep(0.1)
