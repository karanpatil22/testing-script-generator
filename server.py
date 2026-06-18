#!/usr/bin/env python3
"""
server.py
-----------------------------------------------------------------------------
Local backend for the Playwright Recorder.

Responsibilities:
  * Serve the static UI (index.html, scripts/, styles/).
  * Expose POST /api/record which launches `playwright codegen` for a given
    URL and returns the generated test code once the user closes the window.

No third-party dependencies — uses only the Python standard library. Playwright
itself is invoked as a subprocess (`python -m playwright codegen`), so it must
be installed in the same interpreter that runs this server (see setup.sh).

Binds to localhost only.
"""

import json
import os
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

ROOT = os.path.dirname(os.path.abspath(__file__))
HOST = "127.0.0.1"
PORT = int(os.environ.get("PORT", "8000"))

# Playwright codegen targets we accept from the client.
VALID_TARGETS = {"python-pytest", "python", "python-async", "javascript"}

# ── Nvidia NIM (optional "polish" step) ───────────────────────
# The browser cannot call NIM directly (no CORS), so the polish request is
# proxied through this server. The API key never reaches the client.
NIM_ENDPOINT = "https://integrate.api.nvidia.com/v1/chat/completions"
# A non-reasoning code/instruct model is intentional here. The earlier default
# (minimaxai/minimax-m2.7) is a chain-of-thought reasoner: it spent the whole
# token budget on `reasoning_content` and returned empty `content` (or timed
# out) for real recordings. qwen3-next-80b-a3b-instruct returns code directly,
# fast, with no reasoning tokens.
NIM_MODEL = "qwen/qwen3-next-80b-a3b-instruct"
NIM_MAX_TOKENS = 4000
NIM_TEMPERATURE = 0.2
NIM_TOP_P = 0.95


def get_nim_key():
    """Resolve the Nvidia NIM key from the environment or a local key file."""
    key = (os.environ.get("NVIDIA_API_KEY")
           or os.environ.get("NVIDIA_NIM_KEY")
           or "").strip()
    if key:
        return key
    key_file = os.path.join(ROOT, "nim_key.txt")
    if os.path.isfile(key_file):
        try:
            with open(key_file, "r", encoding="utf-8") as f:
                return f.read().strip()
        except OSError:
            pass
    return ""


def polish(prompt):
    """Call Nvidia NIM to polish a recording. Returns (code, error_message)."""
    key = get_nim_key()
    if not key:
        return None, ("No Nvidia NIM API key configured. Set NVIDIA_API_KEY "
                      "or create a nim_key.txt file next to server.py.")

    body = json.dumps({
        "model": NIM_MODEL,
        "max_tokens": NIM_MAX_TOKENS,
        "temperature": NIM_TEMPERATURE,
        "top_p": NIM_TOP_P,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")

    req = urllib.request.Request(
        NIM_ENDPOINT,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + key,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = e.read().decode("utf-8")[:300]
        except Exception:
            pass
        if e.code == 401:
            return None, "Nvidia NIM rejected the API key (401). Check the key."
        if e.code == 429:
            return None, "Nvidia NIM rate limit hit (429). Wait ~60s and retry."
        return None, f"Nvidia NIM request failed (HTTP {e.code}). {detail}".strip()
    except urllib.error.URLError as e:
        return None, f"Could not reach Nvidia NIM: {e.reason}"
    except (ValueError, json.JSONDecodeError):
        return None, "Invalid response from Nvidia NIM."

    try:
        choice = data["choices"][0]
        content = choice["message"]["content"]
    except (KeyError, IndexError, TypeError):
        choice, content = {}, None

    if not content or not content.strip():
        if choice.get("finish_reason") == "length":
            return None, ("Nvidia NIM hit the token limit while reasoning and "
                          "produced no code. The recording may be very long — "
                          "try a shorter flow, or raise NIM_MAX_TOKENS.")
        return None, "Nvidia NIM returned an empty response."
    return content, None

STATIC_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
}


def run_codegen(url, target):
    """Run `playwright codegen` and return (code, error_message).

    Blocks until the user closes the codegen browser window.
    """
    fd, out_path = tempfile.mkstemp(suffix=".py", prefix="rec_")
    os.close(fd)
    try:
        cmd = [
            sys.executable, "-m", "playwright", "codegen",
            "--target", target,
            "-o", out_path,
            url,
        ]
        # No shell=True; args are passed as a list to avoid injection.
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            msg = (proc.stderr or proc.stdout or "").strip()
            low = msg.lower()
            if "no module named playwright" in low:
                msg = "Playwright is not installed. Run ./setup.sh first."
            elif "executable doesn't exist" in low or "playwright install" in low:
                msg = ("Browser not installed. Run: "
                       "python -m playwright install chromium")
            elif not msg:
                msg = "playwright codegen exited with an error."
            return None, msg

        with open(out_path, "r", encoding="utf-8") as f:
            return f.read(), None
    except FileNotFoundError:
        return None, "Playwright is not installed. Run ./setup.sh first."
    finally:
        try:
            os.remove(out_path)
        except OSError:
            pass


class Handler(BaseHTTPRequestHandler):
    server_version = "PlaywrightRecorder/1.0"

    # ── helpers ───────────────────────────────────────────────
    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, code, obj):
        self._send(code, json.dumps(obj))

    # ── routes ────────────────────────────────────────────────
    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            path = "/index.html"

        # Resolve safely under ROOT to prevent path traversal.
        safe = os.path.normpath(os.path.join(ROOT, path.lstrip("/")))
        if not (safe == ROOT or safe.startswith(ROOT + os.sep)) or not os.path.isfile(safe):
            self._send(404, "Not found", "text/plain; charset=utf-8")
            return

        ext = os.path.splitext(safe)[1].lower()
        ctype = STATIC_TYPES.get(ext, "application/octet-stream")
        with open(safe, "rb") as f:
            self._send(200, f.read(), ctype)

    def do_POST(self):
        path = urlparse(self.path).path
        if path not in ("/api/record", "/api/polish"):
            self._send_json(404, {"error": "Unknown endpoint"})
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
        except (ValueError, json.JSONDecodeError):
            self._send_json(400, {"error": "Invalid JSON body"})
            return

        if path == "/api/polish":
            prompt = (payload.get("prompt") or "").strip()
            if not prompt:
                self._send_json(400, {"error": "Missing prompt"})
                return
            print("[recorder] polishing recording via Nvidia NIM…")
            code, err = polish(prompt)
            if err:
                print(f"[recorder] polish error: {err}")
                self._send_json(502, {"error": err})
                return
            self._send_json(200, {"code": code})
            return

        url = (payload.get("url") or "").strip()
        target = (payload.get("target") or "python-pytest").strip()

        if not (url.startswith("http://") or url.startswith("https://")):
            self._send_json(400, {"error": "URL must start with http:// or https://"})
            return
        if target not in VALID_TARGETS:
            target = "python-pytest"

        print(f"[recorder] launching codegen for {url} (target={target})")
        code, err = run_codegen(url, target)
        if err:
            print(f"[recorder] codegen error: {err}")
            self._send_json(500, {"error": err})
            return

        print("[recorder] recording captured")
        self._send_json(200, {"code": code})

    def log_message(self, fmt, *args):  # quieter default logging
        sys.stderr.write("[server] " + (fmt % args) + "\n")


def main():
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Playwright Recorder running at http://{HOST}:{PORT}")
    print("Open that URL in your browser. Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
