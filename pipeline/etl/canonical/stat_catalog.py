"""Data dictionary for player season stats: what each stat means and how to read it.

Every (source_system, stat_table, stat_name) in fact_player_season_stat gets a
``dim_stat`` row with a label, definition, category, unit, basis and direction.

Units
    count           raw count (basis says total / per game / per 36 / per 100 poss)
    fraction        0-1 share or percentage (0.456 = 45.6%)
    percent         0-100 percentage
    index           league average = 100
    rating          points per 100 possessions
    points          point differential or points added
    ratio           one number per another (points per possession, dribbles per touch)
    minutes, seconds, years, feet, miles, mph, per_48, estimate

higher_is_better: 1 higher is better, 0 lower is better, NULL depends on context
(volume, age, pace, shot mix).

Stats matched by no rule get documented = 0 so gaps are visible, never hidden.
"""
from __future__ import annotations

import re
import sqlite3

from .schema import STAT_TABLES

# canonical concept -> (label, category, unit, higher_is_better, definition)
CONCEPTS: dict[str, tuple[str, str, str, int | None, str]] = {
    "gp": ("Games played", "availability", "count", None, "Games in which the player appeared."),
    "gs": ("Games started", "availability", "count", None, "Games the player started."),
    "min": ("Minutes", "availability", "minutes", None, "Minutes played."),
    "age": ("Age", "bio", "years", None, "Player age for the season (as of Feb 1 on Basketball-Reference)."),
    "w": ("Wins", "team_results", "count", 1, "Team wins in games the player appeared in."),
    "l": ("Losses", "team_results", "count", 0, "Team losses in games the player appeared in."),
    "w_pct": ("Win %", "team_results", "fraction", 1, "Team win percentage in games the player appeared in."),
    "pts": ("Points", "scoring", "count", 1, "Points scored."),
    "fgm": ("Field goals made", "shooting", "count", 1, "Field goals made (2s and 3s)."),
    "fga": ("Field goal attempts", "shooting", "count", None, "Field goals attempted; shot volume."),
    "fg_pct": ("FG%", "shooting", "fraction", 1, "Field goals made / attempted."),
    "fg2m": ("2-pt FG made", "shooting", "count", 1, "Two-point field goals made."),
    "fg2a": ("2-pt FG attempts", "shooting", "count", None, "Two-point field goals attempted."),
    "fg2_pct": ("2-pt FG%", "shooting", "fraction", 1, "Two-point field goals made / attempted."),
    "fg3m": ("3-pt FG made", "shooting", "count", 1, "Three-point field goals made."),
    "fg3a": ("3-pt FG attempts", "shooting", "count", None, "Three-point field goals attempted."),
    "fg3_pct": ("3-pt FG%", "shooting", "fraction", 1, "Three-point field goals made / attempted."),
    "ftm": ("Free throws made", "shooting", "count", 1, "Free throws made."),
    "fta": ("Free throw attempts", "shooting", "count", None, "Free throws attempted."),
    "ft_pct": ("FT%", "shooting", "fraction", 1, "Free throws made / attempted."),
    "efg_pct": ("Effective FG%", "shooting", "fraction", 1,
                "(FGM + 0.5 x 3PM) / FGA: FG% with threes weighted for their extra point."),
    "ts_pct": ("True shooting %", "shooting", "fraction", 1,
               "PTS / (2 x (FGA + 0.44 x FTA)): scoring efficiency including threes and free throws."),
    "oreb": ("Offensive rebounds", "rebounding", "count", 1, "Offensive rebounds."),
    "dreb": ("Defensive rebounds", "rebounding", "count", 1, "Defensive rebounds."),
    "reb": ("Total rebounds", "rebounding", "count", 1, "Offensive + defensive rebounds."),
    "ast": ("Assists", "playmaking", "count", 1, "Assists."),
    "stl": ("Steals", "defense", "count", 1, "Steals."),
    "blk": ("Blocks", "defense", "count", 1, "Blocked shots."),
    "blka": ("Shots blocked against", "ball_security", "count", 0, "The player's own shots that were blocked."),
    "tov": ("Turnovers", "ball_security", "count", 0, "Turnovers committed."),
    "pf": ("Personal fouls", "fouls", "count", 0, "Personal fouls committed."),
    "pfd": ("Fouls drawn", "fouls", "count", 1, "Personal fouls drawn."),
    "plus_minus": ("Plus-minus", "impact", "points", 1, "Team point differential while the player was on the court."),
    "dd2": ("Double-doubles", "scoring", "count", 1, "Games with 10+ in two of PTS/REB/AST/STL/BLK."),
    "td3": ("Triple-doubles", "scoring", "count", 1, "Games with 10+ in three of PTS/REB/AST/STL/BLK."),
    "nba_fantasy_pts": ("NBA fantasy points", "impact", "count", 1, "NBA.com fantasy scoring."),
    "fp_high_score": ("Fantasy high score", "impact", "count", 1, "Best single-game NBA.com fantasy score."),
}

# Source names that are the same concept under another spelling.
ALIASES = {
    "games": "gp", "g": "gp", "games_started": "gs", "mp": "min", "fg": "fgm", "fg2": "fg2m", "fg3": "fg3m",
    "ft": "ftm", "orb": "oreb", "drb": "dreb", "trb": "reb", "tpl_dbl": "td3", "fga_pg": "fga", "fgm_pg": "fgm",
    "points": "pts",
}

BASIS_BY_TABLE = {"totals": "total", "per_game": "per game", "per_36": "per 36 minutes",
                  "per_100": "per 100 possessions"}
BBREF_SUFFIX_BASIS = {"_per_g": "per game", "_per_minute_36": "per 36 minutes", "_per_poss": "per 100 possessions"}
COUNT_UNITS = {"count", "minutes"}
# Season counts reported unchanged in per-game / per-36 / per-100 tables.
UNSCALED = {"gp", "gs", "w", "l", "dd2", "td3", "fp_high_score"}

