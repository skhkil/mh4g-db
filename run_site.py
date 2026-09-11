#!/usr/bin/env python3
from __future__ import annotations
import functools
import http.server
import os
import socketserver
import threading
import webbrowser
from pathlib import Path

VERSION = "0.6.7"
ROOT = Path(__file__).resolve().parent

class NoCacheHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def log_message(self, fmt, *args):
        print("[MH4G] " + (fmt % args))

class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True


def main():
    os.chdir(ROOT)
    handler = functools.partial(NoCacheHandler, directory=str(ROOT))
    # Port 0 asks Windows/Python to choose a currently free port, so an old
    # localhost:8080 server can never cause us to show the previous version.
    with ReusableTCPServer(("127.0.0.1", 0), handler) as httpd:
        port = httpd.server_address[1]
        url = f"http://127.0.0.1:{port}/?v={VERSION}"
        print("=" * 60)
        print(f" MH4G Simulator v{VERSION}")
        print(f" {url}")
        print(" Ctrl+C to stop")
        print("=" * 60)
        threading.Timer(0.7, lambda: webbrowser.open(url)).start()
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[MH4G] server stopped")

if __name__ == "__main__":
    main()
