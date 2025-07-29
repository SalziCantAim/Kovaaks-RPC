import customtkinter as ctk
from tkinter import filedialog

from modules.config import save_settings
from modules.startup_utils import set_startup_shortcut


class MainWindow(ctk.CTk):
    def __init__(self, settings, tray_app):
        super().__init__()
        self.settings = settings
        self.tray_app = tray_app
        self.title("FPSAimTrainer Discord RPC")
        self.geometry("900x700")
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.create_widgets()

    def on_closing(self):
        self.withdraw()

    def create_widgets(self):
        self.tabview = ctk.CTkTabview(self, width=850, height=650)
        self.tabview.pack(fill="both", expand=True, padx=20, pady=20)

        self.tabview.add("Main")
        self.tabview.add("Settings")

        self.create_main_tab()
        self.create_settings_tab()

    def create_main_tab(self):
        main_frame = self.tabview.tab("Main")

        title_frame = ctk.CTkFrame(main_frame)
        title_frame.pack(fill="x", pady=10, padx=20)

        title_label = ctk.CTkLabel(title_frame, text="FPSAimTrainer Discord RPC", font=("Arial", 24))
        title_label.pack(pady=20)

        status_frame = ctk.CTkFrame(main_frame)
        status_frame.pack(fill="x", pady=10, padx=20)

        rpc_status = "Running" if self.tray_app.rpc_running else "Stopped"
        self.status_label = ctk.CTkLabel(status_frame, text=f"Discord RPC Status: {rpc_status}", font=("Arial", 16))
        self.status_label.pack(pady=20)

        if self.tray_app.current_scenario:
            scenario_label = ctk.CTkLabel(status_frame, text=f"Current Scenario: {self.tray_app.current_scenario}",
                                          font=("Arial", 14))
            scenario_label.pack(pady=5)

        button_frame = ctk.CTkFrame(main_frame)
        button_frame.pack(fill="x", pady=20, padx=20)

        if self.tray_app.rpc_running:
            ctk.CTkButton(button_frame, text="Stop RPC", command=self.stop_rpc).pack(side="left", padx=10, pady=10)
        else:
            ctk.CTkButton(button_frame, text="Start RPC", command=self.start_rpc).pack(side="left", padx=10, pady=10)

        ctk.CTkButton(button_frame, text="Minimize to Tray", command=self.minimize_to_tray).pack(side="right", padx=10,
                                                                                                 pady=10)

    def create_settings_tab(self):
        settings_frame = self.tabview.tab("Settings")

        scrollable_frame = ctk.CTkScrollableFrame(settings_frame)
        scrollable_frame.pack(fill="both", expand=True, padx=20, pady=20)

        rpc_frame = ctk.CTkFrame(scrollable_frame)
        rpc_frame.pack(fill="x", pady=10, padx=10)

        ctk.CTkLabel(rpc_frame, text="RPC Settings", font=("Arial", 18, "bold")).pack(pady=10)

        self.open_manually_var = ctk.BooleanVar(value=self.settings.get("open_manually", True))
        self.cb_open_manually = ctk.CTkCheckBox(
            rpc_frame, text="Start Discord RPC manually (unchecked = auto-start when Kovaak opens)",
            variable=self.open_manually_var)
        self.cb_open_manually.pack(pady=5, padx=20, anchor="w")

        self.start_with_windows_var = ctk.BooleanVar(value=self.settings.get("start_with_windows", False))
        self.cb_start_with_windows = ctk.CTkCheckBox(
            rpc_frame, text="Start with Windows (auto-launch this app when you login)",
            variable=self.start_with_windows_var)
        self.cb_start_with_windows.pack(pady=5, padx=20, anchor="w")

        self.start_tray_var = ctk.BooleanVar(value=self.settings.get("start_in_tray", False))
        self.cb_start_tray = ctk.CTkCheckBox(
            rpc_frame, text="Start minimized to system tray",
            variable=self.start_tray_var)
        self.cb_start_tray.pack(pady=5, padx=20, anchor="w")

        online_frame = ctk.CTkFrame(scrollable_frame)
        online_frame.pack(fill="x", pady=10, padx=10)

        ctk.CTkLabel(online_frame, text="Online Features", font=("Arial", 18, "bold")).pack(pady=10)

        ctk.CTkLabel(online_frame, text="Kovaak Webapp Username:").pack(anchor="w", padx=20)
        self.webapp_entry = ctk.CTkEntry(online_frame, width=300)
        self.webapp_entry.insert(0, self.settings.get("webapp_username", ""))
        self.webapp_entry.pack(pady=5, padx=20, anchor="w")
        self.webapp_entry.bind("<KeyRelease>", self.on_username_change)

        self.show_online_var = ctk.BooleanVar(value=self.settings.get("show_online_scores", False))
        self.cb_online = ctk.CTkCheckBox(
            online_frame, text="Show online scenario highscores in Discord RPC",
            variable=self.show_online_var)
        self.cb_online.pack(pady=5, padx=20, anchor="w")

        self.online_only_var = ctk.BooleanVar(value=self.settings.get("online_only_scenarios", False))
        self.cb_online_only = ctk.CTkCheckBox(
            online_frame, text="Only show scenarios that are available online (exact match required)",
            variable=self.online_only_var)
        self.cb_online_only.pack(pady=5, padx=20, anchor="w")

        self.update_online_checkbox_state()

        path_frame = ctk.CTkFrame(scrollable_frame)
        path_frame.pack(fill="x", pady=10, padx=10)

        ctk.CTkLabel(path_frame, text="Path Settings", font=("Arial", 18, "bold")).pack(pady=10)

        ctk.CTkLabel(path_frame, text="FPSAimTrainer Installation Path:").pack(anchor="w", padx=20)
        install_path_frame = ctk.CTkFrame(path_frame)
        install_path_frame.pack(fill="x", padx=20, pady=5)

        self.install_entry = ctk.CTkEntry(install_path_frame, width=400)
        self.install_entry.insert(0, self.settings.get("installation_path", ""))
        self.install_entry.pack(side="left", fill="x", expand=True, padx=5, pady=5)
        ctk.CTkButton(install_path_frame, text="Browse", command=self.browse_installation).pack(side="right", padx=5)

        ctk.CTkLabel(path_frame, text="Steam.exe Path:").pack(anchor="w", padx=20, pady=(10, 0))
        steam_path_frame = ctk.CTkFrame(path_frame)
        steam_path_frame.pack(fill="x", padx=20, pady=5)

        self.steam_entry = ctk.CTkEntry(steam_path_frame, width=400)
        self.steam_entry.insert(0, self.settings.get("steam_path", ""))
        self.steam_entry.pack(side="left", fill="x", expand=True, padx=5, pady=5)
        ctk.CTkButton(steam_path_frame, text="Browse", command=self.browse_steam).pack(side="right", padx=5)

        save_button_frame = ctk.CTkFrame(scrollable_frame)
        save_button_frame.pack(fill="x", pady=20, padx=10)

        ctk.CTkButton(save_button_frame, text="Save Settings", command=self.save_settings,
                      font=("Arial", 16, "bold")).pack(pady=10)
        set_startup_shortcut(self.settings["start_with_windows"])

    def on_username_change(self, event=None):
        self.update_online_checkbox_state()

    def update_online_checkbox_state(self):
        has_username = bool(self.webapp_entry.get().strip())
        if has_username:
            self.cb_online.configure(state="normal")
        else:
            self.cb_online.configure(state="disabled")
            self.show_online_var.set(False)

    def browse_installation(self):
        path = filedialog.askdirectory(title="Select Kovaaks Folder")
        if path:
            self.install_entry.delete(0, "end")
            self.install_entry.insert(0, path)

    def browse_steam(self):
        path = filedialog.askopenfilename(title="Select Steam.exe", filetypes=[("EXE files", "*.exe")])
        if path:
            self.steam_entry.delete(0, "end")
            self.steam_entry.insert(0, path)

    def save_settings(self):
        self.settings["open_manually"] = self.open_manually_var.get()
        self.settings["start_in_tray"] = self.start_tray_var.get()
        self.settings["webapp_username"] = self.webapp_entry.get().strip()
        self.settings["show_online_scores"] = self.show_online_var.get()
        self.settings["online_only_scenarios"] = self.online_only_var.get()
        self.settings["installation_path"] = self.install_entry.get().strip()
        self.settings["steam_path"] = self.steam_entry.get().strip()
        self.settings["start_with_windows"] = self.start_with_windows_var.get()

        save_settings(self.settings)
        if self.tray_app.on_settings_saved:
            self.tray_app.on_settings_saved(self.settings)

        confirmation = ctk.CTkToplevel(self)
        confirmation.title("Settings Saved")
        confirmation.geometry("300x200")
        confirmation.grab_set()
        ctk.CTkLabel(confirmation, text="Settings saved!").pack(pady=30)
        ctk.CTkButton(confirmation, text="OK", command=confirmation.destroy).pack()

    def start_rpc(self):
        self.tray_app.start_rpc()
        self.update_status()

    def stop_rpc(self):
        self.tray_app.stop_rpc()
        self.update_status()

    def update_status(self):
        rpc_status = "Running" if self.tray_app.rpc_running else "Stopped"
        self.status_label.configure(text=f"Discord RPC Status: {rpc_status}")

    def minimize_to_tray(self):
        self.withdraw()