# Stats specific to one source/table: stat_name -> (label, category, unit, higher_is_better, definition)
SPECIFIC: dict[str, tuple[str, str, str, int | None, str]] = {
    # --- Basketball-Reference advanced ---
    "per": ("PER", "impact", "index", 1, "Player Efficiency Rating: per-minute production, league average 15."),
    "fg3a_per_fga_pct": ("3-pt attempt rate", "shot_profile", "fraction", None, "Share of FGA that are threes (3PAr)."),
    "fta_per_fga_pct": ("Free throw rate", "shot_profile", "fraction", 1, "FTA per FGA (FTr)."),
    "orb_pct": ("Offensive rebound %", "rebounding", "fraction", 1,
                "Share of available offensive rebounds grabbed while on court."),
    "drb_pct": ("Defensive rebound %", "rebounding", "fraction", 1,
                "Share of available defensive rebounds grabbed while on court."),
    "trb_pct": ("Total rebound %", "rebounding", "fraction", 1, "Share of available rebounds grabbed while on court."),
    "ast_pct": ("Assist %", "playmaking", "fraction", 1, "Share of teammate field goals assisted while on court."),
    "stl_pct": ("Steal %", "defense", "fraction", 1, "Share of opponent possessions ending in the player's steal."),
    "blk_pct": ("Block %", "defense", "fraction", 1, "Share of opponent 2-pt attempts blocked while on court."),
    "tov_pct": ("Turnover %", "ball_security", "fraction", 0, "Turnovers per 100 plays used (as a fraction)."),
    "usg_pct": ("Usage %", "usage", "fraction", None,
                "Share of team plays used (FGA, FTA, TOV) while on court. Role, not quality."),
    "ows": ("Offensive win shares", "impact", "estimate", 1, "Wins contributed by offense."),
    "dws": ("Defensive win shares", "impact", "estimate", 1, "Wins contributed by defense."),
    "ws": ("Win shares", "impact", "estimate", 1, "Total wins contributed (OWS + DWS)."),
    "ws_per_48": ("Win shares per 48", "impact", "per_48", 1, "Win shares per 48 minutes; league average ~0.100."),
    "obpm": ("Offensive BPM", "impact", "points", 1, "Offensive box plus-minus: points per 100 poss above average."),
    "dbpm": ("Defensive BPM", "impact", "points", 1, "Defensive box plus-minus: points per 100 poss above average."),
    "bpm": ("Box plus-minus", "impact", "points", 1, "Points per 100 possessions above a league-average player."),
    "vorp": ("VORP", "impact", "estimate", 1, "Value over replacement player: BPM converted to a season total."),
    "off_rtg": ("Offensive rating (individual)", "impact", "rating", 1,
                "Points produced per 100 individual possessions (Dean Oliver)."),
    "def_rtg": ("Defensive rating (individual)", "impact", "rating", 0,
                "Points allowed per 100 possessions (Dean Oliver estimate)."),
    # --- Basketball-Reference play-by-play ---
    "pct_1": ("Time at PG", "position", "fraction", None, "Estimated share of minutes played at point guard."),
    "pct_2": ("Time at SG", "position", "fraction", None, "Estimated share of minutes played at shooting guard."),
    "pct_3": ("Time at SF", "position", "fraction", None, "Estimated share of minutes played at small forward."),
    "pct_4": ("Time at PF", "position", "fraction", None, "Estimated share of minutes played at power forward."),
    "pct_5": ("Time at C", "position", "fraction", None, "Estimated share of minutes played at center."),
    "plus_minus_on": ("On-court +/- per 100", "impact", "points", 1,
                      "Team point differential per 100 possessions with the player on the court."),
    "plus_minus_net": ("On-off +/- per 100", "impact", "points", 1,
                       "On-court minus off-court team differential per 100 possessions."),
    "tov_bad_pass": ("Bad-pass turnovers", "ball_security", "count", 0, "Turnovers from bad passes."),
    "tov_lost_ball": ("Lost-ball turnovers", "ball_security", "count", 0, "Turnovers from losing the ball."),
    "fouls_shooting": ("Shooting fouls committed", "fouls", "count", 0, "Shooting fouls committed."),
    "fouls_offensive": ("Offensive fouls committed", "fouls", "count", 0, "Offensive fouls committed."),
    "drawn_shooting": ("Shooting fouls drawn", "fouls", "count", 1, "Shooting fouls drawn."),
    "drawn_offensive": ("Offensive fouls drawn", "defense", "count", 1, "Offensive fouls drawn (charges taken etc.)."),
    "astd_pts": ("Points generated by assists", "playmaking", "count", 1, "Points created by the player's assists."),
    "and1s": ("And-ones", "scoring", "count", 1, "Made shots while fouled."),
    "own_shots_blk": ("Own shots blocked", "ball_security", "count", 0, "The player's shot attempts that were blocked."),
    # --- Basketball-Reference shooting ---
    "avg_dist": ("Average shot distance", "shot_profile", "feet", None, "Average distance of field goal attempts."),
    "pct_fga_fg2a": ("Share of FGA: 2-pt", "shot_profile", "fraction", None, "Share of FGA that are two-pointers."),
    "pct_fga_fg3a": ("Share of FGA: 3-pt", "shot_profile", "fraction", None, "Share of FGA that are three-pointers."),
    "pct_fga_00_03": ("Share of FGA: 0-3 ft", "shot_profile", "fraction", None, "Share of FGA from 0-3 feet."),
    "pct_fga_03_10": ("Share of FGA: 3-10 ft", "shot_profile", "fraction", None, "Share of FGA from 3-10 feet."),
    "pct_fga_10_16": ("Share of FGA: 10-16 ft", "shot_profile", "fraction", None, "Share of FGA from 10-16 feet."),
    "pct_fga_16_xx": ("Share of FGA: 16 ft-3P", "shot_profile", "fraction", None,
                      "Share of FGA from 16 feet to the 3-point line."),
    "fg_pct_fg2a": ("FG% on 2-pt attempts", "shooting", "fraction", 1, "FG% on two-point attempts."),
    "fg_pct_fg3a": ("FG% on 3-pt attempts", "shooting", "fraction", 1, "FG% on three-point attempts."),
    "fg_pct_00_03": ("FG%: 0-3 ft", "shooting", "fraction", 1, "FG% on shots from 0-3 feet."),
    "fg_pct_03_10": ("FG%: 3-10 ft", "shooting", "fraction", 1, "FG% on shots from 3-10 feet."),
    "fg_pct_10_16": ("FG%: 10-16 ft", "shooting", "fraction", 1, "FG% on shots from 10-16 feet."),
    "fg_pct_16_xx": ("FG%: 16 ft-3P", "shooting", "fraction", 1, "FG% on shots from 16 feet to the 3-point line."),
    "pct_ast_fg2": ("Assisted share of 2-pt FGM", "shot_creation", "fraction", None,
                    "Share of made twos that were assisted (lower = more self-created)."),
    "pct_ast_fg3": ("Assisted share of 3-pt FGM", "shot_creation", "fraction", None,
                    "Share of made threes that were assisted (lower = more self-created)."),
    "pct_fga_dunk": ("Share of FGA: dunks", "shot_profile", "fraction", None, "Share of FGA that are dunks."),
    "fg_dunk": ("Dunks made", "scoring", "count", 1, "Dunks made."),
    "pct_fg3a_corner3": ("Share of 3PA: corner", "shot_profile", "fraction", None, "Share of 3PA from the corners."),
    "fg_pct_corner3": ("Corner 3-pt FG%", "shooting", "fraction", 1, "FG% on corner threes."),
    "fg3a_heave": ("Heave attempts", "shot_profile", "count", None, "End-of-quarter heaves attempted."),
    "fg3_heave": ("Heaves made", "shooting", "count", 1, "End-of-quarter heaves made."),
    # --- Basketball-Reference adjusted shooting (league average = 100) ---
    "adj_fg_pct": ("FG+ (league-adjusted FG%)", "shooting", "index", 1, "FG% relative to league average (100)."),
    "adj_fg2_pct": ("2P+ (league-adjusted 2P%)", "shooting", "index", 1, "2-pt FG% relative to league average (100)."),
    "adj_fg3_pct": ("3P+ (league-adjusted 3P%)", "shooting", "index", 1, "3-pt FG% relative to league average (100)."),
    "adj_efg_pct": ("eFG+ (league-adjusted eFG%)", "shooting", "index", 1, "eFG% relative to league average (100)."),
    "adj_ft_pct": ("FT+ (league-adjusted FT%)", "shooting", "index", 1, "FT% relative to league average (100)."),
    "adj_ts_pct": ("TS+ (league-adjusted TS%)", "shooting", "index", 1, "TS% relative to league average (100)."),
    "adj_fta_per_fga_pct": ("FTr+ (league-adjusted FT rate)", "shot_profile", "index", 1,
                            "Free throw rate relative to league average (100)."),
    "adj_fg3a_per_fga_pct": ("3PAr+ (league-adjusted 3PA rate)", "shot_profile", "index", None,
                             "Three-point attempt rate relative to league average (100)."),
    "fg_pts_added": ("Points added by FG%", "shooting", "points", 1,
                     "Points added over a league-average shooter on the same field goal attempts."),
    "ts_pts_added": ("Points added by TS%", "shooting", "points", 1,
                     "Points added over league-average true shooting on the same scoring attempts."),
    # --- stats.nba.com advanced (on-court team ratings while the player plays) ---
    "off_rating": ("Offensive rating (on court)", "impact", "rating", 1,
                   "Team points scored per 100 possessions while the player is on the court."),
    "def_rating": ("Defensive rating (on court)", "impact", "rating", 0,
                   "Team points allowed per 100 possessions while the player is on the court."),
    "net_rating": ("Net rating (on court)", "impact", "rating", 1, "Offensive minus defensive rating while on court."),
    "e_off_rating": ("Estimated offensive rating", "impact", "rating", 1, "NBA.com estimated offensive rating."),
    "e_def_rating": ("Estimated defensive rating", "impact", "rating", 0, "NBA.com estimated defensive rating."),
    "e_net_rating": ("Estimated net rating", "impact", "rating", 1, "NBA.com estimated net rating."),
    "ast_to": ("Assist-to-turnover ratio", "playmaking", "ratio", 1, "Assists per turnover."),
    "ast_ratio": ("Assist ratio", "playmaking", "per_100_poss", 1, "Assists per 100 possessions used."),
    "oreb_pct": ("Offensive rebound %", "rebounding", "fraction", 1,
                 "Share of available offensive rebounds grabbed while on court."),
    "dreb_pct": ("Defensive rebound %", "rebounding", "fraction", 1,
                 "Share of available defensive rebounds grabbed while on court."),
    "reb_pct": ("Total rebound %", "rebounding", "fraction", 1, "Share of available rebounds grabbed while on court."),
    "tm_tov_pct": ("Turnover % (per 100 plays)", "ball_security", "percent", 0, "Turnovers per 100 plays (0-100)."),
    "e_tov_pct": ("Estimated turnover %", "ball_security", "percent", 0, "NBA.com estimated turnovers per 100 plays."),
    "e_usg_pct": ("Estimated usage %", "usage", "fraction", None, "NBA.com estimated usage rate."),
    "pace": ("Pace (on court)", "pace", "count", None, "Possessions per 48 minutes while the player is on the court."),
    "e_pace": ("Estimated pace", "pace", "count", None, "NBA.com estimated possessions per 48 minutes."),
    "pace_per40": ("Pace per 40", "pace", "count", None, "Possessions per 40 minutes while on court."),
    "poss": ("Possessions", "pace", "count", None, "Possessions played."),
    "pie": ("PIE", "impact", "fraction", 1,
            "Player Impact Estimate: share of game events (points, rebounds, assists...) the player produced."),
    # --- stats.nba.com misc ---
    "pts_off_tov": ("Points off turnovers", "scoring", "count", 1, "Points scored following opponent turnovers."),
    "pts_2nd_chance": ("Second-chance points", "scoring", "count", 1, "Points after an offensive rebound."),
    "pts_fb": ("Fast-break points", "scoring", "count", 1, "Points on fast breaks."),
    "pts_paint": ("Points in the paint", "scoring", "count", 1, "Points scored in the paint."),
    "opp_pts_off_tov": ("Opp. points off turnovers (on court)", "defense", "count", 0,
                        "Opponent points off turnovers while the player is on the court."),
    "opp_pts_2nd_chance": ("Opp. second-chance points (on court)", "defense", "count", 0,
                           "Opponent second-chance points while the player is on the court."),
    "opp_pts_fb": ("Opp. fast-break points (on court)", "defense", "count", 0,
                   "Opponent fast-break points while the player is on the court."),
    "opp_pts_paint": ("Opp. points in the paint (on court)", "defense", "count", 0,
                      "Opponent paint points while the player is on the court."),
    # --- stats.nba.com scoring (share of the player's own shots/points) ---
    "pct_fga_2pt": ("Share of FGA: 2-pt", "shot_profile", "fraction", None, "Share of the player's FGA that are twos."),
    "pct_fga_3pt": ("Share of FGA: 3-pt", "shot_profile", "fraction", None,
                    "Share of the player's FGA that are threes."),
    "pct_pts_2pt": ("Share of points: 2-pt", "shot_profile", "fraction", None, "Share of points from twos."),
    "pct_pts_2pt_mr": ("Share of points: mid-range", "shot_profile", "fraction", None,
                       "Share of points from mid-range twos."),
    "pct_pts_3pt": ("Share of points: 3-pt", "shot_profile", "fraction", None, "Share of points from threes."),
    "pct_pts_fb": ("Share of points: fast break", "shot_profile", "fraction", None, "Share of points on fast breaks."),
    "pct_pts_ft": ("Share of points: free throws", "shot_profile", "fraction", None,
                   "Share of points from free throws."),
    "pct_pts_off_tov": ("Share of points: off turnovers", "shot_profile", "fraction", None,
                        "Share of points following opponent turnovers."),
    "pct_pts_paint": ("Share of points: paint", "shot_profile", "fraction", None, "Share of points in the paint."),
    "pct_ast_2pm": ("Assisted share of 2-pt FGM", "shot_creation", "fraction", None, "Share of made twos assisted."),
    "pct_uast_2pm": ("Unassisted share of 2-pt FGM", "shot_creation", "fraction", None,
                     "Share of made twos self-created."),
    "pct_ast_3pm": ("Assisted share of 3-pt FGM", "shot_creation", "fraction", None, "Share of made threes assisted."),
    "pct_uast_3pm": ("Unassisted share of 3-pt FGM", "shot_creation", "fraction", None,
                     "Share of made threes self-created."),
    "pct_ast_fgm": ("Assisted share of FGM", "shot_creation", "fraction", None, "Share of made field goals assisted."),
    "pct_uast_fgm": ("Unassisted share of FGM", "shot_creation", "fraction", None,
                     "Share of made field goals self-created."),
}

