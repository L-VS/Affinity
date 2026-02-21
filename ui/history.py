"""Affinity — Onglet Historique (timeline)."""

import customtkinter as ctk
from datetime import datetime
from pathlib import Path

from config import COLORS
from database import get_recent_events


def _time_ago(ts: str) -> str:
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00").replace(" ", "T"))
        if dt.tzinfo:
            dt = dt.replace(tzinfo=None)
        delta = datetime.now() - dt
        if delta.days > 0:
            return f"il y a {delta.days}j"
        h = delta.seconds // 3600
        if h > 0:
            return f"il y a {h}h"
        m = delta.seconds // 60
        return f"il y a {m}min" if m > 0 else "à l'instant"
    except Exception:
        return ""


def _format_date(ts: str) -> str:
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00").replace(" ", "T"))
        return dt.strftime("%H:%M")
    except Exception:
        return ""


TYPE_LABELS = {
    "clean": "NETTOYAGE",
    "security": "SÉCURITÉ",
    "device": "PÉRIPHÉRIQUE",
    "system": "SYSTÈME",
    "optimize": "OPTIMISATION",
    "ai": "IA",
}


class HistoryFrame(ctk.CTkScrollableFrame):
    """Onglet Historique avec timeline."""

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self._build_ui()

    def _build_ui(self) -> None:
        ctk.CTkLabel(
            self,
            text="Historique",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=COLORS["text"],
        ).pack(anchor="w", pady=(0, 16))

        self.chip_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.chip_frame.pack(fill="x", pady=(0, 12))
        chips = [("Tous", None)] + [
            ("🧹 Nettoyage", "clean"),
            ("🛡 Sécurité", "security"),
            ("🔌 Périphériques", "device"),
        ]
        self._filter = None
        self._chips = []
        for label, ftype in chips:
            c = ctk.CTkButton(
                self.chip_frame,
                text=label,
                font=ctk.CTkFont(size=11),
                fg_color="transparent",
                text_color=COLORS["text_dim"],
                width=100,
                height=28,
                command=lambda t=ftype: self._set_filter(t),
            )
            c.pack(side="left", padx=4)
            self._chips.append((ftype, c))

        self.timeline = ctk.CTkFrame(self, fg_color="transparent")
        self.timeline.pack(fill="both", expand=True)
        self._set_filter(None)

    def _set_filter(self, ftype) -> None:
        self._filter = ftype
        for chip_ftype, btn in self._chips:
            active = (ftype is None and chip_ftype is None) or (ftype == chip_ftype)
            btn.configure(
                fg_color=COLORS["cyan_soft"] if active else "transparent",
                text_color=COLORS["cyan"] if active else COLORS["text_dim"],
            )
        self._refresh()

    def _refresh(self) -> None:
        for w in self.timeline.winfo_children():
            w.destroy()
        events = get_recent_events(50)
        if self._filter:
            events = [e for e in events if e.get("type") == self._filter]
        if not events:
            ctk.CTkLabel(
                self.timeline,
                text="Aucun événement.",
                font=ctk.CTkFont(size=12),
                text_color=COLORS["text_dim"],
            ).pack(anchor="w", pady=20)
            return
        current_day = None
        severity_colors = {"info": COLORS["cyan"], "warning": COLORS["orange"], "alert": COLORS["red"]}
        for ev in events:
            ts = ev.get("timestamp", "")
            try:
                s = ts.replace(" ", "T")[:19]
                dt = datetime.fromisoformat(s)
                day_str = dt.strftime("%A %d %B")
            except Exception:
                day_str = ""
            if day_str != current_day:
                current_day = day_str
                sep = ctk.CTkFrame(self.timeline, fg_color="transparent")
                sep.pack(fill="x", pady=(16, 8))
                ctk.CTkLabel(sep, text=day_str, font=ctk.CTkFont(size=11, weight="bold"), text_color=COLORS["text_dim"]).pack(anchor="center")
            card = ctk.CTkFrame(self.timeline, fg_color=COLORS["bg_card"], corner_radius=10, border_width=1, border_color=COLORS["border"])
            card.pack(fill="x", pady=4)
            row = ctk.CTkFrame(card, fg_color="transparent")
            row.pack(fill="x", padx=12, pady=10)
            ctk.CTkLabel(row, text=_format_date(ts), font=ctk.CTkFont(family="monospace", size=11), text_color=COLORS["text_dim"], width=45).pack(side="left")
            c = severity_colors.get(ev.get("severity", "info"), COLORS["cyan"])
            ctk.CTkLabel(row, text="●", font=ctk.CTkFont(size=12), text_color=c).pack(side="left", padx=8)
            ctk.CTkLabel(row, text=f"{ev.get('title', '?')} · {ev.get('description', '')[:40]}", font=ctk.CTkFont(size=12)).pack(side="left", fill="x", expand=True)
            t = ev.get("type", "")
            badge_color = COLORS["green_soft"] if t == "clean" else COLORS["cyan_soft"]
            ctk.CTkLabel(row, text=TYPE_LABELS.get(t, t.upper()), font=ctk.CTkFont(size=10), text_color=COLORS["text_mid"], fg_color=badge_color, corner_radius=4, padx=6, pady=2).pack(side="right")
