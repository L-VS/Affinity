"""Affinity — Constantes et configuration."""

from pathlib import Path

VERSION = "1.0.0"
AUTHOR = "l-vs"

# Chemins
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path.home() / ".affinity"
CONFIG_FILE = DATA_DIR / "config.json"
DB_PATH = DATA_DIR / "data.db"
ASSETS_DIR = BASE_DIR / "assets"
SECURITY_DIR = DATA_DIR / "security"
QUARANTINE_DIR = DATA_DIR / "quarantine"

# Création des dossiers
DATA_DIR.mkdir(parents=True, exist_ok=True)
SECURITY_DIR.mkdir(parents=True, exist_ok=True)
QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)

# Couleurs (design prototype)
COLORS = {
    "bg": "#0A0E1A",
    "bg_card": "#0F1629",
    "bg_hover": "#141D38",
    "border": "#1E2A45",
    "text": "#E8EDF7",
    "text_dim": "#6B7A99",
    "text_mid": "#A0AECF",
    "cyan": "#00D2D2",
    "cyan_soft": "#0D2030",
    "green": "#00E5A0",
    "green_soft": "#0A1F18",
    "orange": "#FF8C42",
    "orange_soft": "#1F1508",
    "red": "#FF4F6A",
    "red_soft": "#1F0810",
    "blue": "#4DA6FF",
    "sidebar": "#080C18",
}

# Fenêtre
WINDOW_WIDTH = 1000
WINDOW_HEIGHT = 650
SIDEBAR_WIDTH = 220
