"""Affinity — Guide d'onboarding au premier lancement."""

import customtkinter as ctk
from config import COLORS, DATA_DIR
from config_loader import load_config, save_config, set_key


class OnboardingWindow(ctk.CTkToplevel):
    """Fenêtre d'onboarding en plusieurs étapes."""

    def __init__(self, parent, on_complete=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.on_complete = on_complete
        self.configure(fg_color=COLORS["bg"])
        self.title("Bienvenue dans Affinity")
        self.geometry("520x420")
        self.resizable(False, False)
        self._config = load_config()
        self._step = 0
        self._build_ui()

    def _build_ui(self) -> None:
        self.content = ctk.CTkFrame(self, fg_color="transparent")
        self.content.pack(fill="both", expand=True, padx=40, pady=30)

        ctk.CTkLabel(
            self.content,
            text="⬡ Affinity",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color=COLORS["text"],
        ).pack(pady=(0, 8))
        ctk.CTkLabel(
            self.content,
            text="Compagnon système intelligent pour Ubuntu\nCreated by l-vs",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_dim"],
            justify="center",
        ).pack(pady=(0, 24))

        self.step_frame = ctk.CTkFrame(self.content, fg_color="transparent")
        self.step_frame.pack(fill="both", expand=True)
        self._show_step(0)

        self.btn_frame = ctk.CTkFrame(self.content, fg_color="transparent")
        self.btn_frame.pack(fill="x", pady=(20, 0))
        self.prev_btn = ctk.CTkButton(
            self.btn_frame,
            text="← Précédent",
            fg_color="transparent",
            command=self._prev,
        )
        self.prev_btn.pack(side="left", padx=4)
        self.prev_btn.configure(state="disabled")
        self.next_btn = ctk.CTkButton(
            self.btn_frame,
            text="Suivant →",
            fg_color=COLORS["cyan"],
            text_color="#001F2E",
            command=self._next,
        )
        self.next_btn.pack(side="right", padx=4)

    def _clear_step(self) -> None:
        for w in self.step_frame.winfo_children():
            w.destroy()

    def _show_step(self, step: int) -> None:
        self._clear_step()
        self._step = step
        self.prev_btn.configure(state="disabled" if step == 0 else "normal")

        if step == 0:
            ctk.CTkLabel(self.step_frame, text="Comment vous appelez-vous ?", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", pady=8)
            self.name_entry = ctk.CTkEntry(self.step_frame, width=300, height=40, placeholder_text="Votre prénom")
            self.name_entry.pack(anchor="w", pady=8)
            ctk.CTkLabel(
                self.step_frame,
                text="Ceci permettra d'afficher une salutation personnalisée.",
                font=ctk.CTkFont(size=11),
                text_color=COLORS["text_dim"],
            ).pack(anchor="w", pady=4)
        elif step == 1:
            ctk.CTkLabel(self.step_frame, text="Recommandations", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", pady=8)
            ctk.CTkLabel(
                self.step_frame,
                text="Cochez ce que vous autorisez Affinity à faire automatiquement :",
                font=ctk.CTkFont(size=11),
                text_color=COLORS["text_dim"],
            ).pack(anchor="w", pady=4)
            self.rec_usb = ctk.CTkCheckBox(self.step_frame, text="Analyser les clés USB à la connexion", font=ctk.CTkFont(size=12))
            self.rec_usb.pack(anchor="w", pady=4)
            self.rec_usb.select()
            self.rec_watch = ctk.CTkCheckBox(self.step_frame, text="Surveiller les dossiers sensibles (Downloads, etc.)", font=ctk.CTkFont(size=12))
            self.rec_watch.pack(anchor="w", pady=4)
            self.rec_watch.select()
        elif step == 2:
            ctk.CTkLabel(self.step_frame, text="Configuration Groq (Assistant IA)", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", pady=8)
            ctk.CTkLabel(
                self.step_frame,
                text="Optionnel. Vous pourrez configurer plus tard dans Paramètres > IA.",
                font=ctk.CTkFont(size=11),
                text_color=COLORS["text_dim"],
            ).pack(anchor="w", pady=4)
            ctk.CTkButton(
                self.step_frame,
                text="Créer un compte Groq gratuit",
                fg_color=COLORS["cyan"],
                text_color="#001F2E",
                command=lambda: __import__("subprocess").run(["xdg-open", "https://console.groq.com"], check=False),
            ).pack(anchor="w", pady=8)
            self.groq_entry = ctk.CTkEntry(self.step_frame, width=400, height=36, placeholder_text="Collez votre clé API (optionnel)")
            self.groq_entry.pack(anchor="w", pady=8)
        else:
            ctk.CTkLabel(self.step_frame, text="Prêt !", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=16)
            ctk.CTkLabel(
                self.step_frame,
                text="Affinity est configuré. Explorez les onglets pour découvrir les fonctionnalités.",
                font=ctk.CTkFont(size=12),
                text_color=COLORS["text_mid"],
                justify="center",
            ).pack(pady=8)
            self.next_btn.configure(text="Terminer")

    def _prev(self) -> None:
        if self._step > 0:
            self._show_step(self._step - 1)
            self.next_btn.configure(text="Suivant →")

    def _next(self) -> None:
        if self._step == 0:
            set_key(self._config, self.name_entry.get().strip(), "profile", "first_name")
            save_config(self._config)
        elif self._step == 1:
            set_key(self._config, self.rec_usb.get(), "recommendations", "usb_scan")
            set_key(self._config, self.rec_watch.get(), "recommendations", "realtime_watch")
            save_config(self._config)
        elif self._step == 2:
            k = self.groq_entry.get().strip() if hasattr(self, "groq_entry") else ""
            if k:
                set_key(self._config, k, "ai", "groq_api_key")
                set_key(self._config, True, "ai", "enabled")
                save_config(self._config)
        elif self._step == 3:
            set_key(self._config, True, "onboarding_complete")
            save_config(self._config)
            if self.on_complete:
                self.on_complete()
            self.destroy()
            return
        self._show_step(self._step + 1)


def should_show_onboarding() -> bool:
    """Retourne True si l'onboarding doit être affiché."""
    cfg = load_config()
    return not cfg.get("onboarding_complete", False)
