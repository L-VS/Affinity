"""Affinity — Moteur de sécurité avancé (niveau professionnel).

Fonctionnalités :
  - 50+ règles heuristiques (scripts, PDF, archives, ELF, PE)
  - Analyse entropique (détection obfuscation/packing)
  - Analyse de fichiers ELF (binaires Linux)
  - Intégration ClamAV optionnelle (clamscan)
  - Scan planifié / temps réel / USB / complet
  - Analyse de démarrage (autostart, cron, systemd)
  - Score de confiance multi-critères
  - Base de hashes MalwareBazaar
Created by l-vs — Affinity Security Engine v2
"""

import hashlib
import math
import os
import re
import shutil
import struct
import subprocess
import time
import zipfile
from pathlib import Path
from typing import Callable

from core.hash_database import hash_is_malicious, hash_is_safe, log_scan

# ─────────────────────────────────────────
# RÈGLES HEURISTIQUES (50+ patterns)
# ─────────────────────────────────────────

HEURISTIC_RULES = [
    # === Exécution distante & reverse shells (critique) ===
    (r"curl\s+.*\|\s*(sudo\s+)?bash", 90, "Téléchargement et exécution directe (curl|bash)", "critical"),
    (r"wget\s+.*\|\s*(sudo\s+)?sh", 90, "Téléchargement et exécution directe (wget|sh)", "critical"),
    (r"\/dev\/tcp\/|nc\s+-[el]|ncat\s+-[el]", 90, "Reverse shell / bind shell", "critical"),
    (r"socket\.connect.*subprocess", 85, "Possible reverse shell réseau (Python)", "critical"),
    (r"bash\s+-i\s+>\s*&\s*/dev/tcp", 95, "Reverse shell bash interactif", "critical"),
    (r"python[23]?\s+-c\s+.*import\s+socket", 80, "Reverse shell Python one-liner", "critical"),
    (r"php\s+-r\s+.*fsockopen", 80, "Reverse shell PHP", "critical"),
    (r"perl\s+-e\s+.*socket", 80, "Reverse shell Perl", "critical"),

    # === Suppression / destruction ===
    (r"rm\s+-rf\s+/[^/]", 95, "Suppression récursive de fichiers système", "critical"),
    (r"rm\s+-rf\s+\$HOME|rm\s+-rf\s+~/", 90, "Suppression du dossier utilisateur", "critical"),
    (r"mkfs\.|dd\s+if=/dev/(zero|random)\s+of=/dev/sd", 95, "Effacement de disque", "critical"),
    (r":(){ :\|:& };:", 95, "Fork bomb", "critical"),

    # === Élévation de privilèges ===
    (r"chmod\s+[46]?777\s+/", 60, "Permissions dangereuses sur fichier système", "high"),
    (r"chmod\s+u\+s|chmod\s+4755", 75, "SetUID bit (élévation de privilèges)", "high"),
    (r"sudo\s+-S|echo.*\|\s*sudo", 65, "Passage de mot de passe root en clair", "high"),
    (r"\/etc\/sudoers|visudo", 70, "Modification des droits sudo", "high"),

    # === Persistence & autostart ===
    (r"crontab\s+-", 50, "Modification des tâches planifiées", "medium"),
    (r"autostart|\.config/autostart", 45, "Ajout au démarrage automatique", "medium"),
    (r"systemctl\s+enable|systemd.*service", 50, "Installation de service systemd", "medium"),
    (r"\.bashrc|\.profile|\.bash_profile", 40, "Modification profil shell", "medium"),
    (r"/etc/rc\.local|/etc/init\.d/", 55, "Modification scripts init", "medium"),
    (r"@reboot.*cron", 55, "Tâche cron au redémarrage", "medium"),

    # === Exfiltration de données ===
    (r"(cat|read)\s+/etc/shadow", 80, "Tentative d'accès aux mots de passe", "critical"),
    (r"(cat|read)\s+/etc/passwd", 40, "Lecture du fichier utilisateurs", "medium"),
    (r"authorized_keys", 65, "Modification des clés SSH", "high"),
    (r"history\s+-c|>\s+~/\.bash_history", 55, "Effacement de l'historique", "high"),
    (r"\.ssh/id_(rsa|ed25519|ecdsa)", 60, "Accès aux clés privées SSH", "high"),
    (r"\.gnupg|gpg\s+--export", 50, "Accès aux clés GPG", "medium"),
    (r"/etc/ssl/private|\.pem|\.key", 55, "Accès aux certificats privés", "high"),

    # === Keylogger / Spyware ===
    (r"keyboard\.on_press|pynput|xdotool", 70, "Possible enregistreur de frappe", "high"),
    (r"screenshot|import\s+-window\s+root", 50, "Capture d'écran furtive", "medium"),
    (r"\.xsession-errors|xclip|xsel", 35, "Accès au presse-papier", "low"),
    (r"webcam|/dev/video|cv2\.VideoCapture", 60, "Accès à la webcam", "high"),
    (r"/dev/snd|arecord|pulseaudio.*record", 55, "Enregistrement audio", "medium"),

    # === Code obfusqué ===
    (r"base64\s+-d.*\|\s*(bash|sh)", 85, "Code encodé et exécuté", "critical"),
    (r"eval\s*\(\s*base64|exec\s*\(\s*base64", 80, "Exécution de code encodé base64", "critical"),
    (r"eval\s*\(\s*compile\s*\(", 75, "Compilation et exécution dynamique", "high"),
    (r"\\x[0-9a-f]{2}.*\\x[0-9a-f]{2}.*\\x[0-9a-f]{2}", 60, "Code binaire hex encodé", "medium"),
    (r"exec\s*\(\s*chr\s*\(|eval\s*\(\s*chr\s*\(", 70, "Obfuscation par chr()", "high"),
    (r"zlib\.decompress|gzip\.decompress.*exec", 65, "Code compressé et exécuté", "high"),
    (r"__import__\s*\(\s*['\"]os['\"]\s*\)\s*\.\s*system", 70, "Import dynamique dangereux", "high"),

    # === Exécution non sécurisée ===
    (r"subprocess\.Popen.*shell\s*=\s*True", 65, "Exécution shell non sécurisée", "high"),
    (r"os\.system\s*\(|os\.popen\s*\(", 55, "Appel système direct", "medium"),
    (r"subprocess\.call.*shell.*True", 60, "Appel subprocess non sécurisé", "high"),

    # === Cryptomining ===
    (r"crypto.*miner|xmrig|stratum|nicehash", 85, "Mineur de cryptomonnaie", "critical"),
    (r"coinhive|cryptoloot|coin-hive", 80, "Cryptojacking web", "critical"),

    # === Injection / hooking ===
    (r"\/etc\/ld\.so\.preload|LD_PRELOAD", 75, "Injection de bibliothèque (LD_PRELOAD)", "high"),
    (r"ptrace|process_vm_readv|PTRACE_ATTACH", 65, "Injection de processus (ptrace)", "high"),
    (r"dlopen|ctypes\.CDLL", 45, "Chargement dynamique de bibliothèque", "medium"),

    # === Réseau suspect ===
    (r"dns.*tunnel|iodine|dnscat", 80, "Tunnel DNS", "critical"),
    (r"tor\s|\.onion|socks5", 50, "Utilisation de Tor / réseau anonyme", "medium"),
    (r"proxy.*chain|proxychains", 55, "Chaînage de proxy", "medium"),
]

