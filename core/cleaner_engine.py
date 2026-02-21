"""Affinity — Moteur de nettoyage avancé (niveau CCleaner professionnel).

Fonctionnalités :
  - 15+ catégories de nettoyage (système, navigateurs, IDE, conteneurs)
  - Nettoyage profond navigateurs (Chrome, Firefox, Edge, Brave, Opera, Vivaldi)
  - Gestionnaire de programmes au démarrage
  - Nettoyage paquets orphelins (apt autoremove)
  - Détection fichiers dupliqués et gros fichiers
  - Nettoyage kernels obsolètes
  - Nettoyage révisions Snap
  - Analyse intelligente avec recommandations
  - Estimation du temps de nettoyage
Created by l-vs — Affinity Cleaner Engine v2
"""

import glob
import hashlib
import os
import re
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Callable


def _home() -> Path:
    return Path.home()


# ─────────────────────────────────────────
# CATÉGORIES DE NETTOYAGE (15+)
# ─────────────────────────────────────────

CLEAN_CATEGORIES = [
    {
        "id": "apt_cache",
        "name": "Cache APT",
        "icon": "📦",
        "description": "Paquets .deb téléchargés et mis en cache",
        "paths": ["/var/cache/apt/archives/*.deb", "/var/cache/apt/archives/partial/*"],
        "needs_root": True,
        "safe": True,
        "priority": "high",
        "clean_cmd": ["apt-get", "clean"],
    },
    {
        "id": "tmp",
        "name": "Fichiers temporaires",
        "icon": "📁",
        "description": "Fichiers temporaires système (/tmp, /var/tmp)",
        "paths": ["/tmp", "/var/tmp"],
        "needs_root": True,
        "safe": True,
        "priority": "high",
        "clean_cmd": None,
    },
    {
        "id": "browser_cache",
        "name": "Cache navigateurs",
        "icon": "🌐",
        "description": "Chrome, Firefox, Edge, Brave, Opera, Vivaldi, Chromium",
        "paths": [
            str(_home() / ".cache/google-chrome/Default/Cache"),
            str(_home() / ".cache/google-chrome/Default/Code Cache"),
            str(_home() / ".cache/google-chrome/Default/Service Worker/CacheStorage"),
            str(_home() / ".cache/google-chrome/Profile */Cache"),
            str(_home() / ".cache/mozilla/firefox"),
            str(_home() / ".mozilla/firefox/*/cache2"),
            str(_home() / ".cache/chromium/Default/Cache"),
            str(_home() / ".cache/chromium/Profile */Cache"),
            str(_home() / ".cache/microsoft-edge/Default/Cache"),
            str(_home() / ".cache/microsoft-edge/Default/Code Cache"),
            str(_home() / ".cache/BraveSoftware/Brave-Browser/Default/Cache"),
            str(_home() / ".cache/opera/Default/Cache"),
            str(_home() / ".cache/vivaldi/Default/Cache"),
        ],
        "needs_root": False,
        "safe": True,
        "priority": "high",
        "clean_cmd": None,
    },
    {
        "id": "browser_history",
        "name": "Historique navigateurs",
        "icon": "🔍",
        "description": "Données de navigation, cookies, sessions expirées",
        "paths": [
            str(_home() / ".cache/google-chrome/Default/GPUCache"),
            str(_home() / ".cache/google-chrome/Default/ShaderCache"),
            str(_home() / ".cache/mozilla/firefox/*/OfflineCache"),
            str(_home() / ".cache/microsoft-edge/Default/GPUCache"),
        ],
        "needs_root": False,
        "safe": True,
        "priority": "medium",
        "clean_cmd": None,
    },
    {
        "id": "logs",
        "name": "Journaux système",
        "icon": "📋",
        "description": "Anciens fichiers journaux compressés et rotationnés",
        "paths": ["/var/log/*.gz", "/var/log/*.old", "/var/log/*.1", "/var/log/*.2*",
                  "/var/log/**/*.gz", "/var/log/**/*.old"],
        "needs_root": True,
        "safe": True,
        "priority": "high",
        "clean_cmd": None,
    },
    {
        "id": "journal",
        "name": "Journal systemd",
        "icon": "📰",
        "description": "Journaux systemd de plus de 3 jours",
        "paths": ["/var/log/journal/*/*"],
        "needs_root": True,
        "safe": True,
        "priority": "medium",
        "clean_cmd": ["journalctl", "--vacuum-time=3d"],
    },
    {
        "id": "thumbnails",
        "name": "Miniatures",
        "icon": "🖼",
        "description": "Cache de vignettes d'images et vidéos",
        "paths": [
            str(_home() / ".cache/thumbnails"),
            str(_home() / ".thumbnails"),
        ],
        "needs_root": False,
        "safe": True,
        "priority": "medium",
        "clean_cmd": None,
    },
    {
        "id": "trash",
        "name": "Poubelle",
        "icon": "🗑",
        "description": "Fichiers supprimés mais pas encore vidés",
        "paths": [
            str(_home() / ".local/share/Trash/files"),
            str(_home() / ".local/share/Trash/info"),
        ],
        "needs_root": False,
        "safe": False,
        "priority": "high",
        "clean_cmd": None,
    },
    {
        "id": "snap_cache",
        "name": "Cache Snap",
        "icon": "📸",
        "description": "Cache des applications Snap",
        "paths": [str(_home() / "snap/*/common/.cache")],
        "needs_root": False,
        "safe": True,
        "priority": "medium",
        "clean_cmd": None,
    },
    {
        "id": "flatpak_cache",
        "name": "Cache Flatpak",
        "icon": "📦",
        "description": "Cache des applications Flatpak",
        "paths": [str(_home() / ".var/app/*/cache"), str(_home() / ".var/app/*/cache/*")],
        "needs_root": False,
        "safe": True,
        "priority": "medium",
        "clean_cmd": None,
    },
    {
        "id": "crash_reports",
        "name": "Rapports de crash",
        "icon": "💥",
        "description": "Rapports d'erreurs système et apport",
        "paths": ["/var/crash/*.crash", "/var/crash/*.upload",
                  str(_home() / ".local/share/apport/crash-reports/*")],
        "needs_root": True,
        "safe": True,
        "priority": "medium",
        "clean_cmd": None,
    },
    {
        "id": "pip_cache",
        "name": "Cache pip",
        "icon": "🐍",
        "description": "Cache du gestionnaire de paquets Python",
        "paths": [str(_home() / ".cache/pip")],
        "needs_root": False,
        "safe": True,
        "priority": "low",
        "clean_cmd": None,
    },
    {
        "id": "npm_cache",
        "name": "Cache npm/yarn",
        "icon": "📦",
        "description": "Cache des gestionnaires de paquets Node.js",
        "paths": [
            str(_home() / ".cache/yarn"),
            str(_home() / ".npm/_cacache"),
        ],
        "needs_root": False,
        "safe": True,
        "priority": "low",
        "clean_cmd": None,
    },
    {
        "id": "ide_cache",
        "name": "Cache IDE & dev",
        "icon": "💻",
        "description": "VS Code, JetBrains, etc.",
        "paths": [
            str(_home() / ".config/Code/Cache"),
            str(_home() / ".config/Code/CachedData"),
            str(_home() / ".config/Code/CachedExtensions"),
            str(_home() / ".config/Code/CachedExtensionVSIXs"),
            str(_home() / ".cache/JetBrains"),
            str(_home() / ".cache/sublime-text"),
        ],
        "needs_root": False,
        "safe": True,
        "priority": "low",
        "clean_cmd": None,
    },
    {
        "id": "old_kernels",
        "name": "Anciens kernels",
        "icon": "🐧",
        "description": "Noyaux Linux obsolètes (garde le plus récent)",
        "paths": [],
        "needs_root": True,
        "safe": True,
        "priority": "high",
        "clean_cmd": None,
        "custom_scan": True,
    },
    {
        "id": "orphan_packages",
        "name": "Paquets orphelins",
        "icon": "🔧",
        "description": "Dépendances qui ne sont plus nécessaires",
        "paths": [],
        "needs_root": True,
        "safe": True,
        "priority": "medium",
        "clean_cmd": ["apt-get", "autoremove", "-y"],
        "custom_scan": True,
    },
]


