#!/usr/bin/env python3
"""Re-anchor every touchdown projection to posted sportsbook numbers.

Why
---
The original board averaged fantasy projection sites. Those sites anchor their
top-of-board numbers on "if he finishes as the RB1" outcomes rather than on expected
values, and they have no budget constraint -- nothing stops the sum of their
projections from exceeding the touchdowns that will actually be scored.

This script replaces that with market data, in three tiers.

  TIER 1  A posted over/under on the exact quantity. ~134 of these exist across
          rushing, receiving and passing touchdowns. Used directly.
  TIER 2  No line on the player, but his team has a Vegas implied point total (all 32
          do). The team's points convert to a touchdown budget; whatever Tier 1 has
          not already claimed is shared among the rest by projected share.
  TIER 3  Defensive touchdowns, which no market prices at all. Left as the prior
          model estimate and labelled as such.

Reading a line correctly
------------------------
A line is not an expectation on its own. Jahmyr Gibbs' receiving touchdown line is 4.5
priced at +155 over / -185 under: the market is saying the under is far more likely, so
his expected total sits nearer 4.0 than 4.5. Taking the raw number would import a bias
the market has already priced out.

So each line is devigged into a true probability, then inverted through a Poisson
distribution to recover the mean. Poisson is an assumption -- but it is the standard
model for counts of independent scoring events, and it is applied uniformly rather than
tuned per player, which is the property the previous reliability factors lacked.
"""

import argparse
import csv
import json
import math
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).parent
GAMES = 17

# Points that follow a touchdown, per touchdown: extra points made plus the occasional
# two-point conversion, net of misses. Prices a touchdown at (6 + PAT_PER_TD).
PAT_PER_TD = 0.94

# Trims the small share of rushing touchdowns that leaks to players too deep to rank.
# Scales every rusher equally, so it moves levels but cannot reorder anyone.
RUSH_LEAKAGE = 0.95

STAT_FIELDS = ["pass_td", "rush_td", "rec_td", "fg", "pat", "dst_td", "safety"]
MARKET = {"rushing_td": "rush_td", "receiving_td": "rec_td", "passing_td": "pass_td"}


def norm(n):
    n = unicodedata.normalize("NFKD", n).encode("ascii", "ignore").decode()
    n = n.lower().replace(".", "").replace("'", "").replace("-", " ")
    n = re.sub(r"\b(jr|sr|ii|iii|iv)\b", "", n)
    return re.sub(r"\s+", " ", n).strip()


def implied(american):
    """American odds -> implied probability, vig still included."""
    a = float(american)
    return 100.0 / (a + 100.0) if a > 0 else -a / (-a + 100.0)


def poisson_sf(lam, k):
    """P(X >= k) for Poisson(lam)."""
    if k <= 0:
        return 1.0
    cdf = sum(math.exp(-lam) * lam ** i / math.factorial(i) for i in range(k))
    return 1.0 - cdf


def line_to_mean(line, over_odds, under_odds):
    """Devig a two-way total, then solve Poisson for the mean that reproduces it.

    Lines are posted on half-points, so "over 4.5" is exactly "5 or more" and there is
    no push to handle.

    A handful of rows in the feed carry a line but no price. Those fall back to an even
    market, which recovers a mean near the line itself -- the same thing taking the raw
    line would have done, so nothing is invented.
    """
    try:
        po, pu = implied(over_odds), implied(under_odds)
        p_over = po / (po + pu)
    except (ValueError, TypeError, ZeroDivisionError):
        p_over = 0.5
    k = int(math.ceil(line))

    lo, hi = 0.01, 60.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if poisson_sf(mid, k) < p_over:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def load_props():
    """Collect every posted line, devig it, and average across books per player."""
    acc = defaultdict(list)
    meta = {}
    for path in (ROOT / "data/vegas_td_props_2026.csv",
                 ROOT / "data/raw/vegas/passing_td_props.csv"):
        if not path.exists():
            continue
        for r in csv.DictReader(open(path, encoding="utf-8")):
            cat = MARKET.get(r["market"])
            if not cat:
                continue
            lam = line_to_mean(float(r["line"]), r["over_odds"], r["under_odds"])
            key = (norm(r["player"]), cat)
            acc[key].append(lam)
            meta.setdefault(key, []).append(f"{r['sportsbook']} {r['line']}")

    props = {k: sum(v) / len(v) for k, v in acc.items()}
    return props, meta


