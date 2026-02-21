"""Affinity — Fenêtre de progression du scan."""

import time
import customtkinter as ctk
from config import COLORS


class ScanProgressWindow(ctk.CTkToplevel):
    """Fenêtre modale affichée pendant un scan."""

    def __init__(self, parent, scan_type: str = "rapide", cancel_callback=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.title("🔍 Scan en cours")
        self.geometry("500x320")
        self.resizable(False, False)
        self.configure(fg_color=COLORS["bg"])
        self.cancel_callback = cancel_callback
        self._start_time = time.time()
        self._cancel_flag = None

        self.attributes("-topmost", True)
        self.transient(parent)
        self.grab_set()

        ctk.CTkLabel(
            self,
            text=f"Scan {scan_type} · Démarré à {time.strftime('%H:%M')}",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_dim"],
        ).pack(anchor="w", padx=24, pady=(20, 8))

        self.progress_bar = ctk.CTkProgressBar(self, width=450, height=8)
        self.progress_bar.pack(padx=24, pady=8)
        self.progress_bar.set(0)

        self.stats_label = ctk.CTkLabel(
            self,
            text="0 / 0 fichiers analysés",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_dim"],
        )
        self.stats_label.pack(anchor="w", padx=24, pady=(0, 4))

        self.current_label = ctk.CTkLabel(
            self,
            text="En attente...",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_mid"],
        )
        self.current_label.pack(anchor="w", padx=24, pady=(0, 12))

        ctk.CTkLabel(
            self,
            text="Résultats en temps réel :",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=COLORS["text_dim"],
        ).pack(anchor="w", padx=24, pady=(0, 4))

        self.results_frame = ctk.CTkScrollableFrame(self, height=100, fg_color=COLORS["bg_card"])
        self.results_frame.pack(fill="x", padx=24, pady=(0, 12))

        self.threats_label = ctk.CTkLabel(
            self,
            text="Menaces trouvées : 0",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["green"],
        )
        self.threats_label.pack(side="left", padx=24, pady=(0, 16))

        self.time_label = ctk.CTkLabel(
            self,
            text="Temps : 00:00",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_dim"],
        )
        self.time_label.pack(side="right", padx=24, pady=(0, 16))

        ctk.CTkButton(
            self,
            text="✕ Annuler",
            font=ctk.CTkFont(size=12),
            fg_color=COLORS["red_soft"],
            text_color=COLORS["red"],
            width=100,
            command=self._on_cancel,
        ).pack(side="right", padx=8, pady=(0, 16))

    def _on_cancel(self) -> None:
        if self._cancel_flag:
            self._cancel_flag.set()
        if self.cancel_callback:
            self.cancel_callback()
        self.destroy()

    def set_cancel_flag(self, flag) -> None:
        """Définit le threading.Event pour annuler le scan."""
        self._cancel_flag = flag

    def update_progress(self, current: int, total: int, current_file: str = "", threats: int = 0) -> None:
        """Met à jour la barre et les labels."""
        if total > 0:
            self.progress_bar.set(current / total)
        self.stats_label.configure(text=f"{current} / {total} fichiers analysés")
        if current_file:
            short = current_file.replace(str(__import__("pathlib").Path.home()), "~")
            self.current_label.configure(text=short[-50:] if len(short) > 50 else short)
        self.threats_label.configure(
            text=f"Menaces trouvées : {threats}",
            text_color=COLORS["green"] if threats == 0 else COLORS["orange"],
        )
        elapsed = int(time.time() - self._start_time)
        self.time_label.configure(text=f"Temps : {elapsed // 60:02d}:{elapsed % 60:02d}")

    def add_result(self, filepath: str, verdict: str) -> None:
        """Ajoute une ligne dans la liste des résultats."""
        short = filepath.replace(str(__import__("pathlib").Path.home()), "~")
        if len(short) > 55:
            short = "..." + short[-52:]
        icon = "✅" if verdict == "clean" else "⚠️"
        color = COLORS["green"] if verdict == "clean" else COLORS["orange"]
        lbl = ctk.CTkLabel(
            self.results_frame,
            text=f"{icon} {short} · {verdict}",
            font=ctk.CTkFont(size=10),
            text_color=color,
            anchor="w",
        )
        lbl.pack(anchor="w", padx=8, pady=2)

    def on_complete(self, files_scanned: int, threats_found: int) -> None:
        """Appelé quand le scan est terminé."""
        self.grab_release()
        self.title("Scan terminé ✓")
        self.progress_bar.set(1)
        self.stats_label.configure(text=f"Terminé · {files_scanned} fichiers · {threats_found} menace(s)")
        self.current_label.configure(text="")
        self.threats_label.configure(
            text=f"Menaces : {threats_found}",
            text_color=COLORS["green"] if threats_found == 0 else COLORS["orange"],
        )
        for w in self.winfo_children():
            if isinstance(w, ctk.CTkButton) and "Annuler" in str(w.cget("text")):
                w.configure(text="Fermer", command=self.destroy)
                break