# ─────────────────────────────────────────
# UTILITAIRES
# ─────────────────────────────────────────

def _get_dir_size(path: Path) -> int:
    total = 0
    try:
        for entry in path.rglob("*"):
            if entry.is_file():
                try:
                    total += entry.stat().st_size
                except OSError:
                    pass
    except OSError:
        pass
    return total


def _get_file_size(path: str) -> int:
    try:
        return os.path.getsize(path)
    except OSError:
        return 0


def format_size(size_bytes: int) -> str:
    if size_bytes >= 1024 * 1024 * 1024:
        return f"{size_bytes / (1024**3):.1f} Go"
    if size_bytes >= 1024 * 1024:
        return f"{size_bytes / (1024**2):.0f} Mo"
    if size_bytes >= 1024:
        return f"{size_bytes / 1024:.0f} Ko"
    return f"{size_bytes} o"


def _run_privileged(args: list[str]) -> bool:
    try:
        subprocess.run(["pkexec"] + args, capture_output=True, timeout=120, check=False)
        return True
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


# ─────────────────────────────────────────
# SCANS SPÉCIAUX
# ─────────────────────────────────────────

def _scan_old_kernels() -> dict:
    """Détecte les anciens kernels Linux installés."""
    total = 0
    files = []
    try:
        r = subprocess.run(
            ["dpkg", "--list", "linux-image-*"],
            capture_output=True, text=True, timeout=15,
        )
        if r.returncode == 0:
            current_kernel = subprocess.run(
                ["uname", "-r"], capture_output=True, text=True, timeout=5
            ).stdout.strip()
            for line in r.stdout.split("\n"):
                if line.startswith("ii") and "linux-image-" in line:
                    parts = line.split()
                    if len(parts) >= 3:
                        pkg = parts[1]
                        # Ne pas toucher au kernel actuel
                        if current_kernel not in pkg and "generic" not in pkg.split("-")[-1]:
                            try:
                                size_r = subprocess.run(
                                    ["dpkg-query", "-W", "--showformat=${Installed-Size}", pkg],
                                    capture_output=True, text=True, timeout=5,
                                )
                                size = int(size_r.stdout.strip() or "0") * 1024  # dpkg gives kB
                            except Exception:
                                size = 200 * 1024 * 1024  # Estimate
                            total += size
                            files.append({"path": f"package:{pkg}", "size": size})
    except Exception:
        pass
    return {"total": total, "files": files}


