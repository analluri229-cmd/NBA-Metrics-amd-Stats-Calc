#!/usr/bin/env python3
"""Launch the external NBA data source connectors used by this workspace.

This project includes the dgrubis.github.io repo as a Git submodule. The repo is
an older Tableau Web Data Connector (WDC) and its Node dependencies are not fully
compatible with modern Node runtimes, so this script attempts a safe start for the
current environment while preserving the source integration.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WDC_DIR = ROOT / "dgrubis.github.io"


def ensure_prereqs() -> None:
    if shutil.which("npm") is None:
        raise RuntimeError("npm is required to run the NBA Stats WDC.")

    if shutil.which("node") is None:
        raise RuntimeError("node is required to run the NBA Stats WDC.")

    if not WDC_DIR.exists():
        raise RuntimeError(
            "dgrubis.github.io is missing. Run: git submodule update --init --recursive"
        )

    if not (WDC_DIR / "package.json").exists():
        raise RuntimeError(f"{WDC_DIR} does not look like the NBA Stats WDC project.")


def node_major_version() -> int:
    result = subprocess.run(
        ["node", "-p", "process.versions.node.split('.')[0]"],
        capture_output=True,
        text=True,
        check=True,
    )
    return int(result.stdout.strip())


def install_dependencies() -> None:
    ensure_prereqs()
    if not (WDC_DIR / "node_modules").exists():
        print("Installing WDC dependencies...")
        subprocess.run(["npm", "install", "--legacy-peer-deps"], cwd=WDC_DIR, check=True)


def start_static_server() -> None:
    print("Starting static WDC server (no CORS proxy) ...")
    print("Connector URL: http://localhost:8888/nbastatsWDC.html")
    print("Press Ctrl+C to stop the server.")
    subprocess.run(["npx", "http-server", "-p", "8888", "-c-1"], cwd=WDC_DIR, check=True)


def start_wdc() -> None:
    ensure_prereqs()
    if not (WDC_DIR / "node_modules").exists():
        install_dependencies()

    major = node_major_version()
    if major >= 18:
        print(
            "The upstream WDC is built on an older Node/Hapi stack and is not fully "
            "compatible with Node 18+ in this environment."
        )
        print("Falling back to a static connector page so the project still has the repo integrated.")
        start_static_server()
        return

    print("Starting NBA Stats WDC...")
    print("Local connector URL: http://localhost:8888")
    print("CORS proxy URL:     http://localhost:8889")
    print("Press Ctrl+C to stop the connector.")

    try:
        subprocess.run(["npm", "start"], cwd=WDC_DIR, check=True)
    except KeyboardInterrupt:
        print("\nStopping NBA Stats WDC.")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Start the external NBA data-source connectors used by this workspace."
    )
    parser.add_argument(
        "--install",
        action="store_true",
        help="Install the WDC dependencies without starting the connector.",
    )
    parser.add_argument(
        "--static-only",
        action="store_true",
        help="Serve only the HTML connector page, without the legacy CORS proxy.",
    )
    args = parser.parse_args()

    try:
        if args.install:
            install_dependencies()
            print(f"Dependencies installed successfully in {WDC_DIR}")
            return 0
        if args.static_only:
            start_static_server()
            return 0
        start_wdc()
        return 0
    except KeyboardInterrupt:
        print("\nStopped.")
        return 0
    except Exception as exc:  # pragma: no cover - CLI error reporting
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
