"""
SubGen Installer — Modern styled console installer
Run: python install.py
"""
import subprocess
import sys
import os
import shutil
import time

# ANSI
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
PURPLE = "\033[38;5;141m"
CYAN = "\033[38;5;87m"
GREEN = "\033[38;5;84m"
RED = "\033[38;5;210m"
YELLOW = "\033[38;5;222m"
GRAY = "\033[38;5;243m"
WHITE = "\033[97m"


def clear():
    os.system("cls" if os.name == "nt" else "clear")


def animate_text(text, delay=0.015):
    for ch in text:
        sys.stdout.write(ch)
        sys.stdout.flush()
        time.sleep(delay)
    print()


def progress_bar(label, duration=2.0, width=36):
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


def status(icon, color, msg):
    print(f"  {color}{icon}{RESET} {msg}")


def check(msg):
    status("✓", GREEN, msg)


def warn(msg):
    status("!", YELLOW, msg)


def fail(msg):
    status("✗", RED, msg)


def info(msg):
    status("→", CYAN, msg)


def header():
    clear()
    if os.name == "nt":
        os.system("")

    print()
    print(f"""
  {PURPLE}{BOLD}╔═══════════════════════════════════════════╗
  ║         SubGen Installer                  ║
  ╚═══════════════════════════════════════════╝{RESET}
    """)


def check_prerequisites():
    print(f"  {WHITE}{BOLD}Checking prerequisites...{RESET}")
    print()
    all_ok = True

    # Python
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    if sys.version_info >= (3, 10):
        check(f"Python {py_ver}")
    else:
        fail(f"Python {py_ver} (need 3.10+)")
        all_ok = False

    # FFmpeg
    if shutil.which("ffmpeg"):
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True, text=True, timeout=10
            )
            ver_line = result.stdout.split("\n")[0] if result.stdout else "unknown"
            check(f"FFmpeg found ({ver_line.split(' ')[2] if len(ver_line.split(' ')) > 2 else 'ok'})")
        except Exception:
            check("FFmpeg found")
    else:
        fail("FFmpeg not found — install from https://ffmpeg.org")
        all_ok = False

    # NVIDIA GPU
    if shutil.which("nvidia-smi"):
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=10
            )
            gpu_info = result.stdout.strip().split(",")
            gpu_name = gpu_info[0].strip() if gpu_info else "unknown"
            gpu_mem = gpu_info[1].strip() + " MB" if len(gpu_info) > 1 else ""
            check(f"GPU: {gpu_name} ({gpu_mem})")
        except Exception:
            check("NVIDIA GPU detected")
    else:
        warn("No NVIDIA GPU — will use CPU (slower)")

    print()
    return all_ok


def install_dependencies():
    print(f"  {WHITE}{BOLD}Installing dependencies...{RESET}")
    print()

    req_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "requirements.txt")

    try:
        proc = subprocess.Popen(
            [sys.executable, "-m", "pip", "install", "-r", req_file,
             "--quiet", "--disable-pip-version-check"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        progress_bar("Installing packages", duration=3.0)

        proc.wait()

        if proc.returncode == 0:
            check("All packages installed")
        else:
            output = proc.stdout.read() if proc.stdout else ""
            fail("Some packages failed to install")
            if output.strip():
                print(f"    {DIM}{output.strip()[-200:]}{RESET}")
            return False

    except Exception as e:
        fail(f"Installation error: {e}")
        return False

    print()
    return True


def verify_install():
    print(f"  {WHITE}{BOLD}Verifying installation...{RESET}")
    print()

    checks = [
        ("fastapi", "FastAPI"),
        ("uvicorn", "Uvicorn"),
        ("faster_whisper", "Faster-Whisper (AI model)"),
        ("sse_starlette", "SSE-Starlette"),
        ("aiofiles", "Aiofiles"),
    ]

    all_ok = True
    for module, name in checks:
        try:
            __import__(module)
            check(name)
        except ImportError:
            fail(f"{name} — not installed")
            all_ok = False

    print()
    return all_ok


def show_complete():
    print(f"  {GREEN}{BOLD}{'━' * 43}{RESET}")
    print()
    print(f"  {GREEN}{BOLD}Installation complete!{RESET}")
    print()
    print(f"  {WHITE}To start SubGen:{RESET}")
    print()
    print(f"    {CYAN}python run.py{RESET}")
    print()
    print(f"  {DIM}Or double-click SubtitleGenerator.exe{RESET}")
    print(f"  {DIM}Then open {WHITE}http://127.0.0.1:8000{RESET}")
    print()
    print(f"  {GRAY}{'━' * 43}{RESET}")
    print()


def show_failed():
    print()
    print(f"  {RED}{BOLD}Installation had errors.{RESET}")
    print(f"  {DIM}Fix the issues above and run:{RESET}")
    print(f"    {CYAN}python install.py{RESET}")
    print()


def main():
    header()

    prereqs_ok = check_prerequisites()
    if not prereqs_ok:
        warn("Some prerequisites missing — attempting install anyway...")
        print()

    if not install_dependencies():
        show_failed()
        return

    if verify_install():
        show_complete()
    else:
        show_failed()


if __name__ == "__main__":
    main()
