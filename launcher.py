import subprocess
import sys
import os
import time
import webbrowser
import threading
import urllib.request

APP_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
URL = "http://127.0.0.1:8000"

# ANSI color codes
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
PURPLE = "\033[38;5;141m"
CYAN = "\033[38;5;87m"
GREEN = "\033[38;5;84m"
GRAY = "\033[38;5;243m"
WHITE = "\033[97m"


def clear():
    os.system("cls" if os.name == "nt" else "clear")


def animate_text(text, delay=0.02):
    for ch in text:
        sys.stdout.write(ch)
        sys.stdout.flush()
        time.sleep(delay)
    print()


def loading_bar(label, duration=1.5, width=30):
    for i in range(width + 1):
        filled = "█" * i
        empty = "░" * (width - i)
        pct = int(i / width * 100)
        sys.stdout.write(
            f"\r  {GRAY}{label} {PURPLE}{filled}{GRAY}{empty}{RESET} {WHITE}{pct}%{RESET}"
        )
        sys.stdout.flush()
        time.sleep(duration / width)
    print()


def show_splash():
    clear()

    # Enable ANSI on Windows
    if os.name == "nt":
        os.system("")

    print()
    logo = f"""{PURPLE}{BOLD}
    ╔═══════════════════════════════════════════╗
    ║                                           ║
    ║        ███████╗██╗   ██╗██████╗           ║
    ║        ██╔════╝██║   ██║██╔══██╗          ║
    ║        ███████╗██║   ██║██████╔╝          ║
    ║        ╚════██║██║   ██║██╔══██╗          ║
    ║        ███████║╚██████╔╝██████╔╝          ║
    ║        ╚══════╝ ╚═════╝ ╚═════╝           ║
    ║           {CYAN}G  E  N{PURPLE}                         ║
    ║                                           ║
    ╚═══════════════════════════════════════════╝{RESET}
    """
    print(logo)

    time.sleep(0.3)
    animate_text(f"  {DIM}Subtitle Generator v1.0{RESET}", 0.025)
    animate_text(f"  {DIM}Powered by Whisper AI + FFmpeg{RESET}", 0.02)
    print()

    loading_bar("Loading AI model", duration=2.0)
    loading_bar("Starting server ", duration=0.8)
    print()

    print(f"  {GREEN}{BOLD}✓{RESET} {WHITE}Server ready{RESET}")
    print(f"  {CYAN}→{RESET} {WHITE}{URL}{RESET}")
    print()
    print(f"  {DIM}Opening browser...{RESET}")
    print()
    print(f"  {GRAY}{'─' * 43}{RESET}")
    print(f"  {DIM}Press {WHITE}Ctrl+C{RESET}{DIM} to stop the server{RESET}")
    print(f"  {GRAY}{'─' * 43}{RESET}")
    print()


def wait_and_open_browser():
    """Wait until the server is actually responding, then open browser once."""
    for _ in range(60):
        time.sleep(1)
        try:
            urllib.request.urlopen(URL, timeout=2)
            webbrowser.open(URL)
            return
        except Exception:
            continue
    print(f"  {PURPLE}!{RESET} Server did not respond within 60 seconds")


def main():
    os.chdir(APP_DIR)

    # Enable ANSI on Windows
    if os.name == "nt":
        os.system("")

    show_splash()

    threading.Thread(target=wait_and_open_browser, daemon=True).start()

    try:
        proc = subprocess.Popen(
            [sys.executable, "-u", "run.py"],
            cwd=APP_DIR,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        proc.wait()
    except KeyboardInterrupt:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            pass
        print()
        print(f"  {GREEN}{BOLD}✓{RESET} {WHITE}Server stopped. Goodbye!{RESET}")
        print()


if __name__ == "__main__":
    main()
