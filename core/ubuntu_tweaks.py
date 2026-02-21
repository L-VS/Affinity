"""Affinity — Tweaks Ubuntu (Dock, raccourcis clavier)."""

import subprocess
from pathlib import Path


def _gsettings_get(schema: str, key: str) -> str:
    try:
        r = subprocess.run(["gsettings", "get", schema, key], capture_output=True, text=True, timeout=5)
        if r.returncode == 0:
            return (r.stdout or "").strip().strip("'\"")
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return ""


def _gsettings_set(schema: str, key: str, value: str | int) -> bool:
    try:
        r = subprocess.run(["gsettings", "set", schema, key, str(value)], capture_output=True, timeout=5)
        return r.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


# Dock — Ubuntu utilise soit dash-to-dock soit ubuntu-dock
DOCK_SCHEMAS = [
    "org.gnome.shell.extensions.dash-to-dock",
    "org.gnome.shell.extensions.ding",
]


def get_dock_size() -> int:
    for schema in DOCK_SCHEMAS:
        val = _gsettings_get(schema, "dash-max-icon-size")
        if val and val.isdigit():
            return int(val)
        val = _gsettings_get(schema, "icon-size")
        if val and val.isdigit():
            return int(val)
    return 48


def set_dock_size(size: int) -> bool:
    size = max(24, min(96, int(size)))
    ok = False
    for schema in DOCK_SCHEMAS:
        if _gsettings_set(schema, "dash-max-icon-size", size):
            ok = True
        if _gsettings_set(schema, "icon-size", size):
            ok = True
    return ok


def get_dock_position() -> str:
    for schema in DOCK_SCHEMAS:
        val = _gsettings_get(schema, "dock-position")
        if val in ("BOTTOM", "LEFT", "RIGHT", "TOP"):
            return val.lower()
    return "bottom"


def set_dock_position(position: str) -> bool:
    pos = position.upper() if position in ("bottom", "left", "right", "top") else "BOTTOM"
    for schema in DOCK_SCHEMAS:
        _gsettings_set(schema, "dock-position", pos)
    return True


def get_keybindings() -> list[dict]:
    """Liste quelques raccourcis courants."""
    bindings = []
    schemas_keys = [
        ("org.gnome.desktop.wm.keybindings", "close", "Fermer la fenêtre"),
        ("org.gnome.desktop.wm.keybindings", "minimize", "Réduire"),
        ("org.gnome.desktop.wm.keybindings", "maximize", "Maximiser"),
        ("org.gnome.settings-daemon.plugins.media-keys", "screensaver", "Écran de veille"),
        ("org.gnome.settings-daemon.plugins.media-keys", "home", "Dossier personnel"),
    ]
    for schema, key, desc in schemas_keys:
        val = _gsettings_get(schema, key)
        bindings.append({"schema": schema, "key": key, "value": val, "description": desc})
    return bindings


def set_keybinding(schema: str, key: str, value: str) -> bool:
    return _gsettings_set(schema, key, value)
