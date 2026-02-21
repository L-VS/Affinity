"""Affinity — Conseiller IA autonome.

Intelligence embarquée pour diagnostiquer et agir sans supervision.
Fonctionne même sans connexion API (analyse locale).

Created by l-vs — Affinity AI Advisor v1
"""

import time
from pathlib import Path

from config_loader import load_config, get


class SmartAdvisor:
    """Conseiller intelligent qui analyse le système et propose des actions."""

    # Seuils d'alerte
    CPU_HIGH = 80
    RAM_HIGH = 85
    DISK_HIGH = 90
    DISK_CRITICAL = 95

    def __init__(self):
        self._last_analysis = 0
        self._cached_advice: list[dict] = []
        self._ai = None
        try:
            from ai.groq_client import AffinityAI
            self._ai = AffinityAI()
        except Exception:
            pass

    def analyze_system(self, metrics: dict | None = None) -> list[dict]:
        """Analyse le système et retourne une liste de conseils priorisés."""
        if not metrics:
            return self._cached_advice
        
        # Rate limit: max une analyse complète toutes les 30 secondes
        now = time.time()
        if now - self._last_analysis < 30 and self._cached_advice:
            return self._cached_advice
        self._last_analysis = now

        advice = []

        # ── 1. CPU ──
        cpu = metrics.get("cpu_percent", 0)
        if cpu > self.CPU_HIGH:
            advice.append({
                "severity": "warning" if cpu < 95 else "critical",
                "category": "cpu",
                "icon": "🔥",
                "title": f"CPU à {cpu:.0f}%",
                "message": self._cpu_advice(cpu, metrics),
                "actions": [
                    {"label": "Appliquer mode Économie", "action": "apply_mode", "param": "economy"},
                    {"label": "Voir les processus", "action": "show_processes"},
                ],
            })

        # ── 2. RAM ──
        ram_pct = metrics.get("ram_percent", 0)
        ram_used = metrics.get("ram_used_gb", 0)
        ram_total = metrics.get("ram_total_gb", 1)
        if ram_pct > self.RAM_HIGH:
            advice.append({
                "severity": "warning" if ram_pct < 95 else "critical",
                "category": "ram",
                "icon": "💾",
                "title": f"RAM à {ram_pct:.0f}% ({ram_used:.1f}/{ram_total:.0f} Go)",
                "message": self._ram_advice(ram_pct, metrics),
                "actions": [
                    {"label": "Libérer la RAM", "action": "free_ram"},
                    {"label": "Voir les processus gourmands", "action": "show_processes"},
                ],
            })

        # ── 3. Disque ──
        disk_pct = metrics.get("disk_percent", 0)
        if disk_pct > self.DISK_HIGH:
            sev = "critical" if disk_pct > self.DISK_CRITICAL else "warning"
            advice.append({
                "severity": sev,
                "category": "disk",
                "icon": "💿",
                "title": f"Disque utilisé à {disk_pct:.0f}%",
                "message": self._disk_advice(disk_pct, metrics),
                "actions": [
                    {"label": "Lancer le nettoyage", "action": "clean_system"},
                    {"label": "Trouver les gros fichiers", "action": "find_large_files"},
                ],
            })

        # ── 4. Température ──
        temp = metrics.get("cpu_temp", 0)
        if temp > 80:
            advice.append({
                "severity": "warning" if temp < 90 else "critical",
                "category": "temp",
                "icon": "🌡️",
                "title": f"Température CPU : {temp:.0f}°C",
                "message": f"La température est {'critique' if temp > 90 else 'élevée'}. "
                          f"{'Arrêtez les tâches lourdes immédiatement.' if temp > 90 else 'Vérifiez la ventilation et les processus gourmands.'}",
                "actions": [
                    {"label": "Mode Économie", "action": "apply_mode", "param": "economy"},
                ],
            })

        # ── 5. Uptime ──
        uptime_s = metrics.get("uptime_seconds", 0)
        if uptime_s > 7 * 86400:  # 7 jours
            days = int(uptime_s // 86400)
            advice.append({
                "severity": "info",
                "category": "uptime",
                "icon": "🔄",
                "title": f"Système actif depuis {days} jours",
                "message": f"Un redémarrage pourrait améliorer les performances et appliquer les mises à jour de sécurité en attente.",
                "actions": [
                    {"label": "Vérifier les mises à jour", "action": "check_updates"},
                ],
            })

        # ── 6. Sécurité ──
        try:
            from core.security_engine import get_security_score
            sec = get_security_score(metrics)
            if sec["score"] < 70:
                advice.append({
                    "severity": "warning" if sec["score"] >= 50 else "critical",
                    "category": "security",
                    "icon": "🛡️",
                    "title": f"Score sécurité : {sec['score']}/100",
                    "message": "; ".join(sec.get("issues", ["Vérifiez la sécurité de votre système"])),
                    "actions": [
                        {"label": "Scan rapide", "action": "quick_scan"},
                    ],
                })
        except Exception:
            pass

        # Sort by severity
        severity_order = {"critical": 0, "warning": 1, "info": 2}
        advice.sort(key=lambda a: severity_order.get(a.get("severity", "info"), 3))

        self._cached_advice = advice
        return advice

    def get_quick_summary(self, metrics: dict | None = None) -> str:
        """Résumé textuel rapide de l'état du système (sans IA)."""
        if not metrics:
            return "Aucune donnée disponible."
        
        parts = []
        cpu = metrics.get("cpu_percent", 0)
        ram = metrics.get("ram_percent", 0)
        disk = metrics.get("disk_percent", 0)
        temp = metrics.get("cpu_temp", 0)

        if cpu < 30 and ram < 50 and disk < 70:
            parts.append("✅ Système en bon état")
        elif cpu > 90 or ram > 95 or disk > 95:
            parts.append("🔴 Système sous pression")
        else:
            parts.append("🟡 Système correct")

        if cpu > 60:
            parts.append(f"CPU chargé ({cpu:.0f}%)")
        if ram > 70:
            parts.append(f"RAM utilisée ({ram:.0f}%)")
        if disk > 80:
            parts.append(f"Disque plein ({disk:.0f}%)")
        if temp > 70:
            parts.append(f"Température élevée ({temp:.0f}°C)")
        
        return " · ".join(parts)

    def ask_ai(self, question: str, metrics: dict | None = None) -> str:
        """Pose une question à l'IA Groq (si disponible)."""
        if not self._ai or not self._ai.is_available():
            # Fallback intelligent local
            return self._local_answer(question, metrics)
        result = self._ai.chat(question, system_metrics=metrics)
        return result.get("response", "Je n'ai pas pu analyser votre demande.")

    def _local_answer(self, question: str, metrics: dict | None = None) -> str:
        """Réponse intelligente locale sans API."""
        q = question.lower()
        
        if any(w in q for w in ["état", "santé", "comment va", "statut", "comment ça va"]):
            return self.get_quick_summary(metrics)
        
        if any(w in q for w in ["nettoyer", "nettoyage", "espace", "libérer", "place"]):
            try:
                from core.cleaner_engine import get_smart_recommendations, format_size
                recs = get_smart_recommendations()
                if recs:
                    total = sum(r["size_bytes"] for r in recs)
                    lines = [f"📊 {format_size(total)} récupérables :\n"]
                    for r in recs[:5]:
                        lines.append(f"  {r['icon']} {r['name']} — {r['size_formatted']}")
                    lines.append("\n💡 Allez dans l'onglet Nettoyage pour libérer cet espace.")
                    return "\n".join(lines)
                return "✅ Votre système est propre, pas de nettoyage nécessaire."
            except Exception:
                return "Allez dans l'onglet Nettoyage pour analyser votre système."

        if any(w in q for w in ["sécurité", "virus", "menace", "scan", "malware"]):
            try:
                from core.security_engine import get_security_score
                sec = get_security_score(metrics)
                issues = sec.get("issues", [])
                msg = f"🛡️ Score sécurité : {sec['score']}/100 ({sec['label']})"
                if issues:
                    msg += "\n" + "\n".join(f"  ⚠️ {i}" for i in issues)
                else:
                    msg += "\n✅ Aucun problème détecté."
                return msg
            except Exception:
                return "Allez dans l'onglet Sécurité pour lancer un scan."

        if any(w in q for w in ["ram", "mémoire"]):
            if metrics:
                used = metrics.get("ram_used_gb", 0)
                total = metrics.get("ram_total_gb", 0)
                pct = metrics.get("ram_percent", 0)
                return (f"💾 RAM : {used:.1f}/{total:.0f} Go ({pct:.0f}%)\n"
                        f"{'⚠️ RAM élevée — fermez les applications inutilisées.' if pct > 80 else '✅ Utilisation normale.'}")
            return "Consultez le tableau de bord pour les détails mémoire."

        if any(w in q for w in ["cpu", "processeur", "lent"]):
            if metrics:
                cpu = metrics.get("cpu_percent", 0)
                return (f"🔧 CPU : {cpu:.0f}%\n"
                        f"{'⚠️ CPU chargé — vérifiez les processus gourmands.' if cpu > 60 else '✅ Activité processeur normale.'}")
            return "Consultez le tableau de bord pour les détails CPU."

        if any(w in q for w in ["démarrage", "startup", "boot", "lent au démarrage"]):
            try:
                from core.cleaner_engine import get_startup_programs
                progs = get_startup_programs()
                enabled = [p for p in progs if p.get("enabled")]
                return (f"🚀 {len(enabled)} programme(s) au démarrage.\n"
                        f"Allez dans Nettoyage > Programmes au démarrage pour les gérer.")
            except Exception:
                return "Vérifiez les programmes au démarrage dans Nettoyage."

        return ("Je suis Affinity, votre assistant système. Je peux vous aider avec :\n"
                "  💻 État du système\n"
                "  🧹 Nettoyage\n" 
                "  🛡️ Sécurité\n"
                "  ⚡ Optimisation\n"
                "\nPosez-moi votre question !")

    # ── Conseils spécifiques ──

    @staticmethod
    def _cpu_advice(cpu: float, metrics: dict) -> str:
        if cpu > 95:
            return ("Le processeur est en surcharge. Fermez les applications non essentielles "
                    "ou passez en mode Économie pour réduire la consommation.")
        return ("Le processeur est fortement sollicité. Vérifiez quels processus "
                "consomment le plus de ressources dans le Moniteur Système.")

    @staticmethod
    def _ram_advice(ram_pct: float, metrics: dict) -> str:
        if ram_pct > 95:
            return ("La mémoire est saturée. Le système risque de ralentir fortement. "
                    "Fermez des applications ou envisagez d'augmenter la RAM.")
        return ("La mémoire est presque pleine. Fermez les onglets navigateur "
                "et applications non utilisées pour libérer de la RAM.")

    @staticmethod
    def _disk_advice(disk_pct: float, metrics: dict) -> str:
        if disk_pct > 95:
            return ("Le disque est presque plein ! Votre système peut devenir instable. "
                    "Lancez immédiatement un nettoyage ou supprimez des fichiers volumineux.")
        return ("Le disque se remplit. Lancez un nettoyage pour récupérer de l'espace : "
                "cache navigateur, fichiers temporaires, et anciens journaux.")