# stats.nba.com "usage" table: the player's share of the team's total while on court.
USAGE_SHARES = {
    "pct_fgm": "made field goals", "pct_fga": "field goal attempts", "pct_fg3m": "made threes",
    "pct_fg3a": "three-point attempts", "pct_ftm": "made free throws", "pct_fta": "free throw attempts",
    "pct_oreb": "offensive rebounds", "pct_dreb": "defensive rebounds", "pct_reb": "rebounds",
    "pct_ast": "assists", "pct_tov": "turnovers", "pct_stl": "steals", "pct_blk": "blocks",
    "pct_blka": "shots blocked against", "pct_pf": "personal fouls", "pct_pfd": "fouls drawn", "pct_pts": "points",
}
USAGE_DIRECTION = {"pct_tov": None, "pct_pf": None, "pct_blka": None}

SHOT_ZONES = {
    "restricted_area": "restricted area", "in_the_paint_non_ra": "paint (non-restricted area)",
    "mid_range": "mid-range", "left_corner_3": "left corner 3", "right_corner_3": "right corner 3",
    "corner_3": "corner 3", "above_the_break_3": "above-the-break 3", "backcourt": "backcourt",
    "less_than_5_ft": "less than 5 ft", "5_9_ft": "5-9 ft", "10_14_ft": "10-14 ft", "15_19_ft": "15-19 ft",
    "20_24_ft": "20-24 ft", "25_29_ft": "25-29 ft", "30_34_ft": "30-34 ft", "35_39_ft": "35-39 ft", "40_ft": "40+ ft",
}
SHOT_ZONE_STAT = re.compile(r"^(?P<zone>.+)_(?P<kind>fgm|fga|fg_pct)$")

