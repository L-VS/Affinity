"""Affinity — Surveillance en temps réel des dossiers sensibles (watchdog)."""

import threading
import time
from pathlib import Path

from config import CONFIG_FILE

WATCHED_DIRS = [
    (Path.home() / "Downloads", "high"),
    (Path.home() / "Desktop", "medium"),
    Path("/tmp"),
    (Path.home() / ".config/autostart", "critical"),
    (Path.home() / ".local/share/applications", "high"),
]
IGNORE_SUFFIXES = (".part", ".crdownload", ".tmp", ".temp")
IGNORE_EXT_SMALL = (".txt", ".md", ".log")
MIN_SIZE = 1024  # 1 Ko
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5 Mo
IMAGE_EXT = (".jpg", ".jpeg", ".png", ".gif", ".webp")

_on_new_file_callback = None
_on_autostart_change_callback = None
_observer = None


def _should_analyze(filepath: Path) -> bool:
    """Détermine si un fichier doit être analysé."""
    if filepath.suffix.lower() in IGNORE_SUFFIXES:
        return False
    try:
        size = filepath.stat().st_size
    except OSError:
        return False
    if size < MIN_SIZE:
        return False
    if filepath.suffix.lower() in IGNORE_EXT_SMALL and size < 10 * 1024:
        return False
    if filepath.suffix.lower() in IMAGE_EXT and size > MAX_IMAGE_SIZE:
        return False
    return True


def _on_file_event(event):
    """Callback watchdog."""
    if event.is_directory:
        return
    src = getattr(event, "src_path", None) or getattr(event, "dest_path", None)
    if not src:
        return
    path = Path(src)
    if not path.exists() or not path.is_file():
        return
    time.sleep(0.5)
    if not path.exists():
        return
    try:
        size = path.stat().st_size
        time.sleep(0.3)
        if path.stat().st_size != size:
            return
    except OSError:
        return
    is_autostart = ".config/autostart" in str(path)
    if is_autostart and _on_autostart_change_callback:
        _on_autostart_change_callback(str(path))
    elif _on_new_file_callback and _should_analyze(path):
        _on_new_file_callback(str(path))


def start_file_watcher(
    on_new_file=None,
    on_autostart_change=None,
) -> bool:
    """Démarre la surveillance. Retourne True si OK."""
    global _on_new_file_callback, _on_autostart_change_callback, _observer
    _on_new_file_callback = on_new_file
    _on_autostart_change_callback = on_autostart_change
    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler

        class Handler(FileSystemEventHandler):
            def on_created(self, event):
                _on_file_event(event)

            def on_modified(self, event):
                if not event.is_directory:
                    _on_file_event(event)

            def on_moved(self, event):
                if event.dest_path:
                    class E:
                        src_path = event.dest_path
                        is_directory = False
                    _on_file_event(E)

        _observer = Observer()
        for entry in WATCHED_DIRS:
            if isinstance(entry, tuple):
                dirpath, _ = entry
            else:
                dirpath = entry
            if dirpath.exists() and dirpath.is_dir():
                _observer.schedule(Handler(), str(dirpath), recursive=True)
        _observer.start()
        return True
    except ImportError:
        return False


def stop_file_watcher() -> None:
    """Arrête la surveillance."""
    global _observer
    if _observer:
        try:
            _observer.stop()
            _observer.join(timeout=2)
        except Exception:
            pass
        _observer = None