# Extensions fichiers à haute priorité pour le scan
HIGH_PRIORITY_EXT = {
    ".sh", ".bash", ".zsh", ".py", ".rb", ".pl", ".php",
    ".exe", ".bat", ".cmd", ".ps1", ".vbs", ".js",
    ".deb", ".rpm", ".appimage",
    ".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".rar",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx",
    ".elf", ".so", ".bin",
}

MEDIUM_PRIORITY_EXT = {
    ".conf", ".cfg", ".ini", ".yaml", ".yml", ".json",
    ".service", ".timer", ".desktop",
    ".sql", ".db",
}


# ─────────────────────────────────────────
# MOTEUR D'ANALYSE
# ─────────────────────────────────────────

def compute_sha256(filepath: str | Path, progress_callback=None) -> dict | None:
    """Calcule le SHA256 d'un fichier. Retourne dict ou None si erreur."""
    p = Path(filepath)
    try:
        size = p.stat().st_size
    except OSError:
        return None
    partial = size > 500 * 1024 * 1024
    to_read = min(50 * 1024 * 1024, size) if partial else size
    h = hashlib.sha256()
    read_so_far = 0
    try:
        with open(p, "rb") as f:
            while read_so_far < to_read:
                chunk = f.read(8192)
                if not chunk:
                    break
                h.update(chunk)
                read_so_far += len(chunk)
                if progress_callback:
                    progress_callback(read_so_far, to_read)
    except (PermissionError, FileNotFoundError, OSError):
        return None
    return {"sha256": h.hexdigest(), "partial": partial, "size_bytes": size}


