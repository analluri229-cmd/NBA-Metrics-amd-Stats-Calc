"""nba.cmd must start the project's venv Python (it has requests/nba_api), not whatever `py -3` finds."""
from __future__ import annotations

from pathlib import Path

NBA_CMD = Path(__file__).resolve().parents[2] / "nba.cmd"


def test_launcher_prefers_venv_python():
    text = NBA_CMD.read_text(encoding="utf-8").lower()
    user_venv = text.find(r"%userprofile%\.venv\scripts\python.exe")
    local_venv = text.find(r"%~dp0.venv\scripts\python.exe")
    fallback = text.find("py -3 -m pipeline")
    assert user_venv != -1 and local_venv != -1 and fallback != -1
    assert local_venv < user_venv < fallback
