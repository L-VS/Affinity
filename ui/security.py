"""Affinity — Onglet Sécurité (antivirus, analyse, quarantaine)."""

import threading
import customtkinter as ctk
from tkinter import filedialog
from config import COLORS

from core.hash_database import get_database_stats, get_last_scan, update_hash_database
from core.security_engine import analyze_file, quick_scan, full_scan
from core.quarantine import get_quarantine_list, quarantine_file, restore_file, delete_permanently, get_quarantine_size
from core.network_monitor import get_active_connections
from core.device_watcher import start_device_watcher, get_current_devices, find_storage_mountpoint
from core.security_engine import scan_usb_device
from core.file_watcher import start_file_watcher
from database import log_event
from ui.scan_progress import ScanProgressWindow


def _format_size(b: int) -> str:
    if b >= 1024 * 1024:
        return f"{b / (1024**2):.1f} Mo"
    if b >= 1024:
        return f"{b / 1024:.0f} Ko"
    return f"{b} o"


class SecurityFrame(ctk.CTkScrollableFrame):
    """Onglet Sécurité complet avec onglets internes."""

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self._master = master
        self._build_header()
        self._build_tabs()
        self._current_result = None
        self._refresh_devices()
        self._refresh_score()
        self.after(200, self._refresh_network)

    def _start_watchers(self) -> None:
        """Démarre file_watcher et device_watcher."""
        def on_new_file(path):
            def analyze():
                r = analyze_file(path)
                if r.get("verdict") != "clean":
                    self.after(0, lambda: self._on_threat_detected(path, r))
            threading.Thread(target=analyze, daemon=True).start()

        def on_usb_added(info):
            self.after(0, self._refresh_devices)
            if info.get("subsystem") != "block" or not info.get("devnode"):
                return
            mp = find_storage_mountpoint(info)
            if mp:
                def scan():
                    for threat in scan_usb_device(mp):
                        self.after(0, lambda t=threat: self._on_usb_threat(mp, t))
                threading.Thread(target=scan, daemon=True).start()

        start_file_watcher(on_new_file=on_new_file)
        start_device_watcher(on_device_added=on_usb_added, on_device_removed=lambda _: self.after(0, self._refresh_devices))

    def _on_threat_detected(self, path: str, result: dict) -> None:
        self.tabview.set("Fichiers")
        self._show_result(result)

    def _on_usb_threat(self, mountpoint: str, result: dict) -> None:
        log_event("security", "Menace sur USB", result.get("filename", "?"), severity="warning")
        self.tabview.set("Fichiers")
        self._show_result(result)

    def _refresh_score(self) -> None:
        last = get_last_scan()
        stats = get_database_stats()
        if last:
            self.score_label.configure(
                text=f"Dernier scan : {last.get('scan_type', '?')} · {last.get('files_scanned', 0)} fichiers"
            )
        else:
            self.score_label.configure(text=f"Signatures : {stats.get('malware_count', 0):,}")

    def _refresh_devices(self) -> None:
        for w in self.devices_frame.winfo_children():
            w.destroy()
        devs = get_current_devices()
        if not devs:
            ctk.CTkLabel(
                self.devices_frame,
                text="Aucun périphérique USB connecté.",
                font=ctk.CTkFont(size=12),
                text_color=COLORS["text_dim"],
            ).pack(anchor="w", pady=8)
            return
        for d in devs:
            card = ctk.CTkFrame(self.devices_frame, fg_color=COLORS["bg"], corner_radius=8)
            card.pack(fill="x", pady=4)
            ctk.CTkLabel(
                card,
                text=f"💾 {d.get('name', 'Périphérique')}",
                font=ctk.CTkFont(weight="bold"),
            ).pack(anchor="w", padx=12, pady=8)
            ctk.CTkLabel(
                card,
                text=f"VID:{d.get('vid', '?')} PID:{d.get('pid', '?')}",
                font=ctk.CTkFont(size=11),
                text_color=COLORS["text_dim"],
            ).pack(anchor="w", padx=12, pady=(0, 8))

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        header.grid_columnconfigure(0, weight=1)

        left = ctk.CTkFrame(header, fg_color="transparent")
        left.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            left,
            text="Score de sécurité",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLORS["text"],
        ).grid(row=0, column=0, sticky="w")
        self.score_label = ctk.CTkLabel(
            left,
            text="—",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_dim"],
        )
        self.score_label.grid(row=1, column=0, sticky="w")

        right = ctk.CTkFrame(header, fg_color="transparent")
        right.grid(row=0, column=1, sticky="e")
        ctk.CTkButton(
            right,
            text="▶ Scan rapide",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=COLORS["cyan"],
            text_color="#001F2E",
            width=120,
            height=34,
            command=self._on_quick_scan,
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            right,
            text="Scan complet",
            font=ctk.CTkFont(size=12),
            fg_color=COLORS["bg_card"],
            border_width=1,
            border_color=COLORS["border"],
            width=100,
            height=34,
            command=self._on_full_scan,
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            right,
            text="📂 Analyser un fichier",
            font=ctk.CTkFont(size=12),
            fg_color=COLORS["bg_card"],
            border_width=1,
            border_color=COLORS["border"],
            width=160,
            height=34,
            command=self._on_analyze_file,
        ).pack(side="left", padx=4)

    def _build_tabs(self) -> None:
        self.tabview = ctk.CTkTabview(self, fg_color=COLORS["bg_card"])
        self.tabview.grid(row=1, column=0, sticky="nsew", pady=(0, 0))
        self.grid_rowconfigure(1, weight=1)
        self.tabview.add("Périphériques")
        self.tabview.add("Fichiers")
        self.tabview.add("Réseau")
        self.tabview.add("Quarantaine")
        self.tabview.set("Fichiers")

        self._build_tab_devices()
        self._build_tab_files()
        self._build_tab_network()
        self._build_tab_quarantine()

    def _build_tab_devices(self) -> None:
        tab = self.tabview.tab("Périphériques")
        ctk.CTkLabel(
            tab,
            text="Périphériques connectés",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLORS["text_mid"],
        ).pack(anchor="w", padx=16, pady=12)
        self.devices_frame = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        self.devices_frame.pack(fill="both", expand=True, padx=16, pady=8)

    def _build_tab_files(self) -> None:
        tab = self.tabview.tab("Fichiers")
        ctk.CTkLabel(
            tab,
            text="Analyser un fichier",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLORS["text_mid"],
        ).pack(anchor="w", padx=16, pady=(12, 4))

        self.drop_zone = ctk.CTkFrame(
            tab,
            fg_color=COLORS["bg_hover"],
            border_width=1,
            border_color=COLORS["border"],
            corner_radius=12,
            height=120,
        )
        self.drop_zone.pack(fill="x", padx=16, pady=8)
        self.drop_zone.pack_propagate(False)
        ctk.CTkLabel(
            self.drop_zone,
            text="📂 Glissez un fichier ici ou cliquez pour choisir\nTous formats · Max 500 Mo",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_dim"],
            justify="center",
        ).place(relx=0.5, rely=0.5, anchor="center")
        self.drop_zone.bind("<Button-1>", lambda e: self._on_analyze_file())

        self.result_frame = ctk.CTkFrame(tab, fg_color="transparent")
        self.result_frame.pack(fill="both", expand=True, padx=16, pady=8)

    def _build_tab_network(self) -> None:
        tab = self.tabview.tab("Réseau")
        top = ctk.CTkFrame(tab, fg_color="transparent")
        top.pack(fill="x", padx=16, pady=12)
        ctk.CTkLabel(
            top,
            text="Connexions réseau actives",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLORS["text_mid"],
        ).pack(side="left")
        ctk.CTkButton(
            top,
            text="↺ Actualiser",
            font=ctk.CTkFont(size=11),
            fg_color="transparent",
            width=80,
            command=self._refresh_network,
        ).pack(side="right")
        self.network_text = ctk.CTkTextbox(
            tab,
            font=ctk.CTkFont(family="monospace", size=11),
            fg_color=COLORS["bg"],
            height=200,
        )
        self.network_text.pack(fill="both", expand=True, padx=16, pady=(0, 16))

    def _build_tab_quarantine(self) -> None:
        tab = self.tabview.tab("Quarantaine")
        top = ctk.CTkFrame(tab, fg_color="transparent")
        top.pack(fill="x", padx=16, pady=12)
        ctk.CTkLabel(
            top,
            text="Fichiers en quarantaine",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLORS["text_mid"],
        ).pack(side="left")
        self.quarantine_label = ctk.CTkLabel(
            top,
            text="",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_dim"],
        )
        self.quarantine_label.pack(side="left", padx=12)
        self.quarantine_list = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        self.quarantine_list.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        self._refresh_quarantine()

    def _refresh_network(self) -> None:
        def do():
            conns = get_active_connections()
            def update():
                self.network_text.delete("1.0", "end")
                for c in conns[:30]:
                    st = c["status"]
                    icon = {"trusted": "✅", "system": "🔵", "suspicious": "⚠️", "dangerous": "🔴"}.get(st, "❓")
                    self.network_text.insert(
                        "end",
                        f"{icon} {c['process_name']:12} {c['remote_addr']:18} {c['remote_port']:5} {c['protocol']}\n"
                    )
            self.after(0, update)
        threading.Thread(target=do, daemon=True).start()

    def _refresh_quarantine(self) -> None:
        items = get_quarantine_list()
        size = get_quarantine_size()
        self.quarantine_label.configure(text=f"{len(items)} fichier(s) · {_format_size(size)}")
        for w in self.quarantine_list.winfo_children():
            w.destroy()
        if not items:
            ctk.CTkLabel(
                self.quarantine_list,
                text="Aucun fichier en quarantaine.",
                font=ctk.CTkFont(size=12),
                text_color=COLORS["text_dim"],
            ).pack(anchor="w", pady=8)
            return
        for it in items:
            card = ctk.CTkFrame(self.quarantine_list, fg_color=COLORS["bg"], corner_radius=8)
            card.pack(fill="x", pady=4)
            row1 = ctk.CTkFrame(card, fg_color="transparent")
            row1.pack(fill="x", padx=12, pady=8)
            ctk.CTkLabel(row1, text=it["original_name"], font=ctk.CTkFont(weight="bold")).pack(side="left")
            ctk.CTkLabel(row1, text=it["reason"][:40], font=ctk.CTkFont(size=11), text_color=COLORS["text_dim"]).pack(side="left", padx=8)
            row2 = ctk.CTkFrame(card, fg_color="transparent")
            row2.pack(fill="x", padx=12, pady=(0, 8))
            ctk.CTkButton(row2, text="↩ Restaurer", width=90, height=28, font=ctk.CTkFont(size=11),
                          fg_color="transparent", command=lambda fn=it["filename"]: self._restore(fn)).pack(side="left", padx=2)
            ctk.CTkButton(row2, text="🗑 Supprimer", width=90, height=28, font=ctk.CTkFont(size=11),
                          fg_color=COLORS["red_soft"], text_color=COLORS["red"],
                          command=lambda fn=it["filename"]: self._delete_perm(fn)).pack(side="left", padx=2)

    def _restore(self, fn: str) -> None:
        if restore_file(fn):
            log_event("security", "Fichier restauré", fn)
            self._refresh_quarantine()

    def _delete_perm(self, fn: str) -> None:
        if delete_permanently(fn):
            log_event("security", "Fichier supprimé définitivement", fn)
            self._refresh_quarantine()

    def _on_analyze_file(self) -> None:
        path = filedialog.askopenfilename(title="Choisir un fichier à analyser")
        if not path:
            return
        self._show_analyzing()
        def do():
            r = analyze_file(path)
            self.after(0, lambda: self._show_result(r))
        threading.Thread(target=do, daemon=True).start()

    def _show_analyzing(self) -> None:
        for w in self.result_frame.winfo_children():
            w.destroy()
        ctk.CTkLabel(
            self.result_frame,
            text="Analyse en cours...",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["cyan"],
        ).pack(anchor="w", pady=8)

    def _show_result(self, r: dict) -> None:
        self._current_result = r
        for w in self.result_frame.winfo_children():
            w.destroy()
        verdict = r.get("verdict", "clean")
        color = COLORS["green"] if verdict == "clean" else COLORS["orange"] if verdict == "suspicious" else COLORS["red"]
        ctk.CTkLabel(
            self.result_frame,
            text=f"📄 {r.get('filename', '?')}  |  {_format_size(r.get('size_bytes', 0))}  |  {r.get('file_type', '?')}",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLORS["text"],
        ).pack(anchor="w", pady=(0, 4))
        ctk.CTkLabel(
            self.result_frame,
            text=f"Verdict : {verdict.upper()}",
            font=ctk.CTkFont(size=12),
            text_color=color,
        ).pack(anchor="w", pady=(0, 4))
        for reason in r.get("reasons", []):
            ctk.CTkLabel(
                self.result_frame,
                text=f"• {reason}",
                font=ctk.CTkFont(size=11),
                text_color=COLORS["text_dim"],
            ).pack(anchor="w")
        ctk.CTkLabel(
            self.result_frame,
            text=f"SHA256 : {r.get('sha256', '?')[:24]}...",
            font=ctk.CTkFont(size=10),
            text_color=COLORS["text_dim"],
        ).pack(anchor="w", pady=(8, 4))
        if verdict != "clean" and r.get("recommended_action") == "quarantine":
            ctk.CTkButton(
                self.result_frame,
                text="🔒 Mettre en quarantaine",
                font=ctk.CTkFont(size=12),
                fg_color=COLORS["orange"],
                text_color="#000",
                command=self._do_quarantine,
            ).pack(anchor="w", pady=8)

    def _do_quarantine(self) -> None:
        if not self._current_result:
            return
        fp = self._current_result.get("filepath")
        reason = "; ".join(self._current_result.get("reasons", ["Suspect"]))
        if quarantine_file(fp, reason, self._current_result):
            log_event("security", "Fichier mis en quarantaine", fp, severity="warning")
            self.tabview.set("Quarantaine")
            self._refresh_quarantine()
            for w in self.result_frame.winfo_children():
                w.destroy()
            ctk.CTkLabel(
                self.result_frame,
                text="✅ Fichier mis en quarantaine.",
                font=ctk.CTkFont(size=12),
                text_color=COLORS["green"],
            ).pack(anchor="w", pady=8)

    def _on_quick_scan(self) -> None:
        self.tabview.set("Fichiers")
        cancel_flag = threading.Event()
        win = ScanProgressWindow(self.winfo_toplevel(), scan_type="rapide")
        win.set_cancel_flag(cancel_flag)
        threats_found = []

        def progress(current, total, current_file, threats):
            self.after(0, lambda: win.update_progress(current, total, current_file, threats))

        def do():
            for item in quick_scan(progress_callback=progress, cancel_flag=cancel_flag):
                if isinstance(item, dict) and "_summary" in item:
                    s = item["_summary"]
                    self.after(0, lambda: win.on_complete(s["files_scanned"], s["threats_found"]))
                    self.after(0, lambda: self._show_scan_done(s))
                elif isinstance(item, dict):
                    threats_found.append(item)
                    self.after(0, lambda r=item: win.add_result(r.get("filepath", ""), r.get("verdict", "")))

        threading.Thread(target=do, daemon=True).start()

    def _on_full_scan(self) -> None:
        self.tabview.set("Fichiers")
        cancel_flag = threading.Event()
        win = ScanProgressWindow(self.winfo_toplevel(), scan_type="complet")
        win.set_cancel_flag(cancel_flag)
        threats_found = []

        def progress(current, total, current_file, threats):
            self.after(0, lambda: win.update_progress(current, total, current_file, threats))

        def do():
            for item in full_scan(progress_callback=progress, cancel_flag=cancel_flag):
                if isinstance(item, dict) and "_summary" in item:
                    s = item["_summary"]
                    self.after(0, lambda: win.on_complete(s["files_scanned"], s["threats_found"]))
                    self.after(0, lambda: self._show_scan_done(s))
                elif isinstance(item, dict):
                    threats_found.append(item)
                    self.after(0, lambda r=item: win.add_result(r.get("filepath", ""), r.get("verdict", "")))

        threading.Thread(target=do, daemon=True).start()

    def _show_scan_done(self, s: dict) -> None:
        for w in self.result_frame.winfo_children():
            w.destroy()
        ctk.CTkLabel(
            self.result_frame,
            text=f"Scan terminé. {s['files_scanned']} fichiers analysés, {s['threats_found']} menace(s) trouvée(s).",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["green"] if s["threats_found"] == 0 else COLORS["orange"],
        ).pack(anchor="w", pady=8)
        self._refresh_score()
