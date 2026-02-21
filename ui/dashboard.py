"""Affinity — Tableau de bord avec métriques temps réel."""

import customtkinter as ctk
from datetime import datetime
from config import COLORS

from database import get_recent_events


def _format_size(gb: float) -> str:
    if gb >= 1:
        return f"{gb:.1f} Go"
    return f"{gb * 1024:.0f} Mo"


def _time_ago(ts: str) -> str:
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        if hasattr(dt, "replace"):
            from datetime import timezone
            dt = dt.replace(tzinfo=None) if dt.tzinfo else dt
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


class DashboardFrame(ctk.CTkScrollableFrame):
    """Onglet Tableau de bord."""

    def __init__(self, master, navigate_cb=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.navigate = navigate_cb or (lambda x: None)
        self.grid_columnconfigure(0, weight=1)
        self._metrics = {}
        self._build_ui()

    def _build_ui(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        header.grid_columnconfigure(0, weight=1)

        left = ctk.CTkFrame(header, fg_color="transparent")
        left.grid(row=0, column=0, sticky="w")
        h = datetime.now().hour
        if 5 <= h < 12:
            greet = "Bonjour"
        elif 12 <= h < 18:
            greet = "Bonjour"
        elif 18 <= h < 22:
            greet = "Bonsoir"
        else:
            greet = "Bonne nuit"
        ctk.CTkLabel(
            left,
            text=f"{greet}, Henri. 👋",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=COLORS["text"],
        ).grid(row=0, column=0, sticky="w")
        self.clock_label = ctk.CTkLabel(
            left,
            text="",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_dim"],
        )
        self.clock_label.grid(row=1, column=0, sticky="w")
        self.context_label = ctk.CTkLabel(
            left,
            text="Votre système fonctionne parfaitement.",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["green"],
        )
        self.context_label.grid(row=2, column=0, sticky="w")

        self.score_label = ctk.CTkLabel(
            header,
            text="Score: —",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLORS["cyan"],
        )
        self.score_label.grid(row=0, column=1, sticky="e", padx=16)
        self._update_clock()

        self.metrics_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.metrics_frame.grid(row=1, column=0, sticky="ew", pady=(0, 16))
        self.metrics_frame.grid_columnconfigure(0, weight=1)
        for i in range(4):
            self.metrics_frame.grid_columnconfigure(i, weight=1)
        self._metric_cards = []
        for i, (title, key, color) in enumerate([
            ("CPU", "cpu", COLORS["green"]),
            ("RAM", "ram", COLORS["cyan"]),
            ("Disque", "disk", COLORS["orange"]),
            ("Réseau", "net", COLORS["blue"]),
        ]):
            card = self._make_metric_card(title, key, color)
            card.grid(row=0, column=i, sticky="nsew", padx=4, pady=4)
            self._metric_cards.append((key, card))

        # Section Modes Système
        mode_frame = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], corner_radius=16, border_width=1, border_color=COLORS["border"])
        mode_frame.grid(row=2, column=0, sticky="ew", pady=(0, 16))
        
        ctk.CTkLabel(mode_frame, text="⚡ Mode Système", font=ctk.CTkFont(size=13, weight="bold"), text_color=COLORS["text_mid"]).pack(anchor="w", padx=16, pady=(12, 8))
        
        modes_row = ctk.CTkFrame(mode_frame, fg_color="transparent")
        modes_row.pack(fill="x", padx=10, pady=(0, 12))
        
        try:
            from core.system_modes import SYSTEM_MODES, apply_mode
            self._mode_btns = {}
            for m in SYSTEM_MODES[:3]: # Eco, Balanced, Performance
                btn = ctk.CTkButton(
                    modes_row,
                    text=f"{m['icon']} {m['name']}",
                    font=ctk.CTkFont(size=12),
                    fg_color=COLORS["bg"] if m['id'] != "balanced" else COLORS["cyan_soft"],
                    text_color=COLORS["text"] if m['id'] != "balanced" else COLORS["cyan"],
                    width=120,
                    height=32,
                    command=lambda mid=m['id']: self._on_mode_change(mid)
                )
                btn.pack(side="left", padx=5)
                self._mode_btns[m['id']] = btn
        except ImportError:
            ctk.CTkLabel(modes_row, text="Modes non disponibles", font=ctk.CTkFont(size=11)).pack(padx=10)

        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.grid(row=3, column=0, sticky="nsew", pady=(0, 0))
        bottom.grid_columnconfigure(0, weight=3)
        bottom.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(3, weight=1)

        act_frame = ctk.CTkFrame(bottom, fg_color=COLORS["bg_card"], corner_radius=16, border_width=1, border_color=COLORS["border"])
        act_frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        act_frame.grid_columnconfigure(0, weight=1)
        act_frame.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(act_frame, text="⊚ Activité récente", font=ctk.CTkFont(size=13, weight="bold"), text_color=COLORS["text_mid"]).grid(row=0, column=0, sticky="w", padx=16, pady=12)
        self.activity_list = ctk.CTkScrollableFrame(act_frame, fg_color="transparent", height=150)
        self.activity_list.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 8))
        link = ctk.CTkLabel(act_frame, text="Voir l'historique complet →", font=ctk.CTkFont(size=11), text_color=COLORS["cyan"], cursor="hand2")
        link.grid(row=2, column=0, sticky="w", padx=16, pady=(0, 12))
        link.bind("<Button-1>", lambda e: self.navigate("history"))

        qa_frame = ctk.CTkFrame(bottom, fg_color=COLORS["bg_card"], corner_radius=16, border_width=1, border_color=COLORS["border"])
        qa_frame.grid(row=0, column=1, sticky="nsew", padx=(12, 0), pady=0)
        qa_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(qa_frame, text="⚡ Actions rapides", font=ctk.CTkFont(size=13, weight="bold"), text_color=COLORS["text_mid"]).grid(row=0, column=0, sticky="w", padx=16, pady=12)
        for icon, name, desc, page in [
            ("🧹", "Nettoyer", "Cache · Temp", "clean"),
            ("🔍", "Analyser", "Scan sécurité", "security"),
            ("⚡", "Optimiser", "Profil Performance", "system"),
            ("⬙", "Assistant IA", "Décrire une action", "ai"),
        ]:
            btn = ctk.CTkFrame(qa_frame, fg_color="transparent", cursor="hand2")
            btn.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(btn, text=f"{icon} {name}", font=ctk.CTkFont(size=13, weight="bold")).grid(row=0, column=0, sticky="w")
            ctk.CTkLabel(btn, text=desc, font=ctk.CTkFont(size=11), text_color=COLORS["text_dim"]).grid(row=1, column=0, sticky="w")
            btn.bind("<Button-1>", lambda e, p=page: self.navigate(p))
            for c in btn.winfo_children():
                c.bind("<Button-1>", lambda e, p=page: self.navigate(p))
            btn.grid(sticky="ew", padx=16, pady=4)

        self._refresh_activity()

    def _update_clock(self) -> None:
        fmt = datetime.now().strftime("%A %d %B %Y · %H:%M:%S")
        jours = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
        mois = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
        d = datetime.now()
        self.clock_label.configure(text=f"{jours[d.weekday()]} {d.day} {mois[d.month-1]} {d.year} · {d.strftime('%H:%M:%S')}")
        self.after(1000, self._update_clock)

    def _make_metric_card(self, title: str, key: str, color: str) -> ctk.CTkFrame:
        card = ctk.CTkFrame(
            self.metrics_frame,
            fg_color=COLORS["bg_card"],
            corner_radius=16,
            border_width=1,
            border_color=COLORS["border"],
            height=140,
        )
        card.grid_propagate(False)
        card.bind("<Button-1>", lambda e: self._on_card_click(key))
        ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=11, weight="bold"), text_color=COLORS["text_dim"]).pack(anchor="w", padx=14, pady=(14, 4))
        val = ctk.CTkLabel(card, text="—", font=ctk.CTkFont(size=26, weight="bold"), text_color=color)
        val.pack(anchor="w", padx=14, pady=(0, 2))
        sub = ctk.CTkLabel(card, text="", font=ctk.CTkFont(size=11), text_color=COLORS["text_dim"])
        sub.pack(anchor="w", padx=14, pady=(0, 8))
        bar = ctk.CTkProgressBar(card, height=3, fg_color=COLORS["border"], progress_color=color)
        bar.pack(fill="x", padx=14, pady=(0, 14))
        card._val = val
        card._sub = sub
        card._bar = bar
        card._key = key
        return card

    def _on_card_click(self, key: str) -> None:
        if key == "disk":
            self.navigate("clean")
        elif key == "net":
            self.navigate("security")

    def _refresh_activity(self) -> None:
        for w in self.activity_list.winfo_children():
            w.destroy()
        events = get_recent_events(5)
        severity_colors = {"info": COLORS["cyan"], "warning": COLORS["orange"], "alert": COLORS["red"], "critical": COLORS["red"]}
        for ev in events:
            row = ctk.CTkFrame(self.activity_list, fg_color="transparent")
            row.pack(fill="x", pady=2)
            c = severity_colors.get(ev.get("severity", "info"), COLORS["cyan"])
            ctk.CTkLabel(row, text="●", font=ctk.CTkFont(size=12), text_color=c, width=12).pack(side="left", padx=(0, 8))
            ctk.CTkLabel(row, text=ev.get("title", "?")[:50], font=ctk.CTkFont(size=12)).pack(side="left", fill="x", expand=True)
            ctk.CTkLabel(row, text=_time_ago(ev.get("timestamp", "")), font=ctk.CTkFont(size=11), text_color=COLORS["text_dim"]).pack(side="right")
        if not events:
            ctk.CTkLabel(self.activity_list, text="Aucune activité récente.", font=ctk.CTkFont(size=12), text_color=COLORS["text_dim"]).pack(anchor="w")
        self.after(30000, self._refresh_activity)

    def update_metrics(self, metrics: dict) -> None:
        self._metrics = metrics
        for key, card in self._metric_cards:
            if key == "cpu":
                card._val.configure(text=f"{metrics.get('cpu_percent', 0):.0f}%")
                card._sub.configure(text=f"Temp : {metrics.get('cpu_temp', 0):.0f}°C")
                card._bar.set(metrics.get("cpu_percent", 0) / 100)
            elif key == "ram":
                card._val.configure(text=f"{metrics.get('ram_used_gb', 0):.1f} Go")
                card._sub.configure(text=f"sur {metrics.get('ram_total_gb', 0):.0f} Go · {metrics.get('ram_percent', 0):.0f}%")
                card._bar.set(metrics.get("ram_percent", 0) / 100)
            elif key == "disk":
                card._val.configure(text=f"{metrics.get('disk_used_gb', 0):.0f} Go")
                card._sub.configure(text=f"sur {metrics.get('disk_total_gb', 0):.0f} Go · {metrics.get('disk_percent', 0):.0f}%")
                card._bar.set(metrics.get("disk_percent", 0) / 100)
            elif key == "net":
                card._val.configure(text=metrics.get("net_ssid", "—")[:18], font=ctk.CTkFont(size=16, weight="bold"))
                card._sub.configure(text=f"↓ {metrics.get('net_dl_mbs', 0):.1f} Mo/s  ↑ {metrics.get('net_ul_mbs', 0):.1f} Mo/s")
                card._bar.set(0.5)

        score = 100
        if metrics.get("cpu_percent", 0) > 80:
            score -= 10
        if metrics.get("cpu_temp", 0) > 75:
            score -= 15
        if metrics.get("ram_percent", 0) > 80:
            score -= 10
        if metrics.get("disk_percent", 0) > 85:
            score -= 20
        score = max(0, score)
        self.score_label.configure(text=f"Score: {score}")
        if score >= 80:
            self.score_label.configure(text_color=COLORS["green"])
        elif score >= 60:
            self.score_label.configure(text_color=COLORS["orange"])
        else:
            self.score_label.configure(text_color=COLORS["red"])

        if metrics.get("disk_percent", 0) > 95:
            self.context_label.configure(text=f"⚠️ Disque presque plein ({metrics.get('disk_percent', 0):.0f}%).", text_color=COLORS["red"])
        elif metrics.get("disk_percent", 0) > 85:
            self.context_label.configure(text=f"💾 Un nettoyage pourrait libérer de l'espace ({metrics.get('disk_free_gb', 0):.1f} Go restants).", text_color=COLORS["orange"])
        elif metrics.get("ram_percent", 0) > 90:
            self.context_label.configure(text=f"⚠️ Mémoire saturée ({metrics.get('ram_percent', 0):.0f}%).", text_color=COLORS["orange"])
        else:
            self.context_label.configure(text="Votre système fonctionne parfaitement.", text_color=COLORS["green"])

    def _on_mode_change(self, mode_id: str):
        try:
            from core.system_modes import apply_mode
            apply_mode(mode_id)
            # Update UI selection (simple toggle simulation)
            for mid, btn in self._mode_btns.items():
                if mid == mode_id:
                    btn.configure(fg_color=COLORS["cyan_soft"], text_color=COLORS["cyan"])
                else:
                    btn.configure(fg_color=COLORS["bg"], text_color=COLORS["text"])
            
            from database import log_event
            log_event("system", f"Mode {mode_id} activé", f"Le système a été optimisé pour le profil {mode_id}.", severity="info")
            self._refresh_activity()
        except Exception:
            pass
