"""Affinity — Chargement et sauvegarde de la configuration."""

import json
from pathlib import Path

from config import CONFIG_FILE, DATA_DIR

DEFAULTS = {
    "version": 1,
    "profile": {"first_name": "", "avatar_path": None, "pc_name": ""},
    "behavior": {"mode": "supervised", "auto_action_delay_sec": 30},
    "antivirus": {
        "realtime": True,
        "usb_auto_scan": True,
        "virustotal_api_key": None,
        "scan_exclusions": ["/usr/bin", "/usr/lib"],
    },
    "cleaner": {
        "scheduled": False,
        "schedule_freq": "weekly",
        "schedule_day": 0,
        "schedule_hour": 3,
        "categories_enabled": ["apt_cache", "tmp", "browser_cache", "logs", "thumbnails"],
        "backup_before_clean": False,
    },
    "ubuntu_custom": {
        "gtk_theme": "Yaru-dark",
        "icon_theme": "Yaru",
        "cursor_theme": "Adwaita",
        "font_name": "Ubuntu",
        "font_size": 11,
        "wallpaper": None,
    },
    "appearance": {
        "theme": "dark",
        "accent_color": "cyan",
        "font_scale": 1.0,
        "animations": True,
    },
    "notifications": {
        "enabled": True,
        "sounds": True,
        "verbosity": "standard",
        "dnd_enabled": False,
    },
    "ai": {
        "enabled": False,
        "groq_api_key": None,
        "auto_usage": "none",
    },
    "recommendations": {
        "auto_clean": False,
        "usb_scan": True,
        "realtime_watch": True,
        "auto_updates": False,
        "network_tweaks": False,
        "thermal_tweaks": False,
        "reduce_animations": False,
        "ai_help_on_error": False,
    },
    "automations": [],
    "system_mode": "balanced",
    "dock": {"size": 48, "position": "bottom"},
}


def _deep_merge(base: dict, override: dict) -> dict:
    out = dict(base)
    for k, v in override.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config() -> dict:
    """Charge la configuration depuis config.json."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not CONFIG_FILE.exists():
        return dict(DEFAULTS)
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return _deep_merge(DEFAULTS, data)
    except (json.JSONDecodeError, OSError):
        return dict(DEFAULTS)


def save_config(config: dict) -> bool:
    """Sauvegarde la configuration."""
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except OSError:
        return False


def get(config: dict, *keys, default=None):
    """Accès imbriqué : get(cfg, "profile", "first_name")"""
    for k in keys:
        if isinstance(config, dict) and k in config:
            config = config[k]
        else:
            return default
    return config


def set_key(config: dict, value, *keys) -> None:
    """Définit une clé imbriquée."""
    for k in keys[:-1]:
        if k not in config:
            config[k] = {}
        config = config[k]
    config[keys[-1]] = value
