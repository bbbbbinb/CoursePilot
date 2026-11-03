from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
BACKEND_DIR = PROJECT_ROOT / "backend"
VENV_DIR = PROJECT_ROOT / ".venv"
REQUIREMENTS_FILE = BACKEND_DIR / "requirements.txt"
ENV_FILE = PROJECT_ROOT / ".env"
ENV_EXAMPLE = PROJECT_ROOT / ".env.example"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Start the Zhiheng enterprise knowledge verification workspace."
    )
    parser.add_argument(
        "--port",
        type=valid_port,
        default=8000,
        help="HTTP port (default: 8000).",
    )
    parser.add_argument(
        "--no-reload",
        action="store_true",
        help="Disable Uvicorn auto-reload.",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not open the browser automatically.",
    )
    return parser.parse_args()


def valid_port(value: str) -> int:
    try:
        port = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("port must be an integer") from exc
    if not 1 <= port <= 65535:
        raise argparse.ArgumentTypeError("port must be between 1 and 65535")
    return port


def venv_python() -> Path:
    if sys.platform == "win32":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def run_checked(command: list[str | Path], **kwargs: object) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [str(item) for item in command],
        cwd=PROJECT_ROOT,
        text=True,
        **kwargs,
    )
    if result.returncode != 0:
        raise SystemExit(f"Command failed with exit code {result.returncode}.")
    return result


def ensure_virtual_environment() -> Path:
    python = venv_python()
    if python.exists():
        return python

    print("[setup] Creating Python virtual environment...")
    run_checked([sys.executable, "-m", "venv", VENV_DIR])
    return python


def check_backend_import(python: Path) -> tuple[bool, str]:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(BACKEND_DIR)
    environment["PYTHONUTF8"] = "1"
    environment["PYTHONIOENCODING"] = "utf-8"
    result = subprocess.run(
        [str(python), "-c", "import app.main"],
        cwd=PROJECT_ROOT,
        env=environment,
        text=True,
        capture_output=True,
    )
    output = "\n".join(part for part in (result.stdout, result.stderr) if part).strip()
    return result.returncode == 0, output


def ensure_dependencies(python: Path) -> None:
    if not REQUIREMENTS_FILE.exists():
        raise SystemExit(f"Missing dependency file: {REQUIREMENTS_FILE}")

    ready, output = check_backend_import(python)
    if ready:
        return

    if "ModuleNotFoundError" not in output:
        print(output, file=sys.stderr)
        raise SystemExit("Backend import check failed. Review the error above.")

    print("[setup] Installing backend dependencies...")
    run_checked([python, "-m", "pip", "install", "-r", REQUIREMENTS_FILE])

    ready, output = check_backend_import(python)
    if not ready:
        print(output, file=sys.stderr)
        raise SystemExit("Backend dependencies are still incomplete after installation.")


def ensure_configuration() -> None:
    if ENV_FILE.exists():
        return
    if not ENV_EXAMPLE.exists():
        raise SystemExit(f"Missing configuration template: {ENV_EXAMPLE}")

    shutil.copyfile(ENV_EXAMPLE, ENV_FILE)
    print(
        "[setup] Created .env from .env.example. "
        "Fill in the API keys before document ingestion or chat."
    )


def ensure_data_directories() -> None:
    for directory in (
        PROJECT_ROOT / "data",
        PROJECT_ROOT / "data" / "chroma",
        PROJECT_ROOT / "data" / "session",
        PROJECT_ROOT / "data" / "uploads",
    ):
        directory.mkdir(parents=True, exist_ok=True)


def open_browser_when_ready(url: str) -> None:
    health_url = f"{url}api/v1/health"
    for _ in range(40):
        try:
            with urllib.request.urlopen(health_url, timeout=1) as response:
                if response.status == 200:
                    webbrowser.open(url)
                    return
        except (OSError, urllib.error.URLError):
            time.sleep(0.5)


def start_server(python: Path, args: argparse.Namespace) -> int:
    url = f"http://127.0.0.1:{args.port}/"
    print(f"[start] Frontend: {url}")
    print(f"[start] API docs: {url}docs")
    print(f"[start] Health:   {url}api/v1/health")
    print("[start] Press Ctrl+C to stop the server.\n")

    if not args.no_browser:
        threading.Thread(
            target=open_browser_when_ready,
            args=(url,),
            daemon=True,
        ).start()

    command = [
        str(python),
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(args.port),
    ]
    if not args.no_reload:
        command.append("--reload")

    environment = os.environ.copy()
    environment["PYTHONUTF8"] = "1"
    environment["PYTHONIOENCODING"] = "utf-8"
    process = subprocess.Popen(command, cwd=BACKEND_DIR, env=environment)

    try:
        return process.wait()
    except KeyboardInterrupt:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        return 130


def main() -> int:
    args = parse_args()
    print("\nZhiheng - Enterprise Knowledge Verification")
    print(f"Project: {PROJECT_ROOT}\n")

    python = ensure_virtual_environment()
    ensure_dependencies(python)
    ensure_configuration()
    ensure_data_directories()
    return start_server(python, args)


if __name__ == "__main__":
    raise SystemExit(main())
