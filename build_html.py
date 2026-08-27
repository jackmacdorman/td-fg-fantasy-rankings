#!/usr/bin/env python3
"""Render an interactive draft board to a single self-contained HTML file.

Reuses board.json and the curated sleeper/trap notes from build_xlsx so the
HTML and the spreadsheet can never drift apart.
"""

import json
from pathlib import Path

from build_xlsx import SLEEPERS, TRAPS

ROOT = Path(__file__).parent
BOARD = json.loads((ROOT / "data" / "board.json").read_text())

STARTERS = {"QB": 1, "RB": 2, "WR": 2, "TE": 1, "K": 1, "DST": 1}

tags = {}
for kind, group in (("sleeper", SLEEPERS), ("trap", TRAPS)):
    for name, _tm, _pos, why in group:
        # A few notes cover a shared backfield ("Kyren Williams / Blake Corum"),
        # which matches no single player row -- tag each name individually.
        for part in name.split(" / "):
            tags[part.strip()] = {"kind": kind, "why": why}

players = []
for p in BOARD["players"]:
    tag = tags.get(p["name"])
    players.append({
        "r": p["overall_rank"],
        "pr": p["pos_rank"],
        "n": p["name"],
        "t": p["team"],
        "p": p["pos"],
        # Category splits, grouped by what they pay rather than by how they were
        # scored: passing TDs are the 3-point bucket, everything else that reaches
        # the end zone is the 6-point bucket -- including D/ST return TDs, which
        # belong with rush/rec for a defense the same way a rushing TD does for a QB.
        "ptd": round(p["pass_td"], 1),
        "td": round(p["rush_td"] + p["rec_td"] + p["dst_td"], 1),
        "fg": round(p["fg"], 1),
        "xp": round(p["pat"], 1),
        "pts": round(p["points"], 1),
        # Last season's actual result under these same rules, as a per-game rate
        # multiplied out. null, not 0, for a rookie or a man who missed the year:
        # they have no season to score, which is a different thing from scoring
        # nothing, and the board must not draw them the same way.
        "e25": None if p.get("exp_2025") is None else round(p["exp_2025"], 1),
        "g25": p.get("games_2025"),
        "vor": round(p["adj_vor"], 1),
        "raw": p["raw_rank"],
        "c": p.get("confidence", ""),
        "note": p.get("notes", ""),
        "tag": tag["kind"] if tag else "",
        "tagwhy": tag["why"] if tag else "",
    })

DATA = json.dumps(players, separators=(",", ":"))
META = json.dumps({"teams": BOARD["teams"], "starters": STARTERS,
                   "replacement": {k: round(v, 1) for k, v in BOARD["replacement"].items()}})

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>2026 TD/FG Draft Board</title>
<style>
:root{
  --bg:#0f1420; --panel:#182031; --line:#2a3448; --txt:#e6ebf5; --dim:#8492ad;
  --accent:#4c9aff; --gone:#4a5568;
  --QB:#ff8a5c; --RB:#5ad18f; --WR:#5ab0ff; --TE:#ffd166; --K:#b9c2d0; --DST:#c08cf0;
  /* Magenta rather than a salmon pink, because the palette already spends the
     warm-red end on things that mean something else: #ff5a68 strikes a player
     off and #ff9aa2 marks a LOW confidence projection. A flag must not read as
     either. It is also clear of QB orange, the one position it can be lit
     alongside without either being a mistake. */
  --flag:#ff77c8;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--txt);
  font:14px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif}
header{position:sticky;top:0;z-index:20;background:var(--panel);
  border-bottom:1px solid var(--line);padding:10px 16px}
.top{display:flex;align-items:center;gap:14px;flex-wrap:wrap}
h1{font-size:16px;margin:0;font-weight:650;letter-spacing:.2px}
.sub{color:var(--dim);font-size:12px}
.spacer{flex:1}
input[type=search]{background:#0d121c;border:1px solid var(--line);color:var(--txt);
  border-radius:6px;padding:6px 10px;width:230px;font-size:13px;outline:none}
