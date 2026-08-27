# TD/FG-Only Fantasy Draft Board — 2026

Rankings for a touchdown-and-field-goal-only fantasy league. Nothing else scores:
no yardage, no receptions, no sacks, no points allowed.

| Event | Points |
|---|---|
| Passing TD | 3 |
| Rushing TD | 6 |
| Receiving TD | 6 |
| Field goal (any distance) | 3 |
| Extra point | 1 |
| Def/ST TD | 6 |
| Safety | 2 |

Roster: 1 QB, 2 RB, 2 WR, 1 TE, 1 K, 1 D/ST · 12 teams.

## Output

**`2026 TD-FG League Draft Board.xlsx`** — 12 tabs: overall board, one per position,
plus Strategy, Sleepers, Traps, Sources, and Settings.

Points and VOR are live formulas pointing at the Settings tab, so editing a projection
or a scoring weight re-ranks the sheet. Blue cells are inputs; black cells are formulas.

## How ranking works

Players are ranked by **adjusted value over replacement**, not raw projected points.

Replacement level is the mean of the players just past the last startable slot at each
position (12 teams × starters). Averaging a small window instead of taking a single
player keeps one noisy projection from swinging every VOR number.

Raw VOR alone badly overrates kickers and defenses. A kicker's floor is enormous
(~132 points for a replacement-level K), so the K1-to-K12 gap looks like a first-round
edge — but kickers have the *flattest* spread relative to their baseline of any position
(1.27× replacement, versus 2.26× for RB) and almost no year-over-year predictive power.
Most of that apparent edge is noise.

So each position's VOR is multiplied by a **reliability factor** — a judgment estimate of
how much of a projected edge actually shows up in reality:

| QB | RB | WR | TE | K | DST |
|---|---|---|---|---|---|
| 0.65 | 0.60 | 0.55 | 0.55 | 0.35 | 0.20 |

These are not fitted from data. They are editable on the Settings tab; set them all to
1.00 to see raw VOR. The effect is to move K1 from #4 overall to #17 — still far earlier
than a normal league, but not a first-round pick.

## Rebuilding

```bash
python3 fetch_espn.py WR TE     # pull ESPN 2026 projections
python3 merge_wr_te.py          # merge with FFToday into consensus
python3 rank.py --teams 12      # score + rank -> data/board.json
python3 build_xlsx.py           # render the workbook
```

`data/players.csv` is the combined input, concatenated from the per-position files.
Edit it directly and re-run `rank.py` to adjust projections.

## Data provenance

See `RESEARCH.md` for the full findings and `Sources` tab in the workbook for
per-category detail. Short version:

- **Vegas coverage is thin.** Nine real RB rushing-TD lines, three RB receiving-TD props,
  four QB passing-TD lines. **Zero QB rushing-TD props exist at any book** — the largest
  single uncertainty here, since rushing TDs carry most of a mobile QB's value.
- **QB/RB/WR/TE** come from a consensus of ESPN (Mike Clay), FFToday, Razzball, Yahoo,
  CBS, Footballguys, and FantasyPros, cross-checked against 2026 depth charts.
- **Kickers** use CBS 2026 FGM/XPM projections plus 2025 team FG attempts as a
  red-zone-stalling proxy.
- **D/ST numbers are a model estimate, not sourced** — three-year defensive TD history
  regressed 50% to the mean, plus a returner-quality adjustment.

Known gaps: no 2026 red zone TD% table (all sources blocked), no projection for
A.J. Dillon (CAR), and Nick Chubb could not be located on any 2026 roster.