def compute_entropy(data: bytes) -> float:
    """Calcule l'entropie de Shannon d'un bloc de données (0-8)."""
    if not data:
        return 0.0
    freq = [0] * 256
    for byte in data:
        freq[byte] += 1
    length = len(data)
    entropy = 0.0
    for count in freq:
        if count > 0:
            p = count / length
            entropy -= p * math.log2(p)
    return entropy


def get_file_type(filepath: str | Path) -> str:
    """Détecte le type du fichier via magic bytes + extension."""
    p = Path(filepath)
    suf = p.suffix.lower()
    try:
        with open(p, "rb") as f:
            head = f.read(512)
    except OSError:
        return "unknown"

    if head.startswith(b"%PDF"):
        return "pdf"
    if head[:4] == b"PK\x03\x04":
        return "zip"
    if head[:4] == b"\x7fELF":
        return "elf"
    if head[:2] == b"MZ":
        return "pe"
    if head.startswith(b"#!/bin/") or head.startswith(b"#!/usr/bin/"):
        return "script"
    if b"python" in head[:50].lower():
        return "script"
    if head[:8] == b"\x89PNG\r\n\x1a\n":
        return "image"
    if head[:4] == b"\x1f\x8b\x08\x00":
        return "gzip"
    if head[:6] in (b"GIF87a", b"GIF89a"):
        return "image"
    if head[:2] in (b"\xff\xd8",):
        return "image"

    ext_map = {
        ".sh": "shell", ".bash": "shell", ".zsh": "shell",
        ".py": "python", ".rb": "ruby", ".pl": "perl", ".php": "php",
        ".exe": "exe", ".bat": "bat", ".cmd": "cmd", ".ps1": "ps1",
        ".deb": "deb", ".appimage": "appimage",
        ".tar": "archive", ".gz": "archive", ".rar": "archive",
        ".7z": "archive", ".bz2": "archive", ".xz": "archive",
        ".service": "systemd", ".timer": "systemd",
        ".desktop": "desktop",
    }
    return ext_map.get(suf, "unknown")


