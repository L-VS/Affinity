# ⬡ Affinity

**Affinity** is an intelligent, high-performance system companion designed specifically for **Ubuntu (GNOME)**. It combines advanced security heuristics, deep system cleaning, and hardware optimization into a single, premium interface powered by artificial intelligence.

 *( Note: https://l-vs.github.io/Affinity/ )*

---
## ✨ Key Features

### 🧠 Intelligent Core
- **AI Advisor**: Powered by Groq (Llama 3), Affinity analyzes your system metrics in real-time to provide personalized optimization advice.
- **Local Fallback**: Works offline with a smart rule-based advisor if no API key is provided.

### 🛡️ Professional Security (v2)
- **Heuristic Engine**: 50+ advanced detection rules (Reverse shells, cryptomined, privilege escalation).
- **Entropy Analysis**: Detects packed or encrypted malicious binaries.
- **Real-time Protection**: Background daemon monitoring file changes, network connections, and USB devices.
- **Auto-Quarantine**: Suspicious files are instantly isolated.

### 🧹 Deep Cleaning
- **15+ Categories**: Cleans APT cache, complex browser profiles (Chrome, Firefox, Brave, etc.), journald logs, and orphan packages.
- **Space Recovery**: Visual breakdown of disk usage with one-click cleanup.

### ⚡ System Modes & Tweaks
- **Performance Profiles**: Instant switch between *Performance*, *Balanced*, and *Economy* modes (adjusts CPU governor and swappiness).
- **Ubuntu Customizer**: Direct control over GNOME animations, dock size, hot corners, and top bar settings.

### 🕒 Visual Automation
- **Smart Scheduler**: Visually plan cleaning and security scans via an intuitive UI.

---

## 🚀 Quick Install

Open your terminal and run the following command:

```bash
git clone https://github.com/l-vs/Affinity.git
cd Affinity
bash install.sh
```

The installer will:
1. Detect and install system dependencies (`sensors`, `smartmontools`, etc.).
2. Setup a secure Python virtual environment.
3. Create a **Desktop Entry** so you can launch Affinity from your app menu.
4. Add a `affinity` command to your terminal.

---

## 🛠️ Requirements
- **OS**: Ubuntu 22.04+ (or GNOME-based distributions)
- **Python**: 3.10 or higher
- **Privileges**: Some actions (cleaning system logs, changing CPU modes) require `sudo` access via `pkexec`.

## 🎨 Professional Aesthetic
Affinity is built with **CustomTkinter**, featuring a bespoke dark theme (`#0A0E1A`), cyan accents (`#00D2D2`), and a focus on visual clarity and responsiveness.

---

## 📜 License
Distribué sous la licence **MIT**. Voir `LICENSE` pour plus d'informations.

---
*Created with 🔥 by **l-vs***