input[type=search]:focus{border-color:var(--accent)}
button{background:#222c40;border:1px solid var(--line);color:var(--txt);
  border-radius:6px;padding:5px 11px;font-size:12.5px;cursor:pointer;font-family:inherit}
button:hover{background:#2b374f}
button.on{background:var(--accent);border-color:var(--accent);color:#06101f;font-weight:600}
/* An active position filter takes that position's own colour, so the pill you
   pressed matches the pills in the Pos column -- green for RB, orange for QB.
   With multi-select this is what makes a two-position selection readable at a
   glance. The star gets pink, matching the lit stars in the rows it filters to.
   Only ALL keeps the neutral blue. The dark text is inherited from button.on
   and is the same choice .pos makes over these same fills. */
#filters button.on[data-p="QB"]{background:var(--QB);border-color:var(--QB)}
#filters button.on[data-p="RB"]{background:var(--RB);border-color:var(--RB)}
#filters button.on[data-p="WR"]{background:var(--WR);border-color:var(--WR)}
#filters button.on[data-p="TE"]{background:var(--TE);border-color:var(--TE)}
#filters button.on[data-p="K"]{background:var(--K);border-color:var(--K)}
#filters button.on[data-p="DST"]{background:var(--DST);border-color:var(--DST)}
#filters button.on[data-p="FLAG"]{background:var(--flag);border-color:var(--flag)}
.filters{display:flex;gap:6px;flex-wrap:wrap;margin-top:9px;align-items:center}
.avail{display:flex;gap:8px;flex-wrap:wrap;margin-top:9px}
.chip{background:#0d121c;border:1px solid var(--line);border-radius:6px;
  padding:4px 9px;font-size:12px;display:flex;gap:7px;align-items:center}
.chip b{font-weight:600}
.chip .pos{font-weight:700;font-size:10.5px;letter-spacing:.4px}
main{padding:12px 16px 60px}
table{width:100%;border-collapse:collapse}
th{position:sticky;top:0;background:#141b29;text-align:left;font-size:11px;
  text-transform:uppercase;letter-spacing:.5px;color:var(--dim);font-weight:600;
  padding:7px 8px;border-bottom:1px solid var(--line);cursor:pointer;white-space:nowrap}
th:hover{color:var(--txt)}
th.sorted::after{content:" \\25BC";font-size:8px}
td{padding:6px 8px;border-bottom:1px solid #1d2536;vertical-align:top}
tr.row{cursor:pointer}
tr.row:hover td{background:#1b2333}
/* A drafted player used to be dim grey with a strike through his name only, which
   at arm's length read as "slightly quieter row" rather than "gone" -- and the
   whole job of this board mid-draft is answering "is he still there?" in one
   glance. Now the strike runs through every cell and the row turns red.
   Colours are listed explicitly rather than via a descendant wildcard, because
   the position and confidence pills draw dark text on a bright fill and would be
   made illegible by inheriting the red. They get dimmed instead. */
tr.gone:not(.mine) td,
tr.gone:not(.mine) td.cat,
tr.gone:not(.mine) .nm,
tr.gone:not(.mine) .tm,
tr.gone:not(.mine) .zero,
tr.gone:not(.mine) .note,
tr.gone:not(.mine) .conf{color:#ff5a68}
/* One unbroken rule across the row, drawn as an overlay per cell rather than with
   text-decoration. Two reasons text-decoration was wrong: it only paints over the
   glyphs, so the line broke at every gap between columns and vanished across the
   empty ones; and it sits relative to each cell's own font, so the 12px team tag
   and note struck at a different height from the 13px numbers -- a line that
   stepped up and down the row. The cells are border-collapsed and touch edge to
   edge, so a full-width bar in each joins into a single continuous line. */
tr.gone td{position:relative}
tr.gone td::after{content:"";position:absolute;left:0;right:0;top:calc(50% - 1px);
  height:2px;pointer-events:none;background:#ff5a68}
tr.gone .pos{opacity:.4}
tr.gone:not(.mine):hover td{background:#2a1a1f}
/* My own picks are also "off the board", so they match .gone unless excluded.
   They are the opposite kind of news and must not read as a loss -- struck
   through, but in the roster green rather than the taken-by-someone-else red. */
tr.mine td{background:#132a1e}
tr.mine td::after{background:#5ad18f}
tr.mine:hover td{background:#183524}
.pos{display:inline-block;min-width:34px;text-align:center;border-radius:4px;
  padding:1px 5px;font-size:11px;font-weight:700;color:#0c1220}
/* Four extra columns squeeze the name cell; without this it wraps to two lines at
   narrower widths and halves how many players fit on screen. */
.nm{font-weight:600;white-space:nowrap}
/* The whole cell, not just the name -- the space before the team tag was a
   wrap opportunity, so "Amon-Ra St. Brown DET" broke to two lines on its own. */
.pl{white-space:nowrap}
.tm{color:var(--dim);font-size:12px}
.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.vor{font-weight:700}
/* Category splits sit between the name and the total, so keep them quieter than
   both -- they are there to be read on demand, not to compete with Pts. */
td.cat{color:#aebbd1}
th.cat{color:#6f7d97}
.zero{color:#39435a}
/* One line, clipped, full text on hover. Left to wrap, a long trap explanation
   grew its row to 170px against a 33px baseline -- five ordinary rows' worth of
   screen for one note, which is the opposite of what you want while a draft is
   running. The text is still there, in the title attribute. */
/* 26vw, not 46: the other twelve columns need about 925px between them, so a
   note wide enough to hit the old cap pushed the star and Draft button off the
   right edge of anything narrower than ~1500px. Notes are the only column that
   can afford to give -- they are clipped either way and the whole text is on
   hover, whereas a Draft button you have to scroll sideways to reach is just
   broken. 26vw keeps the whole table on screen from 1280px up. */
.note{color:var(--dim);font-size:12px;max-width:min(26vw,560px);
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
/* Sleepers and traps carry no per-row badge or accent bar. They read as a
   verdict on a player the board has already ranked, and 288 rows of them turn
   into visual noise you stop seeing by the second round. The star filter is the
   way to reach them, and their reasoning still fills the Notes cell. */
.conf{font-size:10.5px;letter-spacing:.3px}
.LOW{color:#ff9aa2}.MEDIUM{color:#ffd166}.HIGH{color:#7ee2a8}
.mineBtn{background:transparent;border:1px solid var(--line);color:var(--dim);
  padding:1px 6px;font-size:11px;border-radius:4px}
.mineBtn:hover{border-color:#5ad18f;color:#5ad18f}
tr.mine .mineBtn{border-color:#5ad18f;color:#5ad18f}
/* The star gets its own cell rather than sharing the Draft button's, so 288
   Draft buttons stay in one straight line whether or not the row is flagged.
   Transparent border, not none, so starring does not shift the row by a pixel. */
.starBtn{background:transparent;border:1px solid transparent;color:#39435a;
  padding:0 3px;font-size:14px;line-height:1.1;border-radius:4px}
.starBtn:hover{background:transparent;color:var(--flag)}
/* button.on is the filter-pill rule -- solid fill and a border. It matches a lit
   star too, so every property it sets has to be put back, not just the colour.
   A starred row was rendering with a blue chip around the glyph. */
.starBtn.on{color:var(--flag);background:transparent;border-color:transparent;font-weight:400}
#roster{margin-top:10px;font-size:12px;color:var(--dim);display:flex;gap:12px;flex-wrap:wrap}
#roster span b{color:var(--txt)}
.empty{padding:40px;text-align:center;color:var(--dim)}
/* The button sits beside #roster rather than inside it, because render() calls
   replaceChildren() on #roster every pass and would delete it. */
.rosterRow{display:flex;align-items:center;gap:12px}
#teamBtn{margin-left:auto;border-color:#2f6b4a;color:#7ee2a8;white-space:nowrap}
#teamBtn:hover{border-color:#5ad18f;color:#5ad18f}
.modalBack{position:fixed;inset:0;background:rgba(6,9,16,.75);z-index:50;
  display:flex;align-items:flex-start;justify-content:center;padding:36px 14px;overflow:auto}
.modalBack[hidden]{display:none}
.modal{background:#141b29;border:1px solid #2a3446;border-radius:10px;
  width:min(620px,100%);box-shadow:0 24px 70px rgba(0,0,0,.55)}
.modal h2{margin:0;font-size:14px;padding:13px 16px;border-bottom:1px solid #232c3d;
  display:flex;align-items:center;gap:10px}
.modal .x{margin-left:auto;background:transparent;border:1px solid var(--line);
  color:var(--dim);border-radius:4px;padding:2px 9px;font-size:12px;cursor:pointer}
.modal .x:hover{color:var(--txt);border-color:#48566f}
.secHdr{padding:7px 16px;font-size:10.5px;letter-spacing:.6px;color:#6f7d97;
  background:#111827;text-transform:uppercase;font-weight:700;
  display:flex;align-items:center;gap:8px}
.secHdr .tot{margin-left:auto;color:#aebbd1;letter-spacing:0}
.slot{display:flex;align-items:center;gap:8px;padding:7px 16px;
  border-bottom:1px solid #1d2536;font-size:13px}
.slot .lbl{width:38px;flex:none;color:#6f7d97;font-size:10.5px;font-weight:700}
.slot .who{font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.slot .sp{margin-left:auto}
.slot .n1{font-variant-numeric:tabular-nums;font-weight:700;min-width:52px;text-align:right}
.slot .n2{font-variant-numeric:tabular-nums;color:#aebbd1;min-width:52px;text-align:right}
.slot.gap .who{color:#4a5568;font-style:italic;font-weight:400}
.modal .foot{padding:10px 16px;font-size:12px;color:var(--dim);
  border-top:1px solid #232c3d;display:flex;gap:8px;align-items:center}
</style>
</head>
<body>
<header>
  <div class="top">
    <h1>2026 TD/FG-Only Draft Board</h1>
    <span class="sub" id="count"></span>
    <div class="spacer"></div>
    <input type="search" id="q" placeholder="Search player or team  (press /)">
    <button id="hide">Hide drafted</button>
    <button id="undo">Undo</button>
    <button id="reset">Reset</button>
  </div>
  <div class="filters" id="filters"></div>
  <div class="avail" id="avail"></div>
  <div class="rosterRow">
    <div id="roster"></div>
    <button id="teamBtn" title="Show my starting lineup and bench">My Team</button>
  </div>
</header>
<main>
  <table>
    <thead><tr>
      <th data-k="r">#</th><th data-k="p">Pos</th><th data-k="n">Player</th>
      <th data-k="pts" class="num" title="Total projected fantasy points for 2026. The category columns to the right are what it is made of.">2026&nbsp;Proj&nbsp;Pts</th>
      <th data-k="e25" class="num cat" title="What this player scored in 2025 under these exact league settings, as a per-game rate multiplied out to 18 games -- NOT his raw 2025 total. Scoring at his 2025 rate over a full 18 games is what this is. Hover a value to see how many games the rate is averaged over. A dash means no 2025 season at all -- a rookie, or a year missed to injury -- which is not the same as having scored nothing.">2025&nbsp;Pts</th>
      <th data-k="vor" class="num" title="Adjusted value over replacement -- how many points this player beats a freely available player at his own position by, discounted for how much of that edge is real. This is what the board is sorted by.">Adj&nbsp;VOR</th>
      <th data-k="ptd" class="num cat" title="Projected passing TDs (3 pts each)">Pass&nbsp;TD</th>
      <th data-k="td" class="num cat" title="Projected rushing + receiving TDs, and D/ST return TDs (6 pts each)">TD</th>
      <th data-k="fg" class="num cat" title="Projected field goals made, all distances (3 pts each)">FG</th>
      <th data-k="xp" class="num cat" title="Projected extra points made (1 pt each)">XP</th>
      <th data-k="c" title="Confidence level in this player's projection: HIGH, MED or LOW.">Conf&nbsp;Lvl</th><th>Notes</th><th></th><th></th>
    </tr></thead>
    <tbody id="tb"></tbody>
  </table>
  <div class="empty" id="empty" hidden>No players match.</div>
</main>
<div class="modalBack" id="teamBack" hidden>
  <div class="modal" role="dialog" aria-modal="true" aria-label="My Team">
    <h2>My Team <span class="sub" id="teamCount"></span>
      <button class="x" id="teamX">Close</button></h2>
    <div id="teamBody"></div>
    <div class="foot" id="teamFoot"></div>
  </div>
</div>
<script>
const P = __DATA__, META = __META__;
const KEY = "tdfg2026";
let st = JSON.parse(localStorage.getItem(KEY) || '{"gone":[],"mine":[],"log":[]}');
let gone = new Set(st.gone), mine = new Set(st.mine), log = st.log || [];
// Flags start as the board's own sleeper and trap picks and become yours the
// moment you touch a star. Seeded only when the key is absent, never when it is
// an empty array -- otherwise unstarring the last player would silently restore
// all seventeen on the next reload.
let flags = new Set(st.flags === undefined ? P.filter(p=>p.tag).map(p=>p.n) : st.flags);
// A set, not a string: positions union together, and FLAG intersects whatever
// positions are active. See the filter handler for why.
let filter = new Set(["ALL"]);
let sortKey = "r", hideDrafted = false, query = "";
const POS = ["QB","RB","WR","TE","K","DST"];

const save = () => localStorage.setItem(KEY,
  JSON.stringify({gone:[...gone], mine:[...mine], log, flags:[...flags]}));

// Almost every player scores in exactly one category, so 288 rows of "0.0" would
// be noise. Show a dot instead, and drop the decimal on whole numbers (FG/XP).
const stat = v => v ? (Number.isInteger(v) ? v : v.toFixed(1))
                    : '<span class="zero">\\u00b7</span>';

// Build filter buttons
const fEl = document.getElementById("filters");
const LABEL = {DST:"D/ST", FLAG:"\\u2605 Flagged"};
// Plain click picks one. Cmd/Ctrl-click adds or removes, so you can hold RB and
// WR together in the round where you are choosing between them.
//
// The two kinds of filter compose differently on purpose. Positions are a union
// -- RB+WR means either -- because they are mutually exclusive and an
// intersection would always be empty. FLAG is a different axis entirely, so it
// intersects: RB + star means flagged running backs, which is the question you
// actually ask, rather than "every RB plus every flagged kicker".
["ALL",...POS,"FLAG"].forEach(p=>{
  const b=document.createElement("button");
  b.textContent = LABEL[p] || p; b.dataset.p=p;
  if(p==="FLAG") b.title="Players you have starred, seeded with the board's sleepers and traps. "+
    "Combines with a position: Cmd/Ctrl-click RB and the star for flagged RBs only.";
  else if(p==="ALL") b.title="Cmd/Ctrl-click a filter to add it to the selection";
  if(p==="ALL") b.classList.add("on");
  b.onclick=e=>{
    if(e.metaKey||e.ctrlKey){
      if(p==="ALL") filter=new Set(["ALL"]);         // ALL is the reset, not a member
      else if(filter.has(p)) filter.delete(p);
      else { filter.delete("ALL"); filter.add(p); }
    } else filter=new Set([p]);
    // Deselecting your way down to nothing, or to the star on its own with no
    // position, is not an empty board -- fall back to every position.
    if(filter.size===0) filter=new Set(["ALL"]);
    syncFilterButtons(); render();
  };
  fEl.appendChild(b);
});
function syncFilterButtons(){
  [...fEl.children].forEach(c=>c.classList.toggle("on", filter.has(c.dataset.p)));
}

const tb = document.getElementById("tb");
const rows = new Map();

function makeRow(pl){
  const tr=document.createElement("tr");
  tr.className="row";
  const note = pl.tagwhy || pl.note || "";
  // Clipped to one line in CSS, so the full text has to live somewhere reachable.
  const noteAttr = note.replace(/"/g, "&quot;");
  // A rate off four games and a rate off seventeen print identically, so the
  // sample size has to be on the cell -- otherwise Malik Willis's 94.5 reads
  // like Josh Allen's 178.9 rather than like the four-game fluke it is.
  // Zero renders as the same middot the TD columns use, but "no season" stays a
  // dash: Kansas City's defence played and scored nothing, Mendoza has no 2025
  // at all, and those are different claims that must not collapse into one glyph.
  // Always one decimal, unlike stat(), because these are three-digit point
  // totals and dropping ".0" off the round ones breaks the column's alignment.
  const a25 = pl.e25===null ? "—"
            : pl.e25 ? pl.e25.toFixed(1) : '<span class="zero">\\u00b7</span>';
  const a25t = pl.e25===null
    ? "No 2025 season — rookie, or missed the year"
    : `2025 rate over ${pl.g25} game${pl.g25===1?"":"s"}, x18`;
  tr.innerHTML=`
    <td class="num" style="color:var(--dim)">${pl.r}</td>
    <td><span class="pos" style="background:var(--${pl.p})">${pl.pr}</span></td>
    <td class="pl"><span class="nm">${pl.n}</span> <span class="tm">${pl.t}</span></td>
    <td class="num">${pl.pts.toFixed(1)}</td>
    <td class="num cat" title="${a25t}">${a25}</td>
    <td class="num vor">${pl.vor.toFixed(1)}</td>
    <td class="num cat">${stat(pl.ptd)}</td>
    <td class="num cat">${stat(pl.td)}</td>
    <td class="num cat">${stat(pl.fg)}</td>
    <td class="num cat">${stat(pl.xp)}</td>
    <td><span class="conf ${pl.c}">${pl.c}</span></td>
    <td class="note" title="${noteAttr}">${note}</td>
    <td><button class="starBtn" title="Flag this player — shows under the ★ Flagged filter">\\u2605</button></td>
    <td><button class="mineBtn" title="Draft to my team">Draft</button></td>`;
  tr.onclick=e=>{
    // Both buttons sit inside the row, whose own click crosses a player off.
    // Each has to claim the event or starring a player would also take him off
    // the board.
    if(e.target.classList.contains("mineBtn")){
      toggle(pl.n, true); e.stopPropagation();
    } else if(e.target.classList.contains("starBtn")){
      toggleFlag(pl.n); e.stopPropagation();
    } else toggle(pl.n, false);
  };
  return tr;
}

function toggleFlag(name){
  flags.has(name) ? flags.delete(name) : flags.add(name);
  save(); render();
}

function toggle(name, asMine){
  const wasGone = gone.has(name), wasMine = mine.has(name);
  if(asMine){
    if(wasMine){ mine.delete(name); gone.delete(name); }
    else { mine.add(name); gone.add(name); }
  } else {
    if(wasGone){ gone.delete(name); mine.delete(name); }
    else gone.add(name);
  }
  log.push({name, wasGone, wasMine});
  save(); render();
}

// ---- My Team -------------------------------------------------------------
// Starters are filled in the order players were drafted: the first RB taken
// holds RB1, the second RB2, and a third RB goes to the bench however good he
// is. `mine` is a Set, and Set iteration order is insertion order, which is
// draft order -- and it survives the localStorage round trip because it is
// stored as an array. Re-drafting a player after undrafting him moves him to
// the end, which is correct: that is when he was actually taken.
const posLabel = p => p==="DST" ? "D/ST" : p;

function buildTeam(){
  const filled={}; POS.forEach(p=>filled[p]=0);
  const starters=[], bench=[];
  [...mine].forEach(n=>{
    const pl=P.find(x=>x.n===n); if(!pl) return;
    if(filled[pl.p] < META.starters[pl.p]){ filled[pl.p]++; starters.push(pl); }
    else bench.push(pl);
  });
  // Lay the starters out in roster order with the unfilled slots left visible,
  // so the panel answers "what do I still need?" and not just "who do I have?".
  const slots=[];
  POS.forEach(p=>{
    const inPos=starters.filter(x=>x.p===p);
    for(let i=0;i<META.starters[p];i++) slots.push({p, pl:inPos[i]||null});
  });
  return {slots, starters, bench};
}

const esc = s => String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;");

function slotHTML(p, pl){
  const lbl=`<span class="lbl">${posLabel(p)}</span>`;
  if(!pl) return `<div class="slot gap">${lbl}<span class="who">— empty —</span></div>`;
  const a25 = pl.e25===null ? "&mdash;" : pl.e25.toFixed(1);
  return `<div class="slot">${lbl}`+
    `<span class="pos" style="background:var(--${pl.p})">${pl.pr}</span>`+
    `<span class="who">${esc(pl.n)} <span class="tm">${pl.t}</span></span>`+
    `<span class="sp"></span><span class="n1">${pl.pts.toFixed(1)}</span>`+
    `<span class="n2" title="2025 rate x18 games">${a25}</span></div>`;
}

function renderTeam(){
  const {slots, starters, bench}=buildTeam();
  const sum=a=>a.reduce((t,x)=>t+x.pts,0);
  const need=POS.reduce((t,p)=>t+META.starters[p],0);
  document.getElementById("teamCount").textContent =
    `${starters.length}/${need} starters · ${bench.length} bench`;
  let h=`<div class="secHdr">Starting lineup<span class="tot">`+
        `${sum(starters).toFixed(1)} pts</span></div>`;
  h+=slots.map(s=>slotHTML(s.p, s.pl)).join("");
  h+=`<div class="secHdr">Bench<span class="tot">${sum(bench).toFixed(1)} pts</span></div>`;
  h+= bench.length ? bench.map(pl=>slotHTML(pl.p, pl)).join("")
                   : `<div class="slot gap"><span class="who">nobody on the bench yet</span></div>`;
  document.getElementById("teamBody").innerHTML=h;
  document.getElementById("teamFoot").textContent =
    `Filled in draft order. Columns are 2026 projected points and 2025 points.`;
}

const teamBack=document.getElementById("teamBack");
const showTeam=v=>{ if(v) renderTeam(); teamBack.hidden=!v; };
document.getElementById("teamBtn").onclick=()=>showTeam(true);
document.getElementById("teamX").onclick=()=>showTeam(false);
teamBack.onclick=e=>{ if(e.target===teamBack) showTeam(false); };

document.getElementById("undo").onclick=()=>{
  const last=log.pop(); if(!last) return;
  last.wasGone?gone.add(last.name):gone.delete(last.name);
  last.wasMine?mine.add(last.name):mine.delete(last.name);
  save(); render();
};
document.getElementById("reset").onclick=()=>{
  if(!confirm("Clear all draft picks?")) return;
  gone.clear(); mine.clear(); log=[]; save(); render();
};
document.getElementById("hide").onclick=e=>{
  hideDrafted=!hideDrafted; e.target.classList.toggle("on",hideDrafted); render();
};
document.getElementById("q").oninput=e=>{query=e.target.value.toLowerCase();render();};
document.querySelectorAll("th[data-k]").forEach(th=>{
  th.onclick=()=>{
    sortKey=th.dataset.k;
    document.querySelectorAll("th").forEach(x=>x.classList.remove("sorted"));
    th.classList.add("sorted"); render();
  };
});
document.addEventListener("keydown",e=>{
  if(e.key==="/"&&document.activeElement.id!=="q"){e.preventDefault();document.getElementById("q").focus();}
  // Escape closes the panel first and stops there, rather than also wiping the
  // search box underneath it -- one key should undo one thing.
  if(e.key==="Escape"){
    if(!teamBack.hidden){ showTeam(false); return; }
    document.getElementById("q").value="";query="";render();
  }
});

function render(){
  const wantPos = POS.filter(p=>filter.has(p));
  let list = P.filter(pl=>{
    if(filter.has("FLAG") && !flags.has(pl.n)) return false;
    if(wantPos.length && !wantPos.includes(pl.p)) return false;
    if(hideDrafted && gone.has(pl.n)) return false;
    if(query && !(pl.n.toLowerCase().includes(query)||pl.t.toLowerCase().includes(query))) return false;
    return true;
  });
  const dir = (sortKey==="r"||sortKey==="n"||sortKey==="p"||sortKey==="c")?1:-1;
  list.sort((a,b)=>{
    const x=a[sortKey], y=b[sortKey];
    // Sorting by 2025, a null is "unknown", not "worst". It must sink to the
    // bottom whichever way the column is pointed -- so it is held out of the
    // comparison rather than coerced, which would make null-0 = 0 and scatter
    // every rookie through the middle of the list.
    if(x===null||y===null) return (x===null)-(y===null);
    if(typeof x==="string") return dir*x.localeCompare(y);
    return dir*(x-y);
  });

  tb.replaceChildren();
  list.forEach(pl=>{
    let tr = rows.get(pl.n);
    if(!tr){ tr = makeRow(pl); rows.set(pl.n, tr); }
    tr.classList.toggle("gone", gone.has(pl.n));
    tr.classList.toggle("mine", mine.has(pl.n));
    // Rows are cached and reused across renders, so the star has to be re-synced
    // rather than set once at construction.
    tr.querySelector(".starBtn").classList.toggle("on", flags.has(pl.n));
    tb.appendChild(tr);
  });
  // Live count on the filter button, so a star click visibly lands even when the
  // row you starred is not one the current filter is showing.
  fEl.querySelector('[data-p="FLAG"]').textContent =
    flags.size ? `\\u2605 Flagged ${flags.size}` : "\\u2605 Flagged";
  document.getElementById("empty").hidden = list.length>0;

  document.getElementById("count").textContent =
    `${gone.size} off the board · ${P.length-gone.size} left · ${mine.size} on my team`;

  // Best available per position
  const av=document.getElementById("avail"); av.replaceChildren();
  POS.forEach(p=>{
    const best=P.filter(x=>x.p===p&&!gone.has(x.n)).sort((a,b)=>b.vor-a.vor)[0];
    const c=document.createElement("div"); c.className="chip";
    c.innerHTML=`<span class="pos" style="background:var(--${p})">${p==="DST"?"D/ST":p}</span>`+
      (best?`<b>${best.n}</b> <span class="tm">${best.t}</span>
        <span style="color:var(--dim)">${best.vor.toFixed(1)}</span>`:"—");
    if(best) c.onclick=()=>{toggle(best.n,false);};
    c.style.cursor="pointer";
    av.appendChild(c);
  });

  // My roster fill
  const rEl=document.getElementById("roster"); rEl.replaceChildren();
  POS.forEach(p=>{
    const have=[...mine].filter(n=>P.find(x=>x.n===n)?.p===p).length;
    const need=META.starters[p];
    const s=document.createElement("span");
    s.innerHTML=`${p==="DST"?"D/ST":p} <b>${have}/${need}</b>`;
    if(have<need) s.style.color="var(--dim)"; else s.style.color="#7ee2a8";
    rEl.appendChild(s);
  });
  const pts=[...mine].reduce((t,n)=>t+(P.find(x=>x.n===n)?.pts||0),0);
  const s=document.createElement("span");
  s.innerHTML=`Projected starters+bench total <b>${pts.toFixed(0)}</b> pts`;
  rEl.appendChild(s);

  // Undo, Reset and the best-available chips can all change the roster while the
  // panel is open, so keep it live rather than showing a stale snapshot.
  if(!teamBack.hidden) renderTeam();
}
render();
</script>
</body>
</html>
"""

page = HTML.replace("__DATA__", DATA).replace("__META__", META)

# index.html is what GitHub Pages serves at the bare repo URL, so it has to exist
# under that name. draft-board.html is kept as a byte-identical copy purely so the
# old local path and any existing bookmark keep working -- both are generated here
# rather than one being a stale hand-copy of the other.
for name in ("index.html", "draft-board.html"):
    out = ROOT / name
    out.write_text(page, encoding="utf-8")
print(f"wrote index.html + draft-board.html  ({len(players)} players, "
      f"{(ROOT / 'index.html').stat().st_size // 1024} KB)")