def analyze_elf(filepath: str | Path) -> list[dict]:
    """Analyse spécifique pour les fichiers ELF (binaires Linux)."""
    findings = []
    p = Path(filepath)
    try:
        with open(p, "rb") as f:
            head = f.read(64)
        if head[:4] != b"\x7fELF":
            return findings

        # Vérifier si stripped (pas de symboles)
        try:
            r = subprocess.run(
                ["file", str(p)], capture_output=True, text=True, timeout=5
            )
            output = r.stdout or ""
            if "not stripped" not in output and "stripped" in output:
                findings.append({
                    "rule": "elf_stripped", "reason": "Binaire supprimé de ses symboles (obfuscation)",
                    "score_added": 25, "severity": "medium"
                })
            if "statically linked" in output:
                findings.append({
                    "rule": "elf_static", "reason": "Lié statiquement (typique de malware portable)",
                    "score_added": 30, "severity": "medium"
                })
        except Exception:
            pass

        # Sections suspectes
        try:
            r = subprocess.run(
                ["readelf", "-S", str(p)], capture_output=True, text=True, timeout=10
            )
            sections = r.stdout or ""
            if ".upx" in sections.lower() or "UPX" in sections:
                findings.append({
                    "rule": "elf_packed_upx", "reason": "Binaire UPX packed (obfuscation)",
                    "score_added": 40, "severity": "high"
                })
        except Exception:
            pass

        # High entropy check for binary
        try:
            with open(p, "rb") as f:
                data = f.read(min(1024 * 1024, p.stat().st_size))
            ent = compute_entropy(data)
            if ent > 7.5:
                findings.append({
                    "rule": "elf_high_entropy",
                    "reason": f"Entropie très élevée ({ent:.2f}/8) — possible packing/chiffrement",
                    "score_added": 35, "severity": "high"
                })
            elif ent > 7.0:
                findings.append({
                    "rule": "elf_medium_entropy",
                    "reason": f"Entropie élevée ({ent:.2f}/8) — possible obfuscation",
                    "score_added": 15, "severity": "medium"
                })
        except Exception:
            pass

        # Check for suspicious strings
        try:
            r = subprocess.run(
                ["strings", "-n", "6", str(p)],
                capture_output=True, text=True, timeout=10
            )
            strings_out = r.stdout or ""
            suspicious_strings = ["reverse", "shell", "payload", "exploit", "backdoor",
                                  "rootkit", "keylog", "meterpreter", "c2_server"]
            for sus in suspicious_strings:
                if sus in strings_out.lower():
                    findings.append({
                        "rule": f"elf_sus_{sus}", "reason": f"Chaîne suspecte trouvée : '{sus}'",
                        "score_added": 40, "severity": "high"
                    })
                    break  # Only add once for first match
        except Exception:
            pass

    except OSError:
        pass
    return findings


def analyze_startup_entries() -> list[dict]:
    """Analyse les programmes au démarrage pour détecter les anomalies."""
    findings = []

    # 1. XDG autostart
    autostart = Path.home() / ".config" / "autostart"
    if autostart.exists():
        for f in autostart.iterdir():
            if f.suffix == ".desktop":
                try:
                    content = f.read_text()
                    if "Exec=" in content:
                        exec_line = [l for l in content.split("\n") if l.startswith("Exec=")]
                        if exec_line:
                            cmd = exec_line[0].split("=", 1)[1]
                            if any(s in cmd.lower() for s in ["bash -c", "sh -c", "python -c", "curl", "wget"]):
                                findings.append({
                                    "type": "autostart",
                                    "path": str(f),
                                    "command": cmd[:100],
                                    "severity": "high",
                                    "reason": "Commande suspecte au démarrage",
                                })
                except OSError:
                    pass

    # 2. Crontab utilisateur
    try:
        r = subprocess.run(["crontab", "-l"], capture_output=True, text=True, timeout=5)
        if r.returncode == 0 and r.stdout:
            for line in r.stdout.split("\n"):
                line = line.strip()
                if line and not line.startswith("#"):
                    if any(s in line.lower() for s in ["curl", "wget", "bash -c", "nc ", "ncat"]):
                        findings.append({
                            "type": "cron",
                            "command": line[:100],
                            "severity": "high",
                            "reason": "Tâche cron suspecte",
                        })
    except Exception:
        pass

    # 3. User systemd services
    user_services = Path.home() / ".config" / "systemd" / "user"
    if user_services.exists():
        for f in user_services.rglob("*.service"):
            try:
                content = f.read_text()
                if "ExecStart=" in content:
                    exec_line = [l for l in content.split("\n") if "ExecStart=" in l]
                    if exec_line:
                        cmd = exec_line[0].split("=", 1)[1]
                        if any(s in cmd.lower() for s in ["curl", "wget", "/tmp/", "bash -c"]):
                            findings.append({
                                "type": "systemd",
                                "path": str(f),
                                "command": cmd[:100],
                                "severity": "high",
                                "reason": "Service systemd utilisateur suspect",
                            })
            except OSError:
                pass

    return findings


