"""
Desktop launcher for TestCraft Goo.

Packaged into TestCraftGoo.exe via PyInstaller. Starts the Streamlit
server and opens the app in the default browser automatically, so
end users never need to touch a terminal.
"""

import os
import sys
import threading
import time
import webbrowser

from streamlit.web import cli as stcli


def _app_base_dir():
    """Directory containing app.py — the exe's own folder when frozen."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def _open_browser_when_ready():
    time.sleep(3)
    webbrowser.open("http://localhost:8501")


if __name__ == "__main__":
    os.chdir(_app_base_dir())

    threading.Thread(target=_open_browser_when_ready, daemon=True).start()

    sys.argv = [
        "streamlit",
        "run",
        "app.py",
        "--global.developmentMode=false",
        # headless=true so Streamlit doesn't also auto-open a browser tab —
        # _open_browser_when_ready() above handles that once, avoiding duplicates.
        "--server.headless=true",
    ]

    sys.exit(stcli.main())
