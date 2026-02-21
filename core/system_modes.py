"""Affinity — Modes système (Économie, Équilibré, Performance, Créatif, Silencieux)."""

import subprocess
from typing import Callable

SYSTEM_MODES = [
    {
        "id": "economy",
        "name": "Économie",
        "icon": "🔋",
        "target": "Batterie, travail léger",
        "details": {
            "cpu_governor": "powersave",
            "swappiness": 60,
            "io_scheduler": "cfq",
            "network": "économie",
            "video": "VSync",
            "thermal": "température prioritaire",
        },
        "description": "Réduit la consommation. Idéal sur batterie ou bureautique légère.",
    },
    {
        "id": "balanced",
        "name": "Équilibré",
        "icon": "⚖️",
        "target": "Usage quotidien",
        "details": {
            "cpu_governor": "schedutil",
            "swappiness": 30,
            "io_scheduler": "none",
            "network": "normal",
            "video": "qualité",
            "thermal": "équilibré",
        },
        "description": "Bon compromis performance/autonomie. Recommandé par défaut.",
    },
    {
        "id": "performance",
        "name": "Performance",
        "icon": "⚡",
        "target": "Jeux, compilation",
        "details": {
            "cpu_governor": "performance",
            "swappiness": 10,
            "io_scheduler": "none",
            "network": "basse latence",
            "video": "haute perf",
            "thermal": "fans max",
        },
        "description": "CPU à fond. Consommation électrique accrue. Pour jeux et compilation.",
    },
    {
        "id": "creative",
        "name": "Créatif",
        "icon": "🎨",
        "target": "Montage vidéo, 3D",
        "details": {
            "cpu_governor": "performance",
            "swappiness": 15,
            "io_scheduler": "bfq",
            "network": "gros débit",
            "video": "rendu rapide",
            "thermal": "optimisé I/O",
        },
        "description": "Optimisé pour gros flux disque et rendu. Idéal pour la création.",
    },
    {
        "id": "silent",
        "name": "Silencieux",
        "icon": "🔇",
        "target": "Nuit, bureautique",
        "details": {
            "cpu_governor": "powersave",
            "swappiness": 40,
            "io_scheduler": "mq-deadline",
            "network": "normal",
            "video": "VSync",
            "thermal": "ventilateurs silencieux",
        },
        "description": "Réduit le bruit des ventilateurs. Pour travail de nuit.",
    },
]


def _run_privileged(args: list[str]) -> bool:
    try:
        r = subprocess.run(["pkexec"] + args, capture_output=True, timeout=30)
        return r.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def apply_mode(mode_id: str, progress_callback: Callable[[str], None] | None = None) -> dict:
    """
    Applique un mode système.
    Retourne {"cpu": bool, "swappiness": bool, "message": str}
    """
    mode = next((m for m in SYSTEM_MODES if m["id"] == mode_id), None)
    if not mode:
        return {"cpu": False, "swappiness": False, "message": "Mode inconnu"}

    result = {"cpu": False, "swappiness": False, "message": ""}

    # CPU Governor (cpupower)
    gov = mode["details"].get("cpu_governor", "schedutil")
    if progress_callback:
        progress_callback(f"Application du governor {gov}...")
    result["cpu"] = _run_privileged(["cpupower", "frequency-set", "-g", gov])
    if not result["cpu"]:
        result["message"] = "cpupower non disponible (installez linux-tools-common)"

    # Swappiness
    sw = mode["details"].get("swappiness", 30)
    if progress_callback:
        progress_callback(f"Swappiness = {sw}...")
    result["swappiness"] = _run_privileged(["sysctl", "-w", f"vm.swappiness={sw}"])

    return result


def get_current_governor() -> str:
    try:
        with open("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor") as f:
            return f.read().strip()
    except OSError:
        return "?"


def get_current_swappiness() -> int:
    try:
        with open("/proc/sys/vm/swappiness") as f:
            return int(f.read().strip())
    except (OSError, ValueError):
        return 60
