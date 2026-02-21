"""Affinity — Daemon de protection temps réel.

Tourne en arrière-plan même quand l'interface est fermée.
Surveille : fichiers, périphériques USB, connexions réseau suspectes,
programmes au démarrage, utilisation anormale CPU/RAM.

Created by l-vs — Affinity Protection Daemon v1
"""

import json
import logging
import os
import signal
import sys
import threading
import time
from pathlib import Path

# Setup logging
LOG_DIR = Path.home() / ".affinity"
LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=str(LOG_DIR / "daemon.log"),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("affinity-daemon")

PID_FILE = LOG_DIR / "daemon.pid"
STATUS_FILE = LOG_DIR / "daemon_status.json"


class AffinityDaemon:
    """Daemon de protection temps réel Affinity."""

    def __init__(self):
        self.running = False
        self._threads: list[threading.Thread] = []
        self._alert_callbacks: list = []
        self._stats = {
            "started_at": None,
            "files_watched": 0,
            "threats_blocked": 0,
            "scans_completed": 0,
            "last_scan": None,
        }

    def start(self) -> None:
        """Démarre le daemon."""
        if self.running:
            return
        self.running = True
        self._stats["started_at"] = time.time()
        self._write_pid()
        self._update_status("running")
        logger.info("Affinity Daemon démarré")

        # Thread 1: File watcher
        t1 = threading.Thread(target=self._run_file_watcher, daemon=True, name="file_watcher")
        t1.start()
        self._threads.append(t1)

        # Thread 2: Device watcher
        t2 = threading.Thread(target=self._run_device_watcher, daemon=True, name="device_watcher")
        t2.start()
        self._threads.append(t2)

        # Thread 3: Network monitor (check every 60s)
        t3 = threading.Thread(target=self._run_network_monitor, daemon=True, name="network_monitor")
        t3.start()
        self._threads.append(t3)

        # Thread 4: Startup checker (every 5min)
        t4 = threading.Thread(target=self._run_startup_checker, daemon=True, name="startup_checker")
        t4.start()
        self._threads.append(t4)

        # Thread 5: Resource anomaly detector (every 30s)
        t5 = threading.Thread(target=self._run_resource_monitor, daemon=True, name="resource_monitor")
        t5.start()
        self._threads.append(t5)

    def stop(self) -> None:
        """Arrête le daemon."""
        self.running = False
        self._update_status("stopped")
        self._remove_pid()
        logger.info("Affinity Daemon arrêté")

    def _write_pid(self) -> None:
        PID_FILE.write_text(str(os.getpid()))

    def _remove_pid(self) -> None:
        PID_FILE.unlink(missing_ok=True)

    def _update_status(self, state: str) -> None:
        try:
            status = {
                "state": state,
                "pid": os.getpid(),
                "stats": self._stats,
                "timestamp": time.time(),
            }
            STATUS_FILE.write_text(json.dumps(status, indent=2))
        except Exception:
            pass

    def _log_alert(self, severity: str, title: str, details: str = "") -> None:
        """Log une alerte et notifie si callbacks configurés."""
        logger.warning(f"[{severity.upper()}] {title}: {details}")
        try:
            from database import log_event
            log_event("security", title, details, severity=severity)
        except Exception:
            pass
        # Desktop notification
        try:
            import subprocess
            subprocess.Popen(
                ["notify-send", "-u", "critical" if severity == "critical" else "normal",
                 f"Affinity — {title}", details[:200]],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass

    # ── Watchers ──

    def _run_file_watcher(self) -> None:
        """Surveille les dossiers sensibles pour les nouveaux fichiers."""
        try:
            from core.file_watcher import start_file_watcher
        except ImportError:
            logger.warning("watchdog non disponible — surveillance fichiers désactivée")
            return

        def on_new_file(filepath: str):
            self._stats["files_watched"] += 1
            try:
                from core.security_engine import analyze_file
                result = analyze_file(filepath)
                if result.get("verdict") not in ("clean", None):
                    self._stats["threats_blocked"] += 1
                    self._log_alert(
                        result.get("severity", "warning"),
                        f"Fichier suspect détecté : {Path(filepath).name}",
                        f"Score: {result.get('score', 0)} — {', '.join(result.get('reasons', [])[:3])}",
                    )
                    # Auto-quarantine si dangerous
                    if result.get("verdict") == "dangerous":
                        try:
                            from core.quarantine import quarantine_file
                            quarantine_file(filepath, "Auto-quarantaine daemon", result)
                            logger.info(f"Fichier mis en quarantaine : {filepath}")
                        except Exception as e:
                            logger.error(f"Quarantaine échouée : {e}")
            except Exception as e:
                logger.error(f"Erreur analyse {filepath}: {e}")

        ok = start_file_watcher(on_new_file=on_new_file)
        if ok:
            logger.info("Surveillance fichiers active")
        while self.running:
            time.sleep(1)

    def _run_device_watcher(self) -> None:
        """Surveille les connexions USB."""
        try:
            from core.device_watcher import start_device_watcher, find_storage_mountpoint
        except ImportError:
            logger.warning("pyudev non disponible — surveillance USB désactivée")
            return

        def on_usb_added(info):
            name = info.get("name", "Périphérique inconnu")
            self._log_alert("info", f"Périphérique connecté : {name}")
            # Auto-scan USB storage
            if info.get("subsystem") == "block" and info.get("devnode"):
                mp = find_storage_mountpoint(info)
                if mp:
                    logger.info(f"Scan USB : {mp}")
                    try:
                        from core.security_engine import scan_usb_device
                        threats = list(scan_usb_device(mp))
                        threats = [t for t in threats if "_summary" not in t]
                        if threats:
                            self._stats["threats_blocked"] += len(threats)
                            self._log_alert(
                                "critical",
                                f"Menaces trouvées sur USB !",
                                f"{len(threats)} fichier(s) suspect(s) sur {name}",
                            )
                    except Exception as e:
                        logger.error(f"Erreur scan USB : {e}")

        ok = start_device_watcher(on_device_added=on_usb_added)
        if ok:
            logger.info("Surveillance USB active")
        while self.running:
            time.sleep(1)

    def _run_network_monitor(self) -> None:
        """Vérifie les connexions réseau toutes les 60 secondes."""
        while self.running:
            try:
                from core.network_monitor import get_active_connections
                conns = get_active_connections()
                suspicious = [c for c in conns if c.get("status") in ("dangerous", "suspicious")]
                if suspicious:
                    for conn in suspicious[:3]:
                        self._log_alert(
                            "warning" if conn["status"] == "suspicious" else "critical",
                            f"Connexion réseau suspecte — {conn.get('process_name', '?')}",
                            f"{conn.get('remote_addr', '?')}:{conn.get('remote_port', '?')} ({conn.get('reason', '?')})",
                        )
            except Exception as e:
                logger.debug(f"Erreur network monitor : {e}")
            for _ in range(60):
                if not self.running:
                    return
                time.sleep(1)

    def _run_startup_checker(self) -> None:
        """Vérifie les programmes au démarrage toutes les 5 minutes."""
        time.sleep(30)  # Wait a bit at startup
        while self.running:
            try:
                from core.security_engine import analyze_startup_entries
                findings = analyze_startup_entries()
                for finding in findings:
                    self._log_alert(
                        finding.get("severity", "warning"),
                        f"Entrée de démarrage suspecte : {finding.get('type', '?')}",
                        finding.get("reason", ""),
                    )
            except Exception as e:
                logger.debug(f"Erreur startup checker : {e}")
            for _ in range(300):
                if not self.running:
                    return
                time.sleep(1)

    def _run_resource_monitor(self) -> None:
        """Détecte les anomalies de ressources (cryptomining, etc.)."""
        import psutil
        cpu_history = []
        while self.running:
            try:
                cpu = psutil.cpu_percent(interval=3)
                cpu_history.append(cpu)
                if len(cpu_history) > 20:
                    cpu_history.pop(0)
                # Si CPU > 90% pendant plus d'une minute
                if len(cpu_history) >= 20 and all(c > 90 for c in cpu_history[-20:]):
                    # Trouver le processus coupable
                    top_procs = sorted(
                        psutil.process_iter(["name", "cpu_percent"]),
                        key=lambda p: p.info.get("cpu_percent", 0),
                        reverse=True,
                    )[:3]
                    names = [f"{p.info['name']}({p.info.get('cpu_percent', 0):.0f}%)" for p in top_procs]
                    self._log_alert(
                        "warning",
                        "Usage CPU anormalement élevé (>90% pendant 1min+)",
                        f"Top processus : {', '.join(names)}",
                    )
                    cpu_history.clear()

                # RAM warning
                ram = psutil.virtual_memory()
                if ram.percent > 95:
                    self._log_alert(
                        "warning",
                        f"RAM critique : {ram.percent}% utilisé",
                        f"{ram.used / 1e9:.1f}/{ram.total / 1e9:.0f} Go",
                    )

                # Disk warning
                disk = psutil.disk_usage("/")
                if disk.percent > 95:
                    self._log_alert(
                        "warning",
                        f"Disque presque plein : {disk.percent}%",
                        f"{disk.free / 1e9:.1f} Go restants",
                    )
            except Exception:
                pass
            for _ in range(30):
                if not self.running:
                    return
                time.sleep(1)


def get_daemon_status() -> dict:
    """Retourne le statut du daemon."""
    if not STATUS_FILE.exists():
        return {"state": "not_running", "stats": {}}
    try:
        return json.loads(STATUS_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return {"state": "unknown", "stats": {}}


def is_daemon_running() -> bool:
    """Vérifie si le daemon est en cours d'exécution."""
    if not PID_FILE.exists():
        return False
    try:
        pid = int(PID_FILE.read_text().strip())
        os.kill(pid, 0)
        return True
    except (OSError, ValueError):
        PID_FILE.unlink(missing_ok=True)
        return False


# Singleton
_daemon_instance: AffinityDaemon | None = None


def start_daemon() -> AffinityDaemon:
    """Démarre le daemon singleton."""
    global _daemon_instance
    if _daemon_instance and _daemon_instance.running:
        return _daemon_instance
    _daemon_instance = AffinityDaemon()
    _daemon_instance.start()
    return _daemon_instance


def stop_daemon() -> None:
    """Arrête le daemon."""
    global _daemon_instance
    if _daemon_instance:
        _daemon_instance.stop()
        _daemon_instance = None
