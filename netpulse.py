#!/usr/bin/env python3
"""
NetPulse - Live Network Moniter 

Features:
 - TCP-connect based latency (ms) to a list of hosts
 - Download speed estimate (Mbps) by reading a small chunk from a URL
 - Live updating modern colored UI with simple sparkline history
 - No external Python packages required (stdlib only)
 - Works on Termux / Linux / macOS / Windows (Python 3.7+)

Author: Karndeep Baror - Ethical Hacker 
"""

from __future__ import annotations
import argparse
import socket
import sys
import time
import threading
import urllib.request
import urllib.error
from collections import deque
from typing import List, Tuple

# ----- ANSI -----
CSI = "\x1b["
RESET = CSI + "0m"
BOLD = CSI + "1m"
DIM = CSI + "2m"
FG_CYAN = CSI + "36m"
FG_BLUE = CSI + "34m"
FG_GREEN = CSI + "32m"
FG_YELLOW = CSI + "33m"
FG_RED = CSI + "31m"
FG_WHITE = CSI + "37m"

def col(s: str, c: str) -> str:
    return f"{c}{s}{RESET}"

# ---- Utilities --------
def clear():
    if sys.platform.startswith("win"):
        _ = __import__("os").system("cls")
    else:
        sys.stdout.write("\033[2J\033[H")

def now_ts() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")

def human_mbps(bps: float) -> str:
    """Convert bytes/sec to Mbps string."""
    if bps is None:
        return "n/a"
    mbps = (bps * 8) / 1_000_000
    return f"{mbps:.2f} Mbps"

def spinner(ch):
    return "|/-\\"[ch % 4]

# ---------------- Networking helpers ----------------
def tcp_connect_time(host: str, port: int, timeout: float = 1.0) -> float:
    """Return connect time in milliseconds, or None on failure."""
    try:
        start = time.time()
        with socket.create_connection((host, port), timeout=timeout):
            end = time.time()
        return (end - start) * 1000.0
    except Exception:
        return None

def download_probe(url: str, bytes_to_read: int = 256 * 1024, timeout: float = 4.0) -> Tuple[int, float]:
    """
    Download up to bytes_to_read from url and return (bytes_read, seconds_elapsed).
    Uses urllib (stdlib). Caller converts to Mbps.
    """
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "NetPulse/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            read = 0
            start = time.time()
            while read < bytes_to_read:
                chunk = resp.read(min(32 * 1024, bytes_to_read - read))
                if not chunk:
                    break
                read += len(chunk)
            end = time.time()
        elapsed = max(0.0001, end - start)
        return read, elapsed
    except Exception:
        return 0, 0.0

# ---------------- Sparkline helper ----------------
SPARK_CHARS = "▁▂▃▄▅▆▇█"
def sparkline(values: List[float], width: int = 30) -> str:
    if not values:
        return " " * width
    vals = list(values)[-width:]
    mx = max(vals) if max(vals) > 0 else 1.0
    out = ""
    for v in vals:
        idx = int((v / mx) * (len(SPARK_CHARS) - 1))
        out += SPARK_CHARS[idx]
    # pad
    if len(out) < width:
        out = (" " * (width - len(out))) + out
    return out

# ---------------- Main NetPulse class ----------------
class NetPulse:
    def __init__(self, hosts: List[Tuple[str,int]], url: str, bytes_probe: int, interval: float):
        self.hosts = hosts
        self.url = url
        self.bytes_probe = bytes_probe
        self.interval = max(1.0, interval)
        self.running = False
        self.lock = threading.Lock()
        # history deques
        self.download_history = deque(maxlen=120)
        self.ping_history = {f"{h[0]}:{h[1]}": deque(maxlen=120) for h in hosts}
        self.last_results = {}
        self.spinner_idx = 0

    def measure_once(self):
        """Perform one round of measurements (latency + download)."""
        results = {}
        # measure pings (TCP connect)
        for host, port in self.hosts:
            ms = tcp_connect_time(host, port, timeout=1.2)
            results[f"{host}:{port}"] = ms  # ms or None
        # measure download
        bytes_read, seconds = download_probe(self.url, bytes_to_read=self.bytes_probe, timeout=6.0)
        bps = (bytes_read / seconds) if seconds > 0 else 0.0
        # update histories
        with self.lock:
            # update download history
            self.download_history.append(bps)
            for hp, val in results.items():
                self.ping_history[hp].append(val if val is not None else 0.0)
            self.last_results = {"pings": results, "download_bps": bps, "bytes": bytes_read, "elapsed": seconds}
        return self.last_results

    def start(self):
        self.running = True
        # run in background thread loop
        def loop():
            while self.running:
                try:
                    self.measure_once()
                except Exception:
                    pass
                time.sleep(self.interval)
        t = threading.Thread(target=loop, daemon=True)
        t.start()

    def stop(self):
        self.running = False

    def snapshot(self):
        with self.lock:
            return dict(self.last_results), list(self.download_history), {k: list(v) for k, v in self.ping_history.items()}

