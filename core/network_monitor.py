"""Affinity — Surveillance des connexions réseau."""

import threading
import time
from pathlib import Path

import psutil

from config import SECURITY_DIR

IP_BLACKLIST_FILE = SECURITY_DIR / "ip_blacklist.txt"
TRUSTED_IPS = {"8.8.8.8", "8.8.4.4", "1.1.1.1", "1.0.0.1"}


def _load_blacklist() -> set[str]:
    """Charge la liste noire locale des IPs."""
    if not IP_BLACKLIST_FILE.exists():
        return set()
    try:
        return set(
            line.strip().split()[0]
            for line in IP_BLACKLIST_FILE.read_text().splitlines()
            if line.strip() and not line.startswith("#")
        )
    except OSError:
        return set()


def get_active_connections() -> list[dict]:
    """
    Retourne les connexions réseau actives avec statut.
    """
    blacklist = _load_blacklist()
    conns = []

    try:
        for nc in psutil.net_connections(kind="inet"):
            if nc.status != "ESTABLISHED" or not nc.raddr:
                continue
            remote_ip = nc.raddr.ip
            remote_port = nc.raddr.port
            try:
                proc = psutil.Process(nc.pid)
                proc_name = proc.name()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                proc_name = "?"
                nc.pid = 0

            status = "unknown"
            reason = None
            if remote_ip in blacklist:
                status = "dangerous"
                reason = "IP dans liste noire"
            elif remote_ip in TRUSTED_IPS:
                status = "trusted"
            elif nc.pid and "affinity" in proc_name.lower():
                status = "system"
            elif remote_port not in (80, 443, 22, 53):
                status = "suspicious"
                reason = "Port non standard"

            conns.append({
                "process_name": proc_name,
                "pid": nc.pid,
                "local_addr": f"{nc.laddr.ip}:{nc.laddr.port}" if nc.laddr else "—",
                "remote_addr": remote_ip,
                "remote_port": remote_port,
                "protocol": "TCP" if nc.type == 1 else "UDP",
                "status": status,
                "reason": reason,
            })
    except (psutil.AccessDenied, OSError):
        pass

    return conns
