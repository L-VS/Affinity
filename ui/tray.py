"""Affinity — Icône de la barre système (Tray).

Permet de contrôler Affinity en arrière-plan.
Action : Ouvrir/Masquer, Scan rapide, Nettoyage, Quitter.

Created by l-vs — Affinity Tray v1
"""

import threading
from pathlib import Path

try:
    import pystray
    from PIL import Image, ImageDraw
    PYSTRAY_AVAILABLE = True
except ImportError:
    PYSTRAY_AVAILABLE = False


class AffinityTray:
    def __init__(self, main_app=None):
        self.main_app = main_app
        self.icon = None
        self._tray_thread = None

    def _create_image(self, width=64, height=64):
        """Crée une icône simple (cercle cyan sur fond transparent)."""
        image = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        dc = ImageDraw.Draw(image)
        # Cercle extérieur cyan (#00D2D2)
        dc.ellipse([8, 8, 56, 56], fill=(0, 210, 210), outline=(0, 0, 0, 0))
        # Intérieur sombre
        dc.ellipse([16, 16, 48, 48], fill=(10, 14, 26), outline=(0, 0, 0, 0))
        # Point central cyan
        dc.ellipse([24, 24, 40, 40], fill=(0, 210, 210), outline=(0, 0, 0, 0))
        return image

    def start(self):
        """Démarre l'icône dans un thread séparé."""
        if not PYSTRAY_AVAILABLE:
            return

        def run_icon():
            menu = pystray.Menu(
                pystray.MenuItem("Affinity — Ouvrir", self._on_show),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Scan Rapide", self._on_quick_scan),
                pystray.MenuItem("Nettoyage Rapide", self._on_quick_clean),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Quitter", self._on_exit)
            )
            self.icon = pystray.Icon("affinity", self._create_image(), "Affinity", menu)
            self.icon.run()

        self._tray_thread = threading.Thread(target=run_icon, daemon=True)
        self._tray_thread.start()

    def stop(self):
        if self.icon:
            self.icon.stop()

    def _on_show(self, icon, item):
        if self.main_app:
            self.main_app.after(0, self.main_app.deiconify)
            self.main_app.after(10, self.main_app.focus_force)

    def _on_quick_scan(self, icon, item):
        if self.main_app:
            self.main_app.after(0, lambda: self.main_app.navigate_to("security"))
            self.main_app.after(10, self.main_app.deiconify)
            # On pourrait déclencher le scan directement ici via une méthode de app

    def _on_quick_clean(self, icon, item):
        if self.main_app:
            self.main_app.after(0, lambda: self.main_app.navigate_to("cleaner"))
            self.main_app.after(10, self.main_app.deiconify)

    def _on_exit(self, icon, item):
        self.stop()
        if self.main_app:
            self.main_app.after(0, self.main_app.quit)
        # Arrêter le daemon aussi
        try:
            from core.daemon import stop_daemon
            stop_daemon()
        except ImportError:
            pass
