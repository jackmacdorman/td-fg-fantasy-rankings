#!/usr/bin/env python3
"""Rank players for a TD/FG-only fantasy league and emit a draft board."""

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

SCORING = {
    "pass_td": 3,
    "rush_td": 6,
    "rec_td": 6,
    "fg": 3,
    "pat": 1,
    "dst_td": 6,
    "safety": 2,
}

STARTERS = {"QB": 1, "RB": 2, "WR": 2, "TE": 1, "DST": 1, "K": 1}

# How much of a projected edge at each position actually shows up in reality.
# Raw VOR treats every projected point as equally trustworthy, which badly
# overrates kickers and defenses: their projections have a very high floor but
# almost no year-over-year predictive power, so most of their apparent spread is
# noise. These are judgment-based, not fitted from data -- tune them and re-run.
RELIABILITY = {
    "QB": 0.65,
    "RB": 0.60,
    "WR": 0.55,
    "TE": 0.55,
    "K": 0.35,
    "DST": 0.20,
}

STAT_FIELDS = list(SCORING)


def load_players(path):
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    players = []
    for row in rows:
        player = {
            "name": row["name"].strip(),
            "team": row["team"].strip(),
            "pos": row["pos"].strip().upper(),
            "confidence": row.get("confidence", "").strip().upper(),
            "notes": row.get("notes", "").strip(),
            "source": row.get("source", "").strip(),
        }
        for field in STAT_FIELDS:
            raw = (row.get(field) or "").strip()
            player[field] = float(raw) if raw else 0.0
        player["points"] = round(
            sum(player[f] * w for f, w in SCORING.items()), 2
        )
        players.append(player)
    return players


def replacement_levels(players, teams):
    """Baseline = mean of the players just past the last startable slot.

    Averaging a small window instead of taking a single player keeps one noisy
    projection from swinging every VOR number at that position.
    """
    levels = {}
    by_pos = defaultdict(list)
    for p in players:
        by_pos[p["pos"]].append(p)

    for pos, starters in STARTERS.items():
        ranked = sorted(by_pos[pos], key=lambda p: -p["points"])
        last_starter = teams * starters
        window = ranked[last_starter : last_starter + max(1, teams // 2)]
        if not window:
            window = ranked[-1:] or [{"points": 0.0}]
        levels[pos] = sum(p["points"] for p in window) / len(window)
    return levels


def rank(players, teams):
    levels = replacement_levels(players, teams)
    for p in players:
        p["replacement"] = round(levels.get(p["pos"], 0.0), 2)
        p["vor"] = round(p["points"] - p["replacement"], 2)
        p["adj_vor"] = round(p["vor"] * RELIABILITY.get(p["pos"], 0.5), 2)

    for pos in STARTERS:
        ranked = sorted(
            (p for p in players if p["pos"] == pos), key=lambda p: -p["points"]
        )
        for i, p in enumerate(ranked, 1):
            p["pos_rank"] = f"{pos}{i}"

    board = sorted(players, key=lambda p: -p["adj_vor"])
    for i, p in enumerate(board, 1):
        p["overall_rank"] = i

    raw = sorted(players, key=lambda p: -p["vor"])
    for i, p in enumerate(raw, 1):
        p["raw_rank"] = i
    return board, levels


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--players", default="data/players.csv")
    ap.add_argument("--teams", type=int, default=12)
    ap.add_argument("--out", default="data/board.json")
    args = ap.parse_args()

    players = load_players(args.players)
    board, levels = rank(players, args.teams)

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(
            {"teams": args.teams, "replacement": levels, "players": board},
            fh,
            indent=2,
        )

    print(f"{len(board)} players ranked -> {args.out}")
    for pos, level in sorted(levels.items()):
        print(f"  replacement {pos}: {level:.2f} pts")
    print()
    for p in board[:20]:
        print(
            f"{p['overall_rank']:>3}. {p['pos_rank']:<5} {p['name']:<24}"
            f" {p['team']:<4} {p['points']:>6.1f} pts  adjVOR {p['adj_vor']:>6.1f}"
            f"  (raw #{p['raw_rank']})"
        )


if __name__ == "__main__":
    main()
