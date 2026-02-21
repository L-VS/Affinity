"""Affinity — Fenêtre principale et navigation."""

import customtkinter as ctk
from config import COLORS, SIDEBAR_WIDTH, WINDOW_HEIGHT, WINDOW_WIDTH
from config_loader import load_config, get
from core.monitor import SystemMonitor


class AffinityApp(ctk.CTk):
    """Application principale Affinity."""

    def __init__(self):
        super().__init__()
        self.title("Affinity")
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.minsize(800, 500)

        # Thème dark
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.configure(fg_color=COLORS["bg"])

        # Conteneur principal
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar
        self._create_sidebar()
        # Zone de contenu
        self._create_content()
        # Barre de statut
        self._create_statusbar()

        # Fermeture → minimize to tray (sera implémenté avec tray)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _create_sidebar(self) -> None:
        """Crée la barre latérale de navigation."""
        self.sidebar = ctk.CTkFrame(
            self,
            width=SIDEBAR_WIDTH,
            corner_radius=0,
            fg_color=COLORS["sidebar"],
            border_width=0,
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        # Logo
        logo_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo_frame.pack(pady=20, padx=20, fill="x")
        ctk.CTkLabel(
            logo_frame,
            text="⬡ Affinity",
            font=ctk.CTkFont(family="Sans", size=18, weight="bold"),
            text_color=COLORS["text"],
        ).pack(side="left")
        cfg = load_config()
        first = get(cfg, "profile", "first_name") or ""
        greet = f"Bonjour, {first} 👋" if first else "Bonjour 👋"
        self.sidebar_greet = ctk.CTkLabel(
            logo_frame,
            text=greet,
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_dim"],
        )
        self.sidebar_greet.pack(side="left", padx=(10, 0))

        # Section Navigation
        ctk.CTkLabel(
            self.sidebar,
            text="NAVIGATION",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=COLORS["text_dim"],
        ).pack(anchor="w", padx=20, pady=(24, 6))

        nav_items = [
            ("⊞", "Tableau de bord", "dashboard"),
            ("✧", "Nettoyage", "clean"),
            ("⬡", "Sécurité", "security"),
            ("⟁", "Système", "system"),
            ("🕒", "Automatisations", "automation"),
        ]
        self.nav_buttons = {}
        for icon, label, page_id in nav_items:
            btn = ctk.CTkButton(
                self.sidebar,
                text=f"{icon}  {label}",
                font=ctk.CTkFont(size=13),
                fg_color="transparent",
                text_color=COLORS["text_dim"],
                anchor="w",
                height=36,
                corner_radius=10,
                hover_color=COLORS["bg_hover"],
                command=lambda p=page_id: self.show_frame(p),
            )
            btn.pack(fill="x", padx=12, pady=2)
            self.nav_buttons[page_id] = btn

        # Section Outils
        ctk.CTkLabel(
            self.sidebar,
            text="OUTILS",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=COLORS["text_dim"],
        ).pack(anchor="w", padx=20, pady=(24, 6))

        tool_items = [
            ("⊚", "Historique", "history"),
            ("⬙", "Assistant IA", "ai"),
            ("⚙", "Paramètres", "settings"),
        ]
        for icon, label, page_id in tool_items:
            btn = ctk.CTkButton(
                self.sidebar,
                text=f"{icon}  {label}",
                font=ctk.CTkFont(size=13),
                fg_color="transparent",
                text_color=COLORS["text_dim"],
                anchor="w",
                height=36,
                corner_radius=10,
                hover_color=COLORS["bg_hover"],
                command=lambda p=page_id: self.show_frame(p),
            )
            btn.pack(fill="x", padx=12, pady=2)
            self.nav_buttons[page_id] = btn

        # Statut monitoring
        status_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        status_frame.pack(side="bottom", fill="x", padx=20, pady=20)
        ctk.CTkLabel(
            status_frame,
            text="● Monitoring actif",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["green"],
        ).pack(anchor="w")
        ctk.CTkLabel(
            status_frame,
            text="Created by l-vs",
            font=ctk.CTkFont(size=9),
            text_color=COLORS["text_dim"],
        ).pack(anchor="w")

    def _create_content(self) -> None:
        """Crée la zone de contenu avec les frames par onglet."""
        self.content = ctk.CTkFrame(
            self,
            fg_color=COLORS["bg"],
            corner_radius=0,
            border_width=0,
        )
        self.content.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(1, weight=1)

        # Barre de titre
        self.title_frame = ctk.CTkFrame(self.content, fg_color="transparent")
        self.title_frame.grid(row=0, column=0, sticky="ew", padx=24, pady=14)
        self.title_frame.grid_columnconfigure(0, weight=1)
        self.page_title = ctk.CTkLabel(
            self.title_frame,
            text="Tableau de bord",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=COLORS["text"],
        )
        self.page_title.grid(row=0, column=0, sticky="w")
        self.page_subtitle = ctk.CTkLabel(
            self.title_frame,
            text="Vendredi 21 février 2026",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_dim"],
        )
        self.page_subtitle.grid(row=1, column=0, sticky="w")

        # Container des pages
        self.frames = {}
        self.pages_container = ctk.CTkFrame(
            self.content, fg_color="transparent"
        )
        self.pages_container.grid(row=1, column=0, sticky="nsew", padx=24, pady=(0, 24))
        self.pages_container.grid_columnconfigure(0, weight=1)
        self.pages_container.grid_rowconfigure(0, weight=1)

        page_titles = {
            ("dashboard", "État du système en temps réel"),
            "clean": ("Nettoyage", "Libérez de l'espace disque"),
            "security": ("Sécurité", "Périphériques et analyse"),
            "system": ("Système", "Optimisation et profils"),
            "automation": ("Automatisations", "Tâches planifiées"),
            "history": ("Historique", "Timeline des actions"),
            "ai": ("Assistant IA", "Conseil et analyse"),
            "settings": ("Paramètres", "Préférences"),
        }
        from ui.ai_tab import AiTabFrame
        from ui.cleaner import CleanerFrame
        from ui.dashboard import DashboardFrame
        from ui.history import HistoryFrame
        from ui.security import SecurityFrame
        from ui.settings_tab import SettingsFrame
        from ui.system_tab import SystemFrame
        from ui.automation_tab import AutomationTabFrame

        def nav(page_id: str) -> None:
            self.show_frame(page_id)

        for page_id, (title, subtitle) in page_titles.items():
            if page_id == "clean":
                frame = CleanerFrame(self.pages_container)
            elif page_id == "security":
                frame = SecurityFrame(self.pages_container)
            elif page_id == "dashboard":
                frame = DashboardFrame(self.pages_container, navigate_cb=nav)
            elif page_id == "history":
                frame = HistoryFrame(self.pages_container)
            elif page_id == "system":
                frame = SystemFrame(self.pages_container)
            elif page_id == "automation":
                frame = AutomationTabFrame(self.pages_container)
            elif page_id == "settings":
                frame = SettingsFrame(self.pages_container)
            elif page_id == "ai":
                frame = AiTabFrame(
                    self.pages_container,
                    get_metrics_cb=lambda: self._metrics,
                )
            else:
                frame = ctk.CTkFrame(
                    self.pages_container,
                    fg_color=COLORS["bg_card"],
                    corner_radius=16,
                    border_width=1,
                    border_color=COLORS["border"],
                )
                frame.grid_columnconfigure(0, weight=1)
                frame.grid_rowconfigure(0, weight=1)
                ctk.CTkLabel(
                    frame,
                    text=title,
                    font=ctk.CTkFont(size=16, weight="bold"),
                    text_color=COLORS["text"],
                ).place(relx=0.5, rely=0.5, anchor="center")
            self.frames[page_id] = frame

        self._metrics = {}
        self._monitor = SystemMonitor(self._on_metrics)
        self._monitor.start()

        self.show_frame("dashboard")

    def _create_statusbar(self) -> None:
        """Crée la barre de statut en bas."""
        self.statusbar = ctk.CTkFrame(
            self,
            height=24,
            fg_color=COLORS["sidebar"],
            corner_radius=0,
        )
        self.statusbar.grid(row=1, column=0, columnspan=2, sticky="ew")
        self.statusbar.grid_propagate(False)
        self.statusbar_label = ctk.CTkLabel(
            self.statusbar,
            text="● Monitoring actif  |  CPU: --  RAM: --  |  Disque: --",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_dim"],
        )
        self.statusbar_label.pack(side="left", padx=12, pady=2)

    def _on_metrics(self, metrics: dict) -> None:
        """Callback du monitor — met à jour dashboard et statusbar (thread-safe)."""
        self._metrics = metrics
        self.after(0, self._update_ui_from_metrics)

    def _update_ui_from_metrics(self) -> None:
        m = self._metrics
        cpu = m.get("cpu_percent", 0)
        ram = m.get("ram_percent", 0)
        disk = m.get("disk_percent", 0)
        self.statusbar_label.configure(
            text=f"● Monitoring actif  |  CPU: {cpu:.0f}%  RAM: {ram:.0f}%  |  Disque: {disk:.0f}%"
        )
        if "dashboard" in self.frames:
            frame = self.frames["dashboard"]
            if hasattr(frame, "update_metrics"):
                frame.update_metrics(m)

    def show_frame(self, page_id: str) -> None:
        """Affiche la frame correspondant à l'onglet sélectionné."""
        # Désactiver le highlight sur tous les boutons
        for pid, btn in self.nav_buttons.items():
            btn.configure(fg_color="transparent", text_color=COLORS["text_dim"])
        # Activer le bouton sélectionné
        if page_id in self.nav_buttons:
            self.nav_buttons[page_id].configure(
                fg_color=COLORS["cyan_soft"],
                text_color=COLORS["cyan"],
            )
        # Cacher toutes les frames
        for frame in self.frames.values():
            frame.grid_forget()
        # Afficher la frame demandée
        if page_id in self.frames:
            self.frames[page_id].grid(row=0, column=0, sticky="nsew")
        # Mettre à jour le titre
        titles = {
            "dashboard": ("Tableau de bord", "État du système"),
            "clean": ("Nettoyage", "Libérez de l'espace disque"),
            "security": ("Sécurité", "Périphériques et analyse"),
            "system": ("Système", "Optimisation et profils"),
            "automation": ("Automatisations", "Tâches planifiées"),
            "history": ("Historique", "Timeline des actions"),
            "ai": ("Assistant IA", "Conseil et analyse"),
            "settings": ("Paramètres", "Préférences"),
        }
        if page_id in titles:
            t, s = titles[page_id]
            self.page_title.configure(text=t)
            self.page_subtitle.configure(text=s)

    def _on_close(self) -> None:
        """Gère la fermeture (arrête le monitor puis quitte)."""
        if hasattr(self, "_monitor") and self._monitor:
            self._monitor.stop()
        self.destroy()


def run_app() -> None:
    """Lance l'application."""
    app = AffinityApp()
    app.mainloop()
