"""The guided menu behind ``python -m pipeline`` (and nba.cmd).

The menu only asks questions and builds command lines for pipeline.etl.orchestrator; it prints
each command before running it, so anything done here can be repeated from the command line.
Defaults come from pipeline/settings.py.
"""
from __future__ import annotations

import math
import sys
from typing import Callable

from pipeline import settings
from pipeline.etl.canonical.dates import season_label
from pipeline.prompts import ask_choice, ask_date, ask_seasons, ask_yes_no

MENU = {
    "1": "Update current season      pull every default source for the current season, then build",
    "2": "Backfill seasons           choose seasons, sources and regular/playoffs",
    "3": "Daily box scores           Basketball-Reference box scores for a date range",
    "4": "DARKO ratings              rating snapshots for chosen seasons",
    "5": "Rebuild warehouse          offline: load raw files -> features",
    "6": "Export CSVs                write data/clean/ from the warehouse",
    "q": "Quit",
}
SEASON_TYPE_CHOICES = {"regular": "regular season", "playoffs": "playoffs", "both": "regular season and playoffs"}
EXPORT_CHOICES = {"1": "latest season", "2": "chosen seasons (one folder each)", "3": "all seasons"}
DARKO_NOTE = "DARKO data: use it locally; don't publish it (Tableau Public, GitHub, shared files)."


def pull_argv(source: str, seasons: list[int], season_type: str, skip_existing: bool) -> list[str]:
    argv = ["pull", "--source", source, "--season", *map(str, seasons)]
    if source == "nba_stats":
        argv += ["--season-type", season_type]
    if source == "bbref" and settings.BBREF_WITH_WEB_SCRAPER:
        argv.append("--with-web-scraper")
    if skip_existing:
        argv.append("--skip-existing")
    return argv


def _requests(source: str, missing_files: int | None, season_count: int) -> float:
    """Rough seconds of request pacing for a pull."""
    if source == "nba_stats":
        return (missing_files or 0) * settings.NBA_STATS_DELAY_SECONDS
    if source == "bbref":
        return 8 * season_count * settings.BBREF_DELAY_SECONDS
    if source == "bbref_team":
        return season_count * settings.BBREF_DELAY_SECONDS
    return 210 / settings.DARKO_EVERY_DAYS * season_count * settings.DARKO_DELAY_SECONDS


def _minutes(seconds: float) -> str:
    return f"about {max(1, math.ceil(seconds / 60))} min"


def _has_game_logs(season: int) -> bool:
    folder = settings.RAW_DIR / "nba_stats" / str(season)
    return (folder / "team_game_log.json").exists() or (folder / "team_game_log_playoffs.json").exists()


def _labels(seasons: list[int]) -> str:
    return ", ".join(season_label(s) for s in seasons)


