import os
import json
import sys
import winreg
import customtkinter as ctk
from tkinter import filedialog

SETTINGS_FILE = "settings.json"
CONFIG_FILE = "checked_files.json"

DEFAULT_SETTINGS = {
    "installation_path": "",
    "steam_path": r"C:\Program Files (x86)\Steam\steam.exe",
    "open_manually": False,
    "start_with_windows": False,
    "webapp_username": "",
    "show_online_scores": False,
    "start_in_tray": False
}


def get_resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def load_settings():
    if os.path.isfile(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as file:
                settings = json.load(file)
                for key, value in DEFAULT_SETTINGS.items():
                    if key not in settings:
                        settings[key] = value
                return settings
        except Exception as e:
            print(f"Error loading settings: {e}")
    return DEFAULT_SETTINGS.copy()


def save_settings(settings):
    try:
        with open(SETTINGS_FILE, "w") as file:
            json.dump(settings, file, indent=4)
    except Exception as e:
        print(f"Error saving settings: {e}")


def load_or_create_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as file:
                config = json.load(file)
                if isinstance(config, list):
                    config = {"checked_files": config, "installation_path": None}
                return config
        except:
            pass
    return {"checked_files": [], "installation_path": None}


def save_config(config):
    with open(CONFIG_FILE, "w") as file:
        json.dump(config, file)


def get_steam_path_from_registry():
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam") as key:
            steam_path = winreg.QueryValueEx(key, "InstallPath")[0]
            candidate = os.path.join(steam_path, "steamapps", "common", "FPSAimTrainer", "FPSAimTrainer")
            if os.path.exists(os.path.join(candidate, "stats")):
                return candidate
    except Exception as e:
        print(f"Error detecting Steam path: {e}")
    return None


def prompt_for_installation_folder():
    root = ctk.CTk()
    root.withdraw()
    folder_path = filedialog.askdirectory(title="Select FPSAimTrainer Installation Folder")
    root.destroy()
    return folder_path


def initialize_installation_path():
    settings = load_settings()
    if not settings.get("installation_path"):
        detected = get_steam_path_from_registry()
        if not detected:
            detected = prompt_for_installation_folder()
            if not detected:
                print("No installation folder selected. Using default behavior.")
                return None, settings
        settings["installation_path"] = detected
        save_settings(settings)
    return settings["installation_path"], settings