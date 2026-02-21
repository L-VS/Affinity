"""Affinity — Personnalisation Ubuntu (thèmes, icônes, polices, wallpapers, tweaks GNOME).

Ce module permet de modifier finement l'apparence et le comportement d'Ubuntu (GNOME).

Created by l-vs — Affinity Customizer v2
"""

import subprocess
from pathlib import Path


def _gsettings_get(schema: str, key: str) -> str:
    """Lit une clé gsettings."""
    try:
        r = subprocess.run(
            ["gsettings", "get", schema, key],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if r.returncode == 0:
            return (r.stdout or "").strip().strip("'\"")
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return ""


def _gsettings_set(schema: str, key: str, value: str) -> bool:
    """Définit une clé gsettings."""
    try:
        # Si c'est un booléen ou un nombre dans une string, on ne met pas de quotes supplémentaires
        # dans la commande subprocess si c'est déjà géré par gsettings
        r = subprocess.run(
            ["gsettings", "set", schema, key, value],
            capture_output=True,
            timeout=5,
        )
        return r.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


# ── Apparence de base ──

def get_available_themes() -> list[str]:
    """Liste les thèmes GTK installés."""
    themes = []
    for base in ["/usr/share/themes", str(Path.home() / ".themes")]:
        p = Path(base)
        if p.exists():
            for d in p.iterdir():
                if d.is_dir() and (d / "gtk-3.0").exists():
                    themes.append(d.name)
    return sorted(set(themes)) or ["Yaru", "Yaru-dark", "Adwaita"]


def get_available_icon_themes() -> list[str]:
    """Liste les thèmes d'icônes installés."""
    themes = []
    for base in ["/usr/share/icons", str(Path.home() / ".icons")]:
        p = Path(base)
        if p.exists():
            for d in p.iterdir():
                if d.is_dir() and (d / "index.theme").exists():
                    themes.append(d.name)
    return sorted(set(themes)) or ["Yaru", "Adwaita"]


def get_current_theme() -> str:
    return _gsettings_get("org.gnome.desktop.interface", "gtk-theme") or "Yaru-dark"


def set_gtk_theme(theme: str) -> bool:
    return _gsettings_set("org.gnome.desktop.interface", "gtk-theme", theme)


def set_icon_theme(theme: str) -> bool:
    return _gsettings_set("org.gnome.desktop.interface", "icon-theme", theme)


def set_dark_mode(enabled: bool) -> bool:
    """Active/désactive le mode sombre."""
    val = "prefer-dark" if enabled else "default"
    return _gsettings_set("org.gnome.desktop.interface", "color-scheme", val)


def set_wallpaper(path: str | Path) -> bool:
    p = Path(path)
    if not p.exists() or not p.is_file():
        return False
    uri = f"file://{p.absolute()}"
    ok = _gsettings_set("org.gnome.desktop.background", "picture-uri", uri)
    if ok:
        _gsettings_set("org.gnome.desktop.background", "picture-uri-dark", uri)
    return ok


# ── Tweaks GNOME (Performance & Workflow) ──

def set_animations_enabled(enabled: bool) -> bool:
    """Active/désactive les animations GNOME pour plus de réactivité."""
    val = "true" if enabled else "false"
    return _gsettings_set("org.gnome.desktop.interface", "enable-animations", val)


def is_animations_enabled() -> bool:
    return _gsettings_get("org.gnome.desktop.interface", "enable-animations") == "true"


def set_dock_autohide(enabled: bool) -> bool:
    """Active le masquage automatique du dock Ubuntu."""
    val = "true" if enabled else "false"
    return _gsettings_set("org.gnome.shell.extensions.dash-to-dock", "dock-fixed", "false" if enabled else "true")


def set_dock_icon_size(size: int) -> bool:
    """Modifie la taille des icônes du dock (standard: 48, compact: 32)."""
    return _gsettings_set("org.gnome.shell.extensions.dash-to-dock", "dash-max-icon-size", str(size))


def get_dock_icon_size() -> int:
    try:
        return int(_gsettings_get("org.gnome.shell.extensions.dash-to-dock", "dash-max-icon-size") or "48")
    except ValueError:
        return 48


def set_top_bar_clock_seconds(enabled: bool) -> bool:
    """Affiche les secondes dans l'horloge de la barre supérieure."""
    val = "true" if enabled else "false"
    return _gsettings_set("org.gnome.desktop.interface", "clock-show-seconds", val)


def set_top_bar_show_date(enabled: bool) -> bool:
    """Affiche la date dans la barre supérieure."""
    val = "true" if enabled else "false"
    return _gsettings_set("org.gnome.desktop.interface", "clock-show-date", val)


def set_hot_corners(enabled: bool) -> bool:
    """Active/désactive le 'coin actif' (Activities) en haut à gauche."""
    val = "true" if enabled else "false"
    return _gsettings_set("org.gnome.desktop.interface", "enable-hot-corners", val)


# ── Polices ──

def set_font(name: str, size: int) -> bool:
    return _gsettings_set("org.gnome.desktop.interface", "font-name", f"{name} {size}")


def get_current_font() -> tuple[str, int]:
    font = _gsettings_get("org.gnome.desktop.interface", "font-name")
    if font:
        parts = font.rsplit(" ", 1)
        if len(parts) == 2:
            try:
                return (parts[0], int(parts[1]))
            except ValueError:
                pass
    return ("Ubuntu", 11)


# ── Application globale ──

def apply_ubuntu_custom(config: dict) -> dict:
    """Applique la configuration depuis un dictionnaire (ex: config.json)."""
    uc = config.get("ubuntu_custom", {}) or {}
    result = {
        "theme": False, "icons": False, "font": False, "wallpaper": False,
        "animations": False, "dock": False,
    }

    if uc.get("gtk_theme"):
        result["theme"] = set_gtk_theme(uc["gtk_theme"])
    if uc.get("icon_theme"):
        result["icons"] = set_icon_theme(uc["icon_theme"])
    if uc.get("font_name") and uc.get("font_size"):
        result["font"] = set_font(str(uc["font_name"]), int(uc["font_size"]))
    if uc.get("wallpaper"):
        result["wallpaper"] = set_wallpaper(uc["wallpaper"])
    
    # Tweaks
    if "animations" in uc:
        result["animations"] = set_animations_enabled(uc["animations"])
    if "dock_size" in uc:
        result["dock"] = set_dock_icon_size(uc["dock_size"])

    return result
