"""Turn one raw file from <your source> into canonical rows. No network, no database.

Copy this folder to pipeline/etl/sources/<your_source>/ and work through each FILL IN.
Real examples: darko/adapter.py (ratings by date), basketball_reference/team_season.py (team
season tables from CSV). Canonical tables and their columns: pipeline/etl/canonical/schema.py.
"""
from __future__ import annotations

from pathlib import Path

from ...canonical.contract import AdapterResult, RawFile, new_result, to_float  # noqa: F401
from ...canonical.resolver import IdResolver


class TemplateAdapter:
    # FILL IN: source_name is this adapter's id (recorded per file in source_manifest);
    # source_system is the data family used for precedence (schema.SOURCE_PRECEDENCE).
    source_name = "template"
    source_system = "template"

    def discover(self, raw_root: Path) -> list[RawFile]:
        """Every raw file this adapter can parse, with its season."""
        # FILL IN: glob the files extract.py writes, e.g.
        #   for season_dir in sorted((raw_root / "<your_source>").glob("[0-9][0-9][0-9][0-9]")):
        #       for path in sorted(season_dir.glob("*.json")):
        #           found.append(RawFile.from_path(path, self.source_name, "<data type>", int(season_dir.name)))
        found: list[RawFile] = []
        return found

    def parse(self, raw: RawFile, resolver: IdResolver) -> AdapterResult:
        """Rows keyed by canonical table: result.add("<table>", {...})."""
        result = new_result(self, raw)
        # FILL IN: read raw.path, set result.raw_row_count, then for each row:
        #   team_id = resolver.team(self.source_name, row["team"], {"file": raw.path.name})
        #   player_id = resolver.player(self.source_name, row["id"], row["name"], team_id, raw.season,
        #                               fallback_id=f"<prefix>_{row['id']}")
        #   result.add("fact_player_season_stat", {...})   # columns: see canonical/schema.py
        #   result.skip(index, "reason") for rows you can't use
        return result