def _scan_orphan_packages() -> dict:
    """Détecte les paquets orphelins via apt autoremove."""
    total = 0
    files = []
    try:
        r = subprocess.run(
            ["apt-get", "-s", "autoremove"],
            capture_output=True, text=True, timeout=30,
        )
        if r.returncode == 0:
            lines = r.stdout.split("\n")
            for line in lines:
                if "freed" in line.lower():
                    m = re.search(r"([\d,.]+)\s*(kB|MB|Go|GB)", line, re.I)
                    if m:
                        val = float(m.group(1).replace(",", "."))
                        unit = m.group(2).upper()
                        if unit == "KB":
                            total = int(val * 1024)
                        elif unit in ("MB", "MO"):
                            total = int(val * 1024 * 1024)
                        elif unit in ("GB", "GO"):
                            total = int(val * 1024 * 1024 * 1024)
                # Count packages
                if "The following packages will be REMOVED" in line:
                    # Next lines are package names
                    pass
            if total > 0:
                files.append({"path": "apt:autoremove", "size": total})
    except Exception:
        pass
    return {"total": total, "files": files}


# ─────────────────────────────────────────
# SCAN & NETTOYAGE
# ─────────────────────────────────────────

def scan_category(cat: dict) -> dict:
    """Scanne une catégorie et retourne taille + fichiers."""
    # Custom scans
    if cat.get("custom_scan"):
        if cat["id"] == "old_kernels":
            return _scan_old_kernels()
        elif cat["id"] == "orphan_packages":
            return _scan_orphan_packages()

    total = 0
    files: list[dict] = []
    for pattern in cat["paths"]:
        expanded = os.path.expanduser(pattern)
        for path_str in glob.glob(expanded, recursive=True):
            p = Path(path_str)
            if p.is_file():
                size = _get_file_size(path_str)
                total += size
                files.append({"path": path_str, "size": size})
            elif p.is_dir():
                size = _get_dir_size(p)
                total += size
                files.append({"path": path_str, "size": size})
    return {"total": total, "files": files}


def scan_all(progress_callback: Callable[[str, int, int], None] | None = None) -> list[dict]:
    """Scanne toutes les catégories."""
    results = []
    total_cats = len(CLEAN_CATEGORIES)
    for i, cat in enumerate(CLEAN_CATEGORIES):
        if progress_callback:
            progress_callback(cat["name"], i + 1, total_cats)
        scan_result = scan_category(cat)
        results.append({
            **cat,
            "size_bytes": scan_result["total"],
            "files": scan_result["files"],
        })
    return results