# ---------------- Terminal rendering ----------------
def render(net: NetPulse):
    # render single frame
    (res, dl_hist, p_hist) = net.snapshot()
    clear()
    print(col("─" * 72, DIM))
    print(col("NetPulse — Live Network Monitor", BOLD + FG_CYAN) + "    " + col(now_ts(), DIM))
    print(col("Python • Lightweight • Press Ctrl+C to exit", DIM))
    print(col("─" * 72, DIM))
    # download
    bps = res.get("download_bps") if res else None
    human = human_mbps(bps) if bps else "n/a"
    print()
    print(col("Download:", FG_BLUE), col(human, BOLD + FG_GREEN), f"({res.get('bytes',0)} bytes in {res.get('elapsed',0):.2f}s)" if res else "")
    # sparkline
    print(col("History:", DIM), sparkline(dl_hist, width=48))
    print()
    # pings table
    print(col(f"{'Host:Port':22} {'Ping (ms)':12} {'Trend':30}", BOLD))
    print(col("-" * 72, DIM))
    if res:
        for hp, val in res["pings"].items():
            hist = p_hist.get(hp, [])
            last = val
            last_str = f"{last:.1f} ms" if last and last > 0 else "timeout"
            trend = sparkline(hist, width=30)
            print(f"{col(hp, FG_CYAN):22} {col(last_str, FG_YELLOW):12} {trend:30}")
    else:
        print("No results yet...")
    print()
    print(col("Probe URL:", DIM), net.url)
    print(col("Update interval:", DIM), f"{net.interval}s   ", col("Bytes/read per probe:", DIM), net.bytes_probe)
    print(col("─" * 72, DIM))
    print(col(f"{col(spinner(net.spinner_idx), FG_CYAN)} Running... (Ctrl+C to stop)", DIM))
    net.spinner_idx = (net.spinner_idx + 1) % 4

# ---------------- CLI & run ----------------
def parse_hosts(s: str) -> List[Tuple[str,int]]:
    out = []
    for part in s.split(","):
        part = part.strip()
        if not part:
            continue
        if ":" in part:
            h, p = part.rsplit(":", 1)
            try:
                out.append((h, int(p)))
                continue
            except Exception:
                pass
        # default port 80 if not specified
        out.append((part, 80))
    return out

def default_hosts():
    return [("8.8.8.8", 53), ("1.1.1.1", 53), ("google.com", 80)]

def main():
    p = argparse.ArgumentParser(description="NetPulse — live network monitor (modern terminal UI).")
    p.add_argument("--hosts", help="Comma-separated host:port list (default: 8.8.8.8:53,1.1.1.1:53,google.com:80)", default=None)
    p.add_argument("--url", help="URL to fetch small chunk from for download speed test (default small file)", default="http://ipv4.download.thinkbroadband.com/5MB.zip")
    p.add_argument("--bytes", type=int, help="Bytes to read per probe (default 262144 = 256 KiB)", default=262144)
    p.add_argument("--interval", type=float, help="Seconds between probes (default 2)", default=2.0)
    args = p.parse_args()

    hosts = parse_hosts(args.hosts) if args.hosts else default_hosts()
    npulse = NetPulse(hosts=hosts, url=args.url, bytes_probe=args.bytes, interval=args.interval)
    try:
        npulse.start()
        # initial small wait so first measurement completes quickly
        time.sleep(0.2)
        # main render loop
        while True:
            render(npulse)
            time.sleep( max(0.5, args.interval / 2) )
    except KeyboardInterrupt:
        npulse.stop()
        clear()
        print(col("─" * 60, DIM))
        print(col("NetPulse Stopped.", BOLD + FG_CYAN))
        print(col("Summary snapshot:", DIM))
        snap, dh, ph = npulse.snapshot()
        if snap:
            print(col(f"Last download: {human_mbps(snap.get('download_bps',0))} ({snap.get('bytes',0)} bytes in {snap.get('elapsed',0):.2f}s)", FG_GREEN))
            for hp, v in snap.get("pings",{}).items():
                if v and v>0:
                    print(f"  {hp:20} {v:.1f} ms")
                else:
                    print(f"  {hp:20} timeout")
        print(col("Goodbye 👋 , By Cryptonic Area", DIM))
    except Exception as e:
        npulse.stop()
        clear()
        print(col(f"Fatal error: {e}", FG_RED))
        sys.exit(1)

if __name__ == "__main__":
    main()
