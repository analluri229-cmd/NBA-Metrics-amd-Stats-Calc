"""Per-season stats for one player, from the warehouse.

Copy to local_analysis/<name>.py, edit STATS, then from the project root:
    python local_analysis/<name>.py "Luka Doncic" [--playoffs] [--chart]
"""
import argparse
import sqlite3
import sys
import unicodedata
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))  # so "pipeline" imports when run from local_analysis/

from pipeline.etl.paths import DB_PATH as DB  # noqa: E402

OUT = ROOT / "local_analysis" / "output"

# column name -> (source_system, stat_table, stat_name); look names up in data/clean/dim_stat.csv
STATS = {
    "ppg": ("nba_stats", "per_game", "pts"),
    "ts_pct": ("nba_stats", "advanced", "ts_pct"),
}


def connect() -> sqlite3.Connection:
    return sqlite3.connect(f"{DB.as_uri()}?mode=ro", uri=True)


def plain(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii").lower().replace("-", " ")


def find_player(con: sqlite3.Connection, name: str) -> pd.Series:
    dim = pd.read_sql("SELECT player_id, player_name FROM dim_player", con)
    names = dim.player_name.map(plain)
    hits = dim[names == plain(name)]
    if hits.empty:
        hits = dim[names.str.contains(plain(name), regex=False)]
    if len(hits) != 1:
        raise SystemExit(f"{len(hits)} players match {name!r}: {hits.player_name.tolist()[:10]}")
    return hits.iloc[0]


def season_stats(con: sqlite3.Connection, player_id: str, stats: dict = STATS,
                 season_type: str = "regular") -> pd.DataFrame:
    where = " OR ".join(["(source_system = ? AND stat_table = ? AND stat_name = ?)"] * len(stats))
    df = pd.read_sql(f"""
        SELECT season, source_system, stat_table, stat_name, value FROM fact_player_season_stat
        WHERE player_id = ? AND season_type = ? AND split = 'TOT' AND ({where})
    """, con, params=[player_id, season_type, *[part for key in stats.values() for part in key]])
    column = {key: col for col, key in stats.items()}
    df["stat"] = [column[k] for k in zip(df.source_system, df.stat_table, df.stat_name)]
    return df.pivot(index="season", columns="stat", values="value").reindex(columns=list(stats))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("player")
    parser.add_argument("--playoffs", action="store_true")
    parser.add_argument("--chart", action="store_true", help="save a PNG to local_analysis/output/")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")  # accented names crash the default Windows console encoding

    with connect() as con:
        player = find_player(con, args.player)
        table = season_stats(con, player.player_id, season_type="playoffs" if args.playoffs else "regular")
    print(player.player_name, f"({player.player_id})")
    print(table.to_string())

    if args.chart:
        import matplotlib.pyplot as plt

        OUT.mkdir(parents=True, exist_ok=True)
        table.plot(subplots=True, marker="o", figsize=(8, 2.5 * len(table.columns)), title=player.player_name)
        path = OUT / f"{player.player_id}.png"
        plt.savefig(path, bbox_inches="tight")
        print(f"saved {path}")


if __name__ == "__main__":
    main()
