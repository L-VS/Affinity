"""Affinity — Onglet Assistant IA (chat + terminal)."""

import threading
import customtkinter as ctk

from config import COLORS
from config_loader import load_config, get


class AiTabFrame(ctk.CTkFrame):
    """Onglet IA avec interface chat et terminal."""

    def __init__(self, master, get_metrics_cb=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.get_metrics = get_metrics_cb or (lambda: {})
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._ai = None
        self._init_ai()
        self._build_ui()

    def _init_ai(self) -> None:
        """Initialise le client IA."""
        try:
            from ai.groq_client import AffinityAI
            self._ai = AffinityAI()
        except Exception:
            self._ai = None

    # ── UI Construction ──

    def _build_ui(self) -> None:
        # Main split: chat left, terminal right
        main = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], corner_radius=16,
                            border_width=1, border_color=COLORS["border"])
        main.grid(row=0, column=0, sticky="nsew")
        main.grid_columnconfigure(0, weight=1)
        main.grid_columnconfigure(1, weight=1)
        main.grid_rowconfigure(0, weight=1)

        # ── Left: Chat ──
        chat_frame = ctk.CTkFrame(main, fg_color="transparent")
        chat_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 1))
        chat_frame.grid_columnconfigure(0, weight=1)
        chat_frame.grid_rowconfigure(1, weight=1)

        # Chat header
        header = ctk.CTkFrame(chat_frame, fg_color="transparent", height=40)
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 8))
        ctk.CTkLabel(
            header, text="💬 Conversation",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLORS["text_mid"],
        ).pack(side="left")
        ctk.CTkButton(
            header, text="🗑 Effacer", width=80, height=28,
            font=ctk.CTkFont(size=11),
            fg_color="transparent", text_color=COLORS["text_dim"],
            hover_color=COLORS["bg_hover"],
            command=self._clear_chat,
        ).pack(side="right")

        # Messages area
        self.messages_frame = ctk.CTkScrollableFrame(
            chat_frame, fg_color=COLORS["bg"],
            corner_radius=8,
        )
        self.messages_frame.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 8))
        self.messages_frame.grid_columnconfigure(0, weight=1)

        # Show initial state
        if self._ai and self._ai.is_available():
            self._add_ai_message("Bonjour ! Je suis l'assistant Affinity. Comment puis-je vous aider ?")
        else:
            self._show_setup_message()

        # Chips
        chips_frame = ctk.CTkFrame(chat_frame, fg_color="transparent")
        chips_frame.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 4))
        for text in ["Comment va mon PC ?", "Libérer la RAM", "Nettoyer le système", "Vérifier sécurité"]:
            chip = ctk.CTkButton(
                chips_frame, text=text,
                font=ctk.CTkFont(size=11),
                fg_color=COLORS["bg"], text_color=COLORS["text_dim"],
                hover_color=COLORS["cyan_soft"],
                border_width=1, border_color=COLORS["border"],
                corner_radius=20, height=28,
                command=lambda t=text: self._send_message(t),
            )
            chip.pack(side="left", padx=3, pady=2)

        # Input area
        input_frame = ctk.CTkFrame(chat_frame, fg_color="transparent")
        input_frame.grid(row=3, column=0, sticky="ew", padx=12, pady=(4, 12))
        input_frame.grid_columnconfigure(0, weight=1)

        self.input_entry = ctk.CTkEntry(
            input_frame,
            placeholder_text="Votre question...",
            height=40,
            font=ctk.CTkFont(size=13),
            fg_color=COLORS["bg"],
            border_color=COLORS["border"],
            corner_radius=10,
        )
        self.input_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.input_entry.bind("<Return>", lambda e: self._on_send())

        self.send_btn = ctk.CTkButton(
            input_frame, text="↑", width=40, height=40,
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color=COLORS["cyan"], text_color="#001F2E",
            corner_radius=10,
            command=self._on_send,
        )
        self.send_btn.grid(row=0, column=1)

        # ── Right: Terminal ──
        term_frame = ctk.CTkFrame(main, fg_color="#060A14", corner_radius=0)
        term_frame.grid(row=0, column=1, sticky="nsew")
        term_frame.grid_columnconfigure(0, weight=1)
        term_frame.grid_rowconfigure(1, weight=1)

        # Terminal header
        term_header = ctk.CTkFrame(term_frame, fg_color="transparent", height=36)
        term_header.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 4))
        for color in ["#FF5F57", "#FFBD2E", "#28C840"]:
            dot = ctk.CTkFrame(term_header, width=10, height=10,
                               fg_color=color, corner_radius=5)
            dot.pack(side="left", padx=2)
        ctk.CTkLabel(
            term_header, text="  affinity",
            font=ctk.CTkFont(family="monospace", size=12),
            text_color=COLORS["text_dim"],
        ).pack(side="left", padx=8)
        self.term_status = ctk.CTkLabel(
            term_header, text="● en attente",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["green"],
        )
        self.term_status.pack(side="right")

        # Terminal body
        self.term_body = ctk.CTkTextbox(
            term_frame,
            fg_color="#060A14",
            font=ctk.CTkFont(family="monospace", size=12),
            text_color=COLORS["text_dim"],
            corner_radius=0,
            state="disabled",
            wrap="word",
        )
        self.term_body.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self._term_write("# Terminal Affinity — en attente de commandes\n", COLORS["text_dim"])

    # ── Message Helpers ──

    def _add_ai_message(self, text: str) -> None:
        """Ajoute un message de l'IA dans le chat."""
        msg_frame = ctk.CTkFrame(
            self.messages_frame, fg_color=COLORS["cyan_soft"],
            corner_radius=12, border_width=1,
            border_color=COLORS["border"],
        )
        msg_frame.pack(fill="x", padx=(0, 40), pady=4, anchor="w")
        # Avatar + text
        inner = ctk.CTkFrame(msg_frame, fg_color="transparent")
        inner.pack(fill="x", padx=12, pady=10)
        ctk.CTkLabel(
            inner, text="⬡", width=28, height=28,
            font=ctk.CTkFont(size=14),
            fg_color=COLORS["cyan"], corner_radius=14,
            text_color="#001F2E",
        ).pack(side="left", padx=(0, 8))
        ctk.CTkLabel(
            inner, text=text,
            font=ctk.CTkFont(size=13),
            text_color=COLORS["text"],
            wraplength=350, justify="left",
        ).pack(side="left", fill="x", expand=True)

    def _add_user_message(self, text: str) -> None:
        """Ajoute un message de l'utilisateur dans le chat."""
        msg_frame = ctk.CTkFrame(
            self.messages_frame, fg_color=COLORS["bg_hover"],
            corner_radius=12, border_width=1,
            border_color=COLORS["border"],
        )
        msg_frame.pack(fill="x", padx=(40, 0), pady=4, anchor="e")
        inner = ctk.CTkFrame(msg_frame, fg_color="transparent")
        inner.pack(fill="x", padx=12, pady=10)
        ctk.CTkLabel(
            inner, text=text,
            font=ctk.CTkFont(size=13),
            text_color=COLORS["text"],
            wraplength=350, justify="left",
        ).pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(
            inner, text="👤", width=28, height=28,
            font=ctk.CTkFont(size=14),
            fg_color=COLORS["border"], corner_radius=14,
            text_color=COLORS["text"],
        ).pack(side="right", padx=(8, 0))

    def _add_typing_indicator(self) -> None:
        """Ajoute un indicateur de saisie."""
        self._typing_frame = ctk.CTkFrame(
            self.messages_frame, fg_color=COLORS["cyan_soft"],
            corner_radius=12, border_width=1,
            border_color=COLORS["border"],
        )
        self._typing_frame.pack(fill="x", padx=(0, 40), pady=4, anchor="w")
        inner = ctk.CTkFrame(self._typing_frame, fg_color="transparent")
        inner.pack(fill="x", padx=12, pady=10)
        ctk.CTkLabel(
            inner, text="⬡", width=28, height=28,
            font=ctk.CTkFont(size=14),
            fg_color=COLORS["cyan"], corner_radius=14,
            text_color="#001F2E",
        ).pack(side="left", padx=(0, 8))
        ctk.CTkLabel(
            inner, text="Affinity réfléchit...",
            font=ctk.CTkFont(size=12, slant="italic"),
            text_color=COLORS["text_dim"],
        ).pack(side="left")

    def _remove_typing_indicator(self) -> None:
        """Supprime l'indicateur de saisie."""
        if hasattr(self, "_typing_frame") and self._typing_frame.winfo_exists():
            self._typing_frame.destroy()

    def _show_setup_message(self) -> None:
        """Affiche un message de configuration quand l'IA n'est pas configurée."""
        frame = ctk.CTkFrame(
            self.messages_frame, fg_color=COLORS["bg"],
            corner_radius=12, border_width=1,
            border_color=COLORS["border"],
        )
        frame.pack(fill="x", pady=20, padx=20)
        inner = ctk.CTkFrame(frame, fg_color="transparent")
        inner.pack(fill="x", padx=20, pady=20)
        ctk.CTkLabel(
            inner, text="⬙ Assistant IA non configuré",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=COLORS["orange"],
        ).pack(anchor="w", pady=(0, 8))
        ctk.CTkLabel(
            inner,
            text="Pour activer l'assistant intelligent, vous devez :\n"
                 "1. Créer un compte gratuit sur console.groq.com\n"
                 "2. Obtenir une clé API\n"
                 "3. La coller dans Paramètres > IA",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_dim"],
            justify="left",
        ).pack(anchor="w", pady=(0, 12))
        btn_row = ctk.CTkFrame(inner, fg_color="transparent")
        btn_row.pack(anchor="w")
        ctk.CTkButton(
            btn_row, text="🌐 Ouvrir Groq Console",
            font=ctk.CTkFont(size=12),
            fg_color=COLORS["cyan"], text_color="#001F2E",
            command=self._open_groq,
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            btn_row, text="🔄 Recharger",
            font=ctk.CTkFont(size=12),
            fg_color=COLORS["bg_hover"], text_color=COLORS["text_dim"],
            command=self._reload_ai,
        ).pack(side="left")

    # ── Terminal ──

    def _term_write(self, text: str, color: str = None) -> None:
        """Écrit dans le terminal."""
        self.term_body.configure(state="normal")
        self.term_body.insert("end", text)
        self.term_body.configure(state="disabled")
        self.term_body.see("end")

    def _term_clear(self) -> None:
        """Efface le terminal."""
        self.term_body.configure(state="normal")
        self.term_body.delete("1.0", "end")
        self.term_body.configure(state="disabled")

    # ── Actions ──

    def _on_send(self) -> None:
        """Envoie le message dans l'input."""
        text = self.input_entry.get().strip()
        if not text:
            return
        self.input_entry.delete(0, "end")
        self._send_message(text)

    def _send_message(self, text: str) -> None:
        """Envoie un message à l'IA."""
        self._add_user_message(text)

        # Check if AI is available
        if not self._ai or not self._ai.is_available():
            self._add_ai_message(
                "L'assistant IA n'est pas configuré. Allez dans Paramètres > IA "
                "pour ajouter votre clé API Groq."
            )
            return

        self._add_typing_indicator()
        self.send_btn.configure(state="disabled")
        self.term_status.configure(text="● traitement...", text_color=COLORS["orange"])
        self._term_write(f"\n$ affinity-ai --query \"{text[:60]}...\"\n", COLORS["cyan"])

        def _do_chat():
            metrics = self.get_metrics()
            result = self._ai.chat(text, system_metrics=metrics)
            self.after(0, lambda: self._on_chat_response(result))

        threading.Thread(target=_do_chat, daemon=True).start()

    def _on_chat_response(self, result: dict) -> None:
        """Callback quand la réponse IA arrive."""
        self._remove_typing_indicator()
        self.send_btn.configure(state="normal")
        self.term_status.configure(text="● en attente", text_color=COLORS["green"])

        response = result.get("response", "Erreur inconnue.")
        self._add_ai_message(response)

        # Log in terminal
        if result.get("command"):
            self._term_write(f"[suggestion] {result['command']}\n", COLORS["cyan"])
        if result.get("error"):
            self._term_write(f"[erreur] {result['error']}\n", COLORS["orange"])
        else:
            self._term_write("[ok] Réponse reçue.\n", COLORS["green"])

        # If there's a suggested action, show an action button
        if result.get("action") and result.get("command"):
            self._add_action_button(result["action"], result["command"])

    def _add_action_button(self, action: str, command: str) -> None:
        """Ajoute un bouton d'action post-réponse."""
        frame = ctk.CTkFrame(
            self.messages_frame, fg_color=COLORS["bg"],
            corner_radius=10, border_width=1,
            border_color=COLORS["border"],
        )
        frame.pack(fill="x", padx=(0, 40), pady=4)
        inner = ctk.CTkFrame(frame, fg_color="transparent")
        inner.pack(fill="x", padx=12, pady=8)
        ctk.CTkLabel(
            inner, text=f"💡 Action suggérée : {command[:80]}",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_dim"],
        ).pack(anchor="w")

    def _clear_chat(self) -> None:
        """Efface l'historique du chat."""
        for w in self.messages_frame.winfo_children():
            w.destroy()
        if self._ai:
            self._ai.clear_history()
        self._term_clear()
        self._term_write("# Terminal effacé\n", COLORS["text_dim"])
        if self._ai and self._ai.is_available():
            self._add_ai_message("Conversation effacée. Comment puis-je vous aider ?")
        else:
            self._show_setup_message()

    def _reload_ai(self) -> None:
        """Recharge le client IA (après config de la clé)."""
        self._init_ai()
        for w in self.messages_frame.winfo_children():
            w.destroy()
        if self._ai and self._ai.is_available():
            self._add_ai_message("Assistant IA activé ! Comment puis-je vous aider ?")
            self._term_write("[ok] Client IA rechargé avec succès.\n", COLORS["green"])
        else:
            self._show_setup_message()

    @staticmethod
    def _open_groq() -> None:
        """Ouvre la console Groq dans le navigateur."""
        try:
            import subprocess
            subprocess.Popen(["xdg-open", "https://console.groq.com"], 
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass
