#!/usr/bin/env python3
"""Score the actual 2025 season under this league's rules, as a reality check.

Why
---
Every other number on this board is a forecast. This one is not: it is what each
player actually did last year, scored under our own settings, so a projection can be
read against a result rather than only against other projections.

It is expressed as a per-game rate multiplied out to a full season, which normalises
for injury -- a back who missed half of 2025 is measured on the games he played, not
punished for the ones he missed.

Sources
-------
nflverse, which is the public, play-by-play-derived dataset the analytics community
uses. Two files:

  stats_player_reg_2025.csv   per-player regular season totals
  play_by_play_2025.csv.gz    every play, used only for defensive/return scoring

Both are cached under data/raw/nflverse/ on first run.

Why defensive scoring comes from play-by-play
---------------------------------------------
The player file carries `def_tds` and `fumble_recovery_tds` as separate columns, and
they overlap: two cornerbacks are credited in both. It also credits fumble-recovery
touchdowns to offensive players -- Tyler Lockett has one -- which are not defensive
scores at all. Summing those columns would double-count some teams and inflate others.

Play-by-play settles it with one unambiguous rule: a touchdown belongs to a team's
defence/special teams when the team that scored it was not the team on offence. That
captures interception returns, fumble returns, punt and kickoff returns, and blocked
kicks, and it cannot double-count, because each play scores at most once.
"""

import argparse
import csv
import gzip
import re
import unicodedata
import urllib.request
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).parent
RAW = ROOT / "data" / "raw" / "nflverse"

BASE = "https://github.com/nflverse/nflverse-data/releases/download"
FILES = {
    "stats_player_reg_2025.csv": f"{BASE}/stats_player/stats_player_reg_2025.csv",
    "play_by_play_2025.csv.gz": f"{BASE}/pbp/play_by_play_2025.csv.gz",
}

# Must mirror SCORING in rank.py. Imported rather than restated so the 2025 column and
# the projection column can never drift into scoring the same event differently.
from rank import SCORING

# Games to extrapolate a per-game rate over.
#
# NOTE: the projections this column sits beside are built on a 17-game season -- that is
# what the Vegas implied team totals in data/raw/vegas/team_totals.json are quoted over,
# and what vegas_anchor.py uses. Setting this to 18 therefore makes the 2025 column about
# 5.9% larger than a like-for-like comparison would be. It is 18 because that is what was
# asked for; change it to 17 to compare the two columns on equal footing.
GAMES_FORWARD = 18

# Real people whose name is spelled differently in the two sources. Deliberately tiny:
# every other near-miss checked turned out to be two different players who happen to
# share a surname (Jonathon Brooks vs Chris Brooks, Antonio Williams vs Jameson
# Williams), and mapping those would have silently attributed one man's season to another.
ALIASES = {
    "chigoziem okonkwo": "chig okonkwo",
    "andres borregales": "andy borregales",
}


def norm(n):
    n = unicodedata.normalize("NFKD", n).encode("ascii", "ignore").decode()
    n = n.lower().replace(".", "").replace("'", "").replace("-", " ")
    n = re.sub(r"\b(jr|sr|ii|iii|iv)\b", "", n)
    n = re.sub(r"\s+", " ", n).strip()
    return ALIASES.get(n, n)


def fetch(name):
    path = RAW / name
    if path.exists():
        return path
    RAW.mkdir(parents=True, exist_ok=True)
    print(f"  downloading {name} ...")
    urllib.request.urlretrieve(FILES[name], path)
    return path