def clean_category(cat: dict, progress_callback: Callable[[int, int], None] | None = None) -> int:
    """Nettoie une catégorie. Retourne les octets libérés."""
    freed = 0

    # Special commands
    if cat.get("clean_cmd"):
        scan_before = scan_category(cat)
        freed = scan_before["total"]
        if cat.get("needs_root"):
            _run_privileged(cat["clean_cmd"])
        else:
            try:
                subprocess.run(cat["clean_cmd"], capture_output=True, timeout=120, check=False)
            except Exception:
                pass
        return freed

    # Old kernels
    if cat["id"] == "old_kernels":
        scan_result = _scan_old_kernels()
        for f in scan_result["files"]:
            pkg = f["path"].replace("package:", "")
            _run_privileged(["apt-get", "purge", "-y", pkg])
            freed += f["size"]
        return freed

    # Standard file cleanup
    scan_result = scan_category(cat)
    files = scan_result["files"]
    total_files = len(files)
    for i, f_info in enumerate(files):
        path = f_info["path"]
        size = f_info["size"]
        p = Path(path)
        try:
            if p.is_file():
                if cat.get("needs_root"):
                    _run_privileged(["rm", "-f", str(p)])
                else:
                    os.remove(path)
                freed += size
            elif p.is_dir():
                import shutil
                if cat.get("needs_root"):
                    _run_privileged(["rm", "-rf", str(p)])
                else:
                    shutil.rmtree(path, ignore_errors=True)
                freed += size
        except OSError:
            pass
        if progress_callback:
            progress_callback(i + 1, total_files)
    return freed


# ─────────────────────────────────────────
# PROGRAMMES AU DÉMARRAGE
# ─────────────────────────────────────────

def get_startup_programs() -> list[dict]:
    """Liste les programmes configurés pour démarrer automatiquement."""
    programs = []

    # XDG autostart
    autostart_dirs = [
        Path.home() / ".config" / "autostart",
        Path("/etc/xdg/autostart"),
    ]
    for adir in autostart_dirs:
        if not adir.exists():
            continue
        for f in adir.glob("*.desktop"):
            try:
                content = f.read_text(encoding="utf-8", errors="ignore")
                name = ""
                exec_cmd = ""
                hidden = False
                for line in content.split("\n"):
                    if line.startswith("Name="):
                        name = line.split("=", 1)[1].strip()
                    elif line.startswith("Exec="):
                        exec_cmd = line.split("=", 1)[1].strip()
                    elif line.startswith("Hidden=true") or line.startswith("X-GNOME-Autostart-enabled=false"):
                        hidden = True
                programs.append({
                    "name": name or f.stem,
                    "command": exec_cmd[:100],
                    "path": str(f),
                    "enabled": not hidden,
                    "source": "xdg",
                    "user": "user" if "home" in str(adir).lower() else "system",
                })
            except OSError:
                pass

    return programs


def toggle_startup_program(desktop_path: str, enabled: bool) -> bool:
    """Active/désactive un programme au démarrage."""
    p = Path(desktop_path)
    if not p.exists():
        return False
    try:
        content = p.read_text(encoding="utf-8")
        lines = content.split("\n")
        new_lines = []
        found = False
        for line in lines:
            if line.startswith("X-GNOME-Autostart-enabled="):
                new_lines.append(f"X-GNOME-Autostart-enabled={'true' if enabled else 'false'}")
                found = True
            elif line.startswith("Hidden="):
                new_lines.append(f"Hidden={'false' if enabled else 'true'}")
                found = True
            else:
                new_lines.append(line)
        if not found:
            # Add the key after [Desktop Entry]
            idx = next((i for i, l in enumerate(new_lines) if "[Desktop Entry]" in l), 0)
            new_lines.insert(idx + 1, f"X-GNOME-Autostart-enabled={'true' if enabled else 'false'}")
        p.write_text("\n".join(new_lines), encoding="utf-8")
        return True
    except OSError:
        return False


# ─────────────────────────────────────────
# DOUBLONS & GROS FICHIERS
# ─────────────────────────────────────────