def scan_with_clamav(filepath: str | Path) -> dict | None:
    """Scan un fichier avec ClamAV si disponible. Retourne résultat ou None."""
    if not shutil.which("clamscan"):
        return None
    try:
        r = subprocess.run(
            ["clamscan", "--no-summary", "--infected", str(filepath)],
            capture_output=True, text=True, timeout=60,
        )
        output = (r.stdout or "").strip()
        if r.returncode == 1 and output:
            # ClamAV found something
            parts = output.split(":")
            threat_name = parts[-1].strip().replace("FOUND", "").strip() if parts else "Unknown"
            return {
                "engine": "ClamAV",
                "result": "infected",
                "threat_name": threat_name,
                "score": 95,
            }
        return {"engine": "ClamAV", "result": "clean", "threat_name": None, "score": 0}
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None


def is_clamav_available() -> bool:
    """Vérifie si ClamAV est installé et la base à jour."""
    return shutil.which("clamscan") is not None


# ─────────────────────────────────────────
# ANALYSE COMPLÈTE D'UN FICHIER
# ─────────────────────────────────────────

def analyze_heuristic(filepath: str | Path) -> dict:
    """Analyse heuristique avancée avec score multi-critères."""
    start = time.time()
    p = Path(filepath)
    ft = get_file_type(filepath)
    score = 0
    matches = []

    try:
        content = p.read_bytes()
    except OSError:
        return {"score": 0, "verdict": "clean", "matches": [], "file_type": ft, "analysis_time_ms": 0}

    size = len(content)

    # === Entropie globale ===
    if size > 64:
        sample = content[:min(1024 * 1024, size)]
        ent = compute_entropy(sample)
        if ent > 7.5 and ft not in ("image", "archive", "zip", "gzip"):
            score += 30
            matches.append({"rule": "high_entropy", "reason": f"Entropie élevée ({ent:.2f}/8) → possible obfuscation", "score_added": 30})
        elif ent > 7.0 and ft in ("script", "shell", "python"):
            score += 15
            matches.append({"rule": "medium_entropy_script", "reason": f"Entropie élevée pour un script ({ent:.2f}/8)", "score_added": 15})

    # === Règles heuristiques textuelles ===
    text_content = content[:1024 * 1024].decode("utf-8", errors="ignore") if size <= 10 * 1024 * 1024 else ""
    if text_content:
        for pattern, pts, reason, severity in HEURISTIC_RULES:
            if re.search(pattern, text_content, re.IGNORECASE):
                score += pts
                matches.append({"rule": pattern[:40], "reason": reason, "score_added": pts, "severity": severity})

    # === PDF ===
    if ft == "pdf":
        pdf_checks = [
            (b"/JS", 60, "JavaScript embarqué dans PDF"),
            (b"/AA", 55, "Action automatique dans PDF"),
            (b"/Launch", 80, "Lancement d'exécutable depuis PDF"),
            (b"/EmbeddedFile", 40, "Fichier embarqué dans PDF"),
            (b"/RichMedia", 35, "Contenu multimédia embarqué"),
            (b"/OpenAction", 50, "Action automatique à l'ouverture"),
            (b"/AcroForm", 25, "Formulaire interactif (peut contenir du code)"),
        ]
        for marker, pts, reason in pdf_checks:
            if marker in content:
                score += pts
                matches.append({"rule": f"pdf_{marker.decode()}", "reason": reason, "score_added": pts, "severity": "high"})

    # === Archives ===
    if ft in ("zip", "archive"):
        try:
            with zipfile.ZipFile(p, "r") as z:
                names = z.namelist()
                for name in names:
                    if ".." in name:
                        score += 75
                        matches.append({"rule": "zip_slip", "reason": "Path traversal dans archive", "score_added": 75, "severity": "critical"})
                        break
                exe_in_zip = [n for n in names if re.search(r"\.(exe|bat|cmd|ps1|vbs|scr|pif)$", n, re.I)]
                if exe_in_zip:
                    score += 35
                    matches.append({"rule": "hidden_exe", "reason": f"Exécutable caché dans archive : {exe_in_zip[0]}", "score_added": 35, "severity": "high"})
                # Double extension (fichier.pdf.exe)
                double_ext = [n for n in names if re.search(r"\.\w+\.(exe|bat|cmd|ps1)$", n, re.I)]
                if double_ext:
                    score += 50
                    matches.append({"rule": "double_ext", "reason": f"Double extension suspecte : {double_ext[0]}", "score_added": 50, "severity": "high"})
        except (zipfile.BadZipFile, OSError):
            pass

    # === ELF binaires ===
    if ft == "elf":
        elf_findings = analyze_elf(p)
        for finding in elf_findings:
            score += finding.get("score_added", 0)
            matches.append(finding)

    # === Desktop files ===
    if ft == "desktop" or p.suffix == ".desktop":
        if b"Exec=" in content:
            exec_lines = [l for l in text_content.split("\n") if l.strip().startswith("Exec=")]
            for el in exec_lines:
                cmd = el.split("=", 1)[1] if "=" in el else ""
                if any(s in cmd.lower() for s in ["curl", "wget", "bash -c", "python -c", "/tmp/"]):
                    score += 55
                    matches.append({"rule": "desktop_suspicious_exec", "reason": f"Fichier .desktop avec commande suspecte", "score_added": 55, "severity": "high"})

    # === Fichiers dans /tmp exécutables ===
    try:
        if "/tmp/" in str(p) or "/var/tmp/" in str(p):
            if os.access(p, os.X_OK):
                score += 20
                matches.append({"rule": "exec_in_tmp", "reason": "Fichier exécutable dans /tmp", "score_added": 20, "severity": "medium"})
    except OSError:
        pass

    # === Limiter le score ===
    score = min(100, score)
    if score >= 80:
        verdict = "dangerous"
    elif score >= 50:
        verdict = "suspicious"
    elif score >= 25:
        verdict = "attention"
    else:
        verdict = "clean"

    return {
        "score": score,
        "verdict": verdict,
        "matches": matches,
        "file_type": ft,
        "analysis_time_ms": int((time.time() - start) * 1000),
    }


