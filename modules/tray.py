import os
import time
import threading
import sys
from pypresence import Presence
import psutil
import pystray
from PIL import Image

from modules.config import load_settings, load_or_create_config, save_config, initialize_installation_path, \
    get_resource_path, save_settings
from modules.kovaaks_utils import is_kovaaks_running, get_current_scenario, find_initial_scores, \
    find_fight_time_and_score
from modules.online_api import OnlineScoreAPI
from modules.discord_rpc import CLIENT_ID, update_presence
from modules.gui import MainWindow


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
        self.online_scores = {}
        self.settings = load_settings()
        self.installation_path = None
        self.config = None
        self.rpc = None
        self.rpc_running = False
        self.monitoring = False
        self.monitor_thread = None
        self.current_scenario = None
        self.checked_files = set()
        self.local_highscore = 0
        self.session_highscore = 0
        self.start_time = None
        self.online_api = OnlineScoreAPI()
        self.scenario_played = False
        self.online_scenario_cache = {}

        self.initialize_paths()
        self.create_tray_icon()

    def create_tray_icon(self):
        image = load_icon()

        menu = pystray.Menu(
            pystray.MenuItem("Show Main Window", self.show_main_window, default=True),
            pystray.MenuItem("Start RPC", self.start_rpc, enabled=lambda item: not self.rpc_running),
            pystray.MenuItem("Stop RPC", self.stop_rpc, enabled=lambda item: self.rpc_running),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit", self.quit_app)
        )

        self.icon = pystray.Icon("kovaak_rpc", image, "Kovaak Discord RPC", menu)

    def show_main_window(self):
        def run_main():
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

    def is_scenario_allowed(self, scenario_name):
        if not self.settings.get("online_only_scenarios", False):
            return True

        if not scenario_name or scenario_name == "Unknown Scenario":
            return False

        if scenario_name in self.online_scenario_cache:
            return self.online_scenario_cache[scenario_name]

        try:
            print(f"Checking online availability for scenario: {scenario_name}")
            is_available = self.online_api.is_scenario_available_online(
                self.settings.get("webapp_username"),
                scenario_name
            )

            self.online_scenario_cache[scenario_name] = is_available

            if is_available:
                print(f"Scenario '{scenario_name}' is available online")
            else:
                print(f"Scenario '{scenario_name}' is NOT available online - will be filtered out")

            return is_available
        except Exception as e:
            print(f"Error checking scenario availability for '{scenario_name}': {e}")
            return True

    def start_rpc(self):
        if self.rpc_running:
            return

        try:
            self.rpc = Presence(CLIENT_ID)
            self.rpc.connect()
            self.rpc_running = True
            self.start_time = time.time()
            self.scenario_played = False

            if self.settings.get("show_online_scores") and self.settings.get("webapp_username"):
                print("Loading online scores...")
                self.online_scores = self.online_api.fetch_user_scenario_scores(
                    self.settings.get("webapp_username")
                )

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
                raw_name = get_current_scenario()
                allowed = self.is_scenario_allowed(raw_name)
                display_name = raw_name if allowed else "Unknown Scenario"

                if display_name != self.current_scenario:
                    self.current_scenario = display_name
                    if allowed:
                        stats_dir = os.path.join(self.installation_path, "stats")
                        self.local_highscore, new_files = find_initial_scores(raw_name, stats_dir)
                        self.checked_files.update(new_files)
                        self.scenario_played = False
                        self.session_highscore = 0
                    else:
                        self.local_highscore = 0
                        self.session_highscore = 0

                self.update_presence_scores(display_name, allowed, raw_name)

            except Exception as e:
                print(f"Error in RPC update loop: {e}")

            time.sleep(10)

        if self.rpc_running:
            self.stop_rpc()

    def update_presence_scores(self, display_name, allowed, raw_name):
        try:
            if not allowed:
                display_name = "Unknown Scenario"
                current_session_score = 0
            else:

                stats_dir = os.path.join(self.installation_path, "stats")
                current_session_score, found_new_score = find_fight_time_and_score(
                    raw_name, stats_dir, self.checked_files
                )

                if found_new_score:
                    self.scenario_played = True
                    self.session_highscore = max(self.session_highscore, current_session_score)


                    if self.settings.get("show_online_scores") and self.settings.get("webapp_username"):
                        username = self.settings.get("webapp_username")
                        if self.online_api.update_local_score(raw_name, self.session_highscore, username):

                            self.online_scores[raw_name] = self.session_highscore
                            print(f"New all-time high detected for '{raw_name}': {self.session_highscore}")
                elif not self.scenario_played:
                    self.session_highscore = 0

            display_highscore = self.local_highscore
            online_score = None

            if self.settings.get("show_online_scores") and self.settings.get("webapp_username"):
                username = self.settings.get("webapp_username")
                online_score = self.online_api.get_online_score(username, display_name)
                if online_score is not None:
                    display_highscore = online_score
                    print(f"Using online highscore for '{display_name}': {online_score}")
                else:
                    print(f"No online score found for '{display_name}', using local: {self.local_highscore}")

            update_presence(
                self.rpc,
                display_name,
                self.start_time,
                display_highscore,
                self.session_highscore,
                online_score,
                self.installation_path
            )

        except Exception as e:
            print(f"Error updating presence: {e}")

    def on_settings_saved(self, new_settings):
        old_username = self.settings.get("webapp_username")
        old_show_online = self.settings.get("show_online_scores")

        self.settings = new_settings
        save_settings(new_settings)
        if (new_settings.get("webapp_username") and new_settings.get("show_online_scores") and
                (new_settings.get("webapp_username") != old_username or not old_show_online)):
            print("Reloading online scores due to settings change...")
            self.online_scores = self.online_api.fetch_user_scenario_scores(
                new_settings.get("webapp_username")
            )

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
        import os
        self.stop_monitoring()
        self.stop_rpc()

        try:
            self.icon.stop()
        except Exception:
            pass

        os._exit(0)