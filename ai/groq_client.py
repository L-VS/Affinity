"""Affinity — Client Groq sécurisé pour l'assistant IA."""

import json
import re
from typing import Any

from config_loader import load_config, get


def _get_api_key() -> str | None:
    """Récupère la clé API Groq depuis la config."""
    cfg = load_config()
    key = get(cfg, "ai", "groq_api_key")
    if key and isinstance(key, str) and len(key) > 10:
        return key
    return None


def _build_system_context(metrics: dict | None = None) -> str:
    """Construit le contexte système injecté dans chaque prompt."""
    if not metrics:
        return "Contexte système non disponible."
    parts = []
    if "cpu_percent" in metrics:
        parts.append(f"CPU: {metrics['cpu_percent']:.0f}%")
    if "cpu_temp" in metrics:
        parts.append(f"Temp CPU: {metrics['cpu_temp']:.0f}°C")
    if "ram_used_gb" in metrics and "ram_total_gb" in metrics:
        parts.append(f"RAM: {metrics['ram_used_gb']:.1f}/{metrics['ram_total_gb']:.0f} Go ({metrics.get('ram_percent', 0):.0f}%)")
    if "disk_used_gb" in metrics and "disk_total_gb" in metrics:
        parts.append(f"Disque: {metrics['disk_used_gb']:.0f}/{metrics['disk_total_gb']:.0f} Go ({metrics.get('disk_percent', 0):.0f}%)")
    if "net_ssid" in metrics:
        parts.append(f"Réseau: {metrics['net_ssid']}")
    if "uptime_seconds" in metrics:
        h = int(metrics["uptime_seconds"] // 3600)
        parts.append(f"Uptime: {h}h")
    return " · ".join(parts) if parts else "Contexte système non disponible."


SYSTEM_PROMPT = """Tu es Affinity, l'assistant système intelligent intégré à Ubuntu.
Tu aides l'utilisateur à comprendre, optimiser et maintenir son ordinateur.

Règles :
1. Réponds toujours en français, dans un style clair et rassurant.
2. Tu ne peux JAMAIS exécuter de commandes directement. Tu proposes des actions.
3. Si tu recommandes une action système, renvoie-la dans un bloc JSON avec "action" et "command".
4. Sois concis (2-4 paragraphes max), pas de roman.
5. Utilise le contexte système fourni pour contextualiser tes réponses.
6. Ne demande jamais de données sensibles (mots de passe, clés API).
7. Si on te demande quelque chose hors de ton domaine, redirige poliment.

Contexte système actuel :
{context}
"""


class AffinityAI:
    """Client IA Groq pour Affinity."""

    def __init__(self):
        self.client = None
        self.model = "mixtral-8x7b-32768"
        self._history: list[dict] = []
        self._load_client()

    def _load_client(self) -> None:
        """Charge le client Groq si une clé est disponible."""
        key = _get_api_key()
        if not key:
            return
        try:
            from groq import Groq
            self.client = Groq(api_key=key)
        except ImportError:
            self.client = None
        except Exception:
            self.client = None

    def is_available(self) -> bool:
        """Retourne True si le client est configuré et fonctionnel."""
        return self.client is not None

    def reload_key(self) -> bool:
        """Recharge la clé API (après modification dans les paramètres)."""
        self.client = None
        self._load_client()
        return self.is_available()

    def test_connection(self) -> tuple[bool, str]:
        """Teste la connexion à Groq. Retourne (succès, message)."""
        if not self.is_available():
            return False, "Clé API non configurée ou module groq manquant."
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5,
                temperature=0,
            )
            return True, f"Connexion OK · Modèle: {self.model}"
        except Exception as e:
            return False, f"Erreur: {str(e)[:100]}"

    def chat(self, user_message: str, system_metrics: dict | None = None) -> dict[str, Any]:
        """
        Envoie un message et retourne la réponse structurée.
        
        Retourne:
            {
                "response": str,         # Texte de la réponse
                "action": str | None,    # Action suggestion (ex: "clean", "optimize")
                "command": str | None,   # Commande suggérée (affichage uniquement)
                "error": str | None,     # Message d'erreur si échec
            }
        """
        if not self.is_available():
            return {
                "response": "L'assistant IA n'est pas configuré. Allez dans Paramètres > IA pour ajouter votre clé API Groq.",
                "action": None,
                "command": None,
                "error": "not_configured",
            }

        context = _build_system_context(system_metrics)
        system_msg = SYSTEM_PROMPT.format(context=context)

        # Garder les 10 derniers messages pour le contexte
        self._history.append({"role": "user", "content": user_message})
        if len(self._history) > 10:
            self._history = self._history[-10:]

        messages = [{"role": "system", "content": system_msg}] + self._history

        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=800,
                temperature=0.4,
            )
            text = resp.choices[0].message.content or ""
            self._history.append({"role": "assistant", "content": text})

            # Essayer d'extraire une action JSON du texte
            action = None
            command = None
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
            if json_match:
                try:
                    data = json.loads(json_match.group(1))
                    action = data.get("action")
                    command = data.get("command")
                except json.JSONDecodeError:
                    pass

            return {
                "response": text,
                "action": action,
                "command": command,
                "error": None,
            }
        except Exception as e:
            error_msg = str(e)
            if "rate_limit" in error_msg.lower():
                return {
                    "response": "Limite de requêtes atteinte. Réessayez dans quelques secondes.",
                    "action": None,
                    "command": None,
                    "error": "rate_limit",
                }
            return {
                "response": f"Erreur de communication avec l'IA : {error_msg[:150]}",
                "action": None,
                "command": None,
                "error": "api_error",
            }

    def clear_history(self) -> None:
        """Efface l'historique de conversation."""
        self._history.clear()

    def get_quick_analysis(self, metrics: dict | None = None) -> str:
        """Génère une analyse rapide du système (utilisable sans interaction)."""
        result = self.chat(
            "Fais une analyse rapide de l'état de mon système en 2-3 phrases. "
            "Mentionne uniquement les points importants ou les problèmes potentiels.",
            system_metrics=metrics,
        )
        return result.get("response", "Analyse non disponible.")