# --- stats.nba.com player tracking ------------------------------------------
TRACKING_SINGLE: dict[str, tuple[str, str, str, int | None, str]] = {
    "drives": ("Drives", "tracking", "count", None, "Dribbles toward the basket from 20+ ft ending inside 10 ft."),
    "touches": ("Touches", "tracking", "count", None, "Times the player gained possession of the ball."),
    "front_ct_touches": ("Frontcourt touches", "tracking", "count", None, "Touches in the frontcourt."),
    "elbow_touches": ("Elbow touches", "tracking", "count", None, "Touches at the elbows of the lane."),
    "post_touches": ("Post touches", "tracking", "count", None, "Touches with the back to the basket near the post."),
    "paint_touches": ("Paint touches", "tracking", "count", None, "Touches inside the paint."),
    "time_of_poss": ("Time of possession", "tracking", "minutes", None, "Minutes the player held the ball."),
    "avg_sec_per_touch": ("Seconds per touch", "tracking", "seconds", None, "Average seconds held per touch."),
    "avg_drib_per_touch": ("Dribbles per touch", "tracking", "ratio", None, "Average dribbles per touch."),
    "pts_per_touch": ("Points per touch", "scoring", "ratio", 1, "Points scored per touch."),
    "pts_per_elbow_touch": ("Points per elbow touch", "scoring", "ratio", 1, "Points scored per elbow touch."),
    "pts_per_post_touch": ("Points per post touch", "scoring", "ratio", 1, "Points scored per post touch."),
    "pts_per_paint_touch": ("Points per paint touch", "scoring", "ratio", 1, "Points scored per paint touch."),
    "passes_made": ("Passes made", "playmaking", "count", None, "Passes thrown."),
    "passes_received": ("Passes received", "playmaking", "count", None, "Passes caught."),
    "ft_ast": ("Free throw assists", "playmaking", "count", 1, "Passes that led to a shooting foul and made free throws."),
    "secondary_ast": ("Secondary assists", "playmaking", "count", 1,
                      "Passes to the player who then made the assist (hockey assists)."),
    "potential_ast": ("Potential assists", "playmaking", "count", 1,
                      "Passes to a shooter who then shot; an assist if the shot had gone in."),
    "ast_pts_created": ("Points created by assists", "playmaking", "count", 1, "Points scored on the player's assists."),
    "ast_adj": ("Adjusted assists", "playmaking", "count", 1, "Assists + secondary assists + free throw assists."),
    "ast_to_pass_pct": ("Assists per pass", "playmaking", "fraction", 1, "Share of passes that became assists."),
    "ast_to_pass_pct_adj": ("Adjusted assists per pass", "playmaking", "fraction", 1,
                            "Share of passes that became adjusted assists."),
    "dist_feet": ("Distance covered (ft)", "tracking", "feet", None, "Total distance run."),
    "dist_miles": ("Distance covered", "tracking", "miles", None, "Total distance run."),
    "dist_miles_off": ("Distance covered on offense", "tracking", "miles", None, "Distance run on offense."),
    "dist_miles_def": ("Distance covered on defense", "tracking", "miles", None, "Distance run on defense."),
    "avg_speed": ("Average speed", "tracking", "mph", None, "Average speed while on the court."),
    "avg_speed_off": ("Average speed on offense", "tracking", "mph", None, "Average speed on offense."),
    "avg_speed_def": ("Average speed on defense", "tracking", "mph", None, "Average speed on defense."),
    "eff_fg_pct": ("Effective FG%", "shooting", "fraction", 1, "(FGM + 0.5 x 3PM) / FGA."),
    "fta_rate": ("Free throw rate", "shot_profile", "fraction", 1, "Free throw attempts per field goal attempt."),
    "def_rim_fgm": ("Opponent FGM at rim defended", "defense", "count", 0,
                    "Opponent makes within 6 ft of the rim while the player defended the rim."),
    "def_rim_fga": ("Opponent FGA at rim defended", "defense", "count", None,
                    "Opponent attempts within 6 ft of the rim while the player defended the rim."),
    "def_rim_fg_pct": ("Opponent FG% at rim defended", "defense", "fraction", 0,
                       "Opponent FG% within 6 ft of the rim while the player defended the rim."),
}

