#!/usr/bin/env python3
"""Merge FFToday and ESPN 2026 WR/TE TD projections into a consensus CSV.

Sources disagree on name suffixes (Kyle Pitts / Kyle Pitts Sr.), punctuation
(D.J. Moore / DJ Moore), and team abbreviations (JAC / JAX), so both sides are
normalized to a common key before averaging.
"""

import csv
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
FFT = ROOT / "data" / "raw" / "fftoday_wr_te.txt"

TEAM_FIX = {"JAC": "JAX", "WSH": "WAS", "LARM": "LAR"}
SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "v"}


def norm(name):
    n = name.lower().replace(".", "").replace("'", "").replace("-", " ")
    parts = [p for p in re.split(r"\s+", n) if p and p not in SUFFIXES]
    return " ".join(parts)


def fix_team(t):
    return TEAM_FIX.get(t.upper(), t.upper())


def load_fft():
    rows = {}
    for line in FFT.read_text().splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        name, team, pos, td = [c.strip() for c in line.split("|")]
        rows[norm(name)] = {
            "name": name,
            "team": fix_team(team),
            "pos": pos,
            "rec_td": float(td),
            "rush_td": 0.0,
        }
    return rows


def load_espn():
    rows = {}
    for pos in ("WR", "TE"):
        out = subprocess.run(
            [sys.executable, str(ROOT / "fetch_espn.py"), pos],
            capture_output=True, text=True, check=True,
        ).stdout
        for line in out.splitlines():
            if not line.strip():
                continue
            name, team, p, rec, rush = [c.strip() for c in line.split("|")]
            rows[norm(name)] = {
                "name": name,
                "team": fix_team(team),
                "pos": p,
                "rec_td": float(rec.split()[1]),
                "rush_td": float(rush.split()[1]),
            }
    return rows


def main():
    fft, espn = load_fft(), load_espn()
    merged = []
    for key in set(fft) | set(espn):
        a, b = fft.get(key), espn.get(key)
        both = [x for x in (a, b) if x]
        ref = a or b
        rec = sum(x["rec_td"] for x in both) / len(both)
        rush = sum(x["rush_td"] for x in both) / len(both)

        if a and b:
            spread = abs(a["rec_td"] - b["rec_td"])
            conf = "HIGH" if spread <= 2 else "MEDIUM"
            src = "FFToday + ESPN"
            team = b["team"]
            if a["team"] != b["team"]:
                conf = "MEDIUM"
        else:
            conf = "LOW"
            src = "FFToday only" if a else "ESPN only"
            team = ref["team"]

        merged.append({
            "name": ref["name"], "team": team, "pos": ref["pos"],
            "pass_td": "", "rush_td": round(rush, 1) or "",
            "rec_td": round(rec, 1), "fg": "", "pat": "",
            "dst_td": "", "safety": "",
            "confidence": conf, "source": src, "notes": "",
        })

    merged.sort(key=lambda r: -(r["rec_td"] + (r["rush_td"] or 0)))
    cutoff = {"WR": 85, "TE": 32}
    kept, seen = [], {"WR": 0, "TE": 0}
    for r in merged:
        if seen[r["pos"]] < cutoff[r["pos"]]:
            seen[r["pos"]] += 1
            kept.append(r)

    out = ROOT / "data" / "players_wr_te.csv"
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(kept[0]))
        w.writeheader()
        w.writerows(kept)
    print(f"{seen['WR']} WR + {seen['TE']} TE -> {out}")
    both_n = sum(1 for r in kept if r["source"] == "FFToday + ESPN")
    print(f"  {both_n} confirmed by both sources, {len(kept) - both_n} single-source")


if __name__ == "__main__":
    main()
