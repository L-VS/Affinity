"""Affinity — Base de données des hashes malveillants (MalwareBazaar)."""

import sqlite3
import time
from datetime import datetime
from pathlib import Path

import requests

from config import CONFIG_FILE, SECURITY_DIR

HASHES_DB = SECURITY_DIR / "hashes.db"
MALWARESHAZAAR_URL = "https://bazaar.abuse.ch/export/txt/sha256/recent/"
MAX_DOWNLOAD_BYTES = 2 * 1024 * 1024  # 2 Mo


def _init_db() -> None:
    """Initialise les tables si nécessaire."""
    SECURITY_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(HASHES_DB)
    c = conn.cursor()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS malware_hashes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sha256 TEXT UNIQUE NOT NULL,
        md5 TEXT,
        name TEXT,
        threat_type TEXT,
        severity TEXT,
        source TEXT DEFAULT 'malwarebazaar',
        added_date DATETIME DEFAULT CURRENT_TIMESTAMP,
        last_seen DATETIME
    );
    CREATE INDEX IF NOT EXISTS idx_malware_sha256 ON malware_hashes(sha256);

    CREATE TABLE IF NOT EXISTS safe_hashes (
        sha256 TEXT PRIMARY KEY,
        filepath TEXT,
        package TEXT
    );

    CREATE TABLE IF NOT EXISTS scan_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        scan_type TEXT,
        started_at DATETIME,
        finished_at DATETIME,
        files_scanned INTEGER DEFAULT 0,
        threats_found INTEGER DEFAULT 0,
        report_json TEXT
    );
    """)
    conn.commit()
    conn.close()


def virustotal_lookup(sha256_hash: str, api_key: str | None) -> dict | None:
    """
    Vérifie un hash via l'API VirusTotal (si clé fournie).
    Retourne {"malicious": int, "total": int, "malware_name": str} ou None.
    """
    if not api_key or len(api_key) < 32:
        return None
    try:
        r = requests.get(
            f"https://www.virustotal.com/vtapi/v2/file/report",
            params={"apikey": api_key, "resource": sha256_hash},
            timeout=15,
        )
        if r.status_code != 200:
            return None
        j = r.json()
        if j.get("response_code") != 1:
            return None
        pos = int(j.get("positives", 0))
        total = int(j.get("total", 0))
        if pos > 0 and total > 0:
            return {
                "malicious": pos,
                "total": total,
                "malware_name": j.get("permalink", "").split("/")[-1] if j.get("permalink") else "VirusTotal",
            }
    except (requests.RequestException, ValueError, KeyError):
        pass
    return None


def hash_is_malicious(sha256_hash: str) -> dict | None:
    """
    Vérifie si un hash est dans la base malveillante.
    Retourne dict avec name, threat_type, severity ou None.
    """
    _init_db()
    conn = sqlite3.connect(HASHES_DB)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT name, threat_type, severity FROM malware_hashes WHERE sha256 = ?",
        (sha256_hash.lower(),),
    ).fetchone()
    conn.close()
    if row:
        return {"name": row[0], "threat_type": row[1], "severity": row[2]}
    return None


def hash_is_safe(sha256_hash: str) -> bool:
    """Vérifie si un hash est dans la whitelist Ubuntu."""
    _init_db()
    conn = sqlite3.connect(HASHES_DB)
    r = conn.execute(
        "SELECT 1 FROM safe_hashes WHERE sha256 = ?", (sha256_hash.lower(),)
    ).fetchone()
    conn.close()
    return r is not None


def update_hash_database(
    progress_callback=None,
) -> dict:
    """
    Télécharge la liste des hashes MalwareBazaar et met à jour la base.
    Retourne {"added": int, "total": int, "duration": float}.
    """
    _init_db()
    start = time.time()
    added = 0
    total = 0

    try:
        resp = requests.get(
            MALWARESHAZAAR_URL,
            timeout=30,
            stream=True,
            headers={"User-Agent": "Affinity-Security/1.0"},
        )
        resp.raise_for_status()
        content = b""
        for chunk in resp.iter_content(chunk_size=8192):
            content += chunk
            if len(content) >= MAX_DOWNLOAD_BYTES:
                break

        lines = content.decode("utf-8", errors="ignore").split("\n")
        total = len([l for l in lines if l.strip() and not l.startswith("#")])

        conn = sqlite3.connect(HASHES_DB)
        count = 0
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            hash_val = line.lower()
            if len(hash_val) != 64 or not all(c in "0123456789abcdef" for c in hash_val):
                continue
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO malware_hashes (sha256, source) VALUES (?, ?)",
                    (hash_val, "malwarebazaar"),
                )
                if conn.total_changes > 0:
                    added += 1
            except sqlite3.IntegrityError:
                pass
            count += 1
            if progress_callback and count % 500 == 0:
                progress_callback(count, total)
        conn.commit()
        conn.close()
    except requests.RequestException:
        pass

    return {"added": added, "total": total, "duration": time.time() - start}


def get_database_stats() -> dict:
    """Retourne les statistiques de la base."""
    _init_db()
    conn = sqlite3.connect(HASHES_DB)
    malware = conn.execute(
        "SELECT COUNT(*) FROM malware_hashes"
    ).fetchone()[0]
    safe = conn.execute("SELECT COUNT(*) FROM safe_hashes").fetchone()[0]
    conn.close()
    size_mb = HASHES_DB.stat().st_size / (1024 * 1024) if HASHES_DB.exists() else 0
    return {
        "malware_count": malware,
        "safe_count": safe,
        "last_update": datetime.now().isoformat(),
        "size_mb": round(size_mb, 2),
    }


def log_scan(
    scan_type: str,
    files_scanned: int,
    threats_found: int,
    report_json: str = "",
) -> None:
    """Enregistre un scan dans l'historique."""
    _init_db()
    conn = sqlite3.connect(HASHES_DB)
    conn.execute(
        """INSERT INTO scan_history (scan_type, started_at, finished_at, files_scanned, threats_found, report_json)
           VALUES (?, datetime('now'), datetime('now'), ?, ?, ?)""",
        (scan_type, files_scanned, threats_found, report_json),
    )
    conn.commit()
    conn.close()


def get_last_scan() -> dict | None:
    """Retourne le dernier scan enregistré."""
    _init_db()
    conn = sqlite3.connect(HASHES_DB)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        """SELECT scan_type, started_at, finished_at, files_scanned, threats_found
           FROM scan_history ORDER BY finished_at DESC LIMIT 1"""
    ).fetchone()
    conn.close()
    return dict(row) if row else None