def load_csv(path):
    rows = list(csv.DictReader(open(path, newline="", encoding="utf-8")))
    for r in rows:
        for f in STAT_FIELDS:
            r[f] = float(r[f]) if (r.get(f) or "").strip() else 0.0
        for f in ("team", "name"):
            r[f] = r[f].strip()
        r["pos"] = r["pos"].strip().upper()
        r["key"] = norm(r["name"])
    return rows


def team_budgets(rows, vegas, props):
    """Turn each team's implied points into touchdown and field-goal budgets.

    points = (6 + PAT_PER_TD) * offensive TDs + 3 * FGM + defensive/return scoring

    Defensive scoring comes out first: a pick-six counts toward a team's implied points
    but is not an offensive touchdown, and leaving it in would inflate every skill
    player on the roster.

    The pass/run split comes from the projections' ratio, not from the quarterbacks'
    posted lines. Deriving it from the lines was tried and abandoned: a team's ranked
    quarterbacks do not necessarily account for its whole season. Arizona's only ranked
    quarterback is Jacoby Brissett at 11.5 passing touchdowns, a bridge-starter number,
    so treating that as the team's entire passing output left roughly nineteen rushing
    touchdowns to hand out and inflated backup Tyler Allgeier to 9.5.

    A quarterback's own posted line still prices that quarterback. It just no longer
    dictates what the rest of his offense is allowed to do.
    """
    fgm = {r["team"]: r["fg"] for r in rows if r["pos"] == "K"}
    dst = {r["team"]: (r["dst_td"], r["safety"]) for r in rows if r["pos"] == "DST"}

    proj = defaultdict(lambda: [0.0, 0.0])
    for r in rows:
        if r["pos"] in ("QB", "RB", "WR", "TE"):
            proj[r["team"]][0] += r["pass_td"]
            proj[r["team"]][1] += r["rush_td"]

    out, warn = {}, []
    for tm, v in vegas.items():
        pts = v["ppg"] * GAMES
        d_td, d_saf = dst.get(tm, (2.8, 0.4))
        g = fgm.get(tm, 29.6)
        offensive_pts = pts - d_td * (6 + PAT_PER_TD) - d_saf * 2
        td = (offensive_pts - 3 * g) / (6 + PAT_PER_TD)

        pp, pr = proj[tm]
        share = pp / (pp + pr) if (pp + pr) else 0.62
        p = td * share

        out[tm] = {"points": round(pts, 1), "fgm": g, "td": td,
                   "pass_td": p, "rush_td": max(0.0, td - p)}
    return out, warn