def num(row, key):
    v = row.get(key)
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def player_actuals():
    """Per-player 2025 totals, keyed by (normalised name, position).

    Keyed on position as well as name because the season file contains eight pairs of
    distinct players sharing a name, two of them at positions this board ranks: a
    Michael Carter at RB and another at CB, a DJ Turner at WR and another at CB.
    """
    out = {}
    with open(fetch("stats_player_reg_2025.csv"), encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            key = (norm(r["player_display_name"]), r["position"])
            if not key[0]:
                continue
            games = num(r, "games")
            if games <= 0:
                continue
            # Only the categories the projections also carry, so the two columns are
            # comparable. A wide receiver's punt-return touchdown is deliberately
            # excluded here: it is scored to the D/ST side of this board, and counting
            # it for him too would score one play twice.
            pts = (num(r, "passing_tds") * SCORING["pass_td"]
                   + num(r, "rushing_tds") * SCORING["rush_td"]
                   + num(r, "receiving_tds") * SCORING["rec_td"]
                   + num(r, "fg_made") * SCORING["fg"]
                   + num(r, "pat_made") * SCORING["pat"])
            out[key] = {"games": games, "points": pts, "team": r["recent_team"]}
    return out


def team_actuals():
    """Per-team 2025 defensive and special-teams scoring, from play-by-play."""
    td, saf = defaultdict(float), defaultdict(float)
    # Every team that took a snap, so that a defence which scored nothing all
    # year is recorded as a real 0.0 rather than dropping out of the file and
    # reading as missing data. In 2025 that is Kansas City and Green Bay: two of
    # the thirty-two returned no non-offensive touchdown and no safety.
    seen = set()
    with gzip.open(fetch("play_by_play_2025.csv.gz"), "rt", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r.get("season_type") != "REG":
                continue
            if r.get("posteam"):
                seen.add(r["posteam"])
            if (r.get("touchdown") == "1" and r.get("td_team")
                    and r.get("posteam") and r["td_team"] != r["posteam"]):
                td[r["td_team"]] += 1
            if r.get("safety") == "1" and r.get("defteam"):
                saf[r["defteam"]] += 1
    return {t: {"games": 17.0,
                "points": td[t] * SCORING["dst_td"] + saf[t] * SCORING["safety"],
                "td": td[t], "safety": saf[t]}
            for t in seen | set(td) | set(saf)}


# nflverse team codes that differ from the board's.
TEAM_FIX = {"LA": "LAR", "LAR": "LAR", "WSH": "WAS", "SL": "LAR", "OAK": "LV",
            "SD": "LAC", "STL": "LAR", "ARZ": "ARI", "BLT": "BAL", "CLV": "CLE",
            "HST": "HOU"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/actual_2025.csv")
    args = ap.parse_args()

    print("2025 actuals, scored under this league's settings:")
    players = player_actuals()
    teams = team_actuals()
    print(f"  {len(players)} players with 2025 snaps, {len(teams)} team defenses")

    rows = []
    for (name, pos), v in sorted(players.items()):
        ppg = v["points"] / v["games"]
        rows.append({"key": name, "pos": pos,
                     "team": TEAM_FIX.get(v["team"], v["team"]),
                     "games": int(v["games"]), "points_2025": round(v["points"], 1),
                     "ppg_2025": round(ppg, 3),
                     "exp_2025": round(ppg * GAMES_FORWARD, 1)})
    for t, v in sorted(teams.items()):
        ppg = v["points"] / v["games"]
        rows.append({"key": TEAM_FIX.get(t, t), "pos": "DST",
                     "team": TEAM_FIX.get(t, t),
                     "games": 17, "points_2025": round(v["points"], 1),
                     "ppg_2025": round(ppg, 3),
                     "exp_2025": round(ppg * GAMES_FORWARD, 1)})

    out = ROOT / args.out
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"  wrote {out} ({len(rows)} rows, rate x{GAMES_FORWARD} games)")

    top = sorted(rows, key=lambda r: -r["exp_2025"])[:8]
    print(f"\n  highest 2025 rate, extrapolated to {GAMES_FORWARD} games:")
    for r in top:
        print(f"    {r['pos']:<4}{r['key']:<24}{r['points_2025']:>6.0f} pts in "
              f"{r['games']:>2} g  ->{r['exp_2025']:>7.1f}")


if __name__ == "__main__":
    main()
