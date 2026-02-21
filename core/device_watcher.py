"""Affinity — Détection en temps réel des périphériques USB (pyudev)."""

import threading
from pathlib import Path

_devices = []
_on_device_added = None
_on_device_removed = None
_watcher_thread = None
_stop_event = threading.Event()


def _get_mountpoint(devnode: str) -> str | None:
    """Retourne le point de montage pour un périphérique de stockage."""
    try:
        with open("/proc/mounts") as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 2 and devnode in parts[0]:
                    return parts[1]
    except OSError:
        pass
    return None


def _get_usb_info(device) -> dict:
    """Extrait les infos d'un device udev."""
    return {
        "name": device.get("ID_MODEL", "Périphérique inconnu"),
        "vendor": device.get("ID_VENDOR", ""),
        "vid": device.get("ID_VENDOR_ID", ""),
        "pid": device.get("ID_MODEL_ID", ""),
        "subsystem": device.subsystem,
        "devnode": device.device_node or "",
        "action": "add",
    }


def _run_watcher() -> None:
    """Boucle principale du watcher."""
    try:
        import pyudev

        context = pyudev.Context()
        monitor = pyudev.Monitor.from_netlink(context)
        monitor.filter_by(subsystem="usb")
        monitor.filter_by(subsystem="block")
        for device in monitor:
            if _stop_event.is_set():
                break
            action = "add" if device.action in ("add", "bind") else "remove"
            info = _get_usb_info(device)
            info["action"] = action
            if action == "add":
                _devices.append(info)
                if _on_device_added:
                    _on_device_added(info)
            else:
                _devices[:] = [d for d in _devices if d.get("devnode") != device.device_node]
                if _on_device_removed:
                    _on_device_removed(info)
    except ImportError:
        pass
    except Exception:
        pass


def start_device_watcher(
    on_device_added=None,
    on_device_removed=None,
) -> bool:
    """Démarre la surveillance des périphériques."""
    global _on_device_added, _on_device_removed, _watcher_thread
    _on_device_added = on_device_added
    _on_device_removed = on_device_removed
    _stop_event.clear()
    try:
        import pyudev
    except ImportError:
        return False
    if _watcher_thread and _watcher_thread.is_alive():
        return True
    _watcher_thread = threading.Thread(target=_run_watcher, daemon=True)
    _watcher_thread.start()
    return True


def stop_device_watcher() -> None:
    """Arrête la surveillance."""
    global _watcher_thread
    _stop_event.set()
    if _watcher_thread:
        _watcher_thread.join(timeout=2)
        _watcher_thread = None


def get_current_devices() -> list[dict]:
    """Retourne la liste des périphériques actuellement connectés."""
    return list(_devices)


def find_storage_mountpoint(device_info: dict) -> str | None:
    """Pour un périphérique de stockage, attend le montage et retourne le chemin."""
    devnode = device_info.get("devnode", "") or ""
    if not devnode:
        return None
    import time

    for _ in range(20):
        mp = _get_mountpoint(devnode)
        if mp and Path(mp).exists():
            return mp
        time.sleep(0.5)
    return None
