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

**Live board: https://jackmacdorman.github.io/td-fg-fantasy-rankings/**

**`index.html`** (also written as `draft-board.html`) — single self-contained file for use
*during* the draft, published to GitHub Pages at the link above. Click a
row to cross a player off; the ✓ button assigns him to your roster instead. State lives
in localStorage, so a reload or an accidental tab close doesn't lose the draft. Undo,
reset, hide-drafted, position filters, search (`/` to focus), sortable columns, a
best-available chip per position, and a roster tracker counting your picks against the
starting requirements.

The **★ Flagged** filter is the one worth knowing about. Sleepers in this format tend to
rank badly on the board itself — Sean Tucker is #265 — because a low projected TD total
is exactly what makes a player cheap. Scrolling will never surface them mid-draft; the
filter will.

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
(129 points for a replacement-level K), so the K1-to-K12 gap looks like a first-round
edge — but kickers have the *flattest* spread relative to their baseline of any position
(K1 is 1.20× replacement, versus 2.23× for RB) and almost no year-over-year predictive
power. Most of that apparent edge is noise.

So each position's VOR is multiplied by a **reliability factor**:

| QB | RB | WR | TE | K | DST |
|---|---|---|---|---|---|
| 0.60 | 0.60 | 0.60 | 0.60 | 0.35 | 0.20 |

The four skill positions share one number because they share one source — every offensive
projection now traces to a posted line or to a Vegas team total (see **Where the numbers
come from** below). There is no basis for trusting a running back's level more than a wide
receiver's, so the earlier 0.65/0.60/0.55 spread was collapsed; it encoded a belief about
which projection feed ran hottest, which is precisely what the re-anchoring removed.

K and DST keep a discount because they are the two things no market prices. That much is a
fact about the pipeline. The *size* of the discount is still judgment, chosen to roughly
preserve how the previous board treated kickers.

They are editable on the Settings tab; set them all to 1.00 to see raw VOR. Doing so pulls
K1 to #12 overall, which is the failure mode the factors exist to prevent. Note that the
top 8 of the board is identical under every setting tried — the factors only begin to bite
from #9 down.

## Rebuilding

```bash
python3 fetch_espn.py WR TE     # pull ESPN 2026 projections
python3 merge_wr_te.py          # merge with FFToday into consensus
python3 vegas_anchor.py         # re-anchor TD levels to market -> data/players_vegas.csv
python3 rank.py --players data/players_vegas.csv --teams 12   # -> data/board.json
python3 build_xlsx.py           # render the workbook
python3 build_html.py           # render draft-board.html
```

Skipping `vegas_anchor.py` and ranking `data/players.csv` directly gives the old
projection-consensus board, which is a useful thing to diff against but is not what the
shipped board is built from.

`build_html.py` imports the Sleepers and Traps lists from `build_xlsx.py` so the two
outputs can't drift apart — edit the notes in one place.

`data/players.csv` is the combined input, concatenated from the per-position files. Edit it
directly and re-run from `vegas_anchor.py` onward — editing `data/players_vegas.csv` instead
works but will be overwritten on the next anchor run.

## Where the numbers come from

Every offensive touchdown total on this board is anchored to market data by
`vegas_anchor.py`. The projection consensus still sets each player's *share* of his
offense, but it no longer sets the *level*.

The problem it fixes: projection sites anchor their top-of-board numbers on "if he
finishes as the RB1" outcomes, and nothing constrains the sum of their projections to the
touchdowns that will actually be scored. There is no budget. Vegas has one.

Three tiers, and the `source` column on every row names which one applies:

- **TIER 1 — a posted line on the exact quantity.** 123 players. The line is devigged into
  a true probability and inverted through a Poisson to recover the mean. A line is not an
  expectation on its own: Gibbs' receiving line of 4.5 is priced +155 over / −185 under,
  so the market's own number is nearer 4.0 than 4.5, and taking the raw line would import a
  bias the market has already priced out.
- **TIER 2 — no line on the player, but his team has an implied point total.** 165 players.
  All 32 teams have one. Points convert to a touchdown budget; whatever Tier 1 has not
  claimed is shared out by projected share.
- **TIER 3 — unpriced.** Defensive touchdowns, which no market quotes at all. Left as the
  prior model estimate and labelled `LOW` confidence.

The league-wide budget lands at **1,307 offensive TDs**, against an NFL actual in the
1,270–1,300 band. The pass/rush split is 780/475 versus roughly 780/470 actual.

**Vegas coverage is much better than this README previously claimed.** An earlier version
of this file asserted that *zero* QB rushing-TD props exist at any book and called it the
largest uncertainty on the board. That was wrong. They exist at five books, listed under
the market name "Total Rushing Touchdowns," where quarterbacks appear alongside running
backs. The board now carries 30 passing, 66 receiving and 37 rushing posted lines.

Two things are still **not** market-anchored, and should be read accordingly:

- **Kicker field goals are a CBS projection passed through untouched.** The FGM number is
  read from the existing kicker rows, used to subtract field-goal points from the team's
  budget, and handed straight back out. Only the extra points are newly derived, and those
  now fall out of the team's touchdown budget so the kicker and the offense can no longer
  disagree about how often the team reached the end zone.
- **D/ST is a model estimate** — three-year defensive TD history regressed 50% to the mean,
  plus a returner-quality adjustment.

Player *shares* (not levels) come from a consensus of ESPN (Mike Clay), FFToday, Razzball,
Yahoo, CBS, Footballguys and FantasyPros, cross-checked against 2026 depth charts. See
`RESEARCH.md` for full findings and the `Sources` tab for per-category detail.

Known gaps: no 2026 red zone TD% table (all sources blocked), no projection for
A.J. Dillon (CAR), and Nick Chubb could not be located on any 2026 roster.
