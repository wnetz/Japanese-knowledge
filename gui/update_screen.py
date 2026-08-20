from __future__ import annotations

import subprocess
import sys
import threading
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk

from .shared import PROJECT_DIR, UPDATE_PROFILE_PATH
from .style import FONTS, style_text_widget


class UpdateScreen(ttk.Frame):
    def __init__(self, parent, *, on_update_complete=None) -> None:
        super().__init__(parent)
        self.on_update_complete = on_update_complete
        self._build_ui()

    def _build_ui(self) -> None:
        ttk.Label(
            self,
            text="Update Profiles",
            style="Heading.TLabel",
        ).pack(anchor="w")

        ttk.Label(
            self,
            text=(
                "Select the external sources you want to refresh. "
                "Unselected source indexes remain unchanged."
            ),
            wraplength=760,
        ).pack(anchor="w", pady=(2, 18))

        selection = ttk.LabelFrame(self, text="Sources", padding=14)
        selection.pack(fill="x")

        self.update_anki_var = tk.BooleanVar(value=True)
        self.update_wanikani_var = tk.BooleanVar(value=False)
        self.update_bunpro_var = tk.BooleanVar(value=False)

        ttk.Checkbutton(
            selection,
            text="Anki",
            variable=self.update_anki_var,
        ).pack(anchor="w", pady=4)

        ttk.Checkbutton(
            selection,
            text="WaniKani",
            variable=self.update_wanikani_var,
        ).pack(anchor="w", pady=4)

        ttk.Checkbutton(
            selection,
            text="Bunpro",
            variable=self.update_bunpro_var,
        ).pack(anchor="w", pady=4)

        self.update_button = ttk.Button(
            self,
            text="Update Selected Sources",
            command=self.update_selected_profiles,
            style="Accent.TButton",
        )
        self.update_button.pack(anchor="w", pady=(18, 12), ipadx=18, ipady=7)

        self.update_status_var = tk.StringVar(value="Ready.")
        ttk.Label(
            self,
            textvariable=self.update_status_var,
            wraplength=780,
        ).pack(anchor="w", pady=(0, 10))

        ttk.Label(
            self,
            text="Update log",
            style="Subheading.TLabel",
        ).pack(anchor="w", pady=(12, 4))

        log_frame = ttk.Frame(self)
        log_frame.pack(fill="both", expand=True)

        self.update_log = tk.Text(
            log_frame,
            height=18,
            wrap="word",
            state="disabled",
            font=FONTS["mono"],
        )

        scrollbar = ttk.Scrollbar(
            log_frame,
            orient="vertical",
            command=self.update_log.yview,
        )

        self.update_log.configure(yscrollcommand=scrollbar.set)
        style_text_widget(self.update_log)
        self.update_log.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def _append_update_log(self, text: str) -> None:
        self.update_log.config(state="normal")
        self.update_log.insert("end", text.rstrip() + "\n")
        self.update_log.see("end")
        self.update_log.config(state="disabled")

    def update_selected_profiles(self) -> None:
        selected = []

        if self.update_anki_var.get():
            selected.append("anki")
        if self.update_wanikani_var.get():
            selected.append("wanikani")
        if self.update_bunpro_var.get():
            selected.append("bunpro")

        if not UPDATE_PROFILE_PATH.exists():
            messagebox.showerror(
                "Missing update_profile.py",
                f"Could not find:\n{UPDATE_PROFILE_PATH}",
            )
            return

        self.update_button.config(state="disabled")
        if selected:
            self.update_status_var.set(
                "Updating "
                + ", ".join(name.title() for name in selected)
                + "..."
            )
        else:
            self.update_status_var.set(
                "Rebuilding profiles from existing source data..."
            )

        self._append_update_log(
            "\n=== " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " ==="
        )
        self._append_update_log(
            "Selected: " + ", ".join(selected)
            if selected
            else "Selected: none — rebuild only"
        )

        threading.Thread(
            target=self._run_profile_update,
            args=(selected,),
            daemon=True,
        ).start()

    def _run_profile_update(self, selected: list[str]) -> None:
        # -u forces unbuffered Python output in the child process so each
        # progress line becomes visible in the GUI immediately.
        command = [
            sys.executable,
            "-u",
            str(UPDATE_PROFILE_PATH),
            "--sources",
            ",".join(selected),
        ]

        try:
            process = subprocess.Popen(
                command,
                cwd=PROJECT_DIR,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )

            if process.stdout is not None:
                for line in iter(process.stdout.readline, ""):
                    line = line.rstrip("\r\n")
                    if line:
                        self.after(
                            0,
                            self._append_update_log,
                            line,
                        )

                process.stdout.close()

            returncode = process.wait()

            self.after(
                0,
                self._finish_profile_update,
                returncode,
                "",
                "",
            )
        except Exception as exc:
            self.after(
                0,
                self._finish_profile_update,
                1,
                "",
                f"{type(exc).__name__}: {exc}",
            )

    def _finish_profile_update(
        self,
        returncode: int,
        stdout: str,
        stderr: str,
    ) -> None:
        self.update_button.config(state="normal")

        if stdout:
            self._append_update_log(stdout)
        if stderr:
            self._append_update_log("ERROR:\n" + stderr)

        if returncode == 0:
            self.update_status_var.set(
                "Update complete — profiles and quiz data refreshed."
            )
            if callable(self.on_update_complete):
                self.on_update_complete()
        else:
            self.update_status_var.set("Update failed. See the log below.")