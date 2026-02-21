"""Affinity — Onglet Système (infos, santé, profils)."""

import platform
import time
import customtkinter as ctk
import psutil

from config import COLORS


class SystemFrame(ctk.CTkScrollableFrame):
    """Onglet Système."""

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self._build_ui()

    def _build_ui(self) -> None:
        self.tabview = ctk.CTkTabview(self, fg_color=COLORS["bg_card"])
        self.tabview.pack(fill="both", expand=True)
        self.tabview.add("Informations")
        self.tabview.add("Optimisation")
        self.tabview.add("Diagnostics")

        self._build_info()
        self._build_optimization()
        self._build_diagnostics()

    @staticmethod
    def _linux_distro() -> str:
        try:
            with open("/etc/os-release") as f:
                for line in f:
                    if line.startswith("PRETTY_NAME="):
                        return line.split("=", 1)[1].strip().strip('"')
            return "Linux"
        except Exception:
            return "Linux"

    def _build_info(self) -> None:
        tab = self.tabview.tab("Informations")
        grid = ctk.CTkFrame(tab, fg_color="transparent")
        grid.pack(fill="both", expand=True)
        grid.grid_columnconfigure(0, weight=1)
        grid.grid_columnconfigure(1, weight=1)
        try:
            cpu = platform.processor() or "?"
            ram = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            boot = psutil.boot_time()
            uptime_s = time.time() - boot if boot else 0
            days = int(uptime_s // 86400)
            hours = int((uptime_s % 86400) // 3600)
            mins = int((uptime_s % 3600) // 60)
            uptime = f"{days}j {hours}h {mins}min" if days else f"{hours}h {mins}min"
        except Exception:
            cpu = "?"
            ram_total = 0
            disk_total = 0
            uptime = "?"

        infos = [
            ("Modèle", platform.node()),
            ("CPU", cpu[:50] if cpu else "?"),
            ("RAM", f"{ram.total / 1e9:.0f} Go"),
            ("Disque", f"{disk.total / 1e9:.0f} Go ({disk.percent}% utilisé)"),
            ("Système", SystemFrame._linux_distro()),
            ("Kernel", platform.release()),
            ("Uptime", uptime),
        ]
        for i, (k, v) in enumerate(infos):
            row = ctk.CTkFrame(grid, fg_color=COLORS["bg"], corner_radius=8)
            row.grid(row=i // 2, column=i % 2, sticky="ew", padx=8, pady=4)
            row.grid_columnconfigure(1, weight=1)
            ctk.CTkLabel(row, text=k, font=ctk.CTkFont(size=11), text_color=COLORS["text_dim"]).grid(row=0, column=0, sticky="w", padx=12, pady=8)
            ctk.CTkLabel(row, text=str(v)[:60], font=ctk.CTkFont(size=11, weight="bold")).grid(row=0, column=1, sticky="e", padx=12, pady=8)

        ctk.CTkButton(
            tab,
            text="📋 Copier le rapport",
            font=ctk.CTkFont(size=12),
            fg_color=COLORS["cyan"],
            text_color="#001F2E",
            command=self._copy_report,
        ).pack(pady=16)

    def _copy_report(self) -> None:
        try:
            ram = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            text = f"Affinity — Rapport système\n{platform.node()}\nCPU: {platform.processor()}\nRAM: {ram.total/1e9:.0f} Go\nDisque: {disk.total/1e9:.0f} Go\nOS: {SystemFrame._linux_distro()}"
            self.winfo_toplevel().clipboard_clear()
            self.winfo_toplevel().clipboard_append(text)
        except Exception:
            pass

    def _build_optimization(self) -> None:
        try:
            from core.system_modes import SYSTEM_MODES, apply_mode, get_current_governor
        except ImportError:
            return
        tab = self.tabview.tab("Optimisation")
        current = get_current_governor()
        ctk.CTkLabel(tab, text="Choisissez un profil système", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", pady=8)
        for m in SYSTEM_MODES:
            card = ctk.CTkFrame(tab, fg_color=COLORS["bg"], corner_radius=10)
            card.pack(fill="x", pady=4)
            det = m.get("details", {})
            header = ctk.CTkFrame(card, fg_color="transparent")
            header.pack(fill="x", padx=12, pady=8)
            ctk.CTkLabel(header, text=f"{m.get('icon', '')} {m.get('name', '')}", font=ctk.CTkFont(size=13, weight="bold")).pack(side="left")
            if det.get("cpu_governor") == current:
                ctk.CTkLabel(header, text="● Actif", font=ctk.CTkFont(size=10), text_color=COLORS["green"]).pack(side="right")
            ctk.CTkLabel(card, text=m.get("description", ""), font=ctk.CTkFont(size=11), text_color=COLORS["text_dim"]).pack(anchor="w", padx=12, pady=(0, 4))
            detail_str = f"Governor: {det.get('cpu_governor', '?')} · Swappiness: {det.get('swappiness', '?')} · I/O: {det.get('io_scheduler', '?')} · {det.get('thermal', '')}"
            ctk.CTkLabel(card, text=detail_str, font=ctk.CTkFont(size=10), text_color=COLORS["text_dim"]).pack(anchor="w", padx=12, pady=(0, 8))
            ctk.CTkButton(card, text="Appliquer", font=ctk.CTkFont(size=11), width=100, fg_color=COLORS["cyan"], text_color="#001F2E", command=lambda mid=m["id"]: self._apply_mode(mid)).pack(anchor="e", padx=12, pady=(0, 8))

    def _apply_mode(self, mode_id: str) -> None:
        try:
            from core.system_modes import apply_mode
            apply_mode(mode_id)
        except Exception:
            pass

    def _build_diagnostics(self) -> None:
        tab = self.tabview.tab("Diagnostics")
        ctk.CTkLabel(tab, text="Outils de diagnostic", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", pady=8)

        self._diag_results = {}
        tests = [
            ("⟁ Test CPU", "Charge CPU 10s + température", self._test_cpu),
            ("◈ Test RAM", "Analyse mémoire détaillée", self._test_ram),
            ("💾 Test disque", "Vitesse lecture séquentielle", self._test_disk),
            ("🌐 Test réseau", "Ping + estimation débit", self._test_network),
        ]
        for name, desc, test_func in tests:
            card = ctk.CTkFrame(tab, fg_color=COLORS["bg"], corner_radius=10)
            card.pack(fill="x", pady=4)
            header = ctk.CTkFrame(card, fg_color="transparent")
            header.pack(fill="x", padx=12, pady=8)
            ctk.CTkLabel(header, text=name, font=ctk.CTkFont(size=12, weight="bold")).pack(side="left")
            ctk.CTkLabel(header, text=desc, font=ctk.CTkFont(size=11), text_color=COLORS["text_dim"]).pack(side="left", padx=12)
            result_label = ctk.CTkLabel(card, text="", font=ctk.CTkFont(size=11), text_color=COLORS["text_dim"], wraplength=500, justify="left")
            result_label.pack(anchor="w", padx=12, pady=(0, 8))
            btn = ctk.CTkButton(
                header, text="Lancer", font=ctk.CTkFont(size=11), width=80,
                fg_color=COLORS["cyan"], text_color="#001F2E",
                command=lambda f=test_func, r=result_label, b=None: self._run_test(f, r),
            )
            btn.pack(side="right")
            self._diag_results[name] = (result_label, btn)

    def _run_test(self, test_func, result_label) -> None:
        """Lance un test en arrière-plan."""
        result_label.configure(text="⏳ Test en cours...", text_color=COLORS["orange"])
        def do():
            try:
                result = test_func()
                self.after(0, lambda: result_label.configure(text=result, text_color=COLORS["green"]))
            except Exception as e:
                self.after(0, lambda: result_label.configure(text=f"❌ Erreur : {e}", text_color=COLORS["red"]))
        import threading
        threading.Thread(target=do, daemon=True).start()

    def _test_cpu(self) -> str:
        """Test CPU : mesure charge et température pendant 10 secondes."""
        import subprocess
        temps_start = self._get_cpu_temp()
        # Use psutil to measure CPU usage over 10 seconds
        readings = []
        for _ in range(10):
            readings.append(psutil.cpu_percent(interval=1))
        temps_end = self._get_cpu_temp()
        avg = sum(readings) / len(readings)
        peak = max(readings)
        freq = psutil.cpu_freq()
        freq_str = f"{freq.current:.0f} MHz" if freq else "?"
        return (
            f"✅ CPU : moy {avg:.0f}% · pic {peak:.0f}% · "
            f"Fréquence : {freq_str} · "
            f"Temp : {temps_start:.0f}°C → {temps_end:.0f}°C"
        )

    @staticmethod
    def _get_cpu_temp() -> float:
        try:
            temps = psutil.sensors_temperatures()
            for name in ("coretemp", "k10temp", "zenpower", "acpitz"):
                if name in temps and temps[name]:
                    return temps[name][0].current
        except Exception:
            pass
        return 0

    def _test_ram(self) -> str:
        """Test RAM : analyse détaillée de la mémoire."""
        ram = psutil.virtual_memory()
        swap = psutil.swap_memory()
        top_procs = []
        for p in sorted(psutil.process_iter(["name", "memory_info"]),
                        key=lambda p: (p.info.get("memory_info") or type("", (), {"rss": 0})()).rss,
                        reverse=True)[:5]:
            try:
                name = p.info["name"][:20]
                mb = p.info["memory_info"].rss / 1e6
                top_procs.append(f"{name} ({mb:.0f} Mo)")
            except Exception:
                pass
        procs_str = ", ".join(top_procs) if top_procs else "?"
        return (
            f"✅ RAM : {ram.used / 1e9:.1f}/{ram.total / 1e9:.0f} Go ({ram.percent}%) · "
            f"Disponible : {ram.available / 1e9:.1f} Go · "
            f"Swap : {swap.used / 1e9:.1f}/{swap.total / 1e9:.0f} Go\n"
            f"Top processus : {procs_str}"
        )

    def _test_disk(self) -> str:
        """Test disque : vitesse de lecture séquentielle via dd."""
        import subprocess, tempfile, os
        disk = psutil.disk_usage("/")
        result_parts = [f"Espace : {disk.used / 1e9:.0f}/{disk.total / 1e9:.0f} Go ({disk.percent}%)"]

        # Sequential read test
        try:
            test_file = tempfile.NamedTemporaryFile(delete=False, dir="/tmp", prefix="affinity_disk_")
            test_file.close()
            # Write 100MB
            r = subprocess.run(
                ["dd", "if=/dev/zero", f"of={test_file.name}", "bs=1M", "count=100", "conv=fdatasync"],
                capture_output=True, text=True, timeout=30,
            )
            # Parse dd output for speed
            stderr = r.stderr or ""
            for line in stderr.split("\n"):
                if "bytes" in line and ("s," in line or "copied" in line):
                    # Extract speed (last part usually like "X MB/s" or "X GB/s")
                    parts = line.strip().split(",")
                    if len(parts) >= 3:
                        result_parts.append(f"Écriture : {parts[-1].strip()}")
                    break
            os.unlink(test_file.name)
        except Exception as e:
            result_parts.append(f"Test vitesse : non disponible ({e})")

        # SMART check
        try:
            r = subprocess.run(
                ["smartctl", "-H", "/dev/sda"],
                capture_output=True, text=True, timeout=10,
            )
            if "PASSED" in (r.stdout or ""):
                result_parts.append("SMART : ✅ PASSED")
            elif r.returncode != 0:
                result_parts.append("SMART : non disponible (droits root requis)")
        except FileNotFoundError:
            result_parts.append("SMART : smartctl non installé")
        except Exception:
            result_parts.append("SMART : non disponible")

        return "✅ " + " · ".join(result_parts)

    def _test_network(self) -> str:
        """Test réseau : ping + estimation de débit."""
        import subprocess
        results = []

        # Ping test
        try:
            r = subprocess.run(
                ["ping", "-c", "5", "-W", "2", "8.8.8.8"],
                capture_output=True, text=True, timeout=15,
            )
            for line in (r.stdout or "").split("\n"):
                if "avg" in line or "rtt" in line:
                    parts = line.split("=")
                    if len(parts) >= 2:
                        vals = parts[-1].strip().split("/")
                        if len(vals) >= 2:
                            results.append(f"Ping : {vals[1]} ms (moy)")
                    break
                if "loss" in line.lower():
                    results.append(line.strip().split(",")[-1].strip())
        except Exception as e:
            results.append(f"Ping : erreur ({e})")

        # Download speed estimation (small Ubuntu file)
        try:
            import time as tm
            import urllib.request
            url = "http://archive.ubuntu.com/ubuntu/dists/jammy/Release"
            start = tm.time()
            req = urllib.request.urlopen(url, timeout=10)
            data = req.read()
            elapsed = tm.time() - start
            size_mb = len(data) / 1e6
            speed = size_mb / elapsed if elapsed > 0 else 0
            results.append(f"Débit estimé : {speed:.1f} Mo/s ({size_mb:.1f} Mo en {elapsed:.1f}s)")
        except Exception:
            results.append("Débit : test non disponible")

        # Local IP
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            results.append(f"IP locale : {ip}")
        except Exception:
            pass

        return "✅ " + " · ".join(results) if results else "✅ Test réseau terminé"
