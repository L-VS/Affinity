"""Affinity — Onglet Nettoyage système."""

import threading
import customtkinter as ctk
from pathlib import Path

from config import COLORS

from core.cleaner_engine import (
    format_size,
    scan_all,
    clean_category,
    find_duplicates,
    find_large_files,
)


class CleanerFrame(ctk.CTkScrollableFrame):
    """Frame d'onglet Nettoyage."""

    def __init__(self, master, **kwargs):
        super().__init__(
            master,
            fg_color="transparent",
            **kwargs,
        )
        self.grid_columnconfigure(0, weight=1)
        self.results: list[dict] = []
        self.selection: dict[str, bool] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        """Construit l'interface."""
        # En-tête
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text="Nettoyage système",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=COLORS["text"],
        ).grid(row=0, column=0, sticky="w")

        self.subtitle_label = ctk.CTkLabel(
            header,
            text="Cliquez sur Analyser pour scanner votre système.",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_dim"],
        )
        self.subtitle_label.grid(row=1, column=0, sticky="w")

        btn_frame = ctk.CTkFrame(header, fg_color="transparent")
        btn_frame.grid(row=0, column=1, rowspan=2, padx=(20, 0))
        self.scan_btn = ctk.CTkButton(
            btn_frame,
            text="▷ Analyser maintenant",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=COLORS["cyan"],
            text_color="#001F2E",
            hover_color="#00B8B8",
            height=40,
            width=200,
            command=self._on_scan,
        )
        self.scan_btn.pack(side="left", padx=4)
        ctk.CTkButton(
            btn_frame,
            text="🔁 Doublons",
            font=ctk.CTkFont(size=12),
            fg_color=COLORS["bg_card"],
            border_width=1,
            border_color=COLORS["border"],
            height=36,
            width=100,
            command=self._on_find_duplicates,
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            btn_frame,
            text="📊 Gros fichiers",
            font=ctk.CTkFont(size=12),
            fg_color=COLORS["bg_card"],
            border_width=1,
            border_color=COLORS["border"],
            height=36,
            width=110,
            command=self._on_find_large,
        ).pack(side="left", padx=4)

        # Zone des cartes (grille 3 colonnes)
        self.cards_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.cards_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 16))
        self.cards_frame.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Message initial
        self.empty_label = ctk.CTkLabel(
            self.cards_frame,
            text="Aucune analyse effectuée.\nCliquez sur « Analyser maintenant » pour commencer.",
            font=ctk.CTkFont(size=14),
            text_color=COLORS["text_dim"],
            justify="center",
        )

        # Barre d'action (sticky en bas)
        self.action_bar = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], corner_radius=12)
        self.action_bar.grid(row=2, column=0, sticky="ew", pady=(0, 0))
        self.action_bar.grid_columnconfigure(0, weight=1)

        self.total_label = ctk.CTkLabel(
            self.action_bar,
            text="Sélectionné : 0 Mo",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=COLORS["green"],
        )
        self.total_label.pack(side="left", padx=18, pady=14)

        self.clean_btn = ctk.CTkButton(
            self.action_bar,
            text="🧹 Nettoyer la sélection",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=COLORS["cyan"],
            text_color="#001F2E",
            hover_color="#00B8B8",
            height=40,
            state="disabled",
            command=self._on_clean,
        )
        self.clean_btn.pack(side="right", padx=18, pady=14)

    def _on_scan(self) -> None:
        """Lance l'analyse."""
        self.scan_btn.configure(state="disabled", text="Analyse en cours...")
        self.empty_label.place_forget()
        self._clear_cards()

        def do_scan():
            self.results = []
            self.selection = {}

            def progress(name: str, current: int, total: int):
                self.after(
                    0,
                    lambda: self.subtitle_label.configure(
                        text=f"Analyse : {name} ({current}/{total})"
                    ),
                )

            self.results = scan_all(progress_callback=progress)

            def update_ui():
                self._show_results()
                self.scan_btn.configure(state="normal", text="▷ Re-analyser")

            self.after(0, update_ui)

        self.after(100, lambda: self._run_async(do_scan))

    def _run_async(self, func) -> None:
        """Exécute une fonction dans un thread (simplifié, synchrone pour l'instant)."""
        import threading

        threading.Thread(target=func, daemon=True).start()

    def _clear_cards(self) -> None:
        """Supprime les cartes existantes."""
        for w in self.cards_frame.winfo_children():
            w.destroy()

    def _show_results(self) -> None:
        """Affiche les résultats sous forme de cartes."""
        self._clear_cards()

        if not self.results:
            self.empty_label.place(relx=0.5, rely=0.5, anchor="center")
            return

        total_recoverable = sum(r["size_bytes"] for r in self.results)
        self.subtitle_label.configure(
            text=f"Total récupérable : {format_size(total_recoverable)}"
        )

        for i, res in enumerate(self.results):
            row, col = divmod(i, 3)
            card = self._make_card(res, row, col)
            self.selection[res["id"]] = res["safe"]

        self._update_total()

    def _make_card(self, res: dict, row: int, col: int) -> ctk.CTkFrame:
        """Crée une carte de catégorie."""
        card = ctk.CTkFrame(
            self.cards_frame,
            fg_color=COLORS["bg_card"],
            corner_radius=12,
            border_width=1,
            border_color=COLORS["border"],
        )
        card.grid(row=row, column=col, sticky="nsew", padx=6, pady=6)
        self.cards_frame.grid_columnconfigure(col, weight=1)

        var = ctk.BooleanVar(value=res["safe"])

        def on_toggle(*_):
            self.selection[res["id"]] = var.get()
            self._update_total()

        var.trace_add("write", on_toggle)

        ctk.CTkLabel(
            card,
            text=res["icon"],
            font=ctk.CTkFont(size=22),
            text_color=COLORS["text"],
        ).pack(anchor="w", padx=14, pady=(14, 4))

        ctk.CTkLabel(
            card,
            text=res["name"],
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLORS["text"],
        ).pack(anchor="w", padx=14, pady=(0, 2))

        size_str = format_size(res["size_bytes"])
        ctk.CTkLabel(
            card,
            text=size_str,
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=COLORS["cyan"],
        ).pack(anchor="w", padx=14, pady=(0, 4))

        path_short = res["paths"][0].replace(str(__import__("pathlib").Path.home()), "~")
        ctk.CTkLabel(
            card,
            text=path_short[:40] + ("..." if len(path_short) > 40 else ""),
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_dim"],
        ).pack(anchor="w", padx=14, pady=(0, 8))

        tag_color = COLORS["green"] if res["safe"] else COLORS["orange"]
        tag_text = "Sûr" if res["safe"] else "Confirmer"
        row2 = ctk.CTkFrame(card, fg_color="transparent")
        row2.pack(fill="x", padx=14, pady=(0, 14))
        ctk.CTkLabel(
            row2,
            text=tag_text,
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=tag_color,
        ).pack(side="left")
        cb = ctk.CTkCheckBox(
            row2,
            text="Inclure",
            variable=var,
            width=20,
            height=20,
            checkbox_width=20,
            checkbox_height=20,
        )
        cb.pack(side="right")

        return card

    def _update_total(self) -> None:
        """Met à jour le total sélectionné."""
        total = sum(
            r["size_bytes"]
            for r in self.results
            if self.selection.get(r["id"], False)
        )
        self.total_label.configure(text=f"Sélectionné : {format_size(total)}")
        self.clean_btn.configure(state="normal" if total > 0 else "disabled")

    def _on_clean(self) -> None:
        """Lance le nettoyage des catégories sélectionnées."""
        to_clean = [
            r for r in self.results
            if self.selection.get(r["id"], False)
        ]
        if not to_clean:
            return

        self.clean_btn.configure(state="disabled", text="Nettoyage...")
        total_freed = 0

        def do_clean():
            nonlocal total_freed
            for res in to_clean:
                freed = clean_category(res)
                total_freed += freed

            def done():
                self.clean_btn.configure(
                    state="normal",
                    text="🧹 Nettoyer la sélection",
                )
                self.subtitle_label.configure(
                    text=f"Nettoyage terminé. {format_size(total_freed)} libérés."
                )
                self._on_scan()

            self.after(0, done)

        self._run_async(do_clean)

    def _on_find_duplicates(self) -> None:
        """Lance la recherche de doublons dans Documents, Images, Téléchargements."""
        roots = [
            Path.home() / "Documents",
            Path.home() / "Pictures",
            Path.home() / "Images",
            Path.home() / "Téléchargements",
        ]
        win = ctk.CTkToplevel(self.winfo_toplevel())
        win.title("Recherche de doublons")
        win.geometry("500x400")
        win.configure(fg_color=COLORS["bg"])
        ctk.CTkLabel(win, text="Recherche en cours...", font=ctk.CTkFont(size=12)).pack(pady=20)
        area = ctk.CTkScrollableFrame(win, fg_color="transparent")
        area.pack(fill="both", expand=True, padx=16, pady=8)

        def do():
            dupes = find_duplicates(roots, min_size_bytes=1024 * 1024)
            def show():
                for w in win.winfo_children():
                    w.destroy()
                ctk.CTkLabel(win, text=f"Doublons trouvés : {len(dupes)} groupe(s)", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=12)
                scroll = ctk.CTkScrollableFrame(win, fg_color="transparent")
                scroll.pack(fill="both", expand=True, padx=16, pady=8)
                for d in dupes[:20]:
                    card = ctk.CTkFrame(scroll, fg_color=COLORS["bg_card"], corner_radius=8)
                    card.pack(fill="x", pady=4)
                    ctk.CTkLabel(card, text=f"{format_size(d['size'])} · {d['count']} exemplaires", font=ctk.CTkFont(size=12)).pack(anchor="w", padx=12, pady=8)
                    for p in d["paths"][:3]:
                        short = p.replace(str(Path.home()), "~")
                        ctk.CTkLabel(card, text=f"  {short[:60]}...", font=ctk.CTkFont(size=10), text_color=COLORS["text_dim"]).pack(anchor="w", padx=12)
            self.after(0, show)

        threading.Thread(target=do, daemon=True).start()

    def _on_find_large(self) -> None:
        """Lance la recherche des gros fichiers (>100 Mo)."""
        roots = [str(Path.home())]
        win = ctk.CTkToplevel(self.winfo_toplevel())
        win.title("Gros fichiers")
        win.geometry("550x450")
        win.configure(fg_color=COLORS["bg"])
        ctk.CTkLabel(win, text="Recherche en cours...", font=ctk.CTkFont(size=12)).pack(pady=20)
        area = ctk.CTkScrollableFrame(win, fg_color="transparent")
        area.pack(fill="both", expand=True, padx=16, pady=8)

        def do():
            large = find_large_files(roots, min_size_bytes=100 * 1024 * 1024, top_n=50)
            def show():
                for w in win.winfo_children():
                    w.destroy()
                ctk.CTkLabel(win, text=f"Top 50 fichiers > 100 Mo", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=12)
                scroll = ctk.CTkScrollableFrame(win, fg_color="transparent")
                scroll.pack(fill="both", expand=True, padx=16, pady=8)
                for item in large:
                    card = ctk.CTkFrame(scroll, fg_color=COLORS["bg_card"], corner_radius=8)
                    card.pack(fill="x", pady=4)
                    short = item["path"].replace(str(Path.home()), "~")
                    ctk.CTkLabel(card, text=f"{format_size(item['size'])} — {Path(item['path']).name}", font=ctk.CTkFont(size=12)).pack(anchor="w", padx=12, pady=8)
                    ctk.CTkLabel(card, text=f"  {short[:70]}...", font=ctk.CTkFont(size=10), text_color=COLORS["text_dim"]).pack(anchor="w", padx=12)
            self.after(0, show)

        threading.Thread(target=do, daemon=True).start()
