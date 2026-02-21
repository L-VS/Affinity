#!/bin/bash
# Affinity — Script d'installation professionnel
# Created by l-vs | v1.0.0
# Usage: bash install.sh

set -e

# Configuration
APP_NAME="Affinity"
INSTALL_DIR="${INSTALL_DIR:-$HOME/.local/share/affinity}"
BIN_LINK="$HOME/.local/bin/affinity"
DESKTOP_ENTRY="$HOME/.local/share/applications/affinity.desktop"

# Couleurs
CYAN='\033[0;36m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════╗"
echo "║  Affinity — Compagnon système pour Ubuntu       ║"
echo "║  Installation en cours...                        ║"
echo "╚══════════════════════════════════════════════════╝"
echo -e "${NC}"

# 1. Vérification de l'OS
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    echo -e "${RED}Erreur : Affinity est optimisé pour Ubuntu/Linux.${NC}"
    exit 1
fi

# 2. Détection de Python 3.10+
PYTHON_CMD=""
for py in python3.12 python3.11 python3.10 python3; do
    if command -v "$py" &>/dev/null; then
        VER=$("$py" -c "import sys; print(sys.version_info.minor)" 2>/dev/null || echo 0)
        if [ "$VER" -ge 10 ] 2>/dev/null; then
            PYTHON_CMD="$py"
            break
        fi
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    echo -e "${RED}Erreur : Python 3.10+ est requis.${NC}"
    echo "Installez-le avec : sudo apt update && sudo apt install python3.10"
    exit 1
fi

# 3. Dépendances système
echo -e "${CYAN}--- Dépendances système ---${NC}"
DEPS="python3-tk python3-pip python3-venv xdg-utils libnotify-bin lm-sensors smartmontools"
MISSING=""
for d in $DEPS; do
    if ! dpkg -l "$d" &>/dev/null 2>&1; then
        MISSING="$MISSING $d"
    fi
done

if [ -n "$MISSING" ]; then
    echo -e "Installation des paquets requis via apt :${MISSING}"
    sudo apt update
    sudo apt install -y $MISSING
else
    echo "Dépendances système OK."
fi

# 4. Préparation du répertoire d'installation
echo -e "\n${CYAN}--- Préparation des fichiers ---${NC}"
mkdir -p "$INSTALL_DIR"
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Installation dans : $INSTALL_DIR"
cd "$SRC_DIR"

# Copie intelligente (ignore .git, venv, etc.)
cp -r ./*.py "$INSTALL_DIR/" 2>/dev/null || true
cp -r ./requirements.txt "$INSTALL_DIR/" 2>/dev/null || true
mkdir -p "$INSTALL_DIR/ui" "$INSTALL_DIR/core" "$INSTALL_DIR/ai" "$INSTALL_DIR/assets" "$INSTALL_DIR/site"

[ -d "./ui" ] && cp -r ./ui/*.py "$INSTALL_DIR/ui/" 2>/dev/null || true
[ -d "./core" ] && cp -r ./core/*.py "$INSTALL_DIR/core/" 2>/dev/null || true
[ -d "./ai" ] && cp -r ./ai/*.py "$INSTALL_DIR/ai/" 2>/dev/null || true
[ -d "./site" ] && cp -r ./site/* "$INSTALL_DIR/site/" 2>/dev/null || true
[ -d "./assets" ] && cp -r ./assets/* "$INSTALL_DIR/assets/" 2>/dev/null || true

# 5. Environnement virtuel Python
echo -e "\n${CYAN}--- Environnement Python ---${NC}"
cd "$INSTALL_DIR"
if [ ! -d "venv" ]; then
    $PYTHON_CMD -m venv venv
fi

source venv/bin/activate
echo "Installation des dépendances Python (CustomTkinter, psutil, pystray...)"
pip install -q --upgrade pip
pip install -q -r requirements.txt || pip install -q customtkinter psutil pyudev requests watchdog Pillow pystray cryptography keyring groq

# 6. Création des lanceurs
echo -e "\n${CYAN}--- Configuration système ---${NC}"

# Binaire CLI
mkdir -p "$HOME/.local/bin"
cat > "$BIN_LINK" << EOF
#!/bin/bash
source "$INSTALL_DIR/venv/bin/activate"
python3 "$INSTALL_DIR/main.py" "\$@"
EOF
chmod +x "$BIN_LINK"

# Desktop Entry
cat > "$DESKTOP_ENTRY" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Affinity
Comment=Compagnon système intelligent pour Ubuntu
Exec=bash -c "source $INSTALL_DIR/venv/bin/activate && python3 $INSTALL_DIR/main.py"
Icon=utilities-system-monitor
Terminal=false
Categories=System;Settings;
Keywords=system;cleaner;antivirus;optimizer;ai;
EOF
chmod +x "$DESKTOP_ENTRY"

# 7. Finalisation
echo -e "\n${GREEN}╔══════════════════════════════════════════════════╗"
echo "║  Affinity est maintenant installé !              ║"
echo "╚══════════════════════════════════════════════════╝${NC}"
echo ""
echo "Vous pouvez lancer l'application :"
echo "1. Via le menu des applications (cherchez 'Affinity')"
echo "2. Via le terminal : affinity"
echo ""
echo "Note : Le daemon de protection démarrera au lancement."
echo ""
