"""Affinity — Onglet Paramètres (complet et personnalisable)."""

import customtkinter as ctk
from pathlib import Path

from config import COLORS, VERSION, DATA_DIR
from config_loader import load_config, save_config, get, set_key


class SettingsFrame(ctk.CTkScrollableFrame):
    """Onglet Paramètres — entièrement personnalisable."""

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self._config = load_config()
        self._build_ui()

    def _save(self) -> None:
        save_config(self._config)

    def _build_ui(self) -> None:
        self.tabview = ctk.CTkTabview(self, fg_color=COLORS["bg_card"])
        self.tabview.pack(fill="both", expand=True)
        for name in ["Profil", "Recommandations", "Comportement", "Antivirus", "Nettoyeur", "Ubuntu", "Automatisations", "IA", "Notifications", "À propos"]:
            self.tabview.add(name)

        self._build_profile()
        self._build_recommendations()
        self._build_behavior()
        self._build_antivirus()
        self._build_cleaner()
        self._build_ubuntu()
        self._build_automations()
        self._build_ai()
        self._build_notifications()
        self._build_about()

    def _build_recommendations(self) -> None:
        tab = self.tabview.tab("Recommandations")
        ctk.CTkLabel(tab, text="Ce que vous autorisez Affinity à faire automatiquement", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", pady=8)
        ctk.CTkLabel(tab, text="Affinity ne fera que ce que vous cochez.", font=ctk.CTkFont(size=11), text_color=COLORS["text_dim"]).pack(anchor="w", pady=(0, 12))
        recs = [
            ("auto_clean", "Nettoyage automatique planifié"),
            ("usb_scan", "Analyser les clés USB à la connexion"),
            ("realtime_watch", "Surveiller les dossiers sensibles (Downloads, etc.)"),
            ("auto_updates", "Mises à jour APT automatiques"),
            ("network_tweaks", "Optimisation réseau (latence)"),
            ("thermal_tweaks", "Régulation thermique intelligente"),
            ("reduce_animations", "Réduire les animations GNOME"),
            ("ai_help_on_error", "L'IA peut m'aider si le système échoue"),
        ]
        self.rec_vars = {}
        for key, label in recs:
            v = ctk.CTkCheckBox(tab, text=label, font=ctk.CTkFont(size=12), command=self._rec_save)
            v.pack(anchor="w", pady=4)
            if get(self._config, "recommendations", key, default=(key in ("usb_scan", "realtime_watch"))):
                v.select()
            self.rec_vars[key] = v

    def _rec_save(self, _key: str = None) -> None:
        if hasattr(self, "rec_vars"):
            for k, v in self.rec_vars.items():
                set_key(self._config, bool(v.get()), "recommendations", k)
            self._save()

    def _build_automations(self) -> None:
        tab = self.tabview.tab("Automatisations")
        ctk.CTkLabel(tab, text="Planifications", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", pady=8)
        ctk.CTkLabel(tab, text="Automatisez le nettoyage ou les scans.", font=ctk.CTkFont(size=11), text_color=COLORS["text_dim"]).pack(anchor="w", pady=(0, 12))
        try:
            from core.automation_engine import load_automations
            autos = load_automations()
            if not autos:
                ctk.CTkLabel(tab, text="Aucune automatisation configurée.", font=ctk.CTkFont(size=12)).pack(anchor="w", pady=8)
            ctk.CTkButton(tab, text="+ Nettoyage hebdomadaire", font=ctk.CTkFont(size=12), command=self._add_auto_clean).pack(anchor="w", pady=8)
        except ImportError:
            ctk.CTkLabel(tab, text="Module d'automatisation non disponible.", font=ctk.CTkFont(size=12)).pack(anchor="w", pady=8)

    def _add_auto_clean(self) -> None:
        try:
            from core.automation_engine import add_automation, install_cron_clean
            add_automation("schedule", "clean", {"day": 0, "hour": 3})
            install_cron_clean(day=0, hour=3)
            self._save()
        except Exception:
            pass

    def _build_ai(self) -> None:
        tab = self.tabview.tab("IA")
        ctk.CTkLabel(tab, text="Assistant IA (Groq)", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", pady=8)
        ctk.CTkButton(tab, text="Créer un compte Groq gratuit", font=ctk.CTkFont(size=12), fg_color=COLORS["cyan"], text_color="#001F2E", command=lambda: __import__("subprocess").run(["xdg-open", "https://console.groq.com"], check=False)).pack(anchor="w", pady=4)
        self.ai_key = ctk.CTkEntry(tab, placeholder_text="Collez votre clé API", width=400, height=36, show="•")
        self.ai_key.insert(0, get(self._config, "ai", "groq_api_key") or "")
        self.ai_key.pack(anchor="w", pady=8)
        ctk.CTkLabel(tab, text="Utilisation automatique", font=ctk.CTkFont(size=11), text_color=COLORS["text_dim"]).pack(anchor="w", pady=(12, 4))
        self.ai_auto = ctk.CTkOptionMenu(tab, values=["Aucune", "Erreurs uniquement", "Optimisations", "Complète"], width=200, command=lambda v: self._ai_save())
        self.ai_auto.pack(anchor="w", pady=4)
        v2l = {"none": "Aucune", "errors": "Erreurs uniquement", "optimizations": "Optimisations", "full": "Complète"}
        self.ai_auto.set(v2l.get(get(self._config, "ai", "auto_usage") or "none", "Aucune"))

    def _ai_save(self) -> None:
        map_ = {"Aucune": "none", "Erreurs uniquement": "errors", "Optimisations": "optimizations", "Complète": "full"}
        set_key(self._config, map_.get(self.ai_auto.get(), "none"), "ai", "auto_usage")
        if hasattr(self, "ai_key"):
            k = self.ai_key.get().strip()
            set_key(self._config, k if k else None, "ai", "groq_api_key")
        self._save()

    def _build_profile(self) -> None:
        tab = self.tabview.tab("Profil")
        ctk.CTkLabel(tab, text="Prénom", font=ctk.CTkFont(size=11), text_color=COLORS["text_dim"]).pack(anchor="w", padx=0, pady=(8, 4))
        self.profile_name = ctk.CTkEntry(tab, placeholder_text="Votre prénom", width=300, height=36)
        self.profile_name.insert(0, get(self._config, "profile", "first_name") or "")
        self.profile_name.pack(anchor="w", pady=(0, 16))
        self.profile_name.bind("<FocusOut>", lambda e: self._on_profile_change())

        ctk.CTkLabel(tab, text="Nom du PC (cosmétique)", font=ctk.CTkFont(size=11), text_color=COLORS["text_dim"]).pack(anchor="w", padx=0, pady=(8, 4))
        self.pc_name = ctk.CTkEntry(tab, placeholder_text="Mon ordinateur", width=300, height=36)
        self.pc_name.insert(0, get(self._config, "profile", "pc_name") or "")
        self.pc_name.pack(anchor="w", pady=(0, 16))
        self.pc_name.bind("<FocusOut>", lambda e: self._on_profile_change())

    def _on_profile_change(self) -> None:
        set_key(self._config, self.profile_name.get().strip(), "profile", "first_name")
        set_key(self._config, self.pc_name.get().strip(), "profile", "pc_name")
        self._save()

    def _build_behavior(self) -> None:
        tab = self.tabview.tab("Comportement")
        ctk.CTkLabel(tab, text="Mode d'action", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", pady=8)
        mode = get(self._config, "behavior", "mode") or "supervised"
        for val, name, desc in [
            ("automatic", "Automatique", "Affinity agit sans vous demander."),
            ("supervised", "Supervisé (recommandé)", "Affinity propose, vous confirmez."),
            ("manual", "Manuel", "Affinity observe et informe."),
        ]:
            row = ctk.CTkFrame(tab, fg_color=COLORS["bg"], corner_radius=8, cursor="hand2")
            row.pack(fill="x", pady=4)
            row.bind("<Button-1>", lambda e, v=val: self._set_behavior(v))
            lbl = ctk.CTkLabel(row, text=f"{'●' if mode == v else '○'} {name}", font=ctk.CTkFont(size=12))
            lbl.pack(anchor="w", padx=12, pady=8)
            lbl.bind("<Button-1>", lambda e, v=val: self._set_behavior(v))
            ctk.CTkLabel(row, text=desc, font=ctk.CTkFont(size=11), text_color=COLORS["text_dim"]).pack(anchor="w", padx=12, pady=(0, 8))

    def _set_behavior(self, mode: str) -> None:
        set_key(self._config, mode, "behavior", "mode")
        self._save()

    def _build_antivirus(self) -> None:
        tab = self.tabview.tab("Antivirus")
        ctk.CTkLabel(tab, text="Protection temps réel", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", pady=8)
        self.av_realtime = ctk.CTkSwitch(
            tab,
            text="Surveillance des dossiers sensibles (Downloads, Desktop, /tmp)",
            font=ctk.CTkFont(size=12),
            command=lambda: self._av_save(),
        )
        self.av_realtime.pack(anchor="w", pady=4)
        self.av_realtime.select() if get(self._config, "antivirus", "realtime", default=True) else self.av_realtime.deselect()

        self.av_usb = ctk.CTkSwitch(
            tab,
            text="Scan automatique des clés USB au branchement",
            font=ctk.CTkFont(size=12),
            command=lambda: self._av_save(),
        )
        self.av_usb.pack(anchor="w", pady=4)
        self.av_usb.select() if get(self._config, "antivirus", "usb_auto_scan", default=True) else self.av_usb.deselect()

        ctk.CTkLabel(tab, text="VirusTotal API (optionnel)", font=ctk.CTkFont(size=11), text_color=COLORS["text_dim"]).pack(anchor="w", pady=(16, 4))
        self.av_vt_key = ctk.CTkEntry(tab, placeholder_text="Clé API VirusTotal (70+ moteurs)", width=400, height=36, show="•")
        self.av_vt_key.insert(0, get(self._config, "antivirus", "virustotal_api_key") or "")
        self.av_vt_key.pack(anchor="w", pady=4)
        self.av_vt_key.bind("<FocusOut>", lambda e: self._av_save())

    def _av_save(self) -> None:
        set_key(self._config, bool(self.av_realtime.get()), "antivirus", "realtime")
        set_key(self._config, bool(self.av_usb.get()), "antivirus", "usb_auto_scan")
        if hasattr(self, "av_vt_key"):
            k = self.av_vt_key.get().strip()
            set_key(self._config, k if k else None, "antivirus", "virustotal_api_key")
        self._save()

    def _build_cleaner(self) -> None:
        tab = self.tabview.tab("Nettoyeur")
        ctk.CTkLabel(tab, text="Planification", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", pady=8)
        self.clean_scheduled = ctk.CTkSwitch(
            tab,
            text="Nettoyage automatique planifié",
            font=ctk.CTkFont(size=12),
            command=lambda: self._clean_save(),
        )
        self.clean_scheduled.pack(anchor="w", pady=4)
        self.clean_scheduled.select() if get(self._config, "cleaner", "scheduled") else self.clean_scheduled.deselect()

        self.clean_backup = ctk.CTkSwitch(
            tab,
            text="Sauvegarder avant nettoyage (recommandé pour catégories risquées)",
            font=ctk.CTkFont(size=12),
            command=lambda: self._clean_save(),
        )
        self.clean_backup.pack(anchor="w", pady=4)
        self.clean_backup.select() if get(self._config, "cleaner", "backup_before_clean") else self.clean_backup.deselect()

    def _clean_save(self) -> None:
        set_key(self._config, bool(self.clean_scheduled.get()), "cleaner", "scheduled")
        set_key(self._config, bool(self.clean_backup.get()), "cleaner", "backup_before_clean")
        self._save()

    def _build_ubuntu(self) -> None:
        tab = self.tabview.tab("Ubuntu")
        try:
            from core.ubuntu_customizer import (
                get_available_themes,
                get_available_icon_themes,
                get_current_theme,
                get_current_icon_theme,
                get_current_font,
                set_gtk_theme,
                set_icon_theme,
                set_font,
                set_animations_enabled,
                is_animations_enabled,
                set_dock_autohide,
                set_dock_icon_size,
                get_dock_icon_size,
                set_top_bar_clock_seconds,
                set_top_bar_show_date,
                set_hot_corners,
            )
        except ImportError:
            ctk.CTkLabel(tab, text="Module de personnalisation non disponible.", font=ctk.CTkFont(size=12)).pack(pady=20)
            return

        # --- Section 1: Thèmes ---
        sub_theme = ctk.CTkFrame(tab, fg_color="transparent")
        sub_theme.pack(fill="x", pady=8)
        
        ctk.CTkLabel(sub_theme, text="Apparence", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w")
        
        row1 = ctk.CTkFrame(sub_theme, fg_color="transparent")
        row1.pack(fill="x", pady=4)
        
        ctk.CTkLabel(row1, text="Thème GTK", font=ctk.CTkFont(size=11), text_color=COLORS["text_dim"]).pack(side="left", padx=(0, 20))
        themes = get_available_themes()
        self.ubuntu_theme = ctk.CTkOptionMenu(
            row1,
            values=themes,
            width=200,
            command=lambda v: (set_key(self._config, v, "ubuntu_custom", "gtk_theme"), set_gtk_theme(v), self._save()),
        )
        self.ubuntu_theme.set(get_current_theme() or "Yaru-dark")
        self.ubuntu_theme.pack(side="left")

        row2 = ctk.CTkFrame(sub_theme, fg_color="transparent")
        row2.pack(fill="x", pady=4)
        
        ctk.CTkLabel(row2, text="Icônes", font=ctk.CTkFont(size=11), text_color=COLORS["text_dim"]).pack(side="left", padx=(0, 48))
        icons = get_available_icon_themes()
        self.ubuntu_icons = ctk.CTkOptionMenu(
            row2,
            values=icons,
            width=200,
            command=lambda v: (set_key(self._config, v, "ubuntu_custom", "icon_theme"), set_icon_theme(v), self._save()),
        )
        self.ubuntu_icons.set(get_current_icon_theme() or "Yaru")
        self.ubuntu_icons.pack(side="left")

        # --- Section 2: Tweaks GNOME ---
        ctk.CTkLabel(tab, text="Tweaks GNOME", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", pady=(16, 8))
        
        # Animations
        self.tweak_anim = ctk.CTkSwitch(tab, text="Animations système", font=ctk.CTkFont(size=12), 
                                       command=lambda: set_animations_enabled(bool(self.tweak_anim.get())))
        self.tweak_anim.pack(anchor="w", pady=4)
        if is_animations_enabled(): self.tweak_anim.select()

        # Dock Autohide
        self.tweak_dock_hide = ctk.CTkSwitch(tab, text="Masquage automatique du Dock", font=ctk.CTkFont(size=12),
                                            command=lambda: set_dock_autohide(bool(self.tweak_dock_hide.get())))
        self.tweak_dock_hide.pack(anchor="w", pady=4)

        # Dock size
        row_dock = ctk.CTkFrame(tab, fg_color="transparent")
        row_dock.pack(fill="x", pady=4)
        ctk.CTkLabel(row_dock, text="Taille icônes Dock", font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 12))
        self.dock_slider = ctk.CTkSlider(row_dock, from_=16, to=64, width=150)
        sz = get_dock_icon_size()
        self.dock_slider.set(sz)
        self.dock_slider.pack(side="left", padx=(0, 12))
        self.dock_label = ctk.CTkLabel(row_dock, text=f"{sz} px", font=ctk.CTkFont(size=11))
        self.dock_label.pack(side="left")
        self.dock_slider.configure(command=lambda v: (set_dock_icon_size(int(v)), self.dock_label.configure(text=f"{int(v)} px")))

        # Multi toggles
        row_opts = ctk.CTkFrame(tab, fg_color="transparent")
        row_opts.pack(fill="x", pady=8)
        
        self.tweak_sec = ctk.CTkCheckBox(row_opts, text="Afficher les secondes", font=ctk.CTkFont(size=11),
                                        command=lambda: set_top_bar_clock_seconds(bool(self.tweak_sec.get())))
        self.tweak_sec.pack(side="left", padx=(0, 12))
        
        self.tweak_date = ctk.CTkCheckBox(row_opts, text="Afficher la date", font=ctk.CTkFont(size=11),
                                         command=lambda: set_top_bar_show_date(bool(self.tweak_date.get())))
        self.tweak_date.pack(side="left", padx=(0, 12))
        
        self.tweak_hot = ctk.CTkCheckBox(row_opts, text="Coins actifs (Hot Corners)", font=ctk.CTkFont(size=11),
                                        command=lambda: set_hot_corners(bool(self.tweak_hot.get())))
        self.tweak_hot.pack(side="left")

        # --- Section 3: Polices ---
        ctk.CTkLabel(tab, text="Typographie", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", pady=(16, 8))
        font_name, font_size = get_current_font()
        row_f = ctk.CTkFrame(tab, fg_color="transparent")
        row_f.pack(anchor="w", pady=4)
        self.ubuntu_font = ctk.CTkEntry(row_f, width=180, height=36)
        self.ubuntu_font.insert(0, font_name)
        self.ubuntu_font.pack(side="left", padx=(0, 8))
        self.ubuntu_font_size = ctk.CTkEntry(row_f, width=50, height=36)
        self.ubuntu_font_size.insert(0, str(font_size))
        self.ubuntu_font_size.pack(side="left", padx=(0, 8))
        ctk.CTkButton(row_f, text="Appliquer", width=100, command=lambda: self._apply_font()).pack(side="left")

    def _apply_font(self) -> None:
        try:
            from core.ubuntu_customizer import set_font
            name = self.ubuntu_font.get().strip()
            size = int(self.ubuntu_font_size.get().strip() or 11)
            set_font(name, size)
            set_key(self._config, name, "ubuntu_custom", "font_name")
            set_key(self._config, size, "ubuntu_custom", "font_size")
            self._save()
        except (ImportError, ValueError):
            pass

    def _build_notifications(self) -> None:
        tab = self.tabview.tab("Notifications")
        ctk.CTkSwitch(tab, text="Notifications système (notify-send)", font=ctk.CTkFont(size=12)).pack(anchor="w", pady=8)
        ctk.CTkSwitch(tab, text="Sons de notification", font=ctk.CTkFont(size=12)).pack(anchor="w", pady=8)
        ctk.CTkLabel(tab, text="Verbosité", font=ctk.CTkFont(size=11), text_color=COLORS["text_dim"]).pack(anchor="w", pady=(16, 4))
        ctk.CTkOptionMenu(tab, values=["Tout", "Standard", "Critique", "Silence"], width=200).pack(anchor="w", pady=4)

    def _build_about(self) -> None:
        tab = self.tabview.tab("À propos")
        ctk.CTkLabel(tab, text="⬡ Affinity", font=ctk.CTkFont(size=24, weight="bold")).pack(pady=16)
        ctk.CTkLabel(tab, text=f"Version {VERSION}", font=ctk.CTkFont(size=12), text_color=COLORS["text_dim"]).pack(pady=4)
        ctk.CTkLabel(tab, text="Votre compagnon système intelligent pour Ubuntu.", font=ctk.CTkFont(size=12), text_color=COLORS["text_mid"]).pack(pady=8)
        ctk.CTkLabel(
            tab,
            text="Created by l-vs",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=COLORS["cyan"],
        ).pack(pady=4)
        ctk.CTkLabel(tab, text="Open-source · Entièrement personnalisable · Licence MIT", font=ctk.CTkFont(size=11), text_color=COLORS["text_dim"]).pack(pady=4)
        ctk.CTkButton(tab, text="📂 Ouvrir le dossier de données", font=ctk.CTkFont(size=12), fg_color="transparent", command=lambda: self._open_data_dir()).pack(pady=8)
        ctk.CTkLabel(tab, text="Licence MIT · Fait avec ❤️ pour Linux.", font=ctk.CTkFont(size=11), text_color=COLORS["text_dim"]).pack(pady=16)

    def _open_data_dir(self) -> None:
        try:
            import subprocess
            subprocess.run(["xdg-open", str(DATA_DIR)], check=False)
        except Exception:
            pass
