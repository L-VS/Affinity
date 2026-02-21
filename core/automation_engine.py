"""Affinity — Moteur d'automatisations (planification Cleaner, Scan, etc.)."""

import json
import subprocess
from pathlib import Path
from typing import Callable

from config import DATA_DIR

AUTOMATIONS_FILE = DATA_DIR / "automatisations.json"


def load_automations() -> list[dict]:
    """Charge la liste des automatisations."""
    if not AUTOMATIONS_FILE.exists():
        return []
    try:
        with open(AUTOMATIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def save_automations(data: list[dict]) -> bool:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with open(AUTOMATIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except OSError:
        return False


def add_automation(
    trigger: str,
    action: str,
    params: dict | None = None,
) -> bool:
    """trigger: cron | schedule | manual. action: clean | scan | both."""
    data = load_automations()
    entry = {
        "id": f"auto_{len(data) + 1}",
        "trigger": trigger,
        "action": action,
        "params": params or {},
        "enabled": True,
    }
    data.append(entry)
    return save_automations(data)


def remove_automation(auto_id: str) -> bool:
    data = [a for a in load_automations() if a.get("id") != auto_id]
    return save_automations(data)


def install_cron_clean(day: int = 0, hour: int = 3) -> bool:
    """Installe une entrée cron pour nettoyage. day: 0=dimanche, 1=lundi..."""
    script = DATA_DIR.parent / "affinity" / "main.py"
    if not script.exists():
        script = Path(__file__).resolve().parent.parent / "main.py"
    cron_line = f"0 {hour} * * {day} cd {script.parent} && python3 main.py --auto-clean 2>/dev/null"
    try:
        result = subprocess.run(
            ["crontab", "-l"],
            capture_output=True,
            text=True,
        )
        current = result.stdout or ""
        if "# AFFINITY" not in current:
            new = current.strip() + f"\n# AFFINITY\n{cron_line}\n"
        else:
            lines = current.split("\n")
            out = []
            skip = False
            for line in lines:
                if "# AFFINITY" in line:
                    skip = True
                    continue
                if skip and line.strip() and not line.strip().startswith("#"):
                    continue
                skip = False
                out.append(line)
            out.append("# AFFINITY")
            out.append(cron_line)
            new = "\n".join(out) + "\n"
        subprocess.run(["crontab", "-"], input=new, capture_output=True, text=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def uninstall_cron_clean() -> bool:
    try:
        result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        current = result.stdout or ""
        lines = [l for l in current.split("\n") if "# AFFINITY" not in l and not (l.strip().startswith("0 ") and "affinity" in l.lower())]
        subprocess.run(["crontab", "-"], input="\n".join(lines), capture_output=True, text=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False
