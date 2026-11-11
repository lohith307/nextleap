"""
Launcher for Zomato Customer Review Pulse Web UI.
Usage:
    python run_ui.py
    python run_ui.py 8080
"""
import sys
import webbrowser
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from ui.server import run_server

if __name__ == "__main__":
    port = 8000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass

    print(f"Launching Zomato Customer Pulse UI on http://localhost:{port}...")
    try:
        webbrowser.open(f"http://localhost:{port}")
    except Exception:
        pass

    run_server(port)
