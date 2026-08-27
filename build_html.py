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
tr.gone td{color:var(--gone)}
tr.gone .nm{text-decoration:line-through}
tr.mine td{background:#132a1e}
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
.note{color:var(--dim);font-size:12px;max-width:min(46vw,560px);
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.badge{font-size:9.5px;font-weight:700;letter-spacing:.4px;padding:1px 5px;
  border-radius:3px;margin-right:6px;vertical-align:1px}
.badge.sleeper{background:#1c4a2e;color:#7ee2a8}
.badge.trap{background:#4d1f24;color:#ff9aa2}
/* Flagged players can sit deep in the board (Sean Tucker is ~#263), so give the
   row a left accent that is visible while scrolling past. */
tr.t-sleeper td:first-child{box-shadow:inset 3px 0 0 #7ee2a8}
tr.t-trap td:first-child{box-shadow:inset 3px 0 0 #ff9aa2}
.conf{font-size:10.5px;letter-spacing:.3px}
.LOW{color:#ff9aa2}.MEDIUM{color:#ffd166}.HIGH{color:#7ee2a8}
.mineBtn{background:transparent;border:1px solid var(--line);color:var(--dim);
  padding:1px 6px;font-size:11px;border-radius:4px}
.mineBtn:hover{border-color:#5ad18f;color:#5ad18f}
tr.mine .mineBtn{border-color:#5ad18f;color:#5ad18f}
#roster{margin-top:10px;font-size:12px;color:var(--dim);display:flex;gap:12px;flex-wrap:wrap}
#roster span b{color:var(--txt)}
.empty{padding:40px;text-align:center;color:var(--dim)}
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
  <div id="roster"></div>
</header>
<main>
  <table>
    <thead><tr>
      <th data-k="r">#</th><th data-k="p">Pos</th><th data-k="n">Player</th>
      <th data-k="pts" class="num" title="Total projected fantasy points. The category columns to the right are what it is made of.">Pts</th>
      <th data-k="ptd" class="num cat" title="Projected passing TDs (3 pts each)">Pass&nbsp;TD</th>
      <th data-k="td" class="num cat" title="Projected rushing + receiving TDs, and D/ST return TDs (6 pts each)">TD</th>
      <th data-k="fg" class="num cat" title="Projected field goals made, all distances (3 pts each)">FG</th>
      <th data-k="xp" class="num cat" title="Projected extra points made (1 pt each)">XP</th>
      <th data-k="vor" class="num" title="Adjusted value over replacement -- how many points this player beats a freely available player at his own position by, discounted for how much of that edge is real. This is what the board is sorted by.">Adj&nbsp;VOR</th>
      <th data-k="c">Conf</th><th>Notes</th><th></th>
    </tr></thead>
    <tbody id="tb"></tbody>
  </table>
  <div class="empty" id="empty" hidden>No players match.</div>
</main>
<script>
const P = __DATA__, META = __META__;
const KEY = "tdfg2026";
let st = JSON.parse(localStorage.getItem(KEY) || '{"gone":[],"mine":[],"log":[]}');
let gone = new Set(st.gone), mine = new Set(st.mine), log = st.log || [];
let filter = "ALL", sortKey = "r", hideDrafted = false, query = "";
const POS = ["QB","RB","WR","TE","K","DST"];

const save = () => localStorage.setItem(KEY,
  JSON.stringify({gone:[...gone], mine:[...mine], log}));

// Almost every player scores in exactly one category, so 288 rows of "0.0" would
// be noise. Show a dot instead, and drop the decimal on whole numbers (FG/XP).
const stat = v => v ? (Number.isInteger(v) ? v : v.toFixed(1))
                    : '<span class="zero">\\u00b7</span>';

// Build filter buttons
const fEl = document.getElementById("filters");
const LABEL = {DST:"D/ST", FLAG:"\\u2605 Flagged"};
["ALL",...POS,"FLAG"].forEach(p=>{
  const b=document.createElement("button");
  b.textContent = LABEL[p] || p; b.dataset.p=p;
  if(p==="FLAG") b.title="Sleepers and traps — players whose projection misleads in this format";
  if(p==="ALL") b.classList.add("on");
  b.onclick=()=>{filter=p;[...fEl.children].forEach(c=>c.classList.toggle("on",c.dataset.p===p));render();};
  fEl.appendChild(b);
});

const tb = document.getElementById("tb");
const rows = new Map();

function makeRow(pl){
  const tr=document.createElement("tr");
  tr.className="row" + (pl.tag?` t-${pl.tag}`:"");
  const badge = pl.tag?`<span class="badge ${pl.tag}">${pl.tag.toUpperCase()}</span>`:"";
  const note = pl.tagwhy || pl.note || "";
  // Clipped to one line in CSS, so the full text has to live somewhere reachable.
  const noteAttr = note.replace(/"/g, "&quot;");
  tr.innerHTML=`
    <td class="num" style="color:var(--dim)">${pl.r}</td>
    <td><span class="pos" style="background:var(--${pl.p})">${pl.pr}</span></td>
    <td class="pl"><span class="nm">${pl.n}</span> <span class="tm">${pl.t}</span></td>
    <td class="num">${pl.pts.toFixed(1)}</td>
    <td class="num cat">${stat(pl.ptd)}</td>
    <td class="num cat">${stat(pl.td)}</td>
    <td class="num cat">${stat(pl.fg)}</td>
    <td class="num cat">${stat(pl.xp)}</td>
    <td class="num vor">${pl.vor.toFixed(1)}</td>
    <td><span class="conf ${pl.c}">${pl.c}</span></td>
    <td class="note" title="${noteAttr}">${badge}${note}</td>
    <td><button class="mineBtn" title="Draft to my team">mine</button></td>`;
  tr.onclick=e=>{
    if(e.target.classList.contains("mineBtn")){
      toggle(pl.n, true); e.stopPropagation();
    } else toggle(pl.n, false);
  };
  return tr;
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
  if(e.key==="Escape"){document.getElementById("q").value="";query="";render();}
});

function render(){
  let list = P.filter(pl=>{
    if(filter==="FLAG"){ if(!pl.tag) return false; }
    else if(filter!=="ALL" && pl.p!==filter) return false;
    if(hideDrafted && gone.has(pl.n)) return false;
    if(query && !(pl.n.toLowerCase().includes(query)||pl.t.toLowerCase().includes(query))) return false;
    return true;
  });
  const dir = (sortKey==="r"||sortKey==="n"||sortKey==="p"||sortKey==="c")?1:-1;
  list.sort((a,b)=>{
    const x=a[sortKey], y=b[sortKey];
    if(typeof x==="string") return dir*x.localeCompare(y);
    return dir*(x-y);
  });

  tb.replaceChildren();
  list.forEach(pl=>{
    let tr = rows.get(pl.n);
    if(!tr){ tr = makeRow(pl); rows.set(pl.n, tr); }
    tr.classList.toggle("gone", gone.has(pl.n));
    tr.classList.toggle("mine", mine.has(pl.n));
    tb.appendChild(tr);
  });
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
