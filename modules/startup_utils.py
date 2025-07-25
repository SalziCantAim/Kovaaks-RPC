import os
import sys
import win32com.client


def get_app_executable_path():
    if getattr(sys, 'frozen', False):
        return sys.executable
    else:
        return os.path.abspath(sys.argv[0])


def get_startup_folder():
    return os.path.join(os.getenv('APPDATA'), r"Microsoft\Windows\Start Menu\Programs\Startup")


def get_startup_shortcut_path():
    exe_name = os.path.basename(get_app_executable_path())
    shortcut_name = os.path.splitext(exe_name)[0] + ".lnk"
    return os.path.join(get_startup_folder(), shortcut_name)


def set_startup_shortcut(enable: bool):
    shortcut_path = get_startup_shortcut_path()
    exe_path = get_app_executable_path()
    if enable:
        if not os.path.exists(shortcut_path):
            shell = win32com.client.Dispatch("WScript.Shell")
            shortcut = shell.CreateShortCut(shortcut_path)
            shortcut.Targetpath = exe_path
            shortcut.WorkingDirectory = os.path.dirname(exe_path)
            shortcut.IconLocation = exe_path
            shortcut.save()
    else:
        if os.path.exists(shortcut_path):
            try:
                os.remove(shortcut_path)
            except Exception as e:
                print(f"Error deleting startup shortcut: {e}")