def analyze_file(filepath: str | Path, deep: bool = False) -> dict:
    """Analyse complète d'un fichier (hash + ClamAV + heuristique + ELF)."""
    start = time.time()
    p = Path(filepath)
    if not p.exists() or not p.is_file():
        return {
            "filepath": str(p), "verdict": "clean", "severity": "none",
            "source": "error", "reasons": ["Fichier inaccessible"],
        }

    hash_result = compute_sha256(p)
    if not hash_result:
        return {
            "filepath": str(p), "filename": p.name, "verdict": "clean",
            "severity": "none", "source": "error",
            "reasons": ["Impossible de calculer le hash"],
        }

    sha256 = hash_result["sha256"]
    size_bytes = hash_result["size_bytes"]

    # 1. Whitelist
    if hash_is_safe(sha256):
        return {
            "filepath": str(p), "filename": p.name, "size_bytes": size_bytes,
            "sha256": sha256, "file_type": get_file_type(p),
            "verdict": "clean", "severity": "none", "score": 0,
            "source": "whitelist", "reasons": ["Fichier système connu"],
            "recommended_action": "none",
        }

    # 2. Hash malware connu
    mal = hash_is_malicious(sha256)
    if mal:
        sev = mal.get("severity") or "high"
        return {
            "filepath": str(p), "filename": p.name, "size_bytes": size_bytes,
            "sha256": sha256, "file_type": get_file_type(p),
            "verdict": "known_malware", "severity": sev, "score": 100,
            "source": "hash_db", "threat_name": mal.get("name"),
            "reasons": [f"Hash connu : {mal.get('name', 'malware')}"],
            "recommended_action": "quarantine",
        }

    # 3. ClamAV (si deep ou si fichier est exécutable/binaire)
    ft = get_file_type(p)
    clamav_result = None
    if deep or ft in ("elf", "exe", "deb", "appimage", "script", "shell", "python"):
        clamav_result = scan_with_clamav(p)
        if clamav_result and clamav_result.get("result") == "infected":
            return {
                "filepath": str(p), "filename": p.name, "size_bytes": size_bytes,
                "sha256": sha256, "file_type": ft,
                "verdict": "malware_clamav", "severity": "critical", "score": 95,
                "source": "clamav", "threat_name": clamav_result.get("threat_name"),
                "reasons": [f"ClamAV : {clamav_result.get('threat_name', 'malware')}"],
                "recommended_action": "quarantine",
            }

    # 4. Analyse heuristique
    heur = analyze_heuristic(p)
    verdict = heur["verdict"]
    score = heur["score"]

    severity = "none"
    if verdict == "dangerous":
        severity = "high"
    elif verdict == "suspicious":
        severity = "medium"
    elif verdict == "attention":
        severity = "low"

    action = "none"
    if verdict == "dangerous":
        action = "quarantine"
    elif verdict == "suspicious":
        action = "monitor"

    reasons = [m["reason"] for m in heur["matches"]]

    return {
        "filepath": str(p), "filename": p.name, "size_bytes": size_bytes,
        "sha256": sha256, "file_type": ft,
        "verdict": verdict, "severity": severity, "score": score,
        "source": "heuristic" + ("+clamav" if clamav_result else ""),
        "reasons": reasons, "recommended_action": action,
        "scan_duration_ms": int((time.time() - start) * 1000),
        "matches_count": len(heur["matches"]),
        "clamav_available": clamav_result is not None,
    }


