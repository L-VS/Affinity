#!/usr/bin/env python3
"""Affinity — Point d'entrée. Compagnon système intelligent pour Ubuntu."""

import sys

# Vérification Python 3.10+
if sys.version_info < (3, 10):
    print("Affinity requiert Python 3.10 ou supérieur.")
    sys.exit(1)


def main() -> None:
    from config import DATA_DIR
    from database import init_db

    # Initialisation du dossier de données
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Initialisation de la base SQLite
    init_db()

    # Mise à jour des hashes MalwareBazaar en arrière-plan (si connexion)
    def _update_hashes():
        try:
            from core.hash_database import update_hash_database
            update_hash_database()
        except Exception:
            pass

    import threading
    threading.Thread(target=_update_hashes, daemon=True).start()

    from ui.app import AffinityApp
    from ui.onboarding import OnboardingWindow, should_show_onboarding
    from ui.tray import AffinityTray
    from core.daemon import start_daemon, stop_daemon

    # Démarrage du daemon de protection
    start_daemon()

    app = AffinityApp()
    
    # Démarrage de l'icône de la barre système
    tray = AffinityTray(app)
    tray.start()

    if should_show_onboarding():
        app.after(500, lambda: OnboardingWindow(app, on_complete=lambda: None))

    try:
        app.mainloop()
    finally:
        # Nettoyage à la fermeture
        tray.stop()
        stop_daemon()


if __name__ == "__main__":
    main()