# (label, plural noun, singular noun)
TRACKING_ACTIONS = {
    "catch_shoot": ("Catch-and-shoot", "catch-and-shoot jumpers (shot 10+ ft away, no dribble)", "catch-and-shoot shot"),
    "pull_up": ("Pull-up", "pull-up jumpers (shot 10+ ft away after dribbling)", "pull-up shot"),
    "drive": ("Drive", "drives", "drive"),
    "elbow_touch": ("Elbow touch", "elbow touches", "elbow touch"),
    "post_touch": ("Post touch", "post touches", "post touch"),
    "paint_touch": ("Paint touch", "paint touches", "paint touch"),
}
TRACKING_ACTION_STAT = re.compile(rf"^(?P<action>{'|'.join(TRACKING_ACTIONS)})_(?P<suffix>.+)$")
# suffix -> (label, category, unit, higher_is_better, definition with {what}/{one})
TRACKING_SUFFIXES: dict[str, tuple[str, str, str, int | None, str]] = {
    "fgm": ("FGM", "shooting", "count", 1, "Field goals made on {what}."),
    "fga": ("FGA", "shooting", "count", None, "Field goals attempted on {what}."),
    "fg_pct": ("FG%", "shooting", "fraction", 1, "FG% on {what}."),
    "fg3m": ("3PM", "shooting", "count", 1, "Threes made on {what}."),
    "fg3a": ("3PA", "shooting", "count", None, "Threes attempted on {what}."),
    "fg3_pct": ("3P%", "shooting", "fraction", 1, "3-pt FG% on {what}."),
    "efg_pct": ("eFG%", "shooting", "fraction", 1, "Effective FG% on {what}."),
    "ftm": ("FTM", "shooting", "count", 1, "Free throws made from {what}."),
    "fta": ("FTA", "shooting", "count", None, "Free throws attempted from {what}."),
    "ft_pct": ("FT%", "shooting", "fraction", 1, "FT% on free throws from {what}."),
    "pts": ("points", "scoring", "count", 1, "Points scored on {what}."),
    "pts_pct": ("points per {one}", "scoring", "ratio", 1,
                "Points per {one}. NBA.com names this PTS%, but it is points per {one}."),
    "passes": ("passes", "playmaking", "count", None, "Passes out of {what}."),
    "passes_pct": ("pass rate", "playmaking", "fraction", None, "Share of {what} ending in a pass."),
    "ast": ("assists", "playmaking", "count", 1, "Assists out of {what}."),
    "ast_pct": ("assist rate", "playmaking", "fraction", 1, "Share of {what} ending in an assist."),
    "tov": ("turnovers", "ball_security", "count", 0, "Turnovers on {what}."),
    "tov_pct": ("turnover rate", "ball_security", "fraction", 0, "Share of {what} ending in a turnover."),
    "pf": ("fouls drawn", "fouls", "count", 1, "Personal fouls drawn on {what}."),
    "pf_pct": ("foul-drawn rate", "fouls", "fraction", 1, "Share of {what} drawing a foul."),
    "fouls": ("fouls drawn", "fouls", "count", 1, "Personal fouls drawn on {what}."),
    "fouls_pct": ("foul-drawn rate", "fouls", "fraction", 1, "Share of {what} drawing a foul."),
}

REBOUND_KINDS = {"oreb": "offensive rebound", "dreb": "defensive rebound", "reb": "rebound"}
REBOUND_STAT = re.compile(r"^(?P<kind>oreb|dreb|reb)_(?P<suffix>contest|uncontest|contest_pct|chances|chance_pct|"
                          r"chance_defer|chance_pct_adj)$|^avg_(?P<dist_kind>oreb|dreb|reb)_dist$")
REBOUND_SUFFIXES: dict[str, tuple[str, str, int | None, str]] = {
    "contest": ("Contested {k}s", "count", 1, "{K}s grabbed with an opponent within 3.5 ft."),
    "uncontest": ("Uncontested {k}s", "count", None, "{K}s grabbed with no opponent within 3.5 ft."),
    "contest_pct": ("Contested share of {k}s", "fraction", None, "Share of the player's {k}s that were contested."),
    "chances": ("{K} chances", "count", None, "Times the player was within 3.5 ft of an available {k}."),
    "chance_pct": ("{K} chance conversion", "fraction", 1, "{K}s / {k} chances."),
    "chance_defer": ("Deferred {k} chances", "count", None, "{K} chances left to a teammate who secured it."),
    "chance_pct_adj": ("Adjusted {k} chance conversion", "fraction", 1, "{K}s / ({k} chances - deferred chances)."),
    "dist": ("Average {k} distance", "feet", None, "Average distance from the basket where {k}s were secured."),
}

HUSTLE: dict[str, tuple[str, str, str, int | None, str]] = {
    "contested_shots": ("Contested shots", "hustle", "count", 1, "Opponent shots the player contested."),
    "contested_shots_2pt": ("Contested 2-pt shots", "hustle", "count", 1, "Opponent twos the player contested."),
    "contested_shots_3pt": ("Contested 3-pt shots", "hustle", "count", 1, "Opponent threes the player contested."),
    "deflections": ("Deflections", "hustle", "count", 1, "Opponent passes or dribbles the player tipped."),
    "charges_drawn": ("Charges drawn", "hustle", "count", 1, "Offensive fouls drawn by taking a charge."),
    "screen_assists": ("Screen assists", "hustle", "count", 1,
                       "Screens that directly freed a teammate for a made field goal."),
    "screen_ast_pts": ("Points from screen assists", "hustle", "count", 1, "Points scored off the player's screens."),
    "off_loose_balls_recovered": ("Offensive loose balls recovered", "hustle", "count", 1,
                                  "Loose balls recovered on offense."),
    "def_loose_balls_recovered": ("Defensive loose balls recovered", "hustle", "count", 1,
                                  "Loose balls recovered on defense."),
    "loose_balls_recovered": ("Loose balls recovered", "hustle", "count", 1, "Loose balls recovered."),
    "pct_loose_balls_recovered_off": ("Share of loose balls: offense", "hustle", "fraction", None,
                                      "Share of the player's loose-ball recoveries made on offense."),
    "pct_loose_balls_recovered_def": ("Share of loose balls: defense", "hustle", "fraction", None,
                                      "Share of the player's loose-ball recoveries made on defense."),
    "off_boxouts": ("Offensive box-outs", "hustle", "count", 1, "Box-outs on offense."),
    "def_boxouts": ("Defensive box-outs", "hustle", "count", 1, "Box-outs on defense."),
    "box_outs": ("Box-outs", "hustle", "count", 1, "Times the player boxed out an opponent."),
    "box_out_player_team_rebs": ("Box-outs leading to team rebounds", "hustle", "count", 1,
                                 "Box-outs after which the player's team secured the rebound."),
    "box_out_player_rebs": ("Box-outs leading to own rebounds", "hustle", "count", 1,
                            "Box-outs after which the player secured the rebound."),
    "pct_box_outs_off": ("Share of box-outs: offense", "hustle", "fraction", None, "Share of box-outs on offense."),
    "pct_box_outs_def": ("Share of box-outs: defense", "hustle", "fraction", None, "Share of box-outs on defense."),
    "pct_box_outs_team_reb": ("Team rebound rate after box-outs", "hustle", "fraction", 1,
                              "Share of box-outs after which the team secured the rebound (NBA.com)."),
    "pct_box_outs_reb": ("Own rebound rate after box-outs", "hustle", "fraction", None,
                         "Share of box-outs after which the player secured the rebound (NBA.com)."),
}