def find_duplicates(
    roots: list[str | Path],
    min_size_bytes: int = 1024 * 1024,
    progress_callback=None,
    cancel_flag=None,
) -> list[dict]:
    """Trouve les fichiers en double (même taille → MD5)."""
    roots = [Path(r) for r in roots if Path(r).exists()]
    by_size: dict[int, list[str]] = defaultdict(list)
    total_files = 0
    for rp in roots:
        if cancel_flag and cancel_flag.is_set():
            break
        try:
            for f in rp.rglob("*"):
                if cancel_flag and cancel_flag.is_set():
                    break
                if not f.is_file():
                    continue
                try:
                    sz = f.stat().st_size
                except OSError:
                    continue
                if sz < min_size_bytes:
                    continue
                by_size[sz].append(str(f))
                total_files += 1
        except (OSError, PermissionError):
            pass

    duplicates = []
    processed = 0
    for size, paths in by_size.items():
        if len(paths) < 2:
            continue
        if cancel_flag and cancel_flag.is_set():
            break
        by_hash: dict[str, list[str]] = defaultdict(list)
        for fp in paths:
            try:
                h = hashlib.md5()
                with open(fp, "rb") as f:
                    for chunk in iter(lambda: f.read(65536), b""):
                        h.update(chunk)
                by_hash[h.hexdigest()].append(fp)
            except OSError:
                pass
            processed += 1
            if progress_callback and processed % 50 == 0:
                progress_callback(processed, total_files)
        for h, plist in by_hash.items():
            if len(plist) >= 2:
                duplicates.append({"size": size, "count": len(plist), "paths": plist, "hash": h})
    return duplicates


def find_large_files(
    roots: list[str | Path],
    min_size_bytes: int = 100 * 1024 * 1024,
    top_n: int = 100,
    progress_callback=None,
    cancel_flag=None,
) -> list[dict]:
    """Trouve les N plus gros fichiers."""
    roots = [Path(r) for r in roots if Path(r).exists()]
    candidates: list[tuple[int, str]] = []
    for rp in roots:
        if cancel_flag and cancel_flag.is_set():
            break
        try:
            for f in rp.rglob("*"):
                if cancel_flag and cancel_flag.is_set():
                    break
                if not f.is_file():
                    continue
                try:
                    sz = f.stat().st_size
                except OSError:
                    continue
                if sz >= min_size_bytes:
                    candidates.append((sz, str(f)))
        except (OSError, PermissionError):
            pass
    candidates.sort(key=lambda x: -x[0])
    result = [{"path": p, "size": s} for s, p in candidates[:top_n]]
    if progress_callback:
        progress_callback(len(candidates), top_n)
    return result


# ─────────────────────────────────────────
# RECOMMANDATIONS INTELLIGENTES
# ─────────────────────────────────────────

def get_smart_recommendations() -> list[dict]:
    """Génère des recommandations intelligentes pour libérer de l'espace."""
    recs = []

    # Quick scan of key categories
    for cat in CLEAN_CATEGORIES:
        if cat["safe"] and cat["priority"] in ("high", "medium"):
            try:
                result = scan_category(cat)
                if result["total"] > 50 * 1024 * 1024:  # > 50 Mo
                    recs.append({
                        "category_id": cat["id"],
                        "name": cat["name"],
                        "size_bytes": result["total"],
                        "size_formatted": format_size(result["total"]),
                        "icon": cat["icon"],
                        "safe": cat["safe"],
                        "priority": cat["priority"],
                        "description": cat["description"],
                    })
            except Exception:
                pass

    # Sort by size descending
    recs.sort(key=lambda r: r["size_bytes"], reverse=True)
    return recs


def get_apt_autoremove_size() -> tuple[int, int]:
    """Retourne (taille_en_octets, nb_paquets) pour apt autoremove."""
    try:
        r = subprocess.run(
            ["apt-get", "-s", "autoremove"],
            capture_output=True, text=True, timeout=30,
        )
        if r.returncode != 0:
            return 0, 0
        lines = r.stdout.split("\n")
        pkgs = 0
        size = 0
        for line in lines:
            if "freed" in line.lower() and "kB" in line:
                m = re.search(r"(\d+)\s*kB", line)
                if m:
                    size = int(m.group(1)) * 1024
            if "The following packages will be REMOVED" in line:
                pkgs = len([l for l in lines if l.startswith("  ")]) - 1
        return size, max(0, pkgs)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return 0, 0


def run_apt_autoremove() -> bool:
    return _run_privileged(["apt-get", "autoremove", "-y"])