def allocate(rows, budgets, props):
    by_team = defaultdict(list)
    for r in rows:
        by_team[r["team"]].append(r)

    for tm, players in by_team.items():
        b = budgets.get(tm)
        if not b:
            continue
        group = [p for p in players if p["pos"] in ("QB", "RB", "WR", "TE")]

        # Denominator for receiving is the team's projected PASSING total. Every passing
        # touchdown is also a receiving touchdown, so that figure counts the unranked
        # bench too -- which stops a thin roster from absorbing a whole team's share.
        # An earlier version used one league-wide coverage constant and a backup Miami
        # tight end gained four touchdowns, because the Dolphins have three ranked
        # receivers and no wide receiver at all.
        denom = {
            "rush_td": sum(p["rush_td"] for p in group) / RUSH_LEAKAGE,
            "rec_td": sum(p["pass_td"] for p in group),
            "pass_td": sum(p["pass_td"] for p in group),
        }

        for cat in ("rush_td", "rec_td", "pass_td"):
            pool = b[cat] if cat != "rec_td" else b["pass_td"]
            elig = [p for p in group if p["pos"] == "QB"] if cat == "pass_td" else group

            pinned = {p["name"]: props[(p["key"], cat)]
                      for p in elig if (p["key"], cat) in props}
            fixed = sum(pinned.values())
            base = denom[cat] - sum(p[cat] for p in elig if p["name"] in pinned)
            left = max(0.0, pool - fixed)

            for p in elig:
                if p["name"] in pinned:
                    p[cat + "_new"] = pinned[p["name"]]
                elif base > 1e-9:
                    p[cat + "_new"] = left * p[cat] / base
                else:
                    p[cat + "_new"] = 0.0

        # Kicker extra points now fall out of the team's touchdown budget rather than
        # being projected on their own, so the kicker and the offense can no longer
        # disagree about how often the team reached the end zone.
        for p in players:
            if p["pos"] == "K":
                p["fg_new"] = b["fgm"]
                p["pat_new"] = b["td"] * PAT_PER_TD


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--players", default="data/players.csv")
    ap.add_argument("--out", default="data/players_vegas.csv")
    args = ap.parse_args()

    rows = load_csv(ROOT / args.players)
    vegas = json.loads((ROOT / "data/raw/vegas/team_totals.json").read_text())["teams"]
    props, meta = load_props()

    n_by_cat = defaultdict(int)
    for (_, cat) in props:
        n_by_cat[cat] += 1
    print("posted lines devigged -> Poisson means: "
          + ", ".join(f"{v} {k}" for k, v in sorted(n_by_cat.items())))

    budgets, warn = team_budgets(rows, vegas, props)
    for w in warn:
        print("  ! " + w)

    before = {r["name"]: (r["pass_td"], r["rush_td"], r["rec_td"]) for r in rows}
    allocate(rows, budgets, props)

    matched = set()
    for r in rows:
        for cat in ("pass_td", "rush_td", "rec_td", "fg", "pat"):
            if cat + "_new" in r:
                r[cat] = round(r[cat + "_new"], 2)
                del r[cat + "_new"]
        hits = [c for c in ("pass_td", "rush_td", "rec_td") if (r["key"], c) in props]
        if hits:
            matched.add(r["name"])
            bits = "; ".join(meta[(r["key"], c)][0] for c in hits)
            r["source"] = f"POSTED LINE ({bits})"
            r["confidence"] = "HIGH"
        elif r["pos"] == "DST":
            r["source"] = "Model est. -- no market prices defensive TDs"
            r["confidence"] = "LOW"
        elif r["pos"] == "K":
            r["source"] = "Vegas team total -> FG/XP budget"
        else:
            r["source"] = "Vegas team budget, share from projections"
        del r["key"]

    print(f"{len(matched)} players priced by a real posted line; "
          f"{len(rows) - len(matched)} allocated from team budgets")

    fields = [f for f in rows[0].keys()]
    with open(ROOT / args.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    tot = sum(r["pass_td"] + r["rush_td"] for r in rows)
    print(f"league offensive TD budget: {sum(b['td'] for b in budgets.values()):.0f}")
    print(f"wrote {ROOT / args.out}")

    moved = sorted(((r["pass_td"] + r["rush_td"] + r["rec_td"] - sum(before[r["name"]]), r)
                    for r in rows if r["pos"] not in ("DST", "K")), key=lambda x: x[0])
    print("\nbiggest downgrades:")
    for d, r in moved[:10]:
        print(f"  {r['pos']:<3}{r['name']:<24}{r['team']:<4}{d:+6.1f} TD")
    print("biggest upgrades:")
    for d, r in moved[-10:][::-1]:
        print(f"  {r['pos']:<3}{r['name']:<24}{r['team']:<4}{d:+6.1f} TD")


if __name__ == "__main__":
    main()