# --- stats.nba.com closest-defender tables (opponent shooting when the player defends) ---
_DEFENSE_SCOPES = {"defense_overall": "all shots", "defense_3pt": "threes", "defense_rim": "shots within 6 ft"}
TABLE_SPECIFIC: dict[tuple[str, str], tuple[str, str, str, int | None, str]] = {
    **{
        (table, "freq"): (f"Share of defended FGA: {scope}", "defense", "fraction", None,
                          f"Share of all shots the player defended that were {scope}.")
        for table, scope in _DEFENSE_SCOPES.items()
    },
    ("defense_overall", "d_fgm"): ("Opponent FGM defended", "defense", "count", 0,
                                   "Opponent makes with the player as the closest defender."),
    ("defense_overall", "d_fga"): ("Opponent FGA defended", "defense", "count", None,
                                   "Opponent attempts with the player as the closest defender."),
    ("defense_overall", "d_fg_pct"): ("Opponent FG% defended", "defense", "fraction", 0,
                                      "Opponent FG% with the player as the closest defender."),
    ("defense_overall", "normal_fg_pct"): ("Opponents' normal FG%", "defense", "fraction", None,
                                           "The same shooters' usual FG% on these shots."),
    ("defense_overall", "pct_plusminus"): ("Opponent FG% vs normal", "defense", "fraction", 0,
                                           "Defended FG% minus the shooters' normal FG%; negative is good."),
    ("defense_3pt", "fg3m"): ("Opponent 3PM defended", "defense", "count", 0,
                              "Opponent threes made with the player as the closest defender."),
    ("defense_3pt", "fg3a"): ("Opponent 3PA defended", "defense", "count", None,
                              "Opponent threes attempted with the player as the closest defender."),
    ("defense_3pt", "fg3_pct"): ("Opponent 3P% defended", "defense", "fraction", 0,
                                 "Opponent 3P% with the player as the closest defender."),
    ("defense_3pt", "ns_fg3_pct"): ("Opponents' normal 3P%", "defense", "fraction", None,
                                    "The same shooters' usual 3P%."),
    ("defense_3pt", "plusminus"): ("Opponent 3P% vs normal", "defense", "fraction", 0,
                                   "Defended 3P% minus the shooters' normal 3P%; negative is good."),
    ("defense_rim", "fgm_lt_06"): ("Opponent FGM within 6 ft defended", "defense", "count", 0,
                                   "Opponent makes within 6 ft with the player as the closest defender."),
    ("defense_rim", "fga_lt_06"): ("Opponent FGA within 6 ft defended", "defense", "count", None,
                                   "Opponent attempts within 6 ft with the player as the closest defender."),
    ("defense_rim", "lt_06_pct"): ("Opponent FG% within 6 ft defended", "defense", "fraction", 0,
                                   "Opponent FG% within 6 ft with the player as the closest defender."),
    ("defense_rim", "ns_lt_06_pct"): ("Opponents' normal FG% within 6 ft", "defense", "fraction", None,
                                      "The same shooters' usual FG% within 6 ft."),
    ("defense_rim", "plusminus"): ("Opponent FG% within 6 ft vs normal", "defense", "fraction", 0,
                                   "Defended FG% within 6 ft minus the shooters' normal; negative is good."),
    # --- DARKO daily ratings (www.darko.app); x_ = DARKO's projection for the next game ---
    ("dpm", "dpm"): ("DARKO DPM", "impact", "points", 1,
                     "Daily Plus-Minus: projected points per 100 possessions above a league-average player, "
                     "from box score and on/off data, as of the rating date."),
    ("dpm", "o_dpm"): ("DARKO offensive DPM", "impact", "points", 1, "Offensive part of DPM."),
    ("dpm", "d_dpm"): ("DARKO defensive DPM", "impact", "points", 1, "Defensive part of DPM."),
    ("dpm", "box_dpm"): ("DARKO box DPM", "impact", "points", 1, "DPM estimated from box score stats only."),
    ("dpm", "on_off_dpm"): ("DARKO on/off DPM", "impact", "points", 1,
                            "DPM estimated from on/off (plus-minus) data."),
    ("dpm", "age"): ("Age", "bio", "years", None, "Player age on the rating date."),
    ("dpm", "career_game_num"): ("Career games", "availability", "count", None,
                                 "Games in the player's career through the rating date, playoffs included."),
    ("dpm", "x_minutes"): ("Projected minutes", "availability", "minutes", None, "DARKO projected minutes per game."),
    ("dpm", "x_pace"): ("Projected pace", "pace", "count", None, "DARKO projected possessions per 48 minutes."),
    ("dpm", "x_pts_100"): ("Projected points per 100", "scoring", "count", 1,
                           "DARKO projected points per 100 possessions."),
    ("dpm", "x_ast_100"): ("Projected assists per 100", "playmaking", "count", 1,
                           "DARKO projected assists per 100 possessions."),
    ("dpm", "x_fg_pct"): ("Projected FG%", "shooting", "fraction", 1, "DARKO projected field goal percentage."),
    ("dpm", "x_fg3_pct"): ("Projected 3P%", "shooting", "fraction", 1, "DARKO projected three-point percentage."),
    ("dpm", "x_ft_pct"): ("Projected FT%", "shooting", "fraction", 1, "DARKO projected free throw percentage."),
    ("dpm", "sal_market_fixed"): ("DARKO salary value", "value", "dollars", 1,
                                  "DARKO's fair-salary estimate for the player's projected impact."),
    ("dpm", "actual_salary"): ("Salary", "value", "dollars", None, "The player's actual salary for the season."),
    ("dpm", "surplus_value"): ("Salary surplus", "value", "dollars", 1, "DARKO salary value minus actual salary."),
}

