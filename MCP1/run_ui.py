"""
Launcher for Zomato Customer Review Pulse Web UI.
Usage:
    python run_ui.py
    python run_ui.py 8000
    python run_ui.py 8000 --no-browser
"""
import sys
import threading
import time
import webbrowser
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from ui.server import run_server


def open_browser_delayed(url: str):
    time.sleep(1.0)
    try:
        webbrowser.open(url)
    except Exception:
        pass


if __name__ == "__main__":
    port = 8000
    auto_open = True

    for arg in sys.argv[1:]:
        if arg == "--no-browser":
            auto_open = False
        else:
            try:
                port = int(arg)
            except ValueError:
                pass

    if auto_open:
        threading.Thread(target=open_browser_delayed, args=(f"http://localhost:{port}",), daemon=True).start()

    run_server(port)
