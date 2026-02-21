"""Affinity — Gestion de la quarantaine des fichiers suspects."""

import json
import os
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

from config import DATA_DIR, DB_PATH, QUARANTINE_DIR


def quarantine_file(
    filepath: str | Path,
    reason: str,
    threat_info: dict | None = None,
) -> dict | None:
    """
    Isole un fichier suspect. Retourne dict avec infos ou None si erreur.
    """
    QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)
    p = Path(filepath)
    if not p.exists() or not p.is_file():
        return None

    from core.security_engine import compute_sha256

    hash_res = compute_sha256(p)
    sha256 = hash_res["sha256"] if hash_res else "unknown"
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    short_hash = sha256[:8] if sha256 != "unknown" else "xxxx"
    safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in p.name)
    q_name = f"{ts}_{short_hash}_{safe_name}"

    dest = QUARANTINE_DIR / q_name
    try:
        shutil.copy2(p, dest)
        hash_dest = compute_sha256(dest)
        if hash_dest and hash_dest["sha256"] != sha256:
            dest.unlink()
            return None
        p.unlink()
    except OSError:
        return None

    # Retirer exécution
    try:
        os.chmod(dest, 0o444)
    except OSError:
        pass

    meta = {
        "original_path": str(p),
        "original_name": p.name,
        "quarantine_date": datetime.now().isoformat(),
        "reason": reason,
        "sha256": sha256,
        "threat_name": (threat_info or {}).get("threat_name"),
        "severity": (threat_info or {}).get("severity", "unknown"),
        "can_restore": True,
    }
    meta_path = dest.with_suffix(dest.suffix + ".meta")
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    # Log SQLite
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """INSERT INTO quarantine (original_path, quarantine_path, quarantine_date, reason, hash_sha256)
           VALUES (?, ?, ?, ?, ?)""",
        (str(p), str(dest), meta["quarantine_date"], reason, sha256),
    )
    conn.commit()
    conn.close()

    return {"filename": q_name, "original_path": str(p)}


def restore_file(quarantine_filename: str) -> bool:
    """Restaure un fichier depuis la quarantaine."""
    q_path = QUARANTINE_DIR / quarantine_filename
    meta_path = QUARANTINE_DIR / (quarantine_filename + ".meta")
    if not q_path.exists():
        meta_path = q_path.with_suffix(q_path.suffix + ".meta")
    if not meta_path.exists():
        return False
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    orig = Path(meta["original_path"])
    orig.parent.mkdir(parents=True, exist_ok=True)
    if orig.exists():
        return False
    try:
        shutil.copy2(q_path, orig)
        q_path.unlink()
        meta_path.unlink(missing_ok=True)
    except OSError:
        return False
    return True


def delete_permanently(quarantine_filename: str) -> bool:
    """Supprime définitivement un fichier en quarantaine."""
    q_path = QUARANTINE_DIR / quarantine_filename
    meta_path = q_path.with_suffix(q_path.suffix + ".meta")
    if not q_path.exists():
        return False
    try:
        with open(q_path, "wb") as f:
            for _ in range(3):
                f.seek(0)
                f.write(b"\x00" * min(1024 * 1024, q_path.stat().st_size))
        q_path.unlink()
        meta_path.unlink(missing_ok=True)
    except OSError:
        return False
    return True


def get_quarantine_list() -> list[dict]:
    """Liste des fichiers en quarantaine."""
    items = []
    for q_path in QUARANTINE_DIR.iterdir():
        if q_path.suffix == ".meta":
            continue
        meta_path = q_path.with_suffix(q_path.suffix + ".meta")
        if not meta_path.exists():
            meta = {"original_path": "?", "original_name": q_path.name, "reason": "?", "severity": "?"}
        else:
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                meta = {}
        items.append({
            "filename": q_path.name,
            "original_path": meta.get("original_path", "?"),
            "original_name": meta.get("original_name", q_path.name),
            "date": meta.get("quarantine_date", "?"),
            "reason": meta.get("reason", "?"),
            "severity": meta.get("severity", "?"),
            "size_bytes": q_path.stat().st_size if q_path.exists() else 0,
        })
    return sorted(items, key=lambda x: x["date"], reverse=True)


def get_quarantine_size() -> int:
    """Taille totale du dossier quarantaine en octets."""
    total = 0
    for p in QUARANTINE_DIR.iterdir():
        if p.is_file() and p.suffix != ".meta":
            total += p.stat().st_size
    return total
