import threading
from modules.config import load_settings
from modules.gui import MainWindow
from modules.tray import SystemTrayApp


def main():
    settings = load_settings()

    if settings.get("start_in_tray", False):
        app = SystemTrayApp()
        app.run_tray()
    else:
        tray_app = SystemTrayApp()

        def run_tray():
            tray_app.run_tray()

        tray_thread = threading.Thread(target=run_tray, daemon=True)
        tray_thread.start()

        main_window = MainWindow(settings, tray_app)
        main_window.mainloop()

        tray_app.quit_app()


if __name__ == "__main__":
    main()