from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
WORKSPACE_ROOT = PROJECT_ROOT.parent
DATA_DIR = WORKSPACE_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
CLEAN_DATA_DIR = DATA_DIR / "clean"
TABLEAU_DATA_DIR = DATA_DIR / "tableau"

DEFAULT_SEASON = 2025
DEFAULT_TEAMS = ["GSW", "BOS", "DAL", "LAL", "MIL"]
DEFAULT_PLAYERS = [
    "Stephen Curry",
    "Jayson Tatum",
    "Nikola Jokic",
    "Giannis Antetokounmpo",
]

RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
CLEAN_DATA_DIR.mkdir(parents=True, exist_ok=True)
TABLEAU_DATA_DIR.mkdir(parents=True, exist_ok=True)