# ─────────────────────────────────────────
# SCANS
# ─────────────────────────────────────────

def _should_scan_file(filepath: Path, max_size: int = 100 * 1024 * 1024) -> bool:
    """Détermine intelligemment si un fichier doit être scanné."""
    try:
        size = filepath.stat().st_size
    except OSError:
        return False
    if size > max_size or size == 0:
        return False
    suf = filepath.suffix.lower()
    if suf in HIGH_PRIORITY_EXT:
        return True
    if suf in MEDIUM_PRIORITY_EXT:
        return True
    # No extension (potentiellement un script)
    if not suf:
        return True
    # Skip images, videos, fonts
    if suf in (".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg",
               ".mp4", ".avi", ".mkv", ".mp3", ".flac", ".wav",
               ".woff", ".woff2", ".ttf", ".otf",
               ".ico", ".cur"):
        return False
    return suf not in (".css", ".html", ".lock", ".log", ".txt", ".md")


def quick_scan(progress_callback=None, cancel_flag=None):
    """Scan rapide — zones à risque uniquement."""
    zones = [
        Path.home() / "Downloads",
        Path.home() / "Desktop",
        Path.home() / "Téléchargements",
        Path("/tmp"),
        Path.home() / ".config/autostart",
        Path.home() / ".local/share/applications",
        Path.home() / ".local/bin",
    ]
    files = []
    max_files = 3000
    for zp in zones:
        if not zp.exists() or len(files) >= max_files:
            continue
        try:
            for f in zp.rglob("*"):
                if len(files) >= max_files or (cancel_flag and cancel_flag.is_set()):
                    break
                if f.is_file() and _should_scan_file(f):
                    files.append(str(f))
        except OSError:
            pass

    threats = []
    scanned = 0
    for i, fp in enumerate(files):
        if cancel_flag and cancel_flag.is_set():
            break
        r = analyze_file(fp)
        scanned += 1
        if r["verdict"] != "clean":
            threats.append(r)
            yield r
        if progress_callback and ((i + 1) % 5 == 0 or r["verdict"] != "clean"):
            progress_callback(i + 1, len(files), fp, len(threats))

    log_scan("quick", scanned, len(threats))
    yield {"_summary": {"files_scanned": scanned, "threats_found": len(threats)}}


