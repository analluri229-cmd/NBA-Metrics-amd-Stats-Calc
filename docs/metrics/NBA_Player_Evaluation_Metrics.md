# Basketball Player Evaluation Metrics — Reference

Compiled from two sources:

- **Part 1**: NBAstuffer's *Analytics 101 → Player Evaluation Metrics* pages (https://www.nbastuffer.com/analytics-101/player-evaluation-metrics/), one section per metric (65 total). Where Basketball-Reference also defines a metric, its definition and formula appear in a **Basketball-Reference** note inside that section.
- **Part 2**: the remaining terms from the Basketball-Reference glossary (https://www.basketball-reference.com/about/glossary.html) and its linked articles (Calculating PER, Win Shares, Individual Offensive & Defensive Ratings, Box Plus/Minus 2.0, Four Factors).

Each metric has four parts:

- **Definition**: what the metric measures.
- **Formula**: how it is calculated.
- **Glossary**: the terms and abbreviations used in that formula or description.
- **Usage**: how and when to use it, plus its known limitations.

> **Formula provenance.** Formulas are taken from the NBAstuffer page unless marked otherwise:
> - **[Basketball-Reference]**: NBAstuffer gives no formula (or only a partial one); the formula is taken directly from Basketball-Reference's glossary or articles.
> - **[Supplemented]**: neither source gives a formula; the standard published version from another source (RealGM, Dean Oliver, etc.) or one derived from the definition.
> - **[Model-based]**: a proprietary model with no public closed-form formula; the method is described instead.
>
> Obvious typos on the source pages have been fixed and noted.

---

## Common Notation

These abbreviations are used throughout. Metric-specific terms are defined in each section's glossary.

| Abbrev. | Meaning |
|---|---|
| PTS | Points |
| FGM / FGA | Field goals made / attempted |
| 3PM (3PTM) / 3PA | Three-point field goals made / attempted |
| FTM / FTA | Free throws made / attempted |
| ORB / DRB / TRB (REB) | Offensive / defensive / total rebounds |
| AST | Assists |
| STL | Steals |
| BLK | Blocked shots |
| TOV (TO) | Turnovers |
| PF | Personal fouls |
| MP | Minutes played |
| Tm / Opp / Lg | Team / opponent / league prefix (e.g., `Tm FGA` = team field goal attempts) |
| Possession | One continuous stretch of one team's control of the ball, ending in a made shot (or last FT), defensive rebound, or turnover |
| Per 100 possessions | Rate normalized to 100 possessions; removes the effect of pace ("tempo-free") |
| Pace | Possessions per 48 minutes |
| 0.44 × FTA | Standard estimate of how many possessions free-throw trips use (and-ones, technicals, and 3-shot fouls make the ratio below 0.5) |

---

## Table of Contents

1. [Adjusted Player Efficiency Rating (APER)](#1-adjusted-player-efficiency-rating-aper)
2. [Adjusted Plus-Minus (APM)](#2-adjusted-plus-minus-apm)
3. [Approximate Value (AV)](#3-approximate-value-av)
4. [Assist Percentage (AST%)](#4-assist-percentage-ast)
5. [Box Plus-Minus (BPM)](#5-box-plus-minus-bpm)
6. [CARMELO](#6-carmelo)
7. [Daily Updated Ranking of Individual Performance (DRIP)](#7-daily-updated-ranking-of-individual-performance-drip)
8. [DARKO (Daily Plus-Minus, DPM)](#8-darko-daily-plus-minus-dpm)
9. [Defensive Plus-Minus (DPM)](#9-defensive-plus-minus-dpm)
10. [Defensive Rating (DRtg)](#10-defensive-rating-drtg)
11. [Defensive Stop](#11-defensive-stop)
12. [Diamond Rating](#12-diamond-rating)
13. [Effective Field Goal Percentage (eFG%)](#13-effective-field-goal-percentage-efg)
14. [Estimated Plus-Minus (EPM)](#14-estimated-plus-minus-epm)
15. [Fantasy Points — DraftKings (DK FPTS)](#15-fantasy-points--draftkings-dk-fpts)
16. [Fantasy Points — FanDuel (FD FPTS)](#16-fantasy-points--fanduel-fd-fpts)
17. [Floor Impact Counter (FIC)](#17-floor-impact-counter-fic)
18. [Game Score (GmSc)](#18-game-score-gmsc)
19. [Gravity](#19-gravity)
20. [Individual Floor Percentage](#20-individual-floor-percentage)
21. [Individual Player Value (IPV)](#21-individual-player-value-ipv)
22. [LEBRON](#22-lebron)
23. [NBA Efficiency (EFF)](#23-nba-efficiency-eff)
24. [Plus-Minus (+/-) — Complete Guide](#24-plus-minus---complete-guide)
25. [Net Plus-Minus (Roland Rating)](#25-net-plus-minus-roland-rating)
26. [Net Points](#26-net-points)
27. [Non-Scoring Player Possessions](#27-non-scoring-player-possessions)
28. [Offensive Conversion Rate](#28-offensive-conversion-rate)
29. [Offensive Rating (ORtg)](#29-offensive-rating-ortg)
30. [Per-Minute Ratings](#30-per-minute-ratings)
31. [Personal Foul Efficiency](#31-personal-foul-efficiency)
32. [Player Efficiency Rating (PER)](#32-player-efficiency-rating-per)
33. [Player Impact Estimate (PIE)](#33-player-impact-estimate-pie)
34. [Player Tracking Plus-Minus (PT-PM)](#34-player-tracking-plus-minus-pt-pm)
35. [Points Created](#35-points-created)
36. [Points Per Possession (PPP)](#36-points-per-possession-ppp)
37. [Points Per Shot Attempt (PTS/FGA)](#37-points-per-shot-attempt-ptsfga)
38. [Points Produced](#38-points-produced)
39. [Position Adjusted Win Score (PAWS)](#39-position-adjusted-win-score-paws)
40. [Potential Assists (PA)](#40-potential-assists-pa)
41. [Quantified Shooter Impact (qSI)](#41-quantified-shooter-impact-qsi)
42. [Quantified Shot Quality (qSQ)](#42-quantified-shot-quality-qsq)
43. [RAPTOR](#43-raptor)
44. [Real Plus-Minus (RPM)](#44-real-plus-minus-rpm)
45. [Rebound Percentage (TRB%)](#45-rebound-percentage-trb)
46. [Regularized Adjusted Plus-Minus (RAPM / xRAPM)](#46-regularized-adjusted-plus-minus-rapm--xrapm)
47. [Scoring Player Possessions](#47-scoring-player-possessions)
48. [Seasons Left](#48-seasons-left)
49. [Simple Projection System (SPS)](#49-simple-projection-system-sps)
50. [Simple Rating System (SRS)](#50-simple-rating-system-srs)
51. [Statistical Player Value (SPV)](#51-statistical-player-value-spv)
52. [Statistical Plus-Minus (SPM)](#52-statistical-plus-minus-spm)
53. [Steal Percentage (STL%)](#53-steal-percentage-stl)
54. [Tendex Rating](#54-tendex-rating)
55. [Total Player Possessions](#55-total-player-possessions)
56. [Touches](#56-touches)
57. [Trade Value](#57-trade-value)
58. [True Shooting Percentage (TS%)](#58-true-shooting-percentage-ts)
59. [Turnover Ratio (TOV%)](#59-turnover-ratio-tov)
60. [Usage Rate (USG%)](#60-usage-rate-usg)
61. [Versatility Index](#61-versatility-index)
62. [Win Probability Added (WPA)](#62-win-probability-added-wpa)
63. [Win Score](#63-win-score)
64. [Win Shares (WS, WS/48)](#64-win-shares-ws-ws48)
65. [Wins Above Replacement Player (WARP)](#65-wins-above-replacement-player-warp)

**Part 2: Basketball-Reference Glossary (additional terms)**

- [B1. Basic box-score stats & shooting percentages](#b1-basic-box-score-stats--shooting-percentages)
- [B2. Block Percentage (BLK%)](#b2-block-percentage-blk)
- [B3. Possessions (Poss)](#b3-possessions-poss)
- [B4. Pace Factor](#b4-pace-factor)
- [B5. True Shooting Attempts (TSA)](#b5-true-shooting-attempts-tsa)
- [B6. Value Over Replacement Player (VORP)](#b6-value-over-replacement-player-vorp)
- [B7. Four Factors](#b7-four-factors)
- [B8. Pythagorean Wins / Losses](#b8-pythagorean-wins--losses)
- [B9. Team Simple Rating System (SRS) & Strength of Schedule (SOS)](#b9-team-simple-rating-system-srs--strength-of-schedule-sos)
- [B10. Margin of Victory (MOV)](#b10-margin-of-victory-mov)
- [B11. Won-Lost Percentage (W-L%) & Games Behind (GB)](#b11-won-lost-percentage-w-l--games-behind-gb)
- [B12. Award Share](#b12-award-share)
- [B13. Win Probability](#b13-win-probability)
- [B14. Other glossary terms (Age, Year, G, GS, awards, prefixes)](#b14-other-glossary-terms-age-year-g-gs-awards-prefixes)

---

## 1. Adjusted Player Efficiency Rating (APER)

**Definition**
A variant of John Hollinger's PER that also credits whether field goals were assisted or unassisted and gives credit for charges taken.

**Formula** — **[Model-based]**
NBAstuffer publishes no formula. Conceptually:
```
APER = PER framework + adjustments for (unassisted FGM vs. assisted FGM) + (charges drawn)
```

**Glossary**
- **PER**: Player Efficiency Rating (see #32).
- **Unassisted / assisted FG**: a made field goal that did / did not come directly from a teammate's pass.
- **Charge taken**: an offensive foul drawn by a defender who established legal guarding position.

**Usage**
- Refines PER for shot creation (unassisted makes are harder) and for a defensive action PER ignores (charges).
- NBAstuffer notes APER "is also as flawed as PER": it is still box-score based and offense-heavy.

---

## 2. Adjusted Plus-Minus (APM)

**Definition**
Basic plus-minus adjusted for the quality of every teammate and opponent on the floor. It estimates a player's impact on his team's scoring margin per 100 possessions relative to a league-average player (APM = 0).

**Formula** — **[Model-based]** (regression)
For each stint (a stretch with the same 10 players on court):
```
MarginPer100_stint = β0 + Σ β_i · x_i,stint + ε

x_i = +1 if player i is on court for the home/reference team
      −1 if player i is on court for the opponent
       0 if player i is off court
```
The stints are weighted by possessions and solved by least squares (minimizing the difference between expected and actual margins). Each player's APM = β_i.

**Glossary**
- **Stint / segment**: a period with no substitutions. APM tracks (1) the other nine players on the floor, (2) the segment length, and (3) the score at the start and end.
- **β0**: intercept (home-court advantage).
- **Multicollinearity**: when two players nearly always share the court, the regression cannot separate their individual effects.
- **League-average player**: APM = 0. A typical game is assumed to have 100 offensive and 100 defensive possessions.

**Usage**
- Interpretation: a +6.5 APM player with 4 average teammates makes his team about 6.5 points per 100 possessions better than 5 average players would. *Example:* Giannis Antetokounmpo, +10.3 APM in 2019-20.
- **Pros:** one of the closest things to an unbiased measure of total impact, including defense and off-ball work.
- **Cons:** high variance; single-season results are noisy (only 7% of 2008-09 APM variance was explained by 2007-08 APM); multicollinearity; sensitive to role, scheme, teammates, and coaching changes.
- History: Wayne Winston & Jeff Sagarin (WINVAL, 2002) → Dan Rosenbaum → David Lewin → Steve Ilardi (first in-season APM) → Aaron Barzilai's BasketballValue (2007-12).

---

## 3. Approximate Value (AV)

**Definition**
Bill James–style rough estimate of a player's value. It is not meant for fine distinctions; it separates very good, average, and poor seasons.

**Formula**
```
Credits = PTS + REB + AST + STL + BLK − FG Missed − FT Missed − TOV

AV = Credits^(3/4) / 21
```
Before 1973-74, STL, BLK, and TOV were not official stats, so they are left out of Credits for those seasons (they roughly cancel out).

**Glossary**
- **Credits**: a simple linear box-score total of positive minus negative actions.
- **FG Missed**: FGA − FGM. **FT Missed**: FTA − FTM.
- **^(3/4)**: the credit total raised to the 0.75 power, which compresses high totals.

**Usage**
- Quick, era-portable season value for historical comparisons.
- Used as an input to **Trade Value** (#57).
- Too coarse for comparing players of similar quality.

---

## 4. Assist Percentage (AST%)

**Definition**
Also called assist ratio: the estimated percentage of teammate field goals a player assisted while on the court. Tempo-free.

**Formula**
```
AST% = 100 × AST / [ ( (MP / (Tm MP / 5)) × Tm FGM ) − FGM ]
```

> **Basketball-Reference:** identical formula, `100 * AST / (((MP / (Tm MP / 5)) * Tm FG) - FG)`. "An estimate of the percentage of teammate field goals a player assisted while he was on the floor." Available since 1964-65.

**Glossary**
- **MP / (Tm MP / 5)**: the fraction of team minutes the player was on the floor.
- **Tm FGM × that fraction − FGM**: teammate field goals made while the player was on court (his own makes are excluded because he can't assist himself).

**Usage**
- Evaluates passing/playmaking independent of pace and minutes.
- Better than raw assists per game: players on fast-paced teams get more assist opportunities per minute.
- Pair with TOV% (#59) and Potential Assists (#40).

---

## 5. Box Plus-Minus (BPM)

**Definition**
A box-score estimate of a player's contribution in points per 100 possessions relative to a league-average player. The weights come from regressing box-score stats on play-by-play plus-minus data. Created by Daniel Myers.

**Formula** — **[Basketball-Reference]** (BPM 2.0; NBAstuffer gives none)

All box-score inputs are **per 100 possessions**. Coefficients vary linearly with the player's estimated **position** (1 = PG … 5 = C) or **offensive role** (1 = Creator … 5 = Receiver):
```
Raw BPM = 0.860 × PTS (adjusted for team shooting context)
        + 0.389 × 3PM
        + c_AST × AST        c_AST: 0.580 (PG) → 1.034 (C)
        − 0.964 × TOV
        + c_ORB × ORB        c_ORB: 0.613 (PG) → 0.181 (C)
        + c_DRB × DRB        c_DRB: 0.116 (PG) → 0.181 (C)
        + c_STL × STL        c_STL: 1.369 (PG) → 1.008 (C)
        + c_BLK × BLK        c_BLK: 1.327 (PG) → 0.703 (C)
        − 0.367 × PF
        + c_FGA × FGA        c_FGA: −0.560 (Creator) → −0.780 (Receiver)
        + c_FTA × FTA        c_FTA: −0.246 (Creator) → −0.343 (Receiver)
        + Position constant  (−0.818 at PG, rising linearly to 0 at SF; 0 for SF–C)
        + Role constant      (−2.774 Creator, 0 Neutral, +2.774 Receiver)

BPM = Raw BPM + Team Adjustment
```
**Team Adjustment:** a constant added to every player on the team so that the players' raw BPMs, weighted by % of minutes, sum to the team's adjusted efficiency (net rating per 100 possessions, corrected by −0.35/2 × average lead, because teams play worse when ahead). It is typically around −8 because it also serves as the regression intercept.

**OBPM** uses the same variables with different coefficients; **DBPM = BPM − OBPM**.

*Worked example (B-Ref):* LeBron James 2017. Position 2.3, role 1.0 → Raw BPM 18.7 − 3.1 (constants) = 15.6; team adjustment −8.0 → **BPM +7.6**.

**Glossary**
- **Per 100 possessions**: pace-neutral scale. BPM is purely a rate stat and ignores playing time (VORP adds it).
- **0.0**: league average. **−2.0**: replacement level.
- **Position / Offensive Role**: estimated from the box score by regression (1–5 scales).
- **OBPM / DBPM**: offensive / defensive components.
- **VORP**: Value Over Replacement Player. See B6.

**Usage**

Basketball-Reference scale (this replaces NBAstuffer's "+5 ≈ All-NBA"):

| BPM | Meaning |
|---|---|
| +10.0 | All-time season (peak Jordan / LeBron) |
| +8.0 | MVP season |
| +6.0 | All-NBA season |
| +4.0 | All-Star consideration |
| +2.0 | Good starter |
| 0.0 | Decent starter / solid 6th man |
| −2.0 | Bench player (replacement level) |
| < −2.0 | End of bench |

- Available since 1973-74. From 1985 on, B-Ref's values are sums of game-level BPMs, which handles strength of schedule better.
- Position and role matter: a block by a guard is worth more than a block by a center, and scoring by a low-usage player must be very efficient to count for much.
- Box-score-based: offense is captured well, but defensive positioning and communication are not.

---

## 6. CARMELO

**Definition**
*Career-Arc Regression Model Estimator with Local Optimization*: FiveThirtyEight's player **projection** system. It compared a player to historically similar players to forecast future performance in terms of WAR. Now retired and replaced by RAPTOR (#43).

**Formula** — **[Model-based]**
```
1. Similarity score (0–100) between the target player and every historical player,
   based on statistical profile, age, height, etc.
2. Projection = weighted average of the career arcs of the most similar comparables.
3. Value expressed as plus-minus (blend of Real Plus-Minus and Box Plus-Minus)
   and converted to Wins Above Replacement.
```

**Glossary**
- **Similarity score**: index from 0 to 100 of how comparable two players are.
- **RPM / BPM**: see #44 and #5; blended as the plus-minus basis.
- **WARP**: Wins Above Replacement Player.

**Usage**
- Forecasting a player's near-future and career trajectory (contracts, trades, draft comparisons).
- Historical interest only; no longer maintained.

---

## 7. Daily Updated Ranking of Individual Performance (DRIP)

**Definition**
A plus-minus–derived metric (by Nathan Walker, published on the Stats Perform blog) that projects a player's contribution to +/- per 100 possessions on offense and defense.

**Formula** — **[Model-based]**
```
Inputs: box score + play-by-play + lineup data → predictive model
Outputs: DRIP_Offense, DRIP_Defense
Total DRIP = DRIP_Offense + DRIP_Defense   (points per 100 possessions)
```

**Glossary**
- **Adjusted +/-**: plus-minus controlled for teammates and opponents (see APM).
- **PIPM**: Player Impact Plus-Minus (Jacob Goldstein), a similar methodology.

**Usage**
- A daily-updated estimate of a player's *current* per-stat performance level rather than a season or career average.
- Methodologically similar to PIPM and DARKO.

---

## 8. DARKO (Daily Plus-Minus, DPM)

**Definition**
*Daily Adjusted and Regressed Kalman Optimized*: Kostya Medvedovsky's composite **predictive** metric that combines box-score and plus-minus data and weights recent performance more heavily. Published at darko.app (web presence by Andrew Patton).

**Formula** — **[Model-based]**
```
1. Project each box-score component with exponential decay (recent games weigh more)
   and Kalman filtering (a time-series state estimate that also accounts for sample size).
2. Blend the box-score projection with the plus-minus projection in proportion to the
   player's total possessions.
3. DPM = projected points per 100 possessions vs. league average (Bayesian output).
```

**Glossary**
- **Exponential decay**: older games get geometrically less weight.
- **Kalman filter**: a statistical method that updates an estimate of a "true" talent level as each new observation arrives, weighted by uncertainty.
- **RMSE**: root mean squared error, the accuracy benchmark for predictive metrics.

**Usage**
- The best-performing predictive all-in-one metric by RMSE (per Medvedovsky's 2021 comparison; EPM second, LEBRON third).
- Forward-looking only. It is not meaningful for "who had the better career" (GOAT) debates.

---

## 9. Defensive Plus-Minus (DPM)

**Definition**
The difference, per 100 possessions, between points allowed with the player on the court and points allowed with him off the court.

**Formula**
```
Defensive +/- = (Opp PTS per 100 poss, player ON court) − (Opp PTS per 100 poss, player OFF court)
```
*Example:* 110 allowed on, 105 allowed off → +5.

**Glossary**
- **On / Off**: team results while the player is on the floor vs. on the bench.
- **Per 100 possessions**: pace-neutral.

**Usage**
- **Lower (more negative) is better**: it means the team allows fewer points with him on the court.
- Reliability depends on minutes played and on who shares the floor with him (bench units vs. starters). It is often a good indicator of overall defensive value when the sample is large.
- Not to be confused with **DARKO DPM** (#8).

---

## 10. Defensive Rating (DRtg)

**Definition**
Dean Oliver's estimate of points allowed per 100 possessions by an individual defender. It is built on the idea that defenders create **stops** (see #11).

**Formula** — **[Basketball-Reference]** ("Calculating Individual Offensive and Defensive Ratings"; NBAstuffer gives none)
```
DRtg = Team_DRtg + 0.2 × ( 100 × D_Pts_per_ScPoss × (1 − Stop%) − Team_DRtg )

Stop%            = (Stops × Opp_MP) / (Team_Possessions × MP)
Team_DRtg        = 100 × Opp_PTS / Team_Possessions
D_Pts_per_ScPoss = Opp_PTS / ( Opp_FGM + (1 − (1 − Opp_FTM/Opp_FTA)^2) × Opp_FTA × 0.4 )

Stops = Stops1 + Stops2
Stops1 = STL + BLK × FMwt × (1 − 1.07 × DOR%) + DRB × (1 − FMwt)
Stops2 = (((Opp_FGA − Opp_FGM − Team_BLK) / Team_MP) × FMwt × (1 − 1.07 × DOR%)
          + ((Opp_TOV − Team_STL) / Team_MP)) × MP
          + (PF / Team_PF) × 0.4 × Opp_FTA × (1 − Opp_FTM/Opp_FTA)^2

DOR%  = Opp_ORB / (Opp_ORB + Team_DRB)
DFG%  = Opp_FGM / Opp_FGA
FMwt  = (DFG% × (1 − DOR%)) / (DFG% × (1 − DOR%) + (1 − DFG%) × DOR%)
```

**Glossary**
- **Stop**: a defensive possession that ends without the opponent scoring.
- **Stop%**: share of opponent possessions (while on court) that ended in a stop credited to the player.
- **FMwt**: forced-miss weight, which balances credit between forcing a miss and securing the rebound.
- **DOR%**: opponent offensive rebound %.
- **0.2**: the individual gets ~20% (1/5) of the credit; the rest reflects team defense.

**Usage**
- Lower is better. Pair with Offensive Rating (#29) to get a net rating.
- Heavily influenced by team defense and box-score-visible events (steals, blocks, defensive rebounds); it misses help defense and contesting. Plus-minus–based metrics complement it.

> **Basketball-Reference:** "For players and teams it is points allowed per 100 possessions." Available since 1973-74. Its caveats: DRtg assumes all teammates are equally good at forcing non-steal turnovers and non-block misses, and that all teammates face the same possessions per minute. As a result, **big men tend to have the best DRtg**, and excellent perimeter defenders who don't get many steals (e.g., Joe Dumars, Doug Christie) are underrated and look only as good as their team's defense.

---

## 11. Defensive Stop

**Definition**
Occurs when a player or team defense regains the ball without allowing the opponent a scoring possession.

**Formula**
A count of events, not a ratio. A stop happens via:
```
1. Forcing a missed shot that is rebounded by the defense
2. Securing a defensive rebound
3. Forcing a turnover
4. Fouling a player who misses both free throws, with the 2nd rebounded by the defense
```
(For the individual Stops estimate, see Stops1 + Stops2 under #10.)

**Glossary**
- **Scoring possession**: a possession in which the offense scores at least one point.

**Usage**
- The building block of Defensive Rating (#10).
- Useful for teaching and film tagging: counting stops per game or per possession for a defender or lineup.

---

## 12. Diamond Rating

**Definition**
Kevin Broom's metric for finding under-used, efficient players ("diamonds in the rough"). It rewards players who produce well in limited minutes.

**Formula**
```
Diamond Rating = (PMR × 40) − (PMR × MPG) + [ (PMR − League PMR) × 40 ]
```
1. `PMR×40 − PMR×MPG`: how much per-game stats undervalue the player's per-40 production.
2. `(PMR − Lg PMR)×40`: confirms he is actually above league average in the minutes he gets.

**Glossary**
- **PMR (Per-Minute Rating)**: any per-minute production metric (e.g., PER-style rating ÷ minutes).
- **MPG**: minutes per game.
- **League PMR**: league-average per-minute rating.

**Usage**
- Scouting for breakout candidates and free-agent bargains.
- The fewer minutes and the better the production in them, the higher the rating.
- Recommended filters: exclude players over 27, with more than 5 years' experience, playing over 30 MPG, or with under 250 total minutes.

---

## 13. Effective Field Goal Percentage (eFG%)

**Definition**
Field goal percentage adjusted for the extra value of a three-pointer.

**Formula**
```
eFG% = (FGM + 0.5 × 3PM) / FGA
```

**Glossary**
- **0.5 × 3PM**: a made three is worth 1.5 made twos, so each 3PM gets a 50% bonus.
- **FGM / FGA** include both 2-pt and 3-pt attempts.

**Usage**
- Compares shooters with different shot diets. Two players with the same FG% are not equally efficient if one shoots more threes; eFG% shows the difference.
- *B-Ref example:* Player A goes 4-for-10 with 2 threes; Player B goes 5-for-10 with 0 threes. Both have 10 points from field goals, so both have **eFG% = 50%** (even though FG% is 40% vs. 50%).
- One of Dean Oliver's Four Factors (at team level).
- Ignores free throws; use TS% (#58) for total scoring efficiency.

---

## 14. Estimated Plus-Minus (EPM)

**Definition**
Taylor Snarr's adjusted plus-minus–type metric (Dunks & Threes). It estimates a player's impact in points per 100 possessions relative to average.

**Formula** — **[Model-based]**
```
EPM = box-score & player-tracking prior + regularized on/off (RAPM-style) adjustment
      → points per 100 possessions vs. league average
      (split into O-EPM and D-EPM)
```

**Glossary**
- **Prior**: a starting estimate from box-score and tracking stats, which the plus-minus data then updates.
- **Prediction error**: out-of-sample error in predicting future outcomes (lower = more accurate).

**Usage**
- Among the most accurate public all-in-one metrics. Snarr's 2020 comparison of prediction error: **EPM 2.48**, RPM 2.60, RAPTOR 2.63, BPM 2.71, PIPM 2.78, RAPM 2.80, WS/48 2.85, PER 3.20.
- Good for ranking overall player impact and for season-to-season forecasting.

---

## 15. Fantasy Points — DraftKings (DK FPTS)

**Definition**
DraftKings' NBA Classic-contest scoring system for daily fantasy.

**Formula**
```
DK FPTS =  1.0  × PTS
         + 0.5  × 3PM
         + 1.25 × REB
         + 1.5  × AST
         + 2.0  × STL
         + 2.0  × BLK
         − 0.5  × TOV
         + 1.5  (if Double-Double)
         + 3.0  (if Triple-Double)
```

**Glossary**
- **Double-Double / Triple-Double**: 10+ in two / three of PTS, REB, AST, STL, BLK.
- **Salary cap**: $50K for 8 players.
- **Positions**: PG, SG, SF, PF, C, G (PG/SG), F (SF/PF), UTIL (any).
- **Late Swap**: you may swap any player whose game hasn't started, even after the slate begins.
- Lineups need players from at least 2 teams and at least 2 games.

**Usage**
- DFS lineup construction and player valuation (FPTS per $1K salary).
- Rewards threes, assists, and multi-category bonuses more than FanDuel does.

---

## 16. Fantasy Points — FanDuel (FD FPTS)

**Definition**
FanDuel's NBA Classic-contest scoring system for daily fantasy.

**Formula**
```
FD FPTS =  1.0 × PTS
         + 1.2 × REB
         + 1.5 × AST
         + 3.0 × BLK
         + 3.0 × STL
         − 1.0 × TOV
```

**Glossary**
- **Salary cap**: $60K for 9 players.
- **Roster**: 2 PG, 2 SG, 2 SF, 2 PF, 1 C; maximum 4 players from one team.
- **Late Swap**: not allowed. Lineups lock when the first game of the slate starts.

**Usage**
- DFS lineup construction.
- Compared with DraftKings, FanDuel weights **steals and blocks more heavily** (3 vs. 2) and **penalizes turnovers more** (−1 vs. −0.5), with no DD/TD bonuses. Defensive specialists gain value.

---

## 17. Floor Impact Counter (FIC)

**Definition**
RealGM's linear box-score metric, designed to fix flaws in PER and PIE. It gives more weight to assists, shot creation, and offensive rebounding.

**Formula** — **[Supplemented]** (RealGM; NBAstuffer gives none)
```
FIC = PTS + ORB + 0.75×DRB + AST + STL + BLK
      − 0.75×FGA − 0.375×FTA − TOV − 0.5×PF
```

**Glossary**
- **ORB weighted 1.0 vs. DRB 0.75**: offensive boards are scarcer and extend possessions.
- **−0.75×FGA / −0.375×FTA**: shot-attempt cost terms that penalize inefficiency.

**Usage**
- Quick single-game or season productivity score.
- **Limitation:** box-score only. It favors triple-double "stat stuffers" who may not drive winning, and it never gained trust among NBA analysts.

---

## 18. Game Score (GmSc)

**Definition**
John Hollinger's simple, linear alternative to PER that reduces a player's single-game box score to one number. ~10 is an average game; 40+ is all-time great.

**Formula**
```
GmSc = PTS + 0.4×FGM − 0.7×FGA − 0.4×(FTA − FTM)
       + 0.7×ORB + 0.3×DRB + STL + 0.7×AST + 0.7×BLK
       − 0.4×PF − TOV
```

**Glossary**
- **FTA − FTM**: free throws missed.
- **Weights**: Hollinger's assigned value of each action. Made shots, rebounds, steals, assists, and blocks add; misses, fouls, and turnovers subtract.
- **No pace adjustment** (unlike PER).

> **Basketball-Reference:** identical formula, `PTS + 0.4*FG - 0.7*FGA - 0.4*(FTA - FT) + 0.7*ORB + 0.3*DRB + STL + 0.7*AST + 0.7*BLK - 0.4*PF - TOV`. "A rough measure of a player's productivity for a single game. The scale is similar to that of points scored (40 is an outstanding performance, 10 is an average performance, etc.)."

**Usage**
| Game Score | Performance level |
|---|---|
| 40+ | Historic, all-time great game |
| 30–40 | Outstanding, dominant outing |
| 20–30 | Excellent, near-star performance |
| 10–20 | Solid to good, roughly average starter |
| 0–10 | Below average, limited impact |
| Negative | Rough night; hurt the team |

- Worked examples from NBAstuffer:
  - 30 pts on 11/18 FG, 6/7 FT, 2 ORB, 6 DRB, 7 AST, 2 STL, 1 BLK, 2 PF, 3 TOV → **28.4**
  - 28 pts on 10/26 FG, 7/9 FT, 5 REB, 5 AST, 1 STL, 3 PF, 5 TOV → **13.2** (volume ≠ efficiency)
  - 22 pts on 8/15 FG, 5/6 FT, 3 ORB, 9 DRB, 11 AST, 2 STL, 2 BLK, 2 PF, 4 TOV → **25.4**
- Best as a **per-game snapshot**; PER (#32) is better for season-long and cross-team comparison.

---

## 19. Gravity

**Definition**
A player-tracking metric (published by the NBA starting in 2025-26) that quantifies how much defensive attention a player draws, based on floor spacing and defender positioning.

**Formula** — **[Model-based]**
No public formula. It is derived from optical tracking of defender distance and positioning relative to the player, compared with expected defensive positioning. It has two components:
```
On-Ball Gravity  : attention drawn while dribbling/handling the ball
Off-Ball Gravity : attention drawn while running off screens or spotting up without the ball
```

**Glossary**
- **Attention**: how far defenders shade toward, or how closely they guard, a player relative to a baseline.
- **Floor spacing**: how the positions of offensive players stretch the defense.

**Usage**
- Captures value that box scores miss, such as elite shooters (e.g., Stephen Curry-type players) who create open shots for teammates just by being on the floor.
- Useful for lineup construction and valuing off-ball shooters and screeners.

---

## 20. Individual Floor Percentage

**Definition**
The percentage of a player's possessions that end in a score, i.e., how often a player's possessions are "successful."

**Formula**
```
Floor% = 100 × Scoring Possessions / Total Possessions
```

**Glossary**
- **Total possessions**: every possession the player ends (shot, trip to the line, turnover). See #55.
- **Scoring possessions**: possessions where the player scored or assisted on a score. See #47.

> **Basketball-Reference:** `Floor% = ScPoss / TotPoss` (Dean Oliver's full ScPoss and TotPoss, see #47 and #55). Oliver's question: "What percentage of the time that a player wants to score does he actually score?"

**Usage**
- Measures reliability: how often a player's possessions produce points, regardless of how many points.
- Pairs with Offensive Rating (#29), which measures points per possession. **ORtg vs. Floor%** reflects points per scoring possession. Oliver's examples: Shaquille O'Neal had a high Floor% but many one-point possessions (poor FT shooting), which lowered his ORtg. Three-point shooters like Reggie Miller may have a lower Floor% but a higher ORtg.

---

## 21. Individual Player Value (IPV)

**Definition**
A plus-minus model from the Talking Practice blog. It runs the standard RAPM procedure but regresses toward a **machine-learning–based Bayesian prior**.

**Formula** — **[Model-based]**
```
1. Build a prior from box score, play-by-play, video-tracking stats,
   and player demographics using a machine-learning model.
2. Run RAPM (ridge regression, #46) shrinking toward that prior
   instead of toward zero.
3. IPV = resulting points per 100 possessions vs. average.
```

**Glossary**
- **RAPM**: Regularized Adjusted Plus-Minus.
- **Bayesian prior**: a starting belief about a player's value that the data then updates.
- **Overfitting**: fitting noise in the training data, which hurts out-of-sample predictions.

**Usage**
- Aims for better out-of-sample accuracy than plain regression models, especially on **defense**.

---

## 22. LEBRON

**Definition**
*Luck-adjusted player Estimate using a Box prior Regularized ON-off*: BBall-Index's (Tim Cranjis, Krishna Narsu) impact metric in points per 100 possessions. It combines box-score elements with luck-adjusted RAPM.

**Formula** — **[Model-based]**
```
1. Box prior: box-score weights derived from PIPM, adjusted for player role/archetype.
2. Luck adjustment: remove noise such as opponent 3P% and FT% variance.
3. Regularized on/off (RAPM) using the box prior.
LEBRON = O-LEBRON + D-LEBRON   (points per 100 possessions)
```

**Glossary**
- **Luck-adjusted**: replaces actual opponent three-point and free-throw results (largely outside a defender's control) with expected values.
- **PIPM**: Player Impact Plus-Minus (Jacob Goldstein).
- **Player role**: offensive archetype (e.g., shot creator, stretch big) used to stabilize estimates.

**Usage**
- An all-in-one impact metric that ranked third in predictive accuracy behind DARKO and EPM in Medvedovsky's 2021 comparison.
- Role adjustment makes it useful for comparing players in very different jobs.

---

## 23. NBA Efficiency (EFF)

**Definition**
Martin Manley's linear efficiency metric, considered the first player evaluation metric. All categories are weighted equally.

**Formula**
```
EFF = PTS + REB + STL + AST + BLK − TOV − Missed Shots
```
(Missed shots = missed FG + missed FT in the NBA's official version.)

**Glossary**
- **Missed shots**: (FGA − FGM) + (FTA − FTM).

**Usage**
- **Pros:** explains free-agent salaries and public perception of performance well.
- **Cons:** equal weights for all stats; no pace adjustment; not possession-based, so a poor measure of impact on wins.

---

## 24. Plus-Minus (+/-) — Complete Guide

**Definition**
The net change in score while a given player is on the court. The NBA has published it in official box scores since 2007-08.

**Formula**
```
+/- = (Team PTS scored while player on court) − (Team PTS allowed while player on court)

Net (on/off) +/- = (+/- per 100 poss ON court) − (+/- per 100 poss OFF court)
```
*Example:* Rockets +15 in Alperen Sengun's 25 minutes and −5 in his 23 rest minutes → **+/- = +15**, **on/off net = +10**.

> **Basketball-Reference:** "+/-: the difference between the team's scoring and the opponent's scoring while the player is on the court."

**Glossary**
- **On/Off**: comparing team results with and without the player.
- **Unit plus-minus**: the same calculation for 2-, 3-, or 5-man combinations.
- **Family of derived metrics**: DPM, Net +/- (Roland Rating), APM (Winston & Sagarin), SPM (Rosenbaum), RAPM (Joe Sill), RPM/xRAPM (Ilardi & Engelmann/ESPN), BPM (Myers), PT-PM, EPM (Snarr), PIPM (Goldstein), CARMELO & RAPTOR (FiveThirtyEight), LEBRON (Cranjis & Narsu), DARKO (Medvedovsky), IPV (Talking Practice), AuPM (Ben Taylor), DRIP (Nathan Walker), Net Points (Dean Oliver/ESPN).

**Usage**
- **Strengths:** captures "invisible" contributions such as screens, rotations, spacing, and IQ. Front offices use it for drafts and free agency; coaches use it for lineups and rotations.
- **Limitations:** heavily influenced by teammates (a great player on a bad team can be negative); small samples are noisy; ignores opponent quality and context (rest days, garbage time).

---

## 25. Net Plus-Minus (Roland Rating)

**Definition**
Roland Beech's unadjusted on/off metric (82games.com). It compares team performance with a player on vs. off the court, combining offense and defense.

**Formula**
```
Net Off +/- = Tm ORtg (ON) − Tm ORtg (OFF)
Net Def +/- = Tm DRtg (ON) − Tm DRtg (OFF)
Net +/-     = Net Off +/- − Net Def +/-
```
*Example:* Offense 115 on / 98 off → +17; defense allows 110 on / 105 off → +5; **Net = +17 − (+5) = +12**.

**Glossary**
- **ORtg / DRtg (team)**: points scored / allowed per 100 possessions.
- **Unadjusted**: no control for teammates or opponents (unlike APM).

**Usage**
- **Tip:** you want a positive net offensive and a negative net defensive value.
- Quick read of a player's team impact; affected by who backs him up and who he plays with.

---

## 26. Net Points

**Definition**
A **descriptive** single-game metric from Dean Oliver and ESPN Analytics. It uses play-by-play data to assign credit and blame for every play based on difficulty and context. Positive = contributed more than an average player.

**Formula** — **[Model-based]**
```
Per game: Net Points = Σ (credit − blame) over every play the player is involved in
          (shots, passes, rebounds, turnovers, steals, blocks, defensive actions),
          each weighted by difficulty/context.

Weights come from an SPM-style regression:
  Dependent variable    : RAPM × total possessions played
  Independent variables : player stat totals (PTS, AST, REB, STL, BLK, TOV, …)
```

**Glossary**
- **Credit / blame**: portion of a scoring or non-scoring outcome assigned to each involved player.
- **Difficulty adjustment**: tough makes and contested stops get more credit than routine plays.
- **Descriptive vs. predictive**: Net Points measures what happened; xRAPM, RAPTOR, and BPM try to predict future impact.

**Usage**
- Evaluating single games (e.g., Giannis's 59-point game = +19.9 Net Points), team dynamics, trades (Doncic ↔ Davis), and team strengths (OKC: +5.9 of +12.6 margin from turnovers; CLE: +8.2/game from FG efficiency).
- 2024-25 leaders: Jokic +427, Gilgeous-Alexander +345, Towns +203, Tatum +183, Sengun +181.

---

## 27. Non-Scoring Player Possessions

**Definition**
Possessions a player ends without scoring: missed field goals, free-throw trips not rebounded by his team, and turnovers.

**Formula**
```
Non-Scoring Poss = (FGA − FGM) + 0.4 × FTA + TOV
```
*(Oliver's fuller version uses missed FTs that end the possession: `0.4 × FTA × (1 − FT%)²`; the NBAstuffer version is simplified. The full version also removes misses his team rebounded: `(FGA − FGM) × (1 − Tm ORB%)`.)*

**Glossary**
- **0.4 × FTA**: estimate of possessions used by free-throw trips.
- **Non-scoring**: the possession ended with no points.

**Usage**
- Component of Total Player Possessions (#55) and Floor% (#20).
- Shows how often a player "wastes" possessions.

---

## 28. Offensive Conversion Rate

**Definition**
The percentage of a player's steals that lead to a made basket or free-throw attempts within 5 seconds.

**Formula** — **[Supplemented]** (derived from the definition)
```
Offensive Conversion Rate = 100 × (Steals followed by FGM or FTA within 5 s) / Total Steals
```

**Glossary**
- **5-second window**: isolates immediate transition offense created by the steal.

**Usage**
- Measures how often a player's defensive takeaways turn into transition points.
- Useful for evaluating "defense-to-offense" players and fast-break systems. Requires play-by-play timing data.

---

## 29. Offensive Rating (ORtg)

**Definition**
Dean Oliver's estimate of the points a player produces per 100 individual possessions.

**Formula** — **[Basketball-Reference]** (Dean Oliver, *Basketball on Paper*; NBAstuffer gives only the components)
```
ORtg = 100 × (PProd / TotPoss)
```
- **PProd (Points Produced)**: full formula in #38.
- **TotPoss (Total Possessions)**: full formula in #55.

> **Basketball-Reference:** "For players it is points produced per 100 possessions, while for teams it is points scored per 100 possessions." Available since 1977-78. In Oliver's words: "How many points is a player likely to generate when he tries?"

**Glossary**
- **Scoring possessions**: credit for times the player's team ends a possession with a score. See #47.
- **Individual points produced**: credit for points the team generates with the player's involvement.

**Usage**
- Efficiency of a player's offense. Read it **together with Usage Rate** (#60): a 120 ORtg on 12% usage is very different from 120 on 30% usage. Oliver calls this **"Skill Curves"**: the bigger the offensive role, the harder it is to keep a high ORtg, so compare ORtg mainly among players in similar roles.
- Pair with Defensive Rating (#10) for net rating.

---

## 30. Per-Minute Ratings

**Definition**
Stats normalized to a fixed number of minutes (usually 36 or 40) so players with different playing time can be compared.

**Formula**
```
Stat per 36 = (Stat total / MP) × 36
Stat per 40 = (Stat total / MP) × 40
```
*Example:* 12 PPG in 24 MPG → (12 / 24) × 36 = **18 points per 36**.

> **Basketball-Reference:** "Per 36 Minutes: a statistic (e.g., assists) divided by minutes played, multiplied by 36." "Per Game: a statistic divided by games." (B-Ref also publishes Per 100 Possessions tables.)

**Glossary**
- **Per 36**: approximates a starter's workload. **Per 40**: common in college/older analysis.

**Usage**
- Judges bench players' production more fairly than per-game averages.
- **Caveat:** production does not always scale linearly with more minutes (fatigue, tougher matchups, role change). Small minute samples are noisy.

---

## 31. Personal Foul Efficiency

**Definition**
Ratio of steals plus blocks to personal fouls: how efficiently a defender forces turnovers or blocks without fouling.

**Formula** — **[Supplemented]** (derived from the definition)
```
PF Efficiency = (STL + BLK) / PF
```

**Glossary**
- **"Jump-happy / slaptastic"**: gambling defenders who pile up blocks or steals but foul a lot. This ratio exposes them.

**Usage**
- Comparative defensive discipline measure.
- **Caveat:** fouls can rise with legitimate defensive effort, so don't use it in isolation.

---

## 32. Player Efficiency Rating (PER)

**Definition**
John Hollinger's per-minute, pace-adjusted rating that sums a player's positive contributions and subtracts negative ones. League average is always **15.0**.

**Formula** — **[Basketball-Reference]** ("Calculating PER"; NBAstuffer links out)
```
uPER = (1 / MP) × [
      3PM
    + (2/3) × AST
    + (2 − factor × (Tm AST / Tm FGM)) × FGM
    + FTM × 0.5 × (1 + (1 − Tm AST/Tm FGM) + (2/3) × (Tm AST/Tm FGM))
    − VOP × TOV
    − VOP × DRB% × (FGA − FGM)
    − VOP × 0.44 × (0.44 + 0.56 × DRB%) × (FTA − FTM)
    + VOP × (1 − DRB%) × (TRB − ORB)
    + VOP × DRB% × ORB
    + VOP × STL
    + VOP × DRB% × BLK
    − PF × ( (Lg FTM / Lg PF) − 0.44 × (Lg FTA / Lg PF) × VOP )
]

factor = (2/3) − (0.5 × (Lg AST / Lg FGM)) / (2 × (Lg FGM / Lg FTM))
VOP    = Lg PTS / (Lg FGA − Lg ORB + Lg TOV + 0.44 × Lg FTA)
DRB%   = (Lg TRB − Lg ORB) / Lg TRB

aPER = (Lg Pace / Tm Pace) × uPER
PER  = aPER × (15 / Lg aPER)      (Lg aPER is minutes-weighted)
```

> **Basketball-Reference:** "The PER sums up all a player's positive accomplishments, subtracts the negative accomplishments, and returns a per-minute rating of a player's performance" (Hollinger). B-Ref computes PER back to 1951-52 using these fallbacks for years with missing stats:
> - Before 1979-80 (no 3PT), 1977-78 (no player TOV), and 1973-74 (no ORB/STL/BLK): zero out 3P, TOV, BLK, and STL; set VOP = 1; set DRB% = 0.7; set ORB = 0.3 × TRB.
> - Before 1973-74 (no pace): estimated pace adjustment = `2 × Lg PPG / (Tm PPG + Opp PPG)` (RMSE 0.0197 vs. actual).

**Glossary**
- **uPER**: unadjusted PER. **aPER**: pace-adjusted PER.
- **VOP**: value of a possession (league points per possession).
- **DRB%** (here): league defensive rebound share.
- **factor**: splits credit for assisted field goals between passer and shooter.

**Usage**
| PER | Typical meaning |
|---|---|
| 35+ | All-time season |
| 25–30 | MVP candidate |
| 20–25 | All-Star |
| 15 | League average |
| < 10 | Fringe roster |

- Popular summary of per-minute offensive productivity (widespread in the early 2010s).
- **Limitations:** mostly measures offense; Hollinger himself says STL and BLK can distort it and it is not a reliable defensive measure. It rewards high-volume shooting.

---

## 33. Player Impact Estimate (PIE)

**Definition**
The NBA's measure of a player's share of all game events: what percentage of the game's box-score "events" the player accounted for.

**Formula**
```
PIE = (PTS + FGM + FTM − FGA − FTA + DRB + ORB/2 + AST + STL + BLK/2 − PF − TOV)
      ÷
      (Game PTS + Game FGM + Game FTM − Game FGA − Game FTA + Game DRB
       + Game ORB/2 + Game AST + Game STL + Game BLK/2 − Game PF − Game TOV)
```

**Glossary**
- **Game ___**: the total for *both* teams in the game.
- **ORB/2, BLK/2**: half-weighted.

**Usage**
- Available on NBA.com. Simpler than PER and includes defensive stats.
- Since the total for all 10 players sums to 100%, ~10% is average; elite players reach 18–20%.
- Good for single-game and season "share of production" comparisons.

---

## 34. Player Tracking Plus-Minus (PT-PM)

**Definition**
Andrew Johnson's metric that combines Real Plus-Minus, box-score data, and SportVU tracking data. It is split into offensive and defensive components.

**Formula**
```
Offensive PT-PM = −4.123
                  + 0.594  × PTS
                  − 0.559  × FGA
                  + 21.809 × Passing Efficiency
                  − 0.587  × TOV per 100 touches
                  + 4.241  × Contested Rebound %
                  + 0.043  × MPG
                  − 0.247  × FTA
                  + 0.138  × REB × 3P Rate

Defensive PT-PM =  1.605
                  − 5.627 × Opponent FG% at Rim
                  + 0.953 × Steals per 100
                  + 0.145 × Opp FGA at Rim
                  − 0.159 × PF per 100

PT-PM = Offensive PT-PM + Defensive PT-PM
```

**Glossary**
- **Passing Efficiency**: points created per pass attempt.
- **TOV per 100 touches**: turnovers committed per 100 touches.
- **Contested Rebound %**: share of the player's rebounds that were contested by an opponent.
- **3P Rate**: 3PA / FGA.
- **Opponent FG% at Rim**: opponents' FG% at the basket when the player was in position to contest.
- **Opp FGA at Rim**: times per 100 possessions the player was in position to contest a rim shot.
- **Steals per 100 / PF per 100**: per 100 possessions.

**Usage**
- An early example of adding tracking data to plus-minus. Its defensive side captures rim protection directly.
- Coefficients are tied to the SportVU era.

---

## 35. Points Created

**Definition**
Bob Bellotti's linear composite metric of overall performance using all primary and secondary box-score categories.

**Formula**
```
Points Created = PTS
               + AST × (2 − VBP)
               + (REB + STL + BLK) × VBP
               − (FG Missed + FT Missed + TOV) × VBP
               − 0.5 × VBP × PF
```

**Glossary**
- **VBP (Value of Ball Possession)**: league-average points per possession (per 100 possessions ÷ 100, ~1.0–1.15).
- **AST × (2 − VBP)**: assist credit = value of a 2-pt basket minus the possession value already "owned."

**Usage**
- Comprehensive single number for players or teams at any granularity (one game, season, career).
- Measures overall performance, not a single skill.

---

## 36. Points Per Possession (PPP)

**Definition**
A player's scoring efficiency per possession used. Most meaningful when split by play type (isolation, pick-and-roll, post-up, transition, spot-up, etc.).

**Formula**
```
PPP = PTS / (FGA + 0.44 × FTA + TOV)
```

**Glossary**
- **FGA + 0.44×FTA + TOV**: possessions the player used (see Usage Rate #60).
- **Play type**: Synergy-style classification of how a possession ended.

**Usage**
- Compare scorers by play type (e.g., 1.10 PPP in isolation is elite; ~0.90 is league-typical).
- Related: Scoring Player Possessions (#47).

---

## 37. Points Per Shot Attempt (PTS/FGA)

**Definition**
Points from field goals divided by field goal attempts.

**Formula**
```
PTS/FGA = (Points from 2PM and 3PM) / FGA
        = (2 × 2PM + 3 × 3PM) / FGA
```

**Glossary**
- **2PM / 3PM**: two- and three-point field goals made.

**Usage**
- Simple shooting efficiency (equals 2 × eFG%).
- **Ignores free throws.** Use TS% (#58) when free-throw scoring matters.

---

## 38. Points Produced

**Definition**
Dean Oliver's measure of a player's offensive contribution: points from made shots, assists, and offensive rebounds, credited proportionally. Considered more meaningful than raw points scored.

**Formula**
```
Points Produced = (FGA + 0.44 × FTA + TOV) × ORtg / 100
```
(Equivalent to ORtg × individual possessions / 100.)

**Full formula — [Basketball-Reference]** (Dean Oliver)
```
PProd = (PProd_FG_Part + PProd_AST_Part + FTM)
        × (1 − (Tm ORB / Tm Scoring Poss) × Tm ORB Weight × Tm Play%)
        + PProd_ORB_Part

PProd_FG_Part  = 2 × (FGM + 0.5 × 3PM) × (1 − 0.5 × ((PTS − FTM) / (2 × FGA)) × qAST)
PProd_AST_Part = 2 × ((Tm FGM − FGM + 0.5 × (Tm 3PM − 3PM)) / (Tm FGM − FGM))
                 × 0.5 × (((Tm PTS − Tm FTM) − (PTS − FTM)) / (2 × (Tm FGA − FGA))) × AST
PProd_ORB_Part = ORB × Tm ORB Weight × Tm Play%
                 × (Tm PTS / (Tm FGM + (1 − (1 − Tm FTM/Tm FTA)²) × 0.4 × Tm FTA))
```
(qAST, Tm Scoring Poss, Tm ORB Weight, and Tm Play% are defined in #47.)

**Glossary**
- **ORtg**: Offensive Rating (#29).
- **FGA + 0.44×FTA + TOV**: possessions used.

**Usage**
- Measures total offensive output with shared credit for assisted baskets and putbacks.
- The teammates' Points Produced should add up to roughly the team's actual points.

---

## 39. Position Adjusted Win Score (PAWS)

**Definition**
David Berri's Win Score (#63) adjusted for a player's primary position. It compares players only against the average at their position (centers naturally post higher Win Scores).

**Formula**
```
PAWS48 = WS48 − (Average WS48 at player's primary position)
PAWS   = (PAWS48 / 48) × Minutes
```
*(NBAstuffer's page is missing the minus sign in PAWS48; it is restored here.)*

**Glossary**
- **WS48**: **Win Score** per 48 minutes (not Win Shares).
- **Primary position**: position played most often.

**Usage**
- Fairer comparison across positions for Win Score–based evaluation (e.g., guards vs. centers).
- Positive = better than a typical player at the same position.

---

## 40. Potential Assists (PA)

**Definition**
Per the NBA: "any pass that leads to a shot within one dribble," whether the shot is made or missed.

**Formula**
A tracked count, not a calculation:
```
PA = count of passes where the receiver shoots (or is fouled shooting) before the 2nd dribble
Official Assists ⊆ Potential Assists (only made shots become assists)
Assist conversion rate = AST / PA
```

**Glossary**
- **One-Dribble-to-Assist rule**: the shot must come before the receiver's second bounce.
- **Second Spectrum**: 6–10 arena cameras tracking all players and the ball 25 times per second, auto-tagging passes, catches, dribbles, and shots.

**Usage**
- **Spot real playmakers**: e.g., 11 AST but 20+ PA → nine more clean looks were created and missed.
- **Context for cold shooting nights**: high PA with low AST means the offense works but the finishing doesn't.
- **Rookie radar**: 3 AST but 12 PA shows vision that should translate later.
- **Fantasy/betting**: assists tend to regress toward the PA level (buy low, sell high).

---

## 41. Quantified Shooter Impact (qSI)

**Definition**
Second Spectrum metric: how much better or worse a shooter converts than expected, given the difficulty of his shots.

**Formula**
```
qSI = eFG% − qSQ
```

**Glossary**
- **eFG%**: actual effective field goal % (#13).
- **qSQ**: expected eFG% given shot difficulty (#42).
- It splits eFG% into **shot quality** (how tough the shot was) and **shooter impact** (finishing skill).

**Usage**
- Separates shot-making skill from shot selection. Positive qSI = a better shot-maker than the average player taking the same shots.

---

## 42. Quantified Shot Quality (qSQ)

**Definition**
Second Spectrum's expected effective FG% for a shot, given its type, location, and nearby defenders. Presented at the 2014 MIT Sloan Sports Analytics Conference.

**Formula** — **[Model-based]**
```
qSQ = P(FGA becomes FGM | shot type, location/distance, closest defender,
                          next-closest defender, shooter velocity, …)
      expressed on the eFG% scale
```
Estimated with machine learning on tracking data (ball trajectory and all player locations).

**Glossary**
- **Shot quality**: how easy a shot is. Higher qSQ = easier shot.
- **Closest / next-closest defender**: distance and angle of contesting defenders.

**Usage**
- Evaluates shot selection and offensive schemes (are we generating good looks?).
- Paired with qSI (#41) to separate a player's shot-making from his shot diet.

---

## 43. RAPTOR

**Definition**
*Robust Algorithm (using) Player Tracking (and) On/Off Ratings*: FiveThirtyEight's plus-minus metric that replaced CARMELO. It measures points contributed per 100 possessions on offense and defense relative to a league-average player.

**Formula** — **[Model-based]**
```
RAPTOR = Box component (box score + player-tracking stats)
       + On/Off component (regularized on/off ratings)
Total RAPTOR = Offensive RAPTOR + Defensive RAPTOR
Projections also factor height, age, draft position, and awards.
```

**Glossary**
- **Offensive RAPTOR +1.5**: team offense is 1.5 points per 100 possessions better with him on the floor.
- **Defensive RAPTOR +2.4**: team defense is 2.4 points per 100 possessions better with him on the floor.
- **Player tracking**: optical data (e.g., defender distance, drives, touches).

**Usage**
- All-in-one impact estimate with offense/defense splits; also converts to WAR.
- FiveThirtyEight has discontinued NBA coverage, so it is mainly historical now.

---

## 44. Real Plus-Minus (RPM)

**Definition**
ESPN's former metric (by Steve Ilardi and Jeremias Engelmann): a player's average impact on net point differential per 100 offensive and defensive possessions.

**Formula** — **[Model-based]**
```
RPM = ORPM + DRPM
Built on xRAPM: ridge-regressed on/off data with a box-score prior (see #46).
```

**Glossary**
- **ORPM**: impact on team points scored per 100 offensive possessions.
- **DRPM**: impact on team points allowed per 100 defensive possessions.
- **xRAPM**: Engelmann's successor version.

**Usage**
- All-in-one impact ranking with offense/defense split; was widely cited in media.
- RPM WINS converted RPM to wins added.

---

## 45. Rebound Percentage (TRB%)

**Definition**
Estimated percentage of available rebounds a player grabs while on the court.

**Formula**
```
TRB% = 100 × (TRB × (Tm MP / 5)) / (MP × (Tm TRB + Opp TRB))
```
Offensive (ORB%) and defensive (DRB%) versions use the matching rebound types:
```
ORB% = 100 × (ORB × (Tm MP/5)) / (MP × (Tm ORB + Opp DRB))
DRB% = 100 × (DRB × (Tm MP/5)) / (MP × (Tm DRB + Opp ORB))
```

> **Basketball-Reference:** identical formulas for TRB%, ORB%, and DRB% (available since 1970-71). Each is "an estimate of the percentage of available [total / offensive / defensive] rebounds a player grabbed while he was on the floor." *Team* versions (Four Factors, B7): `ORB% = ORB / (ORB + Opp DRB)` and `DRB% = DRB / (Opp ORB + DRB)`.

**Glossary**
- **Available rebounds**: all missed-shot rebounds (both teams) while the player is on court.
- **Tm MP / 5**: team minutes per player slot (≈ game minutes).

**Usage**
- Pace- and minutes-neutral rebounding comparison. Elite bigs reach ~20%+ TRB%.
- Evaluate ORB% and DRB% separately; they reflect different skills and team roles.

---

## 46. Regularized Adjusted Plus-Minus (RAPM / xRAPM)

**Definition**
APM (#2) estimated with **ridge regression** (regularization) to reduce noise. xRAPM is Jeremias Engelmann's version (formerly the basis of ESPN's RPM).

**Formula** — **[Model-based]**
```
Minimize over β:   Σ_stints w_s × (y_s − X_s β)²  +  λ × Σ_i β_i²

y_s = point margin per 100 possessions in stint s
X_s = player on-court indicators (+1 / −1 / 0)
w_s = possessions in stint s
λ   = regularization strength (tuned by cross-validation)
```
xRAPM additionally shrinks toward a box-score prior instead of toward 0.

**Glossary**
- **Ridge regression / regularization**: penalizes large coefficients, pulling uncertain estimates toward 0 (or a prior). This is equivalent to a Bayesian prior.
- **Multi-year data**: typically 3 seasons with past seasons down-weighted.

**Usage**
- About twice as accurate as standard APM (with 3 years of data and optimized weighting).
- The standard "ground truth" that most modern box-score metrics (BPM, SPM, Net Points) are trained on.

---

## 47. Scoring Player Possessions

**Definition**
Dean Oliver's count of possessions a player finishes with a score. It includes unassisted FGs, a share of assisted FGs, a share of his assists, and free-throw trips that produce points.

**Formula**
```
Scoring Poss = FGM − 0.37 × FGM × (Q / R) + 0.37 × AST + 0.5 × FTM

Q = 5 × MP × Tm AST / Tm MP − AST
R = 5 × MP × Tm FGM / Tm MP − AST
```
The version above is NBAstuffer's simplified form.

**Full formula — [Basketball-Reference]** (Dean Oliver)
```
ScPoss = (FG_Part + AST_Part + FT_Part)
         × (1 − (Tm ORB / Tm Scoring Poss) × Tm ORB Weight × Tm Play%)
         + ORB_Part

FG_Part  = FGM × (1 − 0.5 × ((PTS − FTM) / (2 × FGA)) × qAST)
qAST     = ((MP / (Tm MP / 5)) × (1.14 × ((Tm AST − AST) / Tm FGM)))
         + ((((Tm AST / Tm MP) × MP × 5 − AST) / ((Tm FGM / Tm MP) × MP × 5 − FGM))
            × (1 − (MP / (Tm MP / 5))))
AST_Part = 0.5 × (((Tm PTS − Tm FTM) − (PTS − FTM)) / (2 × (Tm FGA − FGA))) × AST
FT_Part  = (1 − (1 − FTM/FTA)²) × 0.4 × FTA
ORB_Part = ORB × Tm ORB Weight × Tm Play%

Tm Scoring Poss = Tm FGM + (1 − (1 − Tm FTM/Tm FTA)²) × Tm FTA × 0.4
Tm Play%        = Tm Scoring Poss / (Tm FGA + Tm FTA × 0.4 + Tm TOV)
Tm ORB%         = Tm ORB / (Tm ORB + (Opp TRB − Opp ORB))
Tm ORB Weight   = ((1 − Tm ORB%) × Tm Play%)
                  / ((1 − Tm ORB%) × Tm Play% + Tm ORB% × (1 − Tm Play%))
```
- **qAST**: estimated share of the player's field goals that were assisted.
- **Tm Play%**: share of team plays that score.
- **Tm ORB Weight**: how credit is split between the offensive rebound and the eventual score.

**Glossary**
- **0.37**: share of credit given to the passer on an assisted basket (the shooter keeps 0.63).
- **Q / R**: estimated share of the player's field goals that were assisted.
- **0.5 × FTM**: approximate possessions scored via free throws.

**Usage**
- Numerator for Floor% (#20); a component of Total Possessions (#55) and ORtg (#29).
- Related: PPP (#36).

---

## 48. Seasons Left

**Definition**
Bill James–style estimate of how many seasons a player has left.

**Formula**
```
Seasons Left = 27 − 0.75 × Age
```

**Glossary**
- **Age**: player age at the time of the estimate.
- *Example:* age 28 → 27 − 21 = **6 seasons**.

**Usage**
- Crude career-length estimate for contract and trade analysis.
- An input to Trade Value (#57).
- Ignores health, position, and play style.

---

## 49. Simple Projection System (SPS)

**Definition**
A projection method that accounts for aging. It uses 3 years of data, weights recent seasons more heavily, and regresses toward the mean.

**Formula** — **[Supplemented]** (Basketball-Reference's SPS approach from memory; it is not in the B-Ref glossary, so verify the weights before relying on them)
```
1. Weighted per-minute rate = (6 × Year_t + 3 × Year_t−1 + 1 × Year_t−2)  [weights by minutes]
2. Regress to the mean: add ~1,000 minutes of league-average production.
3. Age adjustment: +/- a small % per year relative to peak age (~28)
   (improvement if younger, decline if older).
4. Projected stat = adjusted rate × projected minutes.
```

**Glossary**
- **Regression to the mean**: pulls small or extreme samples back toward league average.
- **Age factor**: expected improvement or decline based on age.

**Usage**
- A baseline "naive" forecast of next-season stats. A good benchmark for more complex models.

---

## 50. Simple Rating System (SRS)

**Definition**
Roland Beech's (82games.com) plus-minus–based player rating that combines on-court impact with how the player produced **vs. his opposing counterpart** while on the court.

**Formula** — **[Model-based]**
No public closed form on NBAstuffer. Conceptually:
```
SRS ≈ blend of (Net on/off +/-) and (Player production − Opponent counterpart production)
```

**Glossary**
- **Counterpart**: the opponent playing the same position at the same time.
- **Not to be confused** with Basketball-Reference's *team* Simple Rating System (margin of victory + strength of schedule). See B9.

**Usage**
- Adds a positional matchup lens to plus-minus data. Published on 82games.com.

---

## 51. Statistical Player Value (SPV)

**Definition**
William Benton's metric that converts each box-score stat (and minutes) into point-equivalent "value points" using team and league factors, then sums them per game.

**Formula**
```
SPV = MIN_VAL + PTS_VAL + REB_VAL + AST_VAL + STL_VAL + BLK_VAL + TOV_VAL

MIN_VAL = 1 × Minutes
PTS_VAL = 1 × Points
REB_VAL = REB × (PSPP + DB)
AST_VAL = AST × PPB
STL_VAL = STL × (PSPP + PAPP)
BLK_VAL = BLK × LPPB
TOV_VAL = −TOV × (PSPP + PAPP)
```
Summary versions:
```
SPVPG  = Σ SPV / Games Played
SPVPM  = Σ SPV / Minutes Played
SPVPTM = Σ SPV / Team Minutes Played
```

**Glossary**
- **PPB (Points Per Basket)**: team PTS / team FGM (includes FT points; always > 2).
- **PSPP (Points Scored Per Possession)**: team ORtg / 100.
- **PAPP (Points Allowed Per Possession)**: team DRtg / 100.
- **DB (Defensive Bonus)**: worst league PAPP − team PAPP (extra rebound credit for good defensive teams).
- **LPPB (League Points Per Basket)**: league PTS / league FGM.
- **ASV (Average Starter Value)**: mean (and SD) of SPV for all starters in a season. This is the comparison baseline, with per-game, per-minute, and per-team-minute versions.

**Usage**
- **SPVPM** → skill and activity (bench players).
- **SPVPG** → conditioning and dominance (starters).
- **SPVPTM** → durability and availability (elites, MVP races; adjusts for overtime and games played).
- Compare to ASV across seasons and eras. *Example:* Jokic's average game beat 95.05% of all starter games (ASVPG 61.57, SD 19.82).
- Note: team factors drift during the season, so values are final only at season's end.

---

## 52. Statistical Plus-Minus (SPM)

**Definition**
Dan Rosenbaum's estimate of a player's contribution to point differential per 100 possessions from box-score stats. It is essentially adjusted plus-minus predicted from the box score.

**Formula** — **[Model-based]**
```
Regress:  APM (or RAPM)_i  =  a + Σ b_k × (box-score rate stat_k)_i  + ε
SPM_i = a + Σ b_k × stat_k,i       (weights b_k chosen to minimize mean residuals)
```

**Glossary**
- **Linear weights**: fixed coefficients for each box-score stat.
- **Residual**: difference between the actual APM and the SPM prediction.

**Usage**
- More stable than raw or adjusted plus-minus year to year. Often a better predictor of **future defense**; APM better describes past defense.
- Combining APM and SPM works best. SPM is the ancestor of BPM (#5).

---

## 53. Steal Percentage (STL%)

**Definition**
Percentage of opponent possessions ending in a steal by the player while he is on the court.

**Formula**
```
STL% = 100 × (STL × (Tm MP / 5)) / (MP × Opp Possessions)
```
*(NBAstuffer's "Minuted Played" typo corrected.)*

**Glossary**
- **Opp Possessions**: estimated opponent possessions. Basketball-Reference uses its two-sided possession formula (B3).

> **Basketball-Reference:** identical formula, `100 * (STL * (Tm MP / 5)) / (MP * Opp Poss)`. Available since 1973-74.

**Usage**
- Pace-neutral measure of ball-hawking. Elite perimeter defenders are ~2.5–3%+.
- High STL% can come with gambling; check alongside Personal Foul Efficiency (#31) and on/off defense.

---

## 54. Tendex Rating

**Definition**
Dave Heeren's per-minute linear-weights rating, generally considered the first player rating system with linear weights.

**Formula**
```
Tendex = [ PTS + REB + AST + STL + BLK
           − Missed FGA − 0.5 × Missed FTA − TOV − PF ] / MP
```

**Glossary**
- **Missed FGA**: FGA − FGM. **Missed FTA**: FTA − FTM (half-weighted).
- **/ MP**: per-minute scale.

**Usage**
- Quick per-minute productivity ranking. 2025-26 leaders: Jokić 1.118, Gilgeous-Alexander 0.924, Dončić 0.902, Leonard 0.841, Mitchell 0.715.
- Heavily rewards rebounds and assists (Jokić leads by a wide margin). Penalizes misses, turnovers, and fouls.

---

## 55. Total Player Possessions

**Definition**
The total number of possessions a player ends, whether by scoring or not.

**Formula**
```
Total Poss = Scoring Poss + Non-Scoring Poss

Expanded:
Total Poss = FGA − (FGA − FGM) × Tm ORB%
           + 0.37 × AST − 0.37 × FGM × Q / R
           + TOV + 0.4 × FTA

Q = 5 × MP × Tm AST / Tm MP − AST
R = 5 × MP × Tm FGM / Tm MP − AST
```

**Full formula — [Basketball-Reference]** (Dean Oliver)
```
TotPoss = ScPoss + FGxPoss + FTxPoss + TOV

FGxPoss = (FGA − FGM) × (1 − 1.07 × Tm ORB%)      (missed-FG possessions)
FTxPoss = (1 − FTM/FTA)² × 0.4 × FTA               (missed-FT possessions)
ScPoss  = full Scoring Possessions formula (#47)
```

**Glossary**
- **Tm ORB%**: team offensive rebound % (removes misses his team rebounded, which didn't end the possession).
- **Q / R**: estimated share of the player's FGs that were assisted (see #47).

**Usage**
- Denominator for Offensive Rating (#29) and Floor% (#20). The basis for measuring a player's offensive load.

---

## 56. Touches

**Definition**
An estimate of how many times a player touched the ball in an attacking position. Once he has the ball he can only pass, shoot, draw a foul, or turn it over.

**Formula**
```
Touches = FGA + TOV + FTA / (Tm FTA / Opp PF) + AST / 0.17

%Pass   = 100 × (AST / 0.17) / Touches
%Shoot  = 100 × FGA / Touches
%Fouled = 100 × (FTA / (Tm FTA / Opp PF)) / Touches
%TO     = 100 × TOV / Touches
```

**Glossary**
- **Tm FTA / Opp PF**: team free throws per foul drawn, which converts FTA into trips drawn.
- **AST / 0.17**: estimated total passes (assumes ~17% of attacking passes become assists).

**Usage**
- Describes a player's offensive role: shooter vs. facilitator vs. foul-drawer vs. turnover-prone.
- Actual tracked touches are available from NBA.com player tracking (stats.nba.com).

---

## 57. Trade Value

**Definition**
Bill James's estimate of a player's remaining career value, using his Approximate Value and age.

**Formula** (as given by NBAstuffer)
```
Trade Value = [ (AV − (27 − 0.75 × Age))² × ((27 − 0.75 × Age) + 1) × AV ] / 190
              + AV × 2 / 13
```
*(The source page's formula is garbled; "2" after the first term is read as squared. Treat the exact structure with caution.)*

**Glossary**
- **AV**: Approximate Value (#3).
- **27 − 0.75 × Age**: Seasons Left (#48).

**Usage**
- Rough ranking of trade assets: combines current production (AV) and remaining career length.
- Very coarse; it ignores contracts, health, and fit.

---

## 58. True Shooting Percentage (TS%)

**Definition**
Scoring efficiency that accounts for twos, threes, and free throws in one number.

**Formula**
```
TS% = PTS / (2 × (FGA + 0.44 × FTA))
    = 0.5 × PTS / (FGA + 0.44 × FTA)
```

**Glossary**
- **FGA + 0.44 × FTA**: true shooting attempts (TSA). 0.44 estimates possessions used by FT trips (and-ones and technicals don't use a possession).
- **Max value**: 150% (a single made 3 on one attempt).

> **Basketball-Reference:** `TS% = PTS / (2 * TSA)`, where `TSA = FGA + 0.44 * FTA`. "A measure of shooting efficiency that takes into account field goals, 3-point field goals, and free throws."

**Usage**
- The standard single measure of scoring efficiency. League average is ~57–58% in the mid-2020s.
- Examples: Stephen Curry 65.3% (2020-21); Alperen Sengun ~54% (2024-25).
- Always read with **Usage Rate** (#60) and role: high TS% on low volume ≠ high TS% on high volume.

---

## 59. Turnover Ratio (TOV%)

**Definition**
Also called turnover percentage: the percentage of a player's (or team's) possessions that end in a turnover. Tempo-free.

**Formula**
```
TOV% = 100 × TOV / (FGA + 0.44 × FTA + AST + TOV)
```
> **Basketball-Reference:** TOV% = `100 * TOV / (FGA + 0.44 * FTA + TOV)`, "an estimate of turnovers per 100 plays" (available since 1977-78). **B-Ref omits AST from the denominator**, so its values are higher than NBAstuffer's Hollinger-style ratio. Both are in common use; state which one you use. Team TOV% is one of the Four Factors (B7).

**Glossary**
- **0.44 × FTA**: possessions used by free-throw trips.
- **AST in denominator**: counts assists as possessions the player "ended" by passing (Hollinger's turnover ratio).

**Usage**
- Ball security relative to involvement. Compare with AST% (#4) to judge playmaking risk vs. reward.
- Limitation: records only how a possession ended, not the quality of decisions.

---

## 60. Usage Rate (USG%)

**Definition**
Estimated percentage of team plays a player "used" (ended with a FGA, FT trip, or turnover) while on the floor.

**Formula**
```
USG% = 100 × (FGA + 0.44 × FTA + TOV) × (Tm MP / 5)
       ÷ ( MP × (Tm FGA + 0.44 × Tm FTA + Tm TOV) )
```
(Equivalent to NBAstuffer's form: `100 × (FGA + 0.44·FTA + TOV) × Tm MP / [(Tm FGA + 0.44·Tm FTA + Tm TOV) × 5 × MP]`.)

> **Basketball-Reference:** identical formula (the form shown first above). "An estimate of the percentage of team plays used by a player while he was on the floor." Available since 1977-78.

**Glossary**
- **Possession used**: a FGA, FT trip, or turnover by the player. An offensive rebound starts a new chance in the same possession.
- **Tm MP / 5**: normalizes to the minutes the player was on the floor.

**Usage**
- ~20% = average share (1/5). 30%+ = primary option. Examples: Harden ~36.1% (2019-20); Westbrook's record usage (2016-17); Klay Thompson 20.2% (2017-18).
- **Usage-efficiency trade-off:** efficiency tends to fall as usage rises. Stars who can carry high usage let teammates play at lower usage near peak efficiency.
- Always pair with TS% (#58) and ORtg (#29).

---

## 61. Versatility Index

**Definition**
John Hollinger's measure of a player's ability to produce in more than one category: points, rebounds, and assists.

**Formula**
```
Versatility Index = (PPG × RPG × APG)^(1/3)
```
(NBAstuffer writes the exponent as 0.333, i.e., the geometric mean.)

**Glossary**
- **Geometric mean**: rewards balance. A zero or tiny value in any category drags the index down sharply.

**Usage**
- ~5 = average player; 10+ = top all-around producers.
- Finds well-rounded contributors (triple-double types, point forwards).

---

## 62. Win Probability Added (WPA)

**Definition**
Mike Beuoy's (2014, Inpredictable) metric that credits players with the change in their team's win probability caused by their actions. It gives more credit to clutch plays and less to garbage time.

**Formula**
```
WPA = Σ over player's plays [ WinProb(after play) − WinProb(before play) ]
```
Tracks made/missed shots, turnovers, and free throws. Rebounds, assists, blocks, and steals are ignored.

**Glossary**
- **Win probability**: model-estimated chance of winning, given score, time remaining, possession, and pre-game spread.
- **Clutch / garbage time**: high- vs. near-zero-leverage moments.

**Usage**
- Measures "clutchness" and game-context value (who swung games).
- Descriptive, not predictive, and very noisy. It ignores non-shooting contributions.

---

## 63. Win Score

**Definition**
David Berri's simplified version of his Wins Produced model. It is a linear score of the relative value of box-score stats.

**Formula**
```
Win Score = PTS + REB + STL + ½ AST + ½ BLK
            − FGA − TOV − ½ FTA − ½ PF
```

**Glossary**
- **FGA fully subtracted**: each shot attempt costs a possession, so inefficient volume shooting is penalized.

**Usage**
- Quick snapshot of a player's productivity; especially useful for tracking whether a player is improving or declining.
- Heavily favors rebounders and efficient scorers. See PAWS (#39) for the position-adjusted version.

---

## 64. Win Shares (WS, WS/48)

**Definition**
Justin Kubatko's (Basketball-Reference) method that divides team wins among players based on offense, defense, and playing time. Player Win Shares on a team sum to roughly the team's win total.

> **Correction:** NBAstuffer quotes "a win share is worth one-third of a team win" (60 wins → 180 WS). That is **Bill James's baseball** convention. Basketball-Reference's article says Kubatko deliberately changed it: **in the basketball system, 1 Win Share = 1 win** (a 50-win team has about 50 WS). Unlike James's system, **negative Win Shares are possible** (a player who "took away wins that his teammates had generated").

**Formula** — **[Basketball-Reference]** ("NBA Win Shares", 1977-78 to present method; NBAstuffer links out)
```
Offensive Win Shares:
  Marginal Offense = Points Produced − 0.92 × (Lg PTS per Poss) × Offensive Possessions
  Marginal PTS per Win = 0.32 × Lg PTS per Game × (Tm Pace / Lg Pace)
  OWS = Marginal Offense / Marginal PTS per Win

Defensive Win Shares:
  Marginal Defense = (MP / Tm MP) × Tm Def Poss × (1.08 × Lg PTS per Poss − DRtg / 100)
  DWS = Marginal Defense / Marginal PTS per Win

WS    = OWS + DWS
WS/48 = WS / MP × 48
```

**Glossary**
- **Points Produced / Offensive Possessions**: see #38 and #55.
- **DRtg**: individual Defensive Rating (#10).
- **0.92 / 1.08**: replacement-level baselines for offense and defense.
- **Marginal PTS per Win**: points needed to add one win.

*B-Ref worked example (LeBron James, 2008-09):* PProd 2345.9, offensive possessions 1928.1, Lg PTS/Poss 1.083 → marginal offense = 2345.9 − 0.92 × 1.083 × 1928.1 = 424.8. Marginal points per win = 0.32 × 100.0 × (88.7 / 91.7) = 30.95 → **OWS = 13.73**. DRtg 99.1 → marginal defense = (3054/19780) × 7341 × (1.08 × 1.083 − 0.991) = 202.5 → **DWS = 6.54**.

Pre-1977-78 seasons use modified methods (estimated player turnovers; before 1973-74, defense is estimated from a regression on rebounds, steals, and blocks).

**Usage**
- WS/48: **.100** ≈ league average (per B-Ref); **.200+** ≈ All-Star; **.250+** ≈ MVP level.
- Records (B-Ref): Kareem Abdul-Jabbar holds the single-season record (25.4 WS, 1971-72) and the career record (273.4 WS). Michael Jordan is the career WS/48 leader among retired players.
- Great for historical and career comparisons (cumulative WS).
- Defense relies on team DRtg, so players on good defensive teams get inflated DWS.

---

## 65. Wins Above Replacement Player (WARP)

**Definition**
Kevin Pelton's metric (borrowing from sabermetrics and Baseball Prospectus, built on Dean Oliver's work). It compares a team of the player + 4 average players against a team of a replacement-level player + 4 average players, expressed in wins.

**Formula** — **[Model-based]**
```
1. Estimate the player's offensive & defensive ratings from the box score
   (accounting for the usage vs. efficiency trade-off and assist value).
2. Team A = player + 4 average players → expected win% (Pythagorean from ORtg/DRtg).
   Team B = replacement player + 4 average players → expected win%.
3. WARP = (Win%_A − Win%_B) × (player's share of team games/minutes)
```

**Glossary**
- **Replacement level**: production of a freely available player (G-League call-up, minimum contract).
- **Pythagorean expectation**: win% ≈ PTS^k / (PTS^k + PTS_allowed^k) with k = 14 in the NBA (see B8).
- **Linear weights**: fixed per-stat values, which WARP avoids.

**Usage**
- Rewards players who log heavy, healthy minutes above replacement level. Win units are intuitive and consistent over time.
- Can be expressed per minute (win% of the player + 4 average players team), by offense/defense, or as total value.
- **Limitations:** box-score based, so it misses untracked defense (e.g., Bruce Bowen types). It relies on assumptions about assist value, the usage/efficiency trade-off, and replacement level.

---

# Part 2: Basketball-Reference Glossary (Additional Terms)

These terms appear in the Basketball-Reference glossary but not among NBAstuffer's player metrics. Glossary entries that duplicate a Part 1 metric (AST%, BPM, DRtg, ORtg, eFG%, GmSc, PER, rebound %, STL%, TOV%, TS%, USG%, WS, WS/48, +/-, PProd, Stops, Per 36) are merged into those sections above.

---

## B1. Basic Box-Score Stats & Shooting Percentages

**Definition**
The counting stats and simple percentages that every other metric is built from.

**Formula**
| Stat | Meaning | Formula | Available since (NBA) |
|---|---|---|---|
| FG / FGA | Field goals / attempts (2s and 3s) | — | — |
| **FG%** | Field Goal Percentage | `FG / FGA` | — |
| 2P / 2PA | 2-point field goals / attempts | — | — |
| **2P%** | 2-Point FG Percentage | `2P / 2PA` | — |
| 3P / 3PA | 3-point field goals / attempts | — | 1979-80 |
| **3P%** | 3-Point FG Percentage | `3P / 3PA` | 1979-80 |
| FT / FTA | Free throws / attempts | — | — |
| **FT%** | Free Throw Percentage | `FT / FTA` | — |
| ORB / DRB | Offensive / defensive rebounds | — | 1973-74 |
| TRB | Total rebounds | `ORB + DRB` | 1950-51 |
| AST | Assists | — | — |
| STL / BLK | Steals / blocks | — | 1973-74 |
| TOV | Turnovers | — | 1977-78 |
| PF | Personal fouls | — | — |
| PTS | Points | `2×2P + 3×3P + FT` | — |
| MP | Minutes played | — | 1951-52 |

**Glossary**
- **"Available since"**: the first season the NBA officially tracked the stat. Metrics that need it (PER, BPM, WS) use estimates for earlier years.

**Usage**
- Inputs to every advanced metric. Always check the "available since" year before comparing across eras.
- FG% treats threes like twos. Use eFG% (#13) or TS% (#58) for efficiency comparisons.

---

## B2. Block Percentage (BLK%)

**Definition**
An estimate of the percentage of opponent **two-point** field goal attempts blocked by the player while he was on the floor.

**Formula** — **[Basketball-Reference]**
```
BLK% = 100 × (BLK × (Tm MP / 5)) / (MP × (Opp FGA − Opp 3PA))
```

**Glossary**
- **Opp FGA − Opp 3PA**: opponent two-point attempts. Threes are excluded because they are rarely blocked.
- **Tm MP / 5**: normalizes to the minutes the player was on the floor.

**Usage**
- Pace- and minutes-neutral rim-protection measure. Elite shot-blockers are ~5–8%+.
- Available since 1973-74. Pair with STL% (#53) and Personal Foul Efficiency (#31).

---

## B3. Possessions (Poss)

**Definition**
Basketball-Reference's estimate of team possessions. It averages estimates from both the team's and the opponent's stats for stability.

**Formula** — **[Basketball-Reference]**
```
Poss = 0.5 × ( [Tm FGA + 0.4 × Tm FTA − 1.07 × (Tm ORB / (Tm ORB + Opp DRB)) × (Tm FGA − Tm FG) + Tm TOV]
             + [Opp FGA + 0.4 × Opp FTA − 1.07 × (Opp ORB / (Opp ORB + Tm DRB)) × (Opp FGA − Opp FG) + Opp TOV] )
```

**Glossary**
- **0.4 × FTA**: possessions used by free-throw trips (B-Ref uses 0.4 here and 0.44 in TSA/USG%).
- **1.07 × ORB% × missed FG**: missed shots recovered by the offense, which do not end the possession.

**Usage**
- The denominator for every "per 100 possessions" stat (ORtg, DRtg, STL%, BPM).
- Available since 1973-74.

---

## B4. Pace Factor

**Definition**
An estimate of the number of possessions per 48 minutes by a team.

**Formula** — **[Basketball-Reference]**
```
Pace = 48 × ((Tm Poss + Opp Poss) / (2 × (Tm MP / 5)))
```
(40 minutes is used instead of 48 for the WNBA.)

**Glossary**
- **Tm MP / 5**: game minutes (includes overtime).

**Usage**
- Shows how fast a team plays. Used to pace-adjust PER (#32) and Win Shares (#64).
- Explains why per-game stats inflate on fast teams. Available since 1973-74.

---

## B5. True Shooting Attempts (TSA)

**Definition**
Shot attempts including the possession cost of free throws.

**Formula** — **[Basketball-Reference]**
```
TSA = FGA + 0.44 × FTA
```

**Glossary**
- **0.44**: the fraction of free-throw attempts that end a possession (excluding and-ones, technicals, and the 2nd/3rd FT of a trip).

**Usage**
- Denominator of TS% (`PTS / (2 × TSA)`, #58) and a measure of scoring volume.

---

## B6. Value Over Replacement Player (VORP)

**Definition**
A box-score estimate of the points per 100 **team** possessions that a player contributed above a replacement-level (−2.0) player, translated to an average team and prorated to an 82-game season.

**Formula** — **[Basketball-Reference]**
```
VORP = [BPM − (−2.0)] × (% of team possessions played) × (Team Games / 82)

Wins Over Replacement ≈ VORP × 2.70
```
*Example (B-Ref):* LeBron 2017: BPM +7.6, played 70% of minutes → (7.6 + 2.0) × 0.70 × 82/82 = **6.7 VORP**.

**Glossary**
- **Replacement level (−2.0)**: a minimum-salary player or one outside a normal rotation. The level was set after a discussion on Tom Tango's blog. (Component replacement levels would be −1.7 on offense and −0.3 on defense, but B-Ref does not publish OVORP or DVORP.)
- **BPM**: Box Plus/Minus (#5).

**Usage**
- Converts BPM (a rate) into total value (rate × playing time). It is a counting stat for MVP races and career value.
- Available since 1973-74.

---

## B7. Four Factors

**Definition**
Dean Oliver's "Four Factors of Basketball Success": the four things that decide games, each applied to offense and defense (eight factors in total).

**Formula** — **[Basketball-Reference]**
| Factor | Weight | Offense | Defense |
|---|---|---|---|
| Shooting | 40% | `eFG% = (FG + 0.5 × 3P) / FGA` | same, using opponent stats |
| Turnovers | 25% | `TOV% = TOV / (FGA + 0.44 × FTA + TOV)` | same, using opponent stats |
| Rebounding | 20% | `ORB% = ORB / (ORB + Opp DRB)` | `DRB% = DRB / (Opp ORB + DRB)` |
| Free Throws | 15% | `FT Rate = FT / FGA` | same, using opponent stats |

*Example (2004-05 Suns):* offense eFG% .534, TOV% .124, ORB% .275, FT/FGA .222; defense eFG% .478, TOV% .120, DRB% .683, FT/FGA .176.

**Glossary**
- **Weights**: Oliver's approximate importance of each factor in winning.
- **FT/FGA**: captures both getting to the line and converting there.

**Usage**
- Team diagnosis: why a team wins or loses and where to improve.
- Shooting matters most, then turnovers, rebounding, and free throws.

---

## B8. Pythagorean Wins / Losses

**Definition**
Expected wins based on points scored and allowed.

**Formula** — **[Basketball-Reference]**
```
W Pyth = G × (Tm PTS^14 / (Tm PTS^14 + Opp PTS^14))
L Pyth = G − W Pyth
```

**Glossary**
- **Exponent 14**: fit by logistic regression on log(Tm PTS / Opp PTS). Across all BAA/NBA/ABA seasons its RMSE is 3.14 wins, vs. 3.48 with the common exponent of 16.5. The WNBA uses 10.

**Usage**
- Teams that win more than W Pyth were probably lucky in close games and tend to regress.
- Used inside WARP (#65) and other win-conversion metrics.

---

## B9. Team Simple Rating System (SRS) & Strength of Schedule (SOS)

**Definition**
- **SRS**: a team rating that accounts for average point differential and strength of schedule, in points above/below average (0 = average).
- **SOS**: strength-of-schedule rating in points above/below average. Positive = harder than average schedule.

**Formula** — **[Basketball-Reference]** (method explained by Doug Drinen, Pro-Football-Reference)
```
SRS = MOV + SOS
SOS = average SRS of the opponents faced
(solved iteratively or as a system of linear equations across all teams)
```

**Glossary**
- **MOV**: Margin of Victory (B10).
- This is a **team** rating. It is different from Roland Beech's **player** SRS (#50).

**Usage**
- Power rankings and point-spread estimates. SRS difference ≈ expected margin on a neutral floor.

---

## B10. Margin of Victory (MOV)

**Definition**
Average point differential.

**Formula** — **[Basketball-Reference]**
```
MOV = PTS − Opp PTS        (per game)
```

**Glossary**
- **PTS / Opp PTS**: points scored / allowed per game.

**Usage**
- A better predictor of future wins than W-L record. It is the base of SRS (B9).

---

## B11. Won-Lost Percentage (W-L%) & Games Behind (GB)

**Definition**
Standard standings measures.

**Formula** — **[Basketball-Reference]**
```
W-L% = W / (W + L)
GB   = ((first W − W) + (L − first L)) / 2
```

**Glossary**
- **first W / first L**: wins and losses of the first-place team.
- **W / L**: wins / losses.

**Usage**
- Standings and playoff races.

---

## B12. Award Share

**Definition**
A player's share of the maximum possible award-voting points.

**Formula** — **[Basketball-Reference]**
```
Award Share = award points received / maximum possible award points
```
*Example:* Tim Duncan, 2002-03 MVP: 962 / 1190 = **0.81**.

**Glossary**
- **Award points**: weighted voting points (e.g., 1st-place votes worth more).
- Applies to **MVP**, **DPOY** (Defensive Player of the Year), **ROY** (Rookie of the Year), and **SMOY** (Sixth Man of the Year).

**Usage**
- Compares award support across years with different numbers of voters. Cumulative award shares measure career recognition.

---

## B13. Win Probability

**Definition**
The estimated probability that Team A will defeat Team B in a given matchup.

**Formula**
Model-based (typically from team ratings such as SRS, plus home court). Not specified in the glossary.

**Glossary**
- In-game win probability, which updates with score and time, underlies WPA (#62).

**Usage**
- Game predictions. Measuring how much a play swung a game (WPA).

---

## B14. Other Glossary Terms (Age, Year, G, GS, awards, prefixes)

| Term | Definition |
|---|---|
| **Age** | Player age on **January 31** of the given season |
| **Year** | The season's **ending** calendar year (1999-00 → 2000) |
| **G** | Games |
| **GS** | Games Started (available since 1982) |
| **W / L** | Wins / Losses |
| **Lg / Tm / Opp** | League / Team / Opponent prefixes |
| **MVP / DPOY / ROY / SMOY** | Most Valuable Player / Defensive Player of the Year / Rookie of the Year / Sixth Man of the Year |
| **OWS / DWS** | Offensive / Defensive Win Shares (#64) |
| **PProd** | Points Produced (#38) |
| **Stops** | Dean Oliver's individual defensive stops (#10, #11) |

**Usage**
- Age as of Jan. 31 and ending-year labeling are Basketball-Reference conventions. Match them when joining B-Ref data with other sources (e.g., NBA.com labels seasons as "2025-26").

---

*Sources: NBAstuffer Analytics 101 (nbastuffer.com/analytics-101/player-evaluation-metrics/), individual metric pages. Basketball-Reference glossary (basketball-reference.com/about/glossary.html) and articles: Calculating PER (/about/per.html), NBA Win Shares (/about/ws.html), Calculating Individual Offensive and Defensive Ratings (/about/ratings.html), Box Plus/Minus 2.0 (/about/bpm2.html), Four Factors (/about/factors.html). All retrieved 2026-09-25. Other supplemented formulas: RealGM (FIC), Dean Oliver's* Basketball on Paper*.*
