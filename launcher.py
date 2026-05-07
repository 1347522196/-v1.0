from __future__ import annotations

import contextlib
import socket
import threading
import time
import traceback
import webbrowser
from pathlib import Path
from tkinter import BOTH, LEFT, RIGHT, Button, Frame, Label, StringVar, Tk

import requests
import uvicorn

from app.main import app as fastapi_app
from app.runtime import executable_dir

HOST = "127.0.0.1"


def find_free_port() -> int:
    with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.bind((HOST, 0))
        sock.listen(1)
        return int(sock.getsockname()[1])


class DesktopLauncher:
    def __init__(self) -> None:
        self.log_path = executable_dir() / "seller_sprite_lite.log"
        self.port = find_free_port()
        self.url = f"http://{HOST}:{self.port}"
        self.browser_opened = False
        self.server = uvicorn.Server(
            uvicorn.Config(
                fastapi_app,
                host=HOST,
                port=self.port,
                log_level="warning",
                access_log=False,
            )
        )
        self.server.install_signal_handlers = lambda: None
        self.server_thread = threading.Thread(target=self.run_server, daemon=True)
        self.root = Tk()
        self.status_text = StringVar(value="Starting local service...")
        self._build_window()
        self.log("Launcher initialized.")

    def log(self, message: str) -> None:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("a", encoding="utf-8") as fh:
            fh.write(f"[{timestamp}] {message}\n")

    def run_server(self) -> None:
        try:
            self.log(f"Starting uvicorn on {self.url}")
            self.server.run()
            self.log("Uvicorn stopped.")
        except Exception:
            self.log("Uvicorn crashed:\n" + traceback.format_exc())

    def _build_window(self) -> None:
        self.root.title("SellerSprite Lite")
        self.root.geometry("520x220")
        self.root.minsize(480, 200)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        shell = Frame(self.root, padx=24, pady=22)
        shell.pack(fill=BOTH, expand=True)

        Label(
            shell,
            text="SellerSprite Lite",
            font=("Microsoft YaHei UI", 18, "bold"),
            anchor="w",
        ).pack(anchor="w")
        Label(
            shell,
            text="Double-click the exe to start the local app and open it in your browser.",
            font=("Microsoft YaHei UI", 10),
            anchor="w",
            pady=10,
        ).pack(anchor="w")
        Label(
            shell,
            textvariable=self.status_text,
            font=("Microsoft YaHei UI", 10),
            anchor="w",
            wraplength=450,
            justify=LEFT,
        ).pack(anchor="w", pady=(0, 18))

        button_row = Frame(shell)
        button_row.pack(anchor="w")

        Button(button_row, text="Open App", width=12, command=self.open_browser).pack(
            side=LEFT, padx=(0, 10)
        )
        Button(button_row, text="Exit", width=12, command=self.close).pack(side=RIGHT)

    def start(self) -> None:
        self.server_thread.start()
        self.root.after(200, self.wait_until_ready)
        self.root.mainloop()

    def wait_until_ready(self) -> None:
        if self.server.started:
            self.log("Health check passed via server.started flag.")
            self._mark_ready()
            return

        if self.server.should_exit:
            self.log("Server flagged should_exit during startup.")
            self.status_text.set("Startup failed. Please reopen the program.")
            return

        try:
            response = requests.get(f"{self.url}/api/health", timeout=1)
            if response.ok:
                self.log("Health endpoint responded successfully.")
                self._mark_ready()
                return
        except requests.RequestException:
            pass

        self.root.after(400, self.wait_until_ready)

    def _mark_ready(self) -> None:
        self.status_text.set(f"App is ready. If the browser did not open, visit: {self.url}")
        if not self.browser_opened:
            self.open_browser()

    def open_browser(self) -> None:
        webbrowser.open(self.url, new=1)
        self.browser_opened = True
        self.status_text.set(f"App is ready. If the browser did not open, visit: {self.url}")

    def close(self) -> None:
        self.log("Shutting down launcher.")
        self.status_text.set("Stopping local service...")
        self.server.should_exit = True
        deadline = time.time() + 8
        while self.server_thread.is_alive() and time.time() < deadline:
            self.root.update_idletasks()
            time.sleep(0.1)
        self.root.destroy()


def main() -> None:
    DesktopLauncher().start()


if __name__ == "__main__":
    main()
