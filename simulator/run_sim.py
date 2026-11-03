"""
Project Alpha - Wall-E Simulator Launcher
Runs a lightweight local web server and opens the interactive digital twin in your default web browser.
"""

import http.server
import socketserver
import webbrowser
import os
import sys

PORT = 8085
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

def main():
    print("=" * 60)
    print("  PROJECT ALPHA - WALL-E ROBOT DIGITAL TWIN SIMULATOR")
    print("=" * 60)
    print(f"Serving simulator from: {DIRECTORY}")
    print(f"Local URL: http://localhost:{PORT}")
    print("Opening browser automatically... (Press Ctrl+C to stop)")
    print("=" * 60)

    url = f"http://localhost:{PORT}/index.html"
    webbrowser.open(url)

    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down simulator server. Goodbye!")

if __name__ == "__main__":
    main()