def full_scan(
    roots: list[str | Path] | None = None,
    exclusions: list[str] | None = None,
    max_files: int = 50000,
    progress_callback=None,
    cancel_flag=None,
):
    """Scan complet du système avec analyse profonde."""
    exclusions = exclusions or ["/usr/bin", "/usr/lib", "/lib", "/sbin", "/proc", "/sys", "/dev"]
    roots = roots or [str(Path.home()), "/tmp", "/var/tmp", "/opt"]
    root_paths = [Path(r) for r in roots if Path(r).exists()]
    files = []
    for rp in root_paths:
        if len(files) >= max_files or (cancel_flag and cancel_flag.is_set()):
            break
        try:
            for f in rp.rglob("*"):
                if len(files) >= max_files or (cancel_flag and cancel_flag.is_set()):
                    break
                if not f.is_file():
                    continue
                s = str(f)
                if any(s.startswith(ex) for ex in exclusions):
                    continue
                if _should_scan_file(f):
                    files.append(s)
        except (OSError, PermissionError):
            pass

    threats = []
    scanned = 0
    for i, fp in enumerate(files):
        if cancel_flag and cancel_flag.is_set():
            break
        r = analyze_file(fp, deep=True)
        scanned += 1
        if r["verdict"] != "clean":
            threats.append(r)
            yield r
        if progress_callback and ((i + 1) % 10 == 0 or r["verdict"] != "clean"):
            progress_callback(i + 1, len(files), fp, len(threats))

    log_scan("full", scanned, len(threats))
    yield {"_summary": {"files_scanned": scanned, "threats_found": len(threats)}}


def scan_usb_device(mountpoint: str | Path, progress_callback=None):
    """Scan d'une clé USB montée (analyse profonde)."""
    mp = Path(mountpoint)
    if not mp.exists() or not mp.is_dir():
        return
    files = []
    try:
        for f in mp.rglob("*"):
            if f.is_file() and _should_scan_file(f):
                files.append(str(f))
    except OSError:
        return
    threats = []
    for i, fp in enumerate(files):
        r = analyze_file(fp, deep=True)
        if r["verdict"] != "clean":
            threats.append(r)
            yield r
        if progress_callback and (i + 1) % 5 == 0:
            progress_callback(i + 1, len(files), len(threats))
    log_scan("usb", len(files), len(threats))


def get_security_score(metrics: dict | None = None) -> dict:
    """Calcule un score de sécurité global (0-100)."""
    score = 100
    issues = []

    # 1. Vérifier programmes au démarrage
    startup = analyze_startup_entries()
    if startup:
        score -= min(30, len(startup) * 10)
        issues.append(f"{len(startup)} entrée(s) suspecte(s) au démarrage")

    # 2. ClamAV disponible ?
    if not is_clamav_available():
        score -= 10
        issues.append("ClamAV non installé (protection limitée)")

    # 3. Fichiers dans quarantaine
    try:
        from core.quarantine import get_quarantine_list
        q = get_quarantine_list()
        if len(q) > 5:
            score -= 5
            issues.append(f"{len(q)} fichier(s) en quarantaine à traiter")
    except Exception:
        pass

    # 4. Métriques système
    if metrics:
        if metrics.get("disk_percent", 0) > 95:
            score -= 10
            issues.append("Disque presque plein (risque stabilité)")

    score = max(0, score)
    label = "Excellent" if score >= 85 else "Bon" if score >= 70 else "Attention" if score >= 50 else "Critique"

    return {
        "score": score,
        "label": label,
        "issues": issues,
        "clamav_available": is_clamav_available(),
        "startup_entries": len(startup),
    }
