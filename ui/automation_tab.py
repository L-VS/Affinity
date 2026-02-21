"""Affinity — Onglet Automatisations.

Interface visuelle pour planifier des tâches (nettoyage, scans).

Created by l-vs — Affinity Automation Tab v1
"""

import customtkinter as ctk
from config import COLORS
from core.automation_engine import load_automations, add_automation, remove_automation, install_cron_clean, uninstall_cron_clean


class AutomationTabFrame(ctk.CTkScrollableFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self._build_ui()

    def _build_ui(self):
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(20, 10))
        
        ctk.CTkLabel(header, text="🕒 Automatisations", font=ctk.CTkFont(size=24, weight="bold")).pack(side="left")
        
        # Section Planification
        container = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], corner_radius=12)
        container.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(container, text="Planifier une nouvelle tâche", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=20, pady=(20, 10))
        
        row1 = ctk.CTkFrame(container, fg_color="transparent")
        row1.pack(fill="x", padx=20, pady=5)
        
        ctk.CTkLabel(row1, text="Action :", font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 10))
        self.action_var = ctk.StringVar(value="Nettoyage complet")
        self.action_menu = ctk.CTkOptionMenu(row1, values=["Nettoyage complet", "Scan Sécurité", "Les deux"], variable=self.action_var, width=180)
        self.action_menu.pack(side="left")
        
        row2 = ctk.CTkFrame(container, fg_color="transparent")
        row2.pack(fill="x", padx=20, pady=5)
        
        ctk.CTkLabel(row2, text="Fréquence :", font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 10))
        self.freq_var = ctk.StringVar(value="Hebdomadaire")
        self.freq_menu = ctk.CTkOptionMenu(row2, values=["Quotidien", "Hebdomadaire", "Mensuel"], variable=self.freq_var, width=180)
        self.freq_menu.pack(side="left")
        
        row3 = ctk.CTkFrame(container, fg_color="transparent")
        row3.pack(fill="x", padx=20, pady=5)
        
        ctk.CTkLabel(row3, text="Jour :", font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 28))
        self.day_var = ctk.StringVar(value="Dimanche")
        self.day_menu = ctk.CTkOptionMenu(row3, values=["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"], variable=self.day_var, width=180)
        self.day_menu.pack(side="left")
        
        row4 = ctk.CTkFrame(container, fg_color="transparent")
        row4.pack(fill="x", padx=20, pady=5)
        
        ctk.CTkLabel(row4, text="Heure :", font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 22))
        self.hour_var = ctk.StringVar(value="03:00")
        self.hour_menu = ctk.CTkOptionMenu(row4, values=[f"{i:02d}:00" for i in range(24)], variable=self.hour_var, width=180)
        self.hour_menu.pack(side="left")
        
        btn_add = ctk.CTkButton(container, text="Ajouter la tâche", fg_color=COLORS["cyan"], text_color="#001F2E", font=ctk.CTkFont(weight="bold"), command=self._on_add)
        btn_add.pack(padx=20, pady=20)
        
        # Section Liste
        ctk.CTkLabel(self, text="Tâches actives", font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w", padx=25, pady=(20, 10))
        self.list_container = ctk.CTkFrame(self, fg_color="transparent")
        self.list_container.pack(fill="x", padx=20)
        
        self.refresh()

    def refresh(self):
        for child in self.list_container.winfo_children():
            child.destroy()
            
        autos = load_automations()
        if not autos:
            ctk.CTkLabel(self.list_container, text="Aucune tâche planifiée.", font=ctk.CTkFont(size=13), text_color=COLORS["text_dim"]).pack(pady=10)
            return
            
        for a in autos:
            row = ctk.CTkFrame(self.list_container, fg_color=COLORS["bg_card"], corner_radius=8)
            row.pack(fill="x", pady=4)
            
            trigger = a.get("trigger", "manual")
            action = a.get("action", "clean")
            params = a.get("params", {})
            
            icon = "🧹" if "clean" in action else "🛡️"
            title = f"{'Nettoyage' if 'clean' in action else 'Scan'} {trigger}"
            details = f"Le {self._get_day_name(params.get('day', 0))} à {params.get('hour', 3):02d}:00"
            
            lbl_icon = ctk.CTkLabel(row, text=icon, font=ctk.CTkFont(size=20))
            lbl_icon.pack(side="left", padx=15, pady=10)
            
            info = ctk.CTkFrame(row, fg_color="transparent")
            info.pack(side="left", fill="both", expand=True)
            ctk.CTkLabel(info, text=title, font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", pady=(5, 0))
            ctk.CTkLabel(info, text=details, font=ctk.CTkFont(size=11), text_color=COLORS["text_dim"]).pack(anchor="w", pady=(0, 5))
            
            btn_del = ctk.CTkButton(row, text="Supprimer", fg_color="#FF4B4B", width=80, height=28, command=lambda aid=a['id']: self._on_delete(aid))
            btn_del.pack(side="right", padx=15)

    def _on_add(self):
        act_val = self.action_var.get()
        freq_val = self.freq_var.get()
        day_val = self.day_var.get()
        hour_val = int(self.hour_var.get().split(":")[0])
        
        days_map = {"Lundi": 1, "Mardi": 2, "Mercredi": 3, "Jeudi": 4, "Vendredi": 5, "Samedi": 6, "Dimanche": 0}
        day_int = days_map.get(day_val, 0)
        
        action_key = "clean" if "Nettoyage" in act_val else "scan" if "Scan" in act_val else "both"
        
        if add_automation(trigger="cron", action=action_key, params={"day": day_int, "hour": hour_val}):
            if action_key in ("clean", "both"):
                install_cron_clean(day_int, hour_val)
            self.refresh()

    def _on_delete(self, aid):
        if remove_automation(aid):
            # On pourrait désinstaller le cron global si c'était le dernier,
            # mais pour l'instant on garde simple (une seule tâche cron active gérée).
            self.refresh()

    def _get_day_name(self, day_int):
        return ["Dimanche", "Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi"][day_int % 7]
