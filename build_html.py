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
.nm{font-weight:600}
.tm{color:var(--dim);font-size:12px}
.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.vor{font-weight:700}
.note{color:var(--dim);font-size:12px;max-width:640px}
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
      <th data-k="pts" class="num">Pts</th><th data-k="vor" class="num">Adj VOR</th>
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
  tr.innerHTML=`
    <td class="num" style="color:var(--dim)">${pl.r}</td>
    <td><span class="pos" style="background:var(--${pl.p})">${pl.pr}</span></td>
    <td><span class="nm">${pl.n}</span> <span class="tm">${pl.t}</span></td>
    <td class="num">${pl.pts.toFixed(1)}</td>
    <td class="num vor">${pl.vor.toFixed(1)}</td>
    <td><span class="conf ${pl.c}">${pl.c}</span></td>
    <td class="note">${badge}${note}</td>
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

out = ROOT / "draft-board.html"
out.write_text(HTML.replace("__DATA__", DATA).replace("__META__", META), encoding="utf-8")
print(f"wrote {out}  ({len(players)} players, {out.stat().st_size // 1024} KB)")
