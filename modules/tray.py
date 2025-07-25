import os
import time
import threading
import sys
from pypresence import Presence
import psutil
import pystray
from PIL import Image

from modules.config import load_settings, load_or_create_config, save_config, initialize_installation_path, get_resource_path
from modules.kovaaks_utils import is_kovaaks_running, get_current_scenario, find_initial_scores, find_fight_time_and_score
from modules.online_api import OnlineScoreAPI
from modules.discord_rpc import CLIENT_ID, update_presence


def load_icon():
    try:
        icon_path = get_resource_path("kvk_icon.ico")
        if os.path.exists(icon_path):
            return Image.open(icon_path).resize((64, 64), Image.Resampling.LANCZOS)
    except Exception as e:
        print(f"Error loading icon: {e}")

    image = Image.new('RGB', (64, 64), color='blue')
    return image


class SystemTrayApp:
    def __init__(self):
        self.settings = load_settings()
        self.installation_path = None
        self.config = None
        self.rpc = None
        self.rpc_running = False
        self.monitoring = False
        self.monitor_thread = None
        self.current_scenario = None
        self.checked_files = set()
        self.highscore = 0
        self.session_highscore = 0
        self.start_time = None
        self.online_api = OnlineScoreAPI()
        self.scenario_played = False

        self.initialize_paths()
        self.create_tray_icon()

    def create_tray_icon(self):
        image = load_icon()

        menu = pystray.Menu(
            pystray.MenuItem("Show Main Window", self.show_main_window),
            pystray.MenuItem("Start RPC", self.start_rpc, enabled=lambda item: not self.rpc_running),
            pystray.MenuItem("Stop RPC", self.stop_rpc, enabled=lambda item: self.rpc_running),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit", self.quit_app)
        )

        self.icon = pystray.Icon("kovaak_rpc", image, "Kovaak Discord RPC", menu)

    def show_main_window(self):
        def run_main():
            from gui import MainWindow
            app = MainWindow(self.settings, self)
            app.mainloop()

        main_thread = threading.Thread(target=run_main, daemon=True)
        main_thread.start()

    def run_tray(self):
        self.start_monitoring()
        self.icon.run()

    def start_monitoring(self):
        if not self.monitoring:
            self.monitoring = True
            self.monitor_thread = threading.Thread(target=self.monitor_kovaaks, daemon=True)
            self.monitor_thread.start()

    def stop_monitoring(self):
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1)

    def monitor_kovaaks(self):
        while self.monitoring:
            if is_kovaaks_running():
                if not self.rpc_running and not self.settings.get("open_manually", True):
                    self.start_rpc()
            else:
                if self.rpc_running:
                    self.current_scenario = None

            time.sleep(5)

    def start_rpc(self):
        if self.rpc_running:
            return

        try:
            self.rpc = Presence(CLIENT_ID)
            self.rpc.connect()
            self.rpc_running = True
            self.start_time = time.time()
            self.scenario_played = False
            print("Discord RPC started")

            rpc_thread = threading.Thread(target=self.rpc_update_loop, daemon=True)
            rpc_thread.start()

        except Exception as e:
            print(f"Error starting RPC: {e}")

    def stop_rpc(self):
        if not self.rpc_running:
            return

        try:
            self.rpc_running = False
            if self.rpc:
                self.rpc.close()
                self.rpc = None
            print("Discord RPC stopped")
        except Exception as e:
            print(f"Error stopping RPC: {e}")

    def rpc_update_loop(self):
        while self.rpc_running and is_kovaaks_running():
            try:
                scenario_name = get_current_scenario()

                if scenario_name != self.current_scenario:
                    if self.current_scenario is not None:
                        print(f"Switching to new scenario: {scenario_name}")
                    self.current_scenario = scenario_name
                    self.initialize_scenario_data(scenario_name)
                    self.scenario_played = False
                    self.session_highscore = 0

                if scenario_name and scenario_name != "Unknown Scenario":
                    self.update_presence(scenario_name)

            except Exception as e:
                print(f"Error in RPC update loop: {e}")

            time.sleep(10)

        if self.rpc_running:
            self.stop_rpc()

    def initialize_scenario_data(self, scenario_name):
        if scenario_name and self.installation_path:
            stats_dir = os.path.join(self.installation_path, "stats")
            self.highscore, new_checked_files = find_initial_scores(scenario_name, stats_dir)
            self.checked_files.update(new_checked_files)

    def update_presence(self, scenario_name):
        try:
            if self.installation_path:
                stats_dir = os.path.join(self.installation_path, "stats")
                current_score, found_new_score = find_fight_time_and_score(scenario_name, stats_dir, self.checked_files)
                if found_new_score:
                    self.scenario_played = True
                    self.session_highscore = max(self.session_highscore, current_score)
                else:
                    if not self.scenario_played:
                        self.session_highscore = 0

                online_score = None
                if self.settings.get("show_online_scores", False) and self.settings.get("webapp_username"):
                    online_score = self.online_api.get_online_highscore(scenario_name, self.settings["webapp_username"])

                update_presence(self.rpc, scenario_name, self.start_time,
                                self.highscore, self.session_highscore, online_score, self.installation_path)
        except Exception as e:
            print(f"Error updating presence: {e}")

    def on_settings_saved(self, new_settings):
        from config import save_settings
        self.settings = new_settings
        save_settings(new_settings)

        if new_settings.get("installation_path") != self.installation_path:
            self.initialize_paths()

    def initialize_paths(self):
        try:
            self.installation_path, self.settings = initialize_installation_path()
            self.config = load_or_create_config()
            self.config["installation_path"] = self.installation_path
            save_config(self.config)
            self.checked_files = set(self.config["checked_files"])
        except Exception as e:
            print(f"Error initializing paths: {e}")

    def quit_app(self):
        self.stop_monitoring()
        self.stop_rpc()

        for proc in psutil.process_iter(['name']):
            try:
                if proc.info['name'] and proc.info['name'].lower() == 'rpc.exe':
                    proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        self.icon.stop()

        sys.exit(0)