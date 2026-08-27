#!/usr/bin/env python3
"""Pull ESPN's 2026 season projections as an independent second source.

ESPN exposes raw per-stat-ID numbers. We read those directly rather than any
friendly-name mapping, because the espn_api library's PLAYER_STATS_MAP collides
several distinct stat IDs onto the same key and silently corrupts yardage.
"""

import json
import sys
import urllib.request

URL = (
    "https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/2026"
    "/segments/0/leaguedefaults/3?view=kona_player_info"
)

# Raw ESPN stat IDs, cross-checked against league scoring formats.
RUSH_TD, REC_TD, PASS_TD = "25", "43", "4"

POS = {1: "QB", 2: "RB", 3: "WR", 4: "TE", 5: "K", 16: "DST"}

TEAMS = {
    1: "ATL", 2: "BUF", 3: "CHI", 4: "CIN", 5: "CLE", 6: "DAL", 7: "DEN",
    8: "DET", 9: "GB", 10: "TEN", 11: "IND", 12: "KC", 13: "LV", 14: "LAR",
    15: "MIA", 16: "MIN", 17: "NE", 18: "NO", 19: "NYG", 20: "NYJ", 21: "PHI",
    22: "ARI", 23: "PIT", 24: "LAC", 25: "SF", 26: "SEA", 27: "TB", 28: "WAS",
    29: "CAR", 30: "JAX", 33: "BAL", 34: "HOU",
}

filters = {"players": {"limit": 1200, "sortPercOwned": {"sortAsc": False, "sortPriority": 1}}}
req = urllib.request.Request(
    URL,
    headers={
        "X-Fantasy-Filter": json.dumps(filters),
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
    },
)

with urllib.request.urlopen(req, timeout=60) as resp:
    data = json.load(resp)

out = []
for entry in data.get("players", []):
    p = entry.get("player") or {}
    pos = POS.get(p.get("defaultPositionId"))
    if not pos:
        continue
    proj = None
    for s in p.get("stats", []):
        # statSourceId 1 = projected, statSplitTypeId 0 = full season
        if (
            s.get("seasonId") == 2026
            and s.get("statSourceId") == 1
            and s.get("statSplitTypeId") == 0
        ):
            proj = s.get("stats", {})
            break
    if not proj:
        continue
    out.append(
        {
            "name": p.get("fullName"),
            "team": TEAMS.get(p.get("proTeamId"), "FA"),
            "pos": pos,
            "pass_td": round(proj.get(PASS_TD, 0) or 0, 1),
            "rush_td": round(proj.get(RUSH_TD, 0) or 0, 1),
            "rec_td": round(proj.get(REC_TD, 0) or 0, 1),
        }
    )

want = set(sys.argv[1:]) or {"WR", "TE"}
rows = [r for r in out if r["pos"] in want]
rows.sort(key=lambda r: -(r["rec_td"] + r["rush_td"] + r["pass_td"]))

print(f"# {len(rows)} players ({', '.join(sorted(want))})", file=sys.stderr)
for r in rows:
    print(
        f"{r['name']} | {r['team']} | {r['pos']} | "
        f"rec {r['rec_td']} | rush {r['rush_td']}"
    )