class Menu:
    def __init__(self, ask: Callable[[str], str], say: Callable[[str], None], run: Callable[[list[str]], int]):
        self.ask, self.say, self.run = ask, say, run
        self.failed = False

    def command(self, argv: list[str]) -> int:
        """Run one orchestrator command; a failure is reported and the menu carries on."""
        self.say("-> python -m pipeline.etl.orchestrator " + " ".join(argv))
        try:
            code = self.run(argv)
        except (KeyboardInterrupt, EOFError):
            raise
        except SystemExit as exc:
            code = exc.code if isinstance(exc.code, int) else 1
        except Exception as exc:
            self.say(f"FAILED: {type(exc).__name__}: {exc}")
            code = 1
        self.failed |= bool(code)
        return code

    def ask_sources(self) -> list[str]:
        default = " ".join(settings.DEFAULT_SOURCES)
        while True:
            answer = self.ask(f"Sources ({', '.join(settings.SOURCE_CHOICES)}) [{default}]: ").strip() or default
            chosen = [s for s in answer.replace(",", " ").split() if s]
            unknown = [s for s in chosen if s not in settings.SOURCE_CHOICES]
            if chosen and not unknown:
                return sorted(set(chosen), key=settings.SOURCE_CHOICES.index)  # darko always after nba_stats
            self.say(f"  Unknown source(s) {', '.join(unknown) or '(none)'}; choose from {', '.join(settings.SOURCE_CHOICES)}.")

    def plan_pulls(self, sources: list[str], seasons: list[int], season_type: str) -> list[list[str]]:
        """Check what is on disk and ask, per source, what to download. Returns the pull commands."""
        from pipeline.etl.sources.inventory import inventory

        pulls: list[list[str]] = []
        for source in sources:
            todo, complete, missing_files = [], [], 0
            for season in seasons:
                if source == "darko" and "nba_stats" not in sources and not _has_game_logs(season):
                    self.say(f"  {season_label(season)}: pull nba_stats for this season first; skipping DARKO.")
                    continue
                found = inventory(source, season, season_type)
                if found.status == "all":
                    complete.append(season)
                    self.say(f"  {source} {season_label(season)}: already complete ({found.have} of {found.expected} files).")
                    continue
                todo.append(season)
                missing_files += (found.expected or 0) - found.have
                detail = "nothing yet" if found.status == "none" else (
                    f"{found.have} of {found.expected} files" if found.expected else f"{found.have} snapshots")
                self.say(f"  {source} {season_label(season)}: {detail}.")
            if todo and ask_yes_no(f"{source}: download what's missing for {_labels(todo)}? "
                                   f"({_minutes(_requests(source, missing_files, len(todo)))})",
                                   True, self.ask, self.say):
                pulls.append(pull_argv(source, todo, season_type, True))
            if complete and ask_yes_no(f"{source}: download {_labels(complete)} again? This replaces the saved files",
                                       False, self.ask, self.say):
                pulls.append(pull_argv(source, complete, season_type, False))
        return pulls

    def pull_then_build(self, pulls: list[list[str]]) -> None:
        if not pulls:
            self.say("Nothing to download.")
            return
        for argv in pulls:
            self.command(argv)
        if ask_yes_no("Load the new files into the warehouse now?", True, self.ask, self.say):
            self.build()

    def build(self) -> None:
        export = ask_yes_no("Export CSVs too?", settings.EXPORT_AFTER_RUN, self.ask, self.say)
        self.command(["run", "--export"] if export else ["run"])

    def update_current(self) -> None:
        from pipeline.etl.sources.inventory import inventory

        season = settings.current_season()
        sources = list(settings.DEFAULT_SOURCES)
        files = sum(inventory(s, season, settings.SEASON_TYPE).expected or 0 for s in sources)
        seconds = sum(_requests(s, inventory(s, season, settings.SEASON_TYPE).expected, 1) for s in sources)
        if not ask_yes_no(f"Update {season_label(season)} from {', '.join(sources)}? Replaces about {files} files, "
                          f"{_minutes(seconds)}", True, self.ask, self.say):
            return
        # Season-to-date tables change after every game, so they are always downloaded again;
        # DARKO snapshots are fixed per date, so only new dates are fetched.
        self.pull_then_build([pull_argv(s, [season], settings.SEASON_TYPE, s == "darko") for s in sources])

    def backfill(self) -> None:
        default = f"{min(settings.SEASONS)}-{max(settings.SEASONS)}"
        seasons = ask_seasons(default, ask=self.ask, say=self.say)
        sources = self.ask_sources()
        season_type = ask_choice("Season type", SEASON_TYPE_CHOICES, settings.SEASON_TYPE, self.ask, self.say)
        self.pull_then_build(self.plan_pulls(sources, seasons, season_type))

    def box_scores(self) -> None:
        start = ask_date("First date", ask=self.ask, say=self.say)
        end = ask_date("Last date", start.isoformat(), self.ask, self.say)
        self.pull_then_build([["pull", "--source", "bbref", "--date", start.isoformat(), "--end", end.isoformat()]])

    def darko(self) -> None:
        self.say(DARKO_NOTE)
        seasons = ask_seasons(str(settings.current_season()), ask=self.ask, say=self.say)
        self.pull_then_build(self.plan_pulls(["darko"], seasons, settings.SEASON_TYPE))

    def export(self) -> None:
        choice = ask_choice("Export", EXPORT_CHOICES, "1", self.ask, self.say)
        if choice == "1":
            self.command(["export"])
        elif choice == "3":
            self.command(["export", "--all-seasons"])
        else:
            for season in ask_seasons(str(settings.current_season()), ask=self.ask, say=self.say):
                self.command(["export", "--season", str(season)])


def interactive() -> bool:
    """A person at a console: stdin and stdout are both terminals (Windows reports NUL as one)."""
    return all(stream is not None and stream.isatty() for stream in (sys.stdin, sys.stdout))


def run_menu(ask: Callable[[str], str] = input, say: Callable[[str], None] = print,
             run: Callable[[list[str]], int] | None = None, is_tty: Callable[[], bool] = interactive) -> int:
    from pipeline.etl import orchestrator

    try:
        settings.validate()
    except settings.SettingsError as exc:
        say(f"pipeline/settings.py: {exc}")
        return 2
    if not is_tty():
        say(orchestrator.build_parser().format_help())
        return 0
    menu = Menu(ask, say, orchestrator.main if run is None else run)
    actions = {"1": menu.update_current, "2": menu.backfill, "3": menu.box_scores, "4": menu.darko,
               "5": menu.build, "6": menu.export}
    try:
        while True:
            say("")
            choice = ask_choice("What do you want to do?", MENU, "q", ask, say)
            if choice == "q":
                return 1 if menu.failed else 0
            actions[choice]()
    except (KeyboardInterrupt, EOFError):
        say("Cancelled.")
        return 1