# --- Synergy play types -------------------------------------------------------
PLAY_TYPES = {
    "isolation": "Isolation", "transition": "Transition", "pr_ball_handler": "P&R ball handler",
    "pr_rollman": "P&R roll man", "postup": "Post-up", "spotup": "Spot-up", "handoff": "Handoff", "cut": "Cut",
    "off_screen": "Off screen", "off_rebound": "Putback", "misc": "Miscellaneous",
}
PLAY_TYPE_STAT = re.compile(rf"^(?P<play_type>{'|'.join(PLAY_TYPES)})_(?P<metric>.+)$")
# metric -> (label, category, unit, higher_is_better offense, defense, definition)
PLAY_TYPE_METRICS: dict[str, tuple[str, str, str, int | None, int | None, str]] = {
    "percentile": ("percentile", "impact", "fraction", 1, 1,
                   "Synergy percentile of points per possession among players, 0-1; higher is better on both sides."),
    "gp": ("games", "availability", "count", None, None, "Games with at least one {pt} possession."),
    "poss_pct": ("frequency", "usage", "fraction", None, None, "Share of the player's {side} possessions that were {pt}."),
    "poss": ("possessions", "usage", "count", None, None, "{Pt} possessions {used}."),
    "ppp": ("points per possession", "impact", "ratio", 1, 0, "Points {scored} per {pt} possession."),
    "pts": ("points", "scoring", "count", 1, 0, "Points {scored} on {pt} possessions."),
    "fgm": ("FGM", "shooting", "count", 1, 0, "Field goals made {against}on {pt} possessions."),
    "fga": ("FGA", "shooting", "count", None, None, "Field goals attempted {against}on {pt} possessions."),
    "fgmx": ("missed FG", "shooting", "count", 0, 1, "Field goals missed {against}on {pt} possessions."),
    "fg_pct": ("FG%", "shooting", "fraction", 1, 0, "FG% {against}on {pt} possessions."),
    "efg_pct": ("eFG%", "shooting", "fraction", 1, 0, "Effective FG% {against}on {pt} possessions."),
    "ft_poss_pct": ("free throw rate", "fouls", "fraction", 1, 0, "Share of {pt} possessions ending in free throws."),
    "tov_poss_pct": ("turnover rate", "ball_security", "fraction", 0, 1, "Share of {pt} possessions ending in a turnover."),
    "sf_poss_pct": ("shooting foul rate", "fouls", "fraction", 1, 0,
                    "Share of {pt} possessions with a shooting foul."),
    "plusone_poss_pct": ("and-one rate", "scoring", "fraction", 1, 0, "Share of {pt} possessions with an and-one."),
    "score_poss_pct": ("scoring rate", "scoring", "fraction", 1, 0, "Share of {pt} possessions scoring at least a point."),
}
CLUTCH_NOTE = " In clutch time: last 5 minutes of the 4th quarter or overtime, score within 5."


def _describe_play_type(stat_table: str, name: str) -> tuple | None:
    match = PLAY_TYPE_STAT.match(name)
    if not match or match["metric"] not in PLAY_TYPE_METRICS:
        return None
    defense = stat_table == "play_type_defense"
    label, category, unit, hib_off, hib_def, definition = PLAY_TYPE_METRICS[match["metric"]]
    play_type = PLAY_TYPES[match["play_type"]]
    words = {"pt": play_type if play_type.startswith("P&R") else play_type.lower(), "Pt": play_type, "side": "defensive" if defense else "offensive",
             "used": "defended" if defense else "used", "scored": "allowed" if defense else "scored",
             "against": "by opponents " if defense else ""}
    return (f"{play_type}{' defense' if defense else ''} {label}", "defense" if defense else category, unit,
            hib_def if defense else hib_off, definition.format(**words))


def _describe_tracking_action(name: str) -> tuple | None:
    match = TRACKING_ACTION_STAT.match(name)
    if not match or match["suffix"] not in TRACKING_SUFFIXES:
        return None
    action, what, one = TRACKING_ACTIONS[match["action"]]
    label, category, unit, higher_is_better, definition = TRACKING_SUFFIXES[match["suffix"]]
    label = label.format(one=one)
    label = label[0].upper() + label[1:] if match["suffix"] == "pts_pct" else f"{action} {label}"
    return (label, category, unit, higher_is_better,
            definition.format(what=what, one=one))


def _describe_rebound(name: str) -> tuple | None:
    match = REBOUND_STAT.match(name)
    if not match:
        return None
    kind = REBOUND_KINDS[match["kind"] or match["dist_kind"]]
    label, unit, higher_is_better, definition = REBOUND_SUFFIXES[match["suffix"] or "dist"]
    words = {"k": kind, "K": kind.capitalize()}
    return label.format(**words), "rebounding", unit, higher_is_better, definition.format(**words)


ENTITY_WORDS = {"team": "team", "lineup": "lineup"}


def _for_entity(text: str, entity: str) -> str:
    """Definitions are written for players; reword them for team and lineup stats."""
    if entity not in ENTITY_WORDS:
        return text
    word = ENTITY_WORDS[entity]
    return (text.replace("the player's", f"the {word}'s").replace("The player's", f"The {word}'s")
            .replace("Player's", f"{word.capitalize()}'s").replace("the player", f"the {word}")
            .replace("The player", f"The {word}"))


def _describe_opponent(source_system: str, stat_table: str, name: str) -> tuple | None:
    """opp_<stat> from the team opponent and four factors tables: the same stat, allowed."""
    if not name.startswith("opp_"):
        return None
    inner = describe(source_system, stat_table, name.removeprefix("opp_"))
    if not inner["documented"]:
        return None
    label = inner["label"]
    label = f"Opponent {label if len(label) > 1 and not label[1].islower() else label[0].lower() + label[1:]}"
    direction = {1: 0, 0: 1}.get(inner["higher_is_better"])
    return label, "defense", inner["unit"], direction, f"Allowed to opponents: {inner['definition']}"


CLOSEST_DEFENDER = {"very_tight": "defender 0-2 ft", "tight": "defender 2-4 ft", "open": "defender 4-6 ft",
                    "wide_open": "defender 6+ ft"}
SHOT_CLOCK = {"clock_24_22": "24-22 s on shot clock", "clock_22_18": "22-18 s on shot clock",
              "clock_18_15": "18-15 s on shot clock", "clock_15_7": "15-7 s on shot clock",
              "clock_7_4": "7-4 s on shot clock", "clock_4_0": "4-0 s on shot clock", "clock_off": "shot clock off"}
SHOT_CONTEXT_STAT = re.compile(
    rf"^(?P<defender>{'|'.join(CLOSEST_DEFENDER)})_(?P<clock>{'|'.join(SHOT_CLOCK)})_(?P<stat>.+)$")
SHOT_FREQUENCY = {"fga_frequency": "FGA", "fg2a_frequency": "2-pt FGA", "fg3a_frequency": "3-pt FGA"}


def _describe_shot_context(source_system: str, name: str) -> tuple | None:
    """very_tight_clock_4_0_fg_pct: a shooting stat on shots with this defender distance and shot clock."""
    match = SHOT_CONTEXT_STAT.match(name)
    if not match:
        return None
    where = f"{CLOSEST_DEFENDER[match['defender']]}, {SHOT_CLOCK[match['clock']]}"
    stat = match["stat"]
    if stat in SHOT_FREQUENCY:
        return (f"Share of {SHOT_FREQUENCY[stat]}: {where}", "shot_context", "fraction", None,
                f"Share of the player's {SHOT_FREQUENCY[stat]} taken with the closest defender and shot clock "
                f"in this range ({where}).")
    inner = describe(source_system, "totals", stat)
    if not inner["documented"]:
        return None
    return (f"{inner['label']}: {where}", "shot_context", inner["unit"], inner["higher_is_better"],
            f"{inner['definition']} Only shots with {where}.")


def _describe_on_off(source_system: str, name: str) -> tuple | None:
    """on_fg3_pct / off_fg3_pct: the team's stat while the player is on (off) the court."""
    court, _, stat = name.partition("_")
    if court not in ("on", "off") or not stat:
        return None
    inner = describe(source_system, "totals", stat, entity="team")
    if not inner["documented"]:
        return None
    where = "on" if court == "on" else "off"
    return (f"Team {inner['label'][0].lower() + inner['label'][1:]} with player {where} court", "on_off",
            inner["unit"], inner["higher_is_better"],
            f"Team stat while the player is {where} the court: {inner['definition']}")


def describe(source_system: str, stat_table: str, stat_name: str, entity: str = "player") -> dict:
    """Catalog row for one stat; documented = 0 when no rule matches."""
    basis = BASIS_BY_TABLE.get(stat_table)
    name = stat_name
    for suffix, suffix_basis in BBREF_SUFFIX_BASIS.items():
        if name.endswith(suffix):
            name, basis = name[: -len(suffix)], suffix_basis
            break

    entry: tuple | None = None
    if stat_table == "usage" and name in USAGE_SHARES:
        noun = USAGE_SHARES[name]
        entry = (f"Share of team {noun}", "usage", "fraction", USAGE_DIRECTION.get(name, 1),
                 f"Player's share of the team's {noun} while on the court.")
        basis = None
    elif stat_table in ("shot_zones", "shot_distance") and (match := SHOT_ZONE_STAT.match(name)) \
            and match["zone"] in SHOT_ZONES:
        zone, kind = SHOT_ZONES[match["zone"]], match["kind"]
        entry = {
            "fgm": (f"FGM: {zone}", "shot_zone", "count", 1, f"Field goals made from {zone}."),
            "fga": (f"FGA: {zone}", "shot_zone", "count", None, f"Field goals attempted from {zone}."),
            "fg_pct": (f"FG%: {zone}", "shot_zone", "fraction", 1, f"FG% on shots from {zone}."),
        }[kind]
    elif stat_table.startswith("play_type_") and (play_type := _describe_play_type(stat_table, name)):
        entry, basis = play_type, None
    elif stat_table == "shot_context" and (context := _describe_shot_context(source_system, name)):
        entry = context
    elif stat_table == "on_off" and (on_off := _describe_on_off(source_system, name)):
        entry, basis = on_off, "total"
    elif (stat_table, name) in TABLE_SPECIFIC:
        entry = TABLE_SPECIFIC[(stat_table, name)]
    elif stat_table.startswith("tracking_") and (tracked := _describe_tracking_action(name) or _describe_rebound(name)):
        entry = tracked
    elif name in TRACKING_SINGLE or name in HUSTLE:
        entry = TRACKING_SINGLE.get(name) or HUSTLE[name]
    elif name in SPECIFIC:
        entry = SPECIFIC[name]
    elif (concept := ALIASES.get(name, name)) in CONCEPTS:
        entry = CONCEPTS[concept]
    elif opponent := _describe_opponent(source_system, stat_table, name):
        entry = opponent

    if entry is None:
        return {"entity": entity, "source_system": source_system, "stat_table": stat_table, "stat_name": stat_name,
                "label": stat_name, "category": "undocumented", "unit": None, "basis": basis,
                "higher_is_better": None, "definition": None, "documented": 0}

    label, category, unit, higher_is_better, definition = entry
    if unit not in COUNT_UNITS or ALIASES.get(name, name) in UNSCALED:
        basis = None  # rates and percentages read the same in every table
    elif basis and basis != "total":
        label = f"{label} {basis}"
    if stat_table.startswith("clutch"):
        keep_case = len(label) > 1 and not label[1].islower()  # FG%, PER, ...
        label = f"Clutch {label if keep_case else label[0].lower() + label[1:]}"
        definition += CLUTCH_NOTE
    return {"entity": entity, "source_system": source_system, "stat_table": stat_table, "stat_name": stat_name,
            "label": label, "category": category, "unit": unit, "basis": basis,
            "higher_is_better": higher_is_better, "definition": _for_entity(definition, entity), "documented": 1}


def refresh_stat_catalog(conn: sqlite3.Connection) -> dict[str, int]:
    """Rebuild dim_stat from the stats present in the player, team and lineup stat tables."""
    rows = []
    for table, entity, _ in STAT_TABLES:
        triples = conn.execute(
            f"SELECT DISTINCT source_system, stat_table, stat_name FROM {table} ORDER BY 1, 2, 3"
        ).fetchall()
        rows += [describe(*triple, entity=entity) for triple in triples]
    columns = list(rows[0]) if rows else []
    with conn:
        conn.execute("DELETE FROM dim_stat")
        if rows:
            conn.executemany(
                f"INSERT INTO dim_stat ({', '.join(columns)}) VALUES ({', '.join(':' + c for c in columns)})", rows
            )
    return {"stats": len(rows), "undocumented": sum(1 for r in rows if not r["documented"])}
