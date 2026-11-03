#!/usr/bin/env python3
"""Build the U SPORTS women's basketball dashboard -> docs/index.html

    python3 src/build_dashboard.py              # season in config.py
    python3 src/build_dashboard.py 2025-2026

Ported from the Canada Basketball 5x5 SWNT dashboard. The competition-tier
system there is replaced by U SPORTS conferences (CW / OUA / RSEQ / AUS).
"""
import json, sys
from pathlib import Path

SRC = Path(__file__).resolve().parent
ROOT = SRC.parent
sys.path.insert(0, str(SRC))
from config import DEFAULT_SEASON, PLAY_TYPES as _PT  # noqa: E402

SEASON = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SEASON
DATA = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / 'data' / SEASON
OUT = Path(sys.argv[3]) if len(sys.argv) > 3 else ROOT / 'docs' / 'index.html'
PLAY_TYPES = [n for n, _ in _PT]

def cpr(pr):
    if not pr: return {}
    m2, a2 = pr.get('shot2Made', 0), pr.get('shot2Attempt', 0)
    m3, a3 = pr.get('shot3Made', 0), pr.get('shot3Attempt', 0)
    # Field goals are 2s + 3s. Synergy's fgMade/fgAttempt are something else.
    return {'p':pr.get('possessions',0),'pts':pr.get('pointMade',0),
        'fa':a2+a3,'fm':m2+m3,'a2':a2,'m2':m2,'a3':a3,'m3':m3,
        'to':pr.get('turnover',0),'fta':pr.get('ftAttempt',0),
        'ftm':pr.get('ftMade',0),'ftt':pr.get('ftTimes',0),
        'sa':pr.get('shotAttempt',0),'sq':round(pr.get('shotQualityTotal',0) or 0,3),
        'sqa':pr.get('shotQualityAttempt',0)}

def cpt(pr):
    d=cpr(pr)
    if d: d['pr']=pr.get('pppRank'); d['qr']=pr.get('possRank')
    return d

def _load(name, default):
    f = DATA / name
    return json.loads(f.read_text()) if f.exists() else default

META = _load('meta.json', {})
_legacy_def_pt = _load('player_def_pt.json', {})   # only present in FIBA-format test data

print(f'Loading {DATA} ...')
TEAMS=[]
for t in _load('teams_all.json', []):
    TEAMS.append({'id':t['team']['id'],'name':t['team']['name'],'gp':t['team'].get('gp',0),
        'conf':t['team'].get('conf',''),
        'off':cpr(t['overall'].get('offense')),'def':cpr(t['overall'].get('defense')),
        'pt_off':{k:cpt(v) for k,v in t['play_types']['offense'].items()},
        'pt_def':{k:cpt(v) for k,v in t['play_types']['defense'].items()}})
TEAMS.sort(key=lambda x:x['name'])
if not TEAMS:
    sys.exit(f'no teams in {DATA}/teams_all.json -- run src/scrape_usports.py first')

PLAYERS=[]
for p in _load('players_all.json', []):
    pid=p['player']['id']
    off=p['overall'].get('offense') or {}
    gp=p.get('gp') or off.get('gp',0)
    pt_def=p['play_types'].get('defense') or _legacy_def_pt.get(pid,{})
    PLAYERS.append({'id':pid,'name':p['player']['name'],
        'tid':p['team']['id'],'team':p['team']['name'],'gp':gp,
        # Season PPG from the leaderboard's full-season totals.
        'ppg':round(off.get('pointMade',0)/gp,1) if gp else 0,
        'off':cpr(off),'def':cpr(p['overall'].get('defense')),
        'pt_off':{k:cpt(v) for k,v in p['play_types']['offense'].items()},
        'pt_def':{k:cpt(v) for k,v in pt_def.items()}})
PLAYERS.sort(key=lambda x:x['name'])
SEASON_LABEL = META.get('season', SEASON)
UPDATED = (META.get('scraped_at') or '')[:10]
import base64
_logo = ROOT / 'assets' / 'warriors_logo.svg'
LOGO_SRC = ('data:image/svg+xml;base64,' + base64.b64encode(_logo.read_bytes()).decode()) if _logo.exists() else ''

teams_json=json.dumps(TEAMS,separators=(',',':'))
players_json=json.dumps(PLAYERS,separators=(',',':'))
pt_json=json.dumps(PLAY_TYPES,separators=(',',':'))
print(f'  Teams:{len(teams_json)//1024}KB  Players:{len(players_json)//1024}KB')

CSS = """
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#f0f2f5;--bg2:#ffffff;--bg3:#f5f6f8;--bg4:#ebedf0;
  --border:#e2e5ea;--border2:#c9cdd4;
  --text:#111827;--text2:#6b7280;--text3:#9ca3af;
  --blue:#1a56db;--green:#16a34a;--red:#dc2626;
  --yellow:#b45309;--orange:#c2410c;--purple:#7c3aed;
  --canada:#8a6b00;--canada-dark:#6b5300;--gold:#FFD100;--ink:#231F20;
  --radius:8px;--font:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
}
html{background:var(--bg);color:var(--text);font-family:var(--font);font-size:14px}
body{min-height:100vh}
.app{display:flex;flex-direction:column;height:100vh;overflow:hidden}
.topbar{background:#000;border-bottom:4px solid var(--gold);padding:0 28px;
  display:flex;align-items:center;gap:20px;flex-shrink:0;height:100px}
.logo{display:flex;align-items:center;gap:14px}
.logo img{height:64px;width:auto}
.logo-text{display:flex;flex-direction:column}
.logo-main{font-size:26px;font-weight:800;color:#fff;letter-spacing:-.5px}
.logo-sub{font-size:13px;color:rgba(255,255,255,.6);margin-top:1px}
.logo-badge{font-size:11px;font-weight:700;background:var(--gold);color:#000;
  padding:3px 9px;border-radius:4px;margin-left:12px;letter-spacing:.3px;align-self:center}
.topstats{display:flex;gap:24px;margin-left:auto}
.topstat{text-align:center}
.topstat-n{font-size:18px;font-weight:800;color:var(--gold);line-height:1}
.topstat-l{font-size:10px;color:rgba(255,255,255,.5);text-transform:uppercase;letter-spacing:.6px;margin-top:2px}
.nav{background:var(--bg2);border-bottom:1px solid var(--border);display:flex;overflow-x:auto;flex-shrink:0}
.nav-btn{padding:12px 20px;font-size:13px;font-weight:500;color:var(--text2);border:none;
  background:none;cursor:pointer;white-space:nowrap;border-bottom:2px solid transparent;
  transition:all .15s}
.nav-btn:hover{color:var(--text)}
.nav-btn.active{color:var(--ink);border-bottom-color:var(--gold);font-weight:600}
.content{flex:1;overflow-y:auto;padding:20px}
.tab{display:none}.tab.active{display:block}
.card{background:var(--bg2);border:1px solid var(--border);border-radius:var(--radius);
  margin-bottom:16px;overflow:hidden}
.card-hdr{padding:12px 16px;background:var(--bg3);border-bottom:1px solid var(--border);
  font-size:11px;font-weight:700;color:var(--text2);text-transform:uppercase;letter-spacing:.8px;
  display:flex;align-items:center;gap:8px}
.card-hdr .accent{color:var(--canada)}
.card-body{padding:16px}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.grid3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px}
.grid4{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}
@media(max-width:1000px){.grid3{grid-template-columns:1fr 1fr}}
@media(max-width:700px){.grid2,.grid3,.grid4{grid-template-columns:1fr}}
.tbl-wrap{overflow-x:auto}
table{width:100%;border-collapse:collapse;font-size:12.5px}
thead th{background:var(--bg3);color:var(--text2);font-weight:600;padding:8px 10px;
  text-align:right;white-space:nowrap;position:sticky;top:0;z-index:2;cursor:pointer;
  user-select:none;border-bottom:1px solid var(--border);font-size:11px}
thead th:first-child,thead th:nth-child(2){text-align:left}
thead th.sorted{color:var(--canada)}
thead th:hover{color:var(--text)}
tbody tr{border-bottom:1px solid var(--border);transition:background .1s}
tbody tr:hover{background:rgba(213,43,30,.05)}
tbody td{padding:7px 10px;text-align:right;color:var(--text)}
tbody td:first-child,tbody td:nth-child(2){text-align:left}
.rank-cell{color:var(--text3);font-size:11px;width:32px}
.hot{color:#16a34a;font-weight:600}.warm{color:#4ade80}
.cold{color:#dc2626;font-weight:600}.cool{color:#f87171}
.controls{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:14px}
.toggle-group{display:flex;border:1px solid var(--border);border-radius:var(--radius);overflow:hidden}
.toggle-btn{padding:6px 16px;font-size:12px;font-weight:500;border:none;
  background:var(--bg2);color:var(--text2);cursor:pointer;transition:all .15s}
.toggle-btn.active{background:var(--gold);color:#000;font-weight:700}
.sel{background:var(--bg2);color:var(--text);border:1px solid var(--border);
  border-radius:var(--radius);padding:6px 10px;font-size:12px;cursor:pointer}
.stat-cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:12px;margin-bottom:16px}
.stat-card{background:var(--bg2);border:1px solid var(--border);border-radius:var(--radius);
  padding:14px 18px}
.stat-card-n{font-size:26px;font-weight:800;color:var(--canada);line-height:1.1}
.stat-card-l{font-size:11px;color:var(--text2);margin-top:3px;font-weight:500}
.stat-card-sub{font-size:10px;color:var(--text3);margin-top:3px}
.hbar-row{display:flex;align-items:center;gap:8px;margin-bottom:6px;font-size:11px}
.hbar-label{width:160px;text-align:right;color:var(--text2);overflow:hidden;
  text-overflow:ellipsis;white-space:nowrap;flex-shrink:0}
.hbar-track{flex:1;height:20px;background:var(--bg3);border-radius:4px;overflow:hidden;position:relative}
.hbar-fill{height:100%;border-radius:4px;display:flex;align-items:center;padding-left:8px;
  font-size:10px;font-weight:700;color:#fff;white-space:nowrap;min-width:0}
.hbar-val{color:var(--text);width:56px;text-align:right;flex-shrink:0;font-weight:600}
.subtabs{display:flex;gap:4px;margin-bottom:14px;flex-wrap:wrap}
.subtab-btn{padding:5px 14px;font-size:12px;font-weight:500;color:var(--text2);
  border:1px solid var(--border);border-radius:20px;background:var(--bg2);cursor:pointer;transition:all .15s}
.subtab-btn.active{background:var(--gold);border-color:var(--gold);color:#000;font-weight:700}
.subtab{display:none}.subtab.active{display:block}
.team-select-row{display:flex;gap:12px;margin-bottom:16px;align-items:center;flex-wrap:wrap}
.team-select-row select{flex:1;min-width:200px}
.lcard{background:var(--bg3);border:1px solid var(--border);border-radius:var(--radius);
  padding:14px;position:relative;overflow:hidden}
.lcard::before{content:'';position:absolute;top:0;left:0;right:0;height:3px;background:var(--gold)}
.lcard-rank{position:absolute;top:10px;right:12px;font-size:20px;font-weight:800;
  color:rgba(255,255,255,.08);line-height:1}
.lcard-rank.top3{color:rgba(210,153,34,.25)}
.lcard-name{font-size:13px;font-weight:700;color:var(--text);line-height:1.2;padding-right:32px}
.lcard-team{font-size:10px;color:var(--text2);margin-top:2px}
.lcard-stat{font-size:26px;font-weight:800;color:var(--canada);margin-top:8px;line-height:1}
.lcard-sub{font-size:10px;color:var(--text3);margin-top:5px}
.lcard-bar{height:3px;border-radius:2px;background:var(--border);margin-top:10px}
.lcard-bar-fill{height:100%;border-radius:2px;background:linear-gradient(90deg,#ffe680,#e0b400)}
.leader-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px}
.pt-tbl{width:100%;border-collapse:collapse;font-size:11.5px}
.pt-tbl th{background:var(--bg3);color:var(--text2);font-weight:600;padding:7px 8px;
  text-align:right;white-space:nowrap;border-bottom:1px solid var(--border);font-size:10px;cursor:pointer}
.pt-tbl th:first-child{text-align:left}
.pt-tbl td{padding:6px 8px;text-align:right;border-bottom:1px solid var(--border)}
.pt-tbl td:first-child{text-align:left;color:var(--text2)}
.poss-cell{background:rgba(255,209,0,.18);color:var(--canada);font-weight:700;border-radius:3px;padding:2px 6px}
/* Percentile rows */
.pct-row{display:flex;align-items:center;gap:8px;padding:6px 0;border-bottom:1px solid rgba(48,54,61,.5)}
.pct-row:last-child{border-bottom:none}
.pct-label{flex:0 0 130px;font-size:11px;color:var(--text2);font-weight:500}
.pct-val{flex:0 0 55px;text-align:right;font-size:12px;font-weight:700;color:var(--text)}
.pct-rank{flex:0 0 58px;text-align:right;font-size:10px;color:var(--text3);font-weight:600}
.pct-track{flex:1;height:10px;background:var(--bg3);border-radius:5px;overflow:hidden;min-width:60px}
.pct-fill{height:100%;border-radius:5px}
.tier-chip{flex:0 0 22px;height:22px;border-radius:4px;font-size:10px;font-weight:800;
  display:flex;align-items:center;justify-content:center;color:#000}
/* Tier badges */
.tier-S{background:#7c3aed;color:#fff}
.tier-A{background:#16a34a;color:#fff}
.tier-B{background:#2563eb;color:#fff}
.tier-C{background:#d97706;color:#fff}
.tier-D{background:#dc2626;color:#fff}
/* Quality filter bar */
.qual-bar{display:flex;align-items:center;gap:8px;padding:6px 20px;background:var(--bg2);border-bottom:1px solid var(--border);flex-shrink:0}
/* Competition tier chips (T1/T2/T3) */
.tcmp-chip{display:inline-block;font-size:9px;font-weight:800;padding:1px 5px;border-radius:3px;vertical-align:middle;line-height:1.5}
.tcmp-1{background:#7c3aed;color:#fff}
.tcmp-2{background:#2563eb;color:#fff}
.tcmp-3{background:#6b7280;color:#fff}
/* Radar chart */
.radar-wrap{display:flex;justify-content:center;padding:8px}
/* Auto analysis */
.analysis-box{display:flex;gap:12px;flex-wrap:wrap}
.analysis-col{flex:1;min-width:180px;background:var(--bg3);border-radius:var(--radius);padding:12px 14px;border:1px solid var(--border)}
.analysis-col-title{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.6px;margin-bottom:8px}
.analysis-item{font-size:11px;color:var(--text);padding:3px 0;display:flex;align-items:center;gap:6px}
.analysis-item::before{content:'';display:inline-block;width:6px;height:6px;border-radius:50%;flex-shrink:0}
.analysis-strength::before{background:var(--green)}
.analysis-weakness::before{background:var(--red)}
/* Net rating */
.net-panel{display:flex;gap:12px;margin-bottom:16px}
.net-box{flex:1;padding:18px 16px;text-align:center;background:var(--bg2);border:1px solid var(--border);border-radius:var(--radius)}
.net-label{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.8px;color:var(--text3);margin-bottom:6px}
.net-val{font-size:32px;font-weight:800;line-height:1.1;margin-bottom:4px}
.net-rank{font-size:11px;color:var(--text2);margin-bottom:8px}
.net-tier{display:inline-block;padding:4px 16px;border-radius:20px;font-size:11px;font-weight:800;letter-spacing:.5px}
/* Extreme cards */
.extreme-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px;margin-bottom:16px}
.extreme-card{background:var(--bg3);border:1px solid var(--border);border-radius:var(--radius);padding:12px 14px}
.extreme-card-title{font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:.7px;color:var(--text3);margin-bottom:6px}
.extreme-card-name{font-size:13px;font-weight:700;color:var(--text)}
.extreme-card-val{font-size:20px;font-weight:800;color:var(--canada);margin-top:4px}
.extreme-card-sub{font-size:10px;color:var(--text3);margin-top:3px}
/* Profile stats */
.pi-stat-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:10px;margin-bottom:16px}
.pi-stat{background:var(--bg3);border:1px solid var(--border);border-radius:var(--radius);padding:10px 12px}
.pi-stat-n{font-size:22px;font-weight:800;color:var(--canada);line-height:1}
.pi-stat-l{font-size:10px;color:var(--text2);margin-top:3px;font-weight:500}
.pi-stat-rank{font-size:9px;color:var(--text3);margin-top:2px}
/* Play type vs league avg */
.pt-vs{display:inline-block;font-size:9px;font-weight:700;padding:1px 4px;border-radius:3px;margin-left:4px}
.pt-vs-up{background:rgba(63,185,80,.2);color:#3fb950}
.pt-vs-dn{background:rgba(248,81,73,.2);color:#f85149}
.empty{text-align:center;padding:48px;color:var(--text3);font-size:13px}
::-webkit-scrollbar{width:6px;height:6px}
::-webkit-scrollbar-track{background:var(--bg2)}
::-webkit-scrollbar-thumb{background:var(--border2);border-radius:3px}
/* Search */
.search-wrap{position:relative;margin-left:16px}
.search-input{background:var(--bg3);border:1px solid var(--border);border-radius:6px;
  padding:5px 10px 5px 28px;font-size:12px;color:var(--text);width:190px;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='13' height='13' viewBox='0 0 24 24' fill='none' stroke='%238b949e' stroke-width='2.5'%3E%3Ccircle cx='11' cy='11' r='8'/%3E%3Cpath d='m21 21-4.35-4.35'/%3E%3C/svg%3E");
  background-repeat:no-repeat;background-position:8px center;transition:border-color .15s}
.search-input::placeholder{color:var(--text3)}
.search-input:focus{outline:none;border-color:var(--canada)}
.search-dropdown{position:absolute;top:calc(100% + 4px);right:0;width:310px;
  background:var(--bg2);border:1px solid var(--border);border-radius:var(--radius);
  z-index:300;max-height:380px;overflow-y:auto;box-shadow:0 8px 32px rgba(0,0,0,.55);display:none}
.search-item{padding:8px 14px;cursor:pointer;border-bottom:1px solid var(--border)}
.search-item:hover{background:var(--bg3)}
.search-item-name{font-size:12px;font-weight:600;color:var(--text)}
.search-item-sub{font-size:10px;color:var(--text2);margin-top:2px}
.search-shdr{padding:4px 14px;font-size:9px;font-weight:700;color:var(--text3);
  text-transform:uppercase;letter-spacing:.8px;background:var(--bg3);border-bottom:1px solid var(--border)}
/* Scatter */
.scatter-wrap{overflow-x:auto;padding:4px 0}
/* Player compare */
.cmp-row{display:grid;grid-template-columns:1fr auto 1fr;align-items:center;
  gap:0;padding:7px 0;border-bottom:1px solid rgba(48,54,61,.5)}
.cmp-row:last-child{border-bottom:none}
.cmp-a{text-align:right;padding-right:12px;font-size:13px;font-weight:700}
.cmp-b{text-align:left;padding-left:12px;font-size:13px;font-weight:700}
.cmp-label{text-align:center;font-size:10px;font-weight:600;color:var(--text3);white-space:nowrap;padding:0 8px}
.cmp-rank{font-size:9px;color:var(--text3);font-weight:400}
/* Tier dist bar */
.tier-dist-wrap{display:flex;align-items:flex-end;justify-content:space-around;height:110px;padding:0 16px}
.tier-dist-col{display:flex;flex-direction:column;align-items:center;gap:4px;flex:1;max-width:80px}
.tier-dist-bar{width:60%;border-radius:4px 4px 0 0;min-height:4px}
/* Play type explorer chips */
.pt-chip{display:inline-block;padding:4px 12px;font-size:12px;font-weight:600;
  border-radius:20px;cursor:pointer;border:1px solid var(--border);background:var(--bg3);
  color:var(--text2);transition:all .15s;white-space:nowrap}
.pt-chip.active{background:var(--gold);border-color:var(--gold);color:#000;font-weight:700}
.pt-chips{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:16px}
.pulse-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin-bottom:16px}
.pulse-card{background:var(--bg3);border:1px solid var(--border);border-radius:var(--radius);padding:12px 14px;text-align:center}
.pulse-card-n{font-size:22px;font-weight:800;color:var(--text);line-height:1}
.pulse-card-l{font-size:10px;color:var(--text2);margin-top:4px}
.pulse-card-sub{font-size:9px;color:var(--text3);margin-top:2px}
.section-hdr{font-size:11px;font-weight:700;color:var(--text2);text-transform:uppercase;
  letter-spacing:.8px;margin-bottom:10px;margin-top:4px;display:flex;align-items:center;gap:8px}
.section-hdr::after{content:'';flex:1;height:1px;background:var(--border)}
.home-row td{background:rgba(255,209,0,.16)}
.matchup-bar-row{display:grid;grid-template-columns:90px 1fr 90px 1fr 90px;align-items:center;gap:0;margin-bottom:4px}
"""

HTML_BODY = """
<div class="app">
<div class="topbar">
  <div class="logo">
    <img src="{LOGO_SRC}" alt="Waterloo Warriors">
    <div class="logo-text">
      <span class="logo-main">Waterloo Warriors</span>
      <span class="logo-sub">Women's Basketball &middot; U SPORTS Analytics{UPDATED}</span>
    </div>
    <span class="logo-badge">{SEASON}</span>
  </div>
  <div class="topstats" id="topstats"></div>
  <div class="search-wrap">
    <input id="search-input" class="search-input" type="text" placeholder="Search team or player..."
      oninput="globalSearch(this.value)" onblur="setTimeout(function(){document.getElementById('search-dropdown').style.display='none';},180)">
    <div id="search-dropdown" class="search-dropdown"></div>
  </div>
</div>
<nav class="nav">
  <button class="nav-btn active" onclick="showTab('overview',this)">&#127760; Overview</button>
  <button class="nav-btn" onclick="showTab('team-rank',this)">&#127942; Team Rankings</button>
  <button class="nav-btn" onclick="showTab('player-rank',this)">&#128100; Player Rankings</button>
  <button class="nav-btn" onclick="showTab('matchup',this)">&#9876;&#65039; Matchup</button>
  <button class="nav-btn" onclick="showTab('team-intel',this)">&#129302; Team Intel</button>
  <button class="nav-btn" onclick="showTab('player-intel',this)">&#127775; Player Intel</button>
  <button class="nav-btn" onclick="showTab('player-compare',this)">&#9878;&#65039; P vs P</button>
  <button class="nav-btn" onclick="showTab('play-types',this)">&#127919; Play Types</button>
</nav>
<div class="qual-bar">
  <span style="font-size:10px;font-weight:700;letter-spacing:.5px;text-transform:uppercase;color:var(--text3)">Conference:</span>
  <div class="toggle-group" id="conf-group">
    <button class="toggle-btn active" onclick="setConf('',this)">All U SPORTS</button>
    <button class="toggle-btn" onclick="setConf('CW',this)">Canada West</button>
    <button class="toggle-btn" onclick="setConf('OUA',this)">OUA</button>
    <button class="toggle-btn" onclick="setConf('RSEQ',this)">RSEQ</button>
    <button class="toggle-btn" onclick="setConf('AUS',this)">AUS</button>
  </div>
  <span id="qual-label" style="font-size:10px;color:var(--text3);margin-left:4px">Ranks (#) are always vs all U SPORTS teams</span>
</div>
<div class="content">

<!-- OVERVIEW -->
<div class="tab active" id="tab-overview">
  <div class="stat-cards" id="ov-cards"></div>
  <div class="section-hdr">League Pulse</div>
  <div class="pulse-grid" id="ov-pulse"></div>
  <div class="section-hdr" style="display:flex;align-items:center;justify-content:space-between">
    <span>Offensive Extremes</span>
  </div>
  <div class="extreme-grid" id="ov-extremes"></div>
  <div class="grid2">
    <div class="card"><div class="card-hdr"><span class="accent">&#9651;</span> Top 10 Offense &mdash; PPP</div><div class="card-body" id="ov-top-off"></div></div>
    <div class="card"><div class="card-hdr"><span class="accent">&#9661;</span> Top 10 Defense &mdash; PPP Allowed</div><div class="card-body" id="ov-top-def"></div></div>
  </div>
  <div class="section-hdr">Play Type League Profile</div>
  <div class="grid2">
    <div class="card"><div class="card-hdr">Frequency &mdash; % of Possessions</div><div class="card-body" id="ov-pt-freq"></div></div>
    <div class="card"><div class="card-hdr">Efficiency &mdash; League Avg PPP</div><div class="card-body" id="ov-pt-ppp"></div></div>
  </div>
  <div class="section-hdr">Team Efficiency Map <span style="font-weight:400;text-transform:none;color:var(--text3);font-size:10px">&mdash; click any dot to open Team Intel</span></div>
  <div class="card">
    <div class="card-hdr" style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px">
      <span><span class="accent">&#9677;</span> Offensive PPP vs Defensive PPP &mdash; colored by net rating</span>
    </div>
    <div class="card-body scatter-wrap" id="ov-scatter"></div>
  </div>
  <div class="grid2" style="align-items:stretch">
    <div style="display:flex;flex-direction:column">
      <div class="section-hdr">Efficiency Tier Distribution <span style="font-weight:400;text-transform:none;color:var(--text3);font-size:10px">(by net rating)</span></div>
      <div class="card" style="flex:1;display:flex;flex-direction:column"><div class="card-body" style="flex:1;display:flex;flex-direction:column" id="ov-tier-dist"></div></div>
    </div>
    <div style="display:flex;flex-direction:column">
      <div class="section-hdr">Shot Quality</div>
      <div class="card" style="flex:1"><div class="card-body" id="ov-shot-quality"></div></div>
    </div>
  </div>
  <div class="section-hdr">Individual Leaders</div>
  <div class="grid2">
    <div class="card"><div class="card-hdr">PPP Leaders <span style="font-weight:400;text-transform:none;color:var(--text3)">(min 30 poss)</span></div><div class="card-body" id="ov-ppp-leaders"></div></div>
    <div class="card"><div class="card-hdr">EFG% Leaders <span style="font-weight:400;text-transform:none;color:var(--text3)">(min 30 FGA)</span></div><div class="card-body" id="ov-efg-leaders"></div></div>
  </div>
  <div class="grid2">
    <div class="card"><div class="card-hdr">Volume Leaders &mdash; Possessions</div><div class="card-body" id="ov-vol-leaders"></div></div>
    <div class="card"><div class="card-hdr">Best Ball Security <span style="font-weight:400;text-transform:none;color:var(--text3)">(min 40 poss)</span></div><div class="card-body" id="ov-to-leaders"></div></div>
  </div>
</div>

<!-- TEAM RANKINGS -->
<div class="tab" id="tab-team-rank">
  <div class="controls">
    <div class="toggle-group">
      <button class="toggle-btn active" id="tr-off" onclick="setTRSide('off',this)">Offense</button>
      <button class="toggle-btn" id="tr-def" onclick="setTRSide('def',this)">Defense</button>
    </div>
    <label style="font-size:11px;color:var(--text2)">Min GP:
      <select class="sel" id="tr-min-gp" onchange="renderTeamRank()">
        <option value="0" selected>All</option><option value="3">3+</option>
        <option value="6">6+</option><option value="10">10+</option>
      </select>
    </label>
  </div>
  <div class="card"><div class="tbl-wrap"><table id="tr-tbl">
    <thead><tr>
      <th>#</th><th onclick="sortTR('name')">Team</th><th onclick="sortTR('gp')">GP</th>
      <th onclick="sortTR('poss')">POSS</th><th onclick="sortTR('pace')">PACE</th>
      <th onclick="sortTR('ppp')" class="sorted">PPP</th>
      <th onclick="sortTR('fg')">FG%</th><th onclick="sortTR('efg')">EFG%</th>
      <th onclick="sortTR('fg2')">2FG%</th><th onclick="sortTR('fg3')">3FG%</th>
      <th onclick="sortTR('3rate')">3PA%</th>
      <th onclick="sortTR('to')">TO%</th><th onclick="sortTR('ftr')">FTR</th>
      <th onclick="sortTR('ts')">TS%</th>
    </tr></thead>
    <tbody id="tr-body"></tbody>
  </table></div></div>
</div>

<!-- PLAYER RANKINGS -->
<div class="tab" id="tab-player-rank">
  <div class="controls">
    <label style="font-size:11px;color:var(--text2)">Min GP:
      <select class="sel" id="pr-min-gp" onchange="renderPlayerRank()">
        <option value="0">All</option><option value="3">3+</option>
        <option value="5" selected>5+</option><option value="10">10+</option>
      </select>
    </label>
    <label style="font-size:11px;color:var(--text2)">Min POSS:
      <select class="sel" id="pr-min-poss" onchange="renderPlayerRank()">
        <option value="0">All</option><option value="15">15+</option>
        <option value="30" selected>30+</option><option value="60">60+</option>
      </select>
    </label>
    <label style="font-size:11px;color:var(--text2)">Team:
      <select class="sel" id="pr-team" onchange="renderPlayerRank()"><option value="">All Teams</option></select>
    </label>
    <label style="font-size:11px;color:var(--text2)">Play Type:
      <select class="sel" id="pr-pt" onchange="renderPlayerRank()"><option value="">Overall</option></select>
    </label>
  </div>
  <div class="card"><div class="tbl-wrap"><table id="pr-tbl">
    <thead><tr>
      <th>#</th><th onclick="sortPR('name')">Player</th><th onclick="sortPR('team')">Team</th><th>Conf</th>
      <th onclick="sortPR('gp')">GP</th><th onclick="sortPR('poss')">POSS</th><th onclick="sortPR('ppg')">PPG</th>
      <th onclick="sortPR('ppp')" class="sorted">PPP</th>
      <th onclick="sortPR('fg')">FG%</th><th onclick="sortPR('efg')">EFG%</th>
      <th onclick="sortPR('fg2')">2FG%</th><th onclick="sortPR('a2')">2FGA</th>
      <th onclick="sortPR('fg3')">3FG%</th><th onclick="sortPR('a3')">3FGA</th>
      <th onclick="sortPR('to')">TO%</th><th onclick="sortPR('ts')">TS%</th>
    </tr></thead>
    <tbody id="pr-body"></tbody>
  </table></div></div>
</div>

<!-- MATCHUP -->
<div class="tab" id="tab-matchup">
  <div class="team-select-row">
    <select class="sel" id="mu-a" onchange="renderMatchup()" style="flex:1"><option value="">-- Team A --</option></select>
    <span style="color:var(--text3);font-weight:800;font-size:20px">VS</span>
    <select class="sel" id="mu-b" onchange="renderMatchup()" style="flex:1"><option value="">-- Team B --</option></select>
  </div>
  <div id="mu-content"><div class="empty">Select two teams to compare</div></div>
</div>

<!-- TEAM INTEL -->
<div class="tab" id="tab-team-intel">
  <div class="team-select-row">
    <select class="sel" id="ti-team" onchange="renderTeamIntel()" style="flex:1"><option value="">-- Select Team --</option></select>
  </div>
  <div id="ti-content"><div class="empty">Select a team to explore</div></div>
</div>

<!-- PLAYER INTEL -->
<div class="tab" id="tab-player-intel">
  <div class="team-select-row">
    <select class="sel" id="pi-team" onchange="populatePiPlayers()" style="flex:1"><option value="">-- Team --</option></select>
    <select class="sel" id="pi-player" onchange="renderPlayerIntel()" style="flex:1"><option value="">-- Player --</option></select>
  </div>
  <div id="pi-content"><div class="empty">Select a team and player</div></div>
</div>

<!-- PLAYER COMPARE -->
<div class="tab" id="tab-player-compare">
  <div class="team-select-row">
    <select class="sel" id="pc-a" onchange="renderPlayerCompare()" style="flex:1"><option value="">-- Player A --</option></select>
    <span style="color:var(--text3);font-weight:800;font-size:18px">VS</span>
    <select class="sel" id="pc-b" onchange="renderPlayerCompare()" style="flex:1"><option value="">-- Player B --</option></select>
  </div>
  <div id="pc-content"><div class="empty">Select two players to compare</div></div>
</div>

<!-- PLAY TYPE EXPLORER -->
<div class="tab" id="tab-play-types">
  <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;margin-bottom:10px">
    <div class="pt-chips" id="pte-chips" style="margin-bottom:0"></div>
    <div style="display:flex;align-items:center;gap:6px;font-size:11px;color:var(--text3);flex-shrink:0">
      <span style="font-weight:700;text-transform:uppercase;letter-spacing:.4px">GP Min:</span>
      <div class="toggle-group">
        <button class="toggle-btn active" id="pt-gp-0" onclick="setPTGP(0,this)">All</button>
        <button class="toggle-btn" id="pt-gp-3" onclick="setPTGP(3,this)">3</button>
        <button class="toggle-btn" id="pt-gp-5" onclick="setPTGP(5,this)">5</button>
        <button class="toggle-btn" id="pt-gp-8" onclick="setPTGP(8,this)">8</button>
      </div>
    </div>
  </div>
  <div class="grid2">
    <div>
      <div class="section-hdr">Team Rankings</div>
      <div class="card"><div class="card-body" id="pte-teams"><div class="empty">Select a play type</div></div></div>
    </div>
    <div>
      <div class="section-hdr">Individual Leaders</div>
      <div class="card"><div class="card-body" id="pte-players"><div class="empty">Select a play type</div></div></div>
    </div>
  </div>
</div>

</div></div>
"""

JS = r"""
// ── Stat helpers ──────────────────────────────────────────────────────────────
var ppp  = function(d){ return d&&d.p>0  ? d.pts/d.p     : 0; };
var fg   = function(d){ return d&&d.fa>0 ? d.fm/d.fa*100  : 0; };
var efg  = function(d){ return d&&d.fa>0 ? (d.fm+0.5*d.m3)/d.fa*100 : 0; };
var fg2  = function(d){ return d&&d.a2>0 ? d.m2/d.a2*100  : 0; };
var fg3  = function(d){ return d&&d.a3>0 ? d.m3/d.a3*100  : 0; };
var topR = function(d){ return d&&d.p>0  ? d.to/d.p*100   : 0; };
var ftr  = function(d){ return d&&d.p>0  ? d.ftt/d.p*100  : 0; };
var ts   = function(d){ var dn=2*(d.fa+0.44*d.fta);return dn>0?d.pts/dn*100:0; };
var pps  = function(d){ return d&&d.sa>0 ? d.pts/d.sa : 0; };
var pace = function(t){ return t.gp>0 ? t.off.p/t.gp : 0; };
var rate3= function(d){ return d&&d.fa>0 ? d.a3/d.fa*100 : 0; };
var net  = function(t){ return ppp(t.off)-ppp(t.def); };

function f1(v)  { return (!isFinite(v)||isNaN(v))?'—':v.toFixed(1); }
function f3(v)  { return (!isFinite(v)||isNaN(v))?'—':v.toFixed(3); }
function fP(v)  { return (!isFinite(v)||isNaN(v))?'—':v.toFixed(1)+'%'; }
function f3n(v) { return (!isFinite(v)||isNaN(v))?0:parseFloat(v.toFixed(3)); }
function esc(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}

// League PPP calibration: thresholds below were tuned at a league PPP of 0.81.
var LEAGUE_PPP=(function(){var p=0,n=0;TEAMS.forEach(function(t){p+=t.off.pts||0;n+=t.off.p||0;});return n?p/n:0.81;})();
var PPP_SCALE=LEAGUE_PPP/0.81;
// ── Color helpers ─────────────────────────────────────────────────────────────
function cPPP(v){ v=v/PPP_SCALE;
  if(v>=1.10) return 'hot'; if(v>=0.92) return 'warm';
  if(v>=0.72) return 'cool'; if(v>0) return 'cold'; return '';
}
function cPPPD(v){ v=v/PPP_SCALE;
  if(v<=0) return '';
  if(v<=0.78) return 'hot'; if(v<=0.88) return 'warm';
  if(v<=1.02) return ''; if(v<=1.12) return 'cool'; return 'cold';
}
function cPct(v,hi,lo){ hi=hi||50;lo=lo||33;
  if(!v) return '';
  if(v>=hi) return 'hot'; if(v>=(hi+lo)/2) return 'warm';
  if(v>=lo) return ''; return 'cool';
}
function cTO(v){
  if(!v) return '';
  if(v<=11) return 'hot'; if(v<=15) return 'warm';
  if(v<=20) return ''; return 'cool';
}

// ── Tier system ───────────────────────────────────────────────────────────────
function tierStr(pct){
  if(pct>=90) return 'S'; if(pct>=75) return 'A';
  if(pct>=50) return 'B'; if(pct>=25) return 'C'; return 'D';
}
function tierCol(pct){
  if(pct>=90) return '#7c3aed'; if(pct>=75) return '#16a34a';
  if(pct>=50) return '#2563eb'; if(pct>=25) return '#d97706'; return '#dc2626';
}
function tierTxtCol(pct){ return '#fff'; }

function pppRating(v){ v=v/PPP_SCALE;
  if(v>=1.10) return 'Elite'; if(v>=0.95) return 'Very Good';
  if(v>=0.85) return 'Good';  if(v>=0.75) return 'Average';
  if(v>=0.60) return 'Below Avg'; return 'Poor';
}
function pppRatingColor(v){ v=v/PPP_SCALE;
  if(v>=1.05) return '#16a34a'; if(v>=0.90) return '#4ade80';
  if(v>=0.80) return '#6b7280'; if(v>=0.70) return '#c2410c'; return '#dc2626';
}

// ── Country theme colours ─────────────────────────────────────────────────────
var COUNTRY_COLORS = {
  'Canada':'#d4a900','USA':'#002868','United States':'#002868',
  'France':'#002395','Spain':'#c60b1e','Australia':'#00843d',
  'China':'#de2910','Belgium':'#000000','Argentina':'#74acdf',
  'Brazil':'#009c3b','Germany':'#000000','Japan':'#bc002d',
  'South Korea':'#003478','Korea':'#003478','Italy':'#009246',
  'Greece':'#0d5eaf','Nigeria':'#008751','Serbia':'#c6363c',
  'Hungary':'#436f4d','Czech Republic':'#d7141a','Sweden':'#006aa7',
  'Poland':'#dc143c','Romania':'#002b7f','Croatia':'#171796',
  'Turkey':'#e30a17','Israel':'#0038b8','Russia':'#d4a900',
  'Netherlands':'#ff6600','Portugal':'#006600','Latvia':'#9e3039',
  'Lithuania':'#fdba12','Ukraine':'#005bbb','Belarus':'#cf101a',
  'Bulgaria':'#00966e','Switzerland':'#ff0000','Austria':'#ed2939',
  'Norway':'#ef2b2d','Denmark':'#c60c30','Finland':'#003580',
  'Slovakia':'#005da4','Slovenia':'#003da5','Bosnia':'#002395',
  'Montenegro':'#d4af37','North Macedonia':'#ce2028','Albania':'#e41e20',
  'Moldova':'#003DA5','Estonia':'#0072ce','Georgia':'#ff0000',
  'Angola':'#cc0000','Mozambique':'#009a44','Senegal':'#00853f',
  'Mali':'#14b53a','Cameroon':'#007a5e','Egypt':'#c8102e',
  'South Africa':'#007a4d','Kenya':'#006600','Rwanda':'#20603d',
  'Morocco':'#c1272d','Tunisia':'#e70013','Algeria':'#006233',
  'Philippines':'#0038a8','Indonesia':'#ce1126','Thailand':'#a51931',
  'India':'#ff9933','Iran':'#239f40','Kazakhstan':'#00afca',
  'Mongolia':'#c4272f','Taiwan':'#003087','Chinese Taipei':'#003087',
  'Tahiti':'#009a44','Cook Islands':'#003087','New Zealand':'#00247d',
  'Puerto Rico':'#ed0c27','Cuba':'#002a8f','Mexico':'#006847',
  'Colombia':'#fcd116','Venezuela':'#cf142b','Peru':'#d91023',
  'Chile':'#d4a900','Ecuador':'#ffd100','Uruguay':'#5EB6E4',
};
function countryColor(name){ return 'var(--ink)'; }

// ── Global rank tables ────────────────────────────────────────────────────────
var TR = {}, PR = {};  // TR[team_id][key]=rank, PR[player_id][key]=rank

var TEAM_STAT_DEFS = [
  {key:'off_ppp',  lb:false, fn:function(t){return ppp(t.off);}},
  {key:'def_ppp',  lb:true,  fn:function(t){return ppp(t.def);}},
  {key:'net',      lb:false, fn:function(t){return net(t);}},
  {key:'pace',     lb:false, fn:function(t){return pace(t);}},
  {key:'off_efg',  lb:false, fn:function(t){return efg(t.off);}},
  {key:'def_efg',  lb:true,  fn:function(t){return efg(t.def);}},
  {key:'off_fg2',  lb:false, fn:function(t){return fg2(t.off);}},
  {key:'def_fg2',  lb:true,  fn:function(t){return fg2(t.def);}},
  {key:'off_fg3',  lb:false, fn:function(t){return fg3(t.off);}},
  {key:'def_fg3',  lb:true,  fn:function(t){return fg3(t.def);}},
  {key:'off_3rate',lb:false, fn:function(t){return rate3(t.off);}},
  {key:'off_to',   lb:true,  fn:function(t){return topR(t.off);}},
  {key:'def_to',   lb:false, fn:function(t){return topR(t.def);}},  // higher = forces more TOs
  {key:'off_ftr',  lb:false, fn:function(t){return ftr(t.off);}},
  {key:'off_ts',   lb:false, fn:function(t){return ts(t.off);}},
  {key:'off_pps',  lb:false, fn:function(t){return pps(t.off);}},
];
var PLAYER_STAT_DEFS = [
  {key:'ppp', lb:false, fn:function(p){return ppp(p.off);}},
  {key:'efg', lb:false, fn:function(p){return efg(p.off);}},
  {key:'fg2', lb:false, fn:function(p){return fg2(p.off);}},
  {key:'fg3', lb:false, fn:function(p){return fg3(p.off);}},
  {key:'to',  lb:true,  fn:function(p){return topR(p.off);}},
  {key:'ts',  lb:false, fn:function(p){return ts(p.off);}},
  {key:'vol', lb:false, fn:function(p){return p.off.p||0;}},
  {key:'ftr', lb:false, fn:function(p){return ftr(p.off);}},
];
var PPG_POOL_SIZE = 0;

function computeRanks() {
  var validT = TEAMS.filter(function(t){return t.off.p>0;});
  TEAM_STAT_DEFS.forEach(function(def){
    var sorted = validT.slice().sort(function(a,b){
      return def.lb ? def.fn(a)-def.fn(b) : def.fn(b)-def.fn(a);
    });
    sorted.forEach(function(t,i){
      if(!TR[t.id]) TR[t.id]={};
      TR[t.id][def.key]=i+1;
    });
    // Within-conference ranks
    CONFS.forEach(function(cf){
      var tierT=validT.filter(function(t){return t.conf===cf;});
      var ts=tierT.slice().sort(function(a,b){return def.lb?def.fn(a)-def.fn(b):def.fn(b)-def.fn(a);});
      ts.forEach(function(t,i){
        TR[t.id]['t_'+def.key]=i+1;
        TR[t.id]['t_size']=tierT.length;
      });
    });
  });
  var pool = PLAYERS.filter(function(p){return p.off.p>=15;});
  PLAYER_STAT_DEFS.forEach(function(def){
    var sorted = pool.slice().sort(function(a,b){
      return def.lb ? def.fn(a)-def.fn(b) : def.fn(b)-def.fn(a);
    });
    sorted.forEach(function(p,i){
      if(!PR[p.id]) PR[p.id]={};
      PR[p.id][def.key]=i+1;
    });
  });
  // PPG ranks use boxscore pool (players with ppg > 0)
  var ppgPool = PLAYERS.filter(function(p){return p.ppg>0;});
  PPG_POOL_SIZE = ppgPool.length;
  ppgPool.slice().sort(function(a,b){return b.ppg-a.ppg;}).forEach(function(p,i){
    if(!PR[p.id]) PR[p.id]={};
    PR[p.id]['ppg']=i+1;
  });
}

// rank → percentile (0-100, 100 = best)
function rPct(rank, total){ return rank&&total ? Math.round((total-rank)/total*100) : 50; }

function pctRow(label, val, rank, total) {
  var pct = rPct(rank, total);
  var col = tierCol(pct);
  var t = tierStr(pct);
  var txtCol = tierTxtCol(pct);
  return '<div class="pct-row">'+
    '<div class="pct-label">'+label+'</div>'+
    '<div class="pct-val">'+val+'</div>'+
    '<div class="pct-rank">#'+rank+'/'+total+'</div>'+
    '<div class="pct-track"><div class="pct-fill" style="width:'+pct+'%;background:'+col+'"></div></div>'+
    '<div class="tier-chip tier-'+t+'" style="background:'+col+';color:'+txtCol+'">'+t+'</div>'+
    '</div>';
}

function tierBadge(pct) {
  var t=tierStr(pct), col=tierCol(pct), tc=tierTxtCol(pct);
  return '<span class="tier-chip tier-'+t+'" style="background:'+col+';color:'+tc+';font-size:11px;padding:2px 8px;border-radius:4px;font-weight:800">'+t+'</span>';
}

// ── Radar chart ───────────────────────────────────────────────────────────────
function radarSvg(vals, labels, color) {
  // vals: array of 0-100 percentile values
  var n=vals.length, sz=220, cx=sz/2, cy=sz/2, r=75;
  color = color||'linear-gradient(90deg,#ffe680,#e0b400)';
  var svg='<svg width="'+sz+'" height="'+sz+'" viewBox="0 0 '+sz+' '+sz+'" style="overflow:visible">';
  // grid rings
  [0.25,0.5,0.75,1.0].forEach(function(ring){
    var pts=[];
    for(var i=0;i<n;i++){
      var a=(i/n)*Math.PI*2-Math.PI/2;
      pts.push((cx+Math.cos(a)*r*ring).toFixed(1)+','+(cy+Math.sin(a)*r*ring).toFixed(1));
    }
    svg+='<polygon points="'+pts.join(' ')+'" fill="none" stroke="#30363d" stroke-width="'+(ring===1?1.5:0.8)+'"/>';
  });
  // axes
  for(var i=0;i<n;i++){
    var a=(i/n)*Math.PI*2-Math.PI/2;
    svg+='<line x1="'+cx+'" y1="'+cy+'" x2="'+(cx+Math.cos(a)*r).toFixed(1)+'" y2="'+(cy+Math.sin(a)*r).toFixed(1)+'" stroke="#484f58" stroke-width="1"/>';
  }
  // data
  var pts=[];
  for(var i=0;i<n;i++){
    var a=(i/n)*Math.PI*2-Math.PI/2;
    var rv=r*(vals[i]/100);
    pts.push((cx+Math.cos(a)*rv).toFixed(1)+','+(cy+Math.sin(a)*rv).toFixed(1));
  }
  svg+='<polygon points="'+pts.join(' ')+'" fill="'+color+'22" stroke="'+color+'" stroke-width="2"/>';
  // dots
  for(var i=0;i<n;i++){
    var a=(i/n)*Math.PI*2-Math.PI/2;
    var rv=r*(vals[i]/100);
    svg+='<circle cx="'+(cx+Math.cos(a)*rv).toFixed(1)+'" cy="'+(cy+Math.sin(a)*rv).toFixed(1)+'" r="3.5" fill="'+color+'"/>';
  }
  // labels
  for(var i=0;i<n;i++){
    var a=(i/n)*Math.PI*2-Math.PI/2;
    var lx=(cx+Math.cos(a)*(r+18)).toFixed(1);
    var ly=(cy+Math.sin(a)*(r+18)).toFixed(1);
    var anchor = Math.abs(Math.cos(a))<0.1?'middle':Math.cos(a)>0?'start':'end';
    svg+='<text x="'+lx+'" y="'+ly+'" text-anchor="'+anchor+'" dominant-baseline="middle" fill="#8b949e" font-size="9" font-weight="600">'+labels[i]+'</text>';
  }
  svg+='</svg>';
  return svg;
}

// ── Auto analysis ──────────────────────────────────────────────────────────────
function autoAnalysis(t) {
  var N=TEAMS.length, r=TR[t.id]||{};
  var defs=[
    {key:'off_ppp',  s:'Offense — PPP',               w:'Offense — PPP'},
    {key:'def_ppp',  s:'Defense — PPP allowed',        w:'Defense — PPP allowed'},
    {key:'off_efg',  s:'Shooting efficiency (EFG%)',   w:'Shooting efficiency (EFG%)'},
    {key:'off_fg3',  s:'3-point shooting',             w:'3-point shooting'},
    {key:'off_fg2',  s:'Paint finishing (2FG%)',        w:'Paint finishing (2FG%)'},
    {key:'off_to',   s:'Ball security (TO%)',           w:'Ball security (TO%)'},
    {key:'off_ftr',  s:'Foul drawing (FT Rate)',        w:'Foul drawing (FT Rate)'},
    {key:'def_to',   s:'Pressure / forced TOs',        w:'Pressure / forced TOs'},
    {key:'def_efg',  s:'Perimeter defense (EFG% allowed)', w:'Perimeter defense (EFG% allowed)'},
    {key:'pace',     s:'Pace / tempo',                 w:'Pace / tempo'},
    {key:'net',      s:'Net efficiency',               w:'Net efficiency'},
  ];
  var scored=[];
  defs.forEach(function(d){
    var rank=r[d.key]; if(!rank) return;
    var pct=rPct(rank, N);
    scored.push({pct:pct, rank:rank, s:d.s, w:d.w});
  });
  scored.sort(function(a,b){return b.pct-a.pct;});
  var TOP=3;
  var strengths=scored.slice(0,TOP).map(function(d){
    return d.s+' <span style="color:var(--text3);font-size:9px">#'+d.rank+'/'+N+'</span>';
  });
  var weaknesses=scored.slice(-TOP).reverse().map(function(d){
    return d.w+' <span style="color:var(--text3);font-size:9px">#'+d.rank+'/'+N+'</span>';
  });
  return {s:strengths, w:weaknesses};
}

// ── Hbar ──────────────────────────────────────────────────────────────────────
function hbar(label, pct, val, color, extraRight) {
  var p=Math.max(pct,0.5);
  return '<div class="hbar-row">'+
    '<div class="hbar-label">'+esc(label)+'</div>'+
    '<div class="hbar-track"><div class="hbar-fill" style="width:'+p.toFixed(1)+'%;background:'+color+'">'+(p>16?val:'')+'</div></div>'+
    '<div class="hbar-val">'+(p<=16?val:'')+(extraRight||'')+'</div></div>';
}

// ── Tab switching ─────────────────────────────────────────────────────────────
function showTab(id,btn){
  document.querySelectorAll('.tab').forEach(function(t){t.classList.remove('active');});
  document.querySelectorAll('.nav-btn').forEach(function(b){b.classList.remove('active');});
  document.getElementById('tab-'+id).classList.add('active');
  btn.classList.add('active');
}
function showSubtab(btn,targetId){
  var parent=btn.closest('.tab')||document.body;
  parent.querySelectorAll('.subtab-btn').forEach(function(b){b.classList.remove('active');});
  parent.querySelectorAll('.subtab').forEach(function(s){s.classList.remove('active');});
  btn.classList.add('active');
  var el=document.getElementById(targetId); if(el) el.classList.add('active');
}

// ── OVERVIEW ─────────────────────────────────────────────────────────────────
function renderOverview(){
  var N=TEAMS.length, NP=PLAYERS.length;
  var totalPts=0,totalPoss=0,totalFGA=0,total3PA=0,totalTO=0,totalFTA=0,totalGP=0;
  for(var i=0;i<N;i++){
    var o=TEAMS[i].off;
    totalPts+=o.pts||0; totalPoss+=o.p||0; totalFGA+=o.fa||0;
    total3PA+=o.a3||0; totalTO+=o.to||0; totalFTA+=o.fta||0;
    totalGP+=TEAMS[i].gp||0;
  }
  var leaguePPP=totalPoss?totalPts/totalPoss:0;
  var leagueEFG=totalFGA?(TEAMS.reduce(function(s,t){return s+t.off.fm;},0)+0.5*TEAMS.reduce(function(s,t){return s+t.off.m3;},0))/totalFGA*100:0;
  var leagueTO=totalPoss?totalTO/totalPoss*100:0;
  var league3Rate=totalFGA?total3PA/totalFGA*100:0;
  var totalGames=(totalGP/2)|0;
  var avgPace=N?totalPoss/totalGP:0;

  // Top banner
  document.getElementById('topstats').innerHTML=
    '<div class="topstat"><div class="topstat-n">'+N+'</div><div class="topstat-l">Teams</div></div>'+
    '<div class="topstat"><div class="topstat-n">'+NP+'</div><div class="topstat-l">Players</div></div>'+
    '<div class="topstat"><div class="topstat-n">~'+totalGames+'</div><div class="topstat-l">Games</div></div>'+
    '<div class="topstat"><div class="topstat-n">'+f3(leaguePPP)+'</div><div class="topstat-l">Avg PPP</div></div>';

  document.getElementById('ov-cards').innerHTML=
    scard(N,'Teams','U SPORTS Women '+SEASON_LABEL)+
    scard(NP,'Players','across '+N+' rosters')+
    scard('~'+totalGames,'Games Played','season total')+
    scard(f3(leaguePPP),'League Avg PPP','offense')+
    scard(fP(leagueEFG),'League EFG%','offense')+
    scard(fP(leagueTO),'League TO%','offense')+
    scard(fP(league3Rate),'3PA Rate','% of FGA')+
    scard(f1(avgPace)+'','Avg Pace','poss / game');

  // Pulse stats (derived)
  var validT=TEAMS.filter(function(t){return t.off.p>0&&inConf(t);});
  var defPoss=TEAMS.reduce(function(s,t){return s+(t.def.p||0);},0);
  var defPts=TEAMS.reduce(function(s,t){return s+(t.def.pts||0);},0);
  var leagueDefPPP=defPoss?defPts/defPoss:0;
  var teams3Heavy=validT.filter(function(t){return rate3(t.off)>=35;}).length;
  var avgNet=validT.reduce(function(s,t){return s+net(t);},0)/validT.length;
  var topPaceT=validT.slice().sort(function(a,b){return pace(b)-pace(a);})[0];
  var topNetT=validT.slice().sort(function(a,b){return net(b)-net(a);})[0];
  var topDefT=validT.filter(function(t){return t.def.p>0;}).sort(function(a,b){return ppp(a.def)-ppp(b.def);})[0];

  document.getElementById('ov-pulse').innerHTML=
    pulse(f1(avgPace),'Avg Pace','possessions per game')+
    pulse(fP(leagueEFG),'League EFG%','offensive efficiency')+
    pulse(f3(leagueDefPPP),'Avg Def PPP','points allowed per poss')+
    pulse(fP(league3Rate),'3PA Rate','% of FGA are 3-pointers')+
    pulse(teams3Heavy+'/'+N,'3PT-Heavy Teams','&#8805;35% 3PA rate')+
    pulse(f1(avgNet),'Avg Net Rating','off PPP minus def PPP');

  // Extremes
  var sorted=validT.slice().sort(function(a,b){return ppp(b.off)-ppp(a.off);});
  var sortedDefF=validT.filter(function(t){return t.def.p>0;}).sort(function(a,b){return ppp(a.def)-ppp(b.def);});
  var sortedTO=validT.slice().sort(function(a,b){return topR(a.off)-topR(b.off);});
  var sorted3=validT.slice().sort(function(a,b){return rate3(b.off)-rate3(a.off);});
  var sortedPace=validT.slice().sort(function(a,b){return pace(b)-pace(a);});
  var sortedFG3=validT.slice().sort(function(a,b){return fg3(b.off)-fg3(a.off);});
  var sortedNet=validT.slice().sort(function(a,b){return net(b)-net(a);});
  document.getElementById('ov-extremes').innerHTML=
    xcard('Most Efficient Off.',sorted[0].name, f3(ppp(sorted[0].off))+' PPP','#'+TR[sorted[0].id]['off_ppp']+' of '+N)+
    xcard('Best Defense',sortedDefF[0]?sortedDefF[0].name:'—', sortedDefF[0]?f3(ppp(sortedDefF[0].def))+' PPP allowed':'', sortedDefF[0]?'#1 def PPP':'')+
    xcard('Best Net Rating',sortedNet[0].name, (net(sortedNet[0])>0?'+':'')+f3(net(sortedNet[0])),'off PPP - def PPP')+
    xcard('Fastest Pace',sortedPace[0].name, f1(pace(sortedPace[0]))+' poss/gm','most possessions per game')+
    xcard('Best Ball Security',sortedTO[0].name, fP(topR(sortedTO[0].off))+' TO%','least turnovers per poss')+
    xcard('3PT Snipers',sortedFG3[0].name, fP(fg3(sortedFG3[0].off)),'3-point shooting %')+
    xcard('Most 3PT Dependent',sorted3[0].name, fP(rate3(sorted3[0].off))+' of FGA','highest 3PA rate')+
    xcard('Lowest PPP Off.',sorted[sorted.length-1].name, f3(ppp(sorted[sorted.length-1].off))+' PPP','needs offensive help');

  // Top offense bars
  var top10=sorted.slice(0,10); var maxOff=ppp(top10[0].off)||1;
  var offHtml='';
  for(var i=0;i<top10.length;i++){
    var t=top10[i]; var v=ppp(t.off); var rank=TR[t.id]['off_ppp'];
    offHtml+=hbar(t.name, v/maxOff*100, f3(v), 'linear-gradient(90deg,#ffe680,#e0b400)', ' <span style="font-size:9px;color:var(--text3)">#'+rank+'</span>');
  }
  document.getElementById('ov-top-off').innerHTML=offHtml;

  // Top defense bars
  var top10D=sortedDefF.slice(0,10); var maxDef=ppp(top10D[top10D.length-1].def)||1;
  var defHtml='';
  for(var i=0;i<top10D.length;i++){
    var t=top10D[i]; var v=ppp(t.def);
    defHtml+=hbar(t.name, (maxDef-v+0.03)/(maxDef+0.03)*100, f3(v), '#3fb950');
  }
  document.getElementById('ov-top-def').innerHTML=defHtml;

  // Play type frequency
  var ptTotals={}, ptPts={}, ptPoss2={};
  for(var j=0;j<PLAY_TYPES.length;j++){ptTotals[PLAY_TYPES[j]]=0;ptPts[PLAY_TYPES[j]]=0;ptPoss2[PLAY_TYPES[j]]=0;}
  for(var i=0;i<N;i++){
    for(var j=0;j<PLAY_TYPES.length;j++){
      var pt=PLAY_TYPES[j]; var s=TEAMS[i].pt_off[pt]||{};
      ptTotals[pt]+=(s.p||0); ptPts[pt]+=(s.pts||0); ptPoss2[pt]+=(s.p||0);
    }
  }
  var ptSorted=PLAY_TYPES.slice().sort(function(a,b){return ptTotals[b]-ptTotals[a];});
  var ptMax=ptTotals[ptSorted[0]]||1;
  var freqHtml=''; var ptPPPArr=[];
  for(var j=0;j<ptSorted.length;j++){
    var pt=ptSorted[j]; var v=ptTotals[pt];
    var lgPPP=ptPoss2[pt]?ptPts[pt]/ptPoss2[pt]:0;
    ptPPPArr.push({pt:pt,ppp:lgPPP});
    freqHtml+=hbar(pt, v/ptMax*100, fP(v/totalPoss*100), '#bc8cff');
  }
  document.getElementById('ov-pt-freq').innerHTML=freqHtml;

  var ptPPPSorted=ptPPPArr.slice().sort(function(a,b){return b.ppp-a.ppp;});
  var maxPTPPP=ptPPPSorted[0]?ptPPPSorted[0].ppp:1;
  var pppHtml='';
  for(var j=0;j<ptPPPSorted.length;j++){
    var x=ptPPPSorted[j];
    var col=x.ppp>leaguePPP?'#d4a900':'#8b949e';
    pppHtml+=hbar(x.pt, x.ppp/maxPTPPP*100, f3(x.ppp), col);
  }
  document.getElementById('ov-pt-ppp').innerHTML=pppHtml;

  // Player leaders — filtered by the conference selector
  var ovPlayers=PLAYERS.filter(pInConf);
  var pppLeaders=ovPlayers.filter(function(p){return p.off.p>=30;}).sort(function(a,b){return ppp(b.off)-ppp(a.off);}).slice(0,8);
  var maxPPP=pppLeaders[0]?ppp(pppLeaders[0].off):1;
  var pppHtml2='<div class="leader-grid">';
  for(var i=0;i<pppLeaders.length;i++){
    var p=pppLeaders[i]; var v=ppp(p.off);
    pppHtml2+=lcard(p.name,p.team,f3(v),p.off.p+' poss',v/maxPPP*100,'','',i);
  }
  document.getElementById('ov-ppp-leaders').innerHTML=pppHtml2+'</div>';

  var efgLeaders=ovPlayers.filter(function(p){return p.off.fa>=30;}).sort(function(a,b){return efg(b.off)-efg(a.off);}).slice(0,8);
  var maxEFG=efgLeaders[0]?efg(efgLeaders[0].off):1;
  var efgHtml='<div class="leader-grid">';
  for(var i=0;i<efgLeaders.length;i++){
    var p=efgLeaders[i]; var v=efg(p.off);
    efgHtml+=lcard(p.name,p.team,fP(v),p.off.fa+' FGA',v/maxEFG*100,'','',i);
  }
  document.getElementById('ov-efg-leaders').innerHTML=efgHtml+'</div>';

  var volLeaders=ovPlayers.slice().sort(function(a,b){return (b.off.p||0)-(a.off.p||0);}).slice(0,8);
  var maxVol=volLeaders[0]?volLeaders[0].off.p:1;
  var volHtml='<div class="leader-grid">';
  for(var i=0;i<volLeaders.length;i++){
    var p=volLeaders[i];
    volHtml+=lcard(p.name,p.team,p.off.p+' poss',p.gp+' GP',p.off.p/maxVol*100,'','',i,'#db6d28');
  }
  document.getElementById('ov-vol-leaders').innerHTML=volHtml+'</div>';

  var toLeaders=ovPlayers.filter(function(p){return p.off.p>=40;}).sort(function(a,b){return topR(a.off)-topR(b.off);}).slice(0,8);
  var maxTOInv=toLeaders.length?1/(topR(toLeaders[toLeaders.length-1].off)||1):1;
  var toHtml='<div class="leader-grid">';
  for(var i=0;i<toLeaders.length;i++){
    var p=toLeaders[i]; var v=topR(p.off);
    toHtml+=lcard(p.name,p.team,fP(v)+' TO%',p.off.p+' poss',(1-v/25)*100,'','',i,'#39d353');
  }
  document.getElementById('ov-to-leaders').innerHTML=toHtml+'</div>';
  renderScatterPlot();
  renderTierDist();
  renderShotQuality();
}
function scard(n,l,sub){
  return '<div class="stat-card"><div class="stat-card-n">'+n+'</div><div class="stat-card-l">'+l+'</div><div class="stat-card-sub">'+sub+'</div></div>';
}
function pulse(n,l,sub){
  return '<div class="pulse-card"><div class="pulse-card-n">'+n+'</div><div class="pulse-card-l">'+l+'</div><div class="pulse-card-sub">'+sub+'</div></div>';
}
function xcard(title,name,val,sub){
  return '<div class="extreme-card"><div class="extreme-card-title">'+title+'</div>'+
    '<div class="extreme-card-name">'+esc(name)+'</div>'+
    '<div class="extreme-card-val">'+val+'</div>'+
    '<div class="extreme-card-sub">'+sub+'</div></div>';
}
function lcard(name,team,stat,sub,barPct,badge,prefix,rank,color){
  prefix=prefix||''; color=color||'var(--canada)'; rank=rank||0;
  return '<div class="lcard">'+
    '<div class="lcard-rank'+(rank<3?' top3':'')+'">'+(rank+1)+'</div>'+
    '<div class="lcard-name">'+esc(name)+'</div>'+
    '<div class="lcard-team">'+esc(team)+'</div>'+
    '<div class="lcard-stat" style="color:'+color+'">'+stat+'</div>'+
    '<div class="lcard-sub">'+sub+(badge?' &nbsp;<span style="color:var(--text3);font-size:9px">'+badge+'</span>':'')+'</div>'+
    '<div class="lcard-bar"><div class="lcard-bar-fill" style="width:'+(Math.max(barPct,1)).toFixed(1)+'%;background:'+color+'"></div></div>'+
    '</div>';
}

// ── TEAM RANKINGS ─────────────────────────────────────────────────────────────
var trSide='off',trSort='ppp',trAsc=false;
function setTRSide(s,btn){
  trSide=s;
  document.querySelectorAll('#tr-off,#tr-def').forEach(function(b){b.classList.remove('active');});
  btn.classList.add('active'); renderTeamRank();
}
function sortTR(col){
  if(trSort===col) trAsc=!trAsc; else{trSort=col;trAsc=(col==='name');} renderTeamRank();
}
function getTRVal(t,col){
  var s=t[trSide];
  if(col==='name') return t.name; if(col==='gp') return t.gp;
  if(col==='poss') return s.p||0; if(col==='pace') return pace(t);
  if(col==='ppp')  return ppp(s); if(col==='fg')  return fg(s);
  if(col==='efg')  return efg(s); if(col==='fg2') return fg2(s);
  if(col==='fg3')  return fg3(s); if(col==='3rate') return rate3(s);
  if(col==='to')   return topR(s);if(col==='ftr') return ftr(s);
  if(col==='ts')   return ts(s);  return 0;
}
function renderTeamRank(){
  var minGP=parseInt(document.getElementById('tr-min-gp').value)||0;
  var rows=TEAMS.filter(function(t){return t.gp>=minGP&&inConf(t);});
  rows.sort(function(a,b){
    var av=getTRVal(a,trSort),bv=getTRVal(b,trSort);
    return trAsc?(av>bv?1:-1):(av<bv?1:-1);
  });
  var isD=(trSide==='def'); var N=TEAMS.length;
  var html='';
  for(var i=0;i<rows.length;i++){
    var t=rows[i]; var s=t[trSide]; var pv=ppp(s);
    var offRank=TR[t.id]&&TR[t.id]['off_ppp'];
    var defRank=TR[t.id]&&TR[t.id]['def_ppp'];
    var tierPct=isD?(offRank?rPct(defRank,N):50):(offRank?rPct(offRank,N):50);
    var tc=tierCol(tierPct); var tt=tierStr(tierPct); var ttc=tierTxtCol(tierPct);
    html+='<tr'+(t.id===HOME_ID?' class="home-row"':'')+'>'+
      '<td class="rank-cell">'+(i+1)+'</td>'+
      '<td><span style="font-weight:700">'+esc(t.name)+'</span> '+
        confChip(t.conf)+' '+
        '<span class="tier-chip" style="display:inline-block;height:auto;background:'+tc+';color:'+ttc+';font-size:9px;padding:1px 5px;border-radius:3px">'+tt+'</span></td>'+
      '<td>'+t.gp+'</td>'+
      '<td>'+(s.p||0)+'</td>'+
      '<td>'+f1(pace(t))+'</td>'+
      '<td class="'+(isD?cPPPD(pv):cPPP(pv))+'">'+f3(pv)+'</td>'+
      '<td class="'+cPct(fg(s),50,33)+'">'+fP(fg(s))+'</td>'+
      '<td class="'+cPct(efg(s),55,38)+'">'+fP(efg(s))+'</td>'+
      '<td class="'+cPct(fg2(s),52,36)+'">'+fP(fg2(s))+'</td>'+
      '<td class="'+cPct(fg3(s),38,25)+'">'+fP(fg3(s))+'</td>'+
      '<td>'+fP(rate3(s))+'</td>'+
      '<td class="'+cTO(topR(s))+'">'+fP(topR(s))+'</td>'+
      '<td>'+fP(ftr(s))+'</td>'+
      '<td>'+fP(ts(s))+'</td>'+
      '</tr>';
  }
  document.getElementById('tr-body').innerHTML=html;
}

// ── PLAYER RANKINGS ──────────────────────────────────────────────────────────
var prSort='ppp',prAsc=false;
function sortPR(col){
  if(prSort===col) prAsc=!prAsc; else{prSort=col;prAsc=(col==='name'||col==='team');} renderPlayerRank();
}
function getPRVal(p,col,d){
  if(col==='name') return p.name; if(col==='team') return p.team;
  if(col==='gp')   return p.gp;   if(col==='ppg')  return p.ppg||0;
  if(col==='poss') return d.p||0; if(col==='ppp')  return ppp(d);
  if(col==='fg')   return fg(d);  if(col==='efg')  return efg(d);
  if(col==='fg2')  return fg2(d); if(col==='a2')   return d.a2||0;
  if(col==='fg3')  return fg3(d); if(col==='a3')   return d.a3||0;
  if(col==='to')   return topR(d);if(col==='ts')   return ts(d);
  return 0;
}
function renderPlayerRank(){
  var minGP=parseInt(document.getElementById('pr-min-gp').value)||0;
  var minPoss=parseInt(document.getElementById('pr-min-poss').value)||0;
  var teamF=document.getElementById('pr-team').value;
  var ptF=document.getElementById('pr-pt').value;
  var rows=PLAYERS.filter(function(p){
    if(p.gp<minGP) return false;
    if(teamF&&p.tid!==teamF) return false;
    if(!pInConf(p)) return false;
    var d=ptF?(p.pt_off[ptF]||null):p.off;
    return d&&(d.p||0)>=minPoss;
  });
  rows.sort(function(a,b){
    var da=ptF?(a.pt_off[ptF]||{}):a.off;
    var db=ptF?(b.pt_off[ptF]||{}):b.off;
    var av=getPRVal(a,prSort,da),bv=getPRVal(b,prSort,db);
    return prAsc?(av>bv?1:-1):(av<bv?1:-1);
  });
  var pool=PLAYERS.filter(function(p){return p.off.p>=15;}).length;
  var html='';
  for(var i=0;i<Math.min(rows.length,300);i++){
    var p=rows[i]; var d=ptF?(p.pt_off[ptF]||{}):p.off;
    var pv=ppp(d); var ev=efg(d);
    var pRank=PR[p.id]&&PR[p.id].ppp;
    html+='<tr'+(p.tid===HOME_ID?' class="home-row"':'')+'>'+
      '<td class="rank-cell">'+(i+1)+'</td>'+
      '<td style="font-weight:700">'+esc(p.name)+'</td>'+
      '<td style="color:var(--text2);font-size:11px">'+esc(p.team)+'</td>'+
      '<td>'+confChip(TEAM_CONF[p.tid])+'</td>'+
      '<td>'+p.gp+'</td>'+
      '<td>'+(d.p||0)+'</td>'+
      '<td style="font-weight:600">'+(p.ppg?p.ppg.toFixed(1):'—')+(PR[p.id]&&PR[p.id].ppg?' <span style="font-size:9px;color:var(--text3)">#'+PR[p.id].ppg+'</span>':'')+'</td>'+
      '<td class="'+cPPP(pv)+'">'+f3(pv)+(pRank&&!ptF?' <span style="font-size:9px;color:var(--text3)">#'+pRank+'</span>':'')+'</td>'+
      '<td class="'+cPct(fg(d),50,33)+'">'+fP(fg(d))+'</td>'+
      '<td class="'+cPct(ev,55,38)+'">'+fP(ev)+'</td>'+
      '<td class="'+cPct(fg2(d),52,36)+'">'+fP(fg2(d))+'</td>'+
      '<td>'+(d.a2||0)+'</td>'+
      '<td class="'+cPct(fg3(d),38,25)+'">'+fP(fg3(d))+'</td>'+
      '<td>'+(d.a3||0)+'</td>'+
      '<td class="'+cTO(topR(d))+'">'+fP(topR(d))+'</td>'+
      '<td>'+fP(ts(d))+'</td>'+
      '</tr>';
  }
  document.getElementById('pr-body').innerHTML=html;
}

// ── MATCHUP ──────────────────────────────────────────────────────────────────
function renderMatchup(){
  var aId=document.getElementById('mu-a').value, bId=document.getElementById('mu-b').value;
  if(!aId||!bId){document.getElementById('mu-content').innerHTML='<div class="empty">Select two teams to compare</div>';return;}
  var ta=null,tb=null;
  for(var i=0;i<TEAMS.length;i++){if(TEAMS[i].id===aId) ta=TEAMS[i];if(TEAMS[i].id===bId) tb=TEAMS[i];}
  if(!ta||!tb) return;
  var N=TEAMS.length;
  var colA=countryColor(ta.name), colB=countryColor(tb.name);

  var statDefs=[
    ['PPP Off',  function(t){return ppp(t.off);}, f3, false, 'off_ppp'],
    ['PPP Def',  function(t){return ppp(t.def);}, f3, true,  'def_ppp'],
    ['Net PPP',  function(t){return net(t);},     f3, false, 'net'],
    ['Pace',     function(t){return pace(t);},    f1, false, 'pace'],
    ['EFG%',     function(t){return efg(t.off);}, fP, false, 'off_efg'],
    ['2FG%',     function(t){return fg2(t.off);}, fP, false, 'off_fg2'],
    ['3FG%',     function(t){return fg3(t.off);}, fP, false, 'off_fg3'],
    ['3PA Rate', function(t){return rate3(t.off);},fP, false, 'off_3rate'],
    ['TO%',      function(t){return topR(t.off);},fP, true,  'off_to'],
    ['FT Rate',  function(t){return ftr(t.off);}, fP, false, 'off_ftr'],
    ['TS%',      function(t){return ts(t.off);},  fP, false, 'off_ts'],
    ['Def EFG%', function(t){return efg(t.def);}, fP, true,  'def_efg'],
    ['Force TO%',function(t){return topR(t.def);},fP, false, 'def_to'],
  ];

  var compHtml='<div class="matchup-bar-row" style="margin-bottom:8px">'+
    '<div style="font-size:11px;font-weight:700;text-align:right;color:'+colA+'">'+esc(ta.name)+'</div>'+
    '<div></div><div style="font-size:10px;color:var(--text3);text-align:center">STAT</div>'+
    '<div></div><div style="font-size:11px;font-weight:700;text-align:left;color:'+colB+'">'+esc(tb.name)+'</div></div>';

  for(var i=0;i<statDefs.length;i++){
    var label=statDefs[i][0],fn=statDefs[i][1],fmt=statDefs[i][2],lb=statDefs[i][3],rkey=statDefs[i][4];
    var av=fn(ta),bv=fn(tb),tot=Math.abs(av)+Math.abs(bv)||1;
    var aW=Math.abs(av)/tot*100, bW=Math.abs(bv)/tot*100;
    var aWins=lb?av<bv:av>=bv;
    var aRk=TR[ta.id]&&TR[ta.id][rkey], bRk=TR[tb.id]&&TR[tb.id][rkey];
    var aRkS=aRk?'<span style="font-size:9px;color:var(--text3)">#'+aRk+'</span>':'';
    var bRkS=bRk?'<span style="font-size:9px;color:var(--text3)">#'+bRk+'</span>':'';
    var aBg=aWins?colA:'var(--border2)', bBg=!aWins?colB:'var(--border2)';
    var aCol=aWins?colA:'var(--text)', bCol=!aWins?colB:'var(--text)';
    compHtml+='<div class="matchup-bar-row">'+
      '<div style="text-align:right;padding:3px 8px;font-size:12px;font-weight:700;color:'+aCol+'">'+fmt(av)+' '+aRkS+'</div>'+
      '<div style="height:16px;background:var(--bg3);border-radius:3px 0 0 3px;overflow:hidden;display:flex;justify-content:flex-end">'+
        '<div style="width:'+aW.toFixed(1)+'%;height:100%;background:'+aBg+'"></div></div>'+
      '<div style="text-align:center;font-size:9px;color:var(--text3);font-weight:600">'+label+'</div>'+
      '<div style="height:16px;background:var(--bg3);border-radius:0 3px 3px 0;overflow:hidden">'+
        '<div style="width:'+bW.toFixed(1)+'%;height:100%;background:'+bBg+'"></div></div>'+
      '<div style="text-align:left;padding:3px 8px;font-size:12px;font-weight:700;color:'+bCol+'">'+bRkS+' '+fmt(bv)+'</div>'+
      '</div>';
  }

  // Play type butterfly builder
  function ptButterfly(ptObjA, ptObjB, titleA, titleB, cA, cB){
    var allV=[];
    PLAY_TYPES.forEach(function(pt){
      var dA=ptObjA[pt]||{},dB=ptObjB[pt]||{};
      if(dA.p) allV.push(ppp(dA)); if(dB.p) allV.push(ppp(dB));
    });
    var mx=allV.length?Math.max.apply(null,allV)*1.05:2;
    var h='<div style="display:grid;grid-template-columns:1fr 140px 1fr;gap:4px;padding:8px 0 10px;border-bottom:2px solid var(--border);margin-bottom:2px">'+
      '<div style="text-align:right;font-weight:700;font-size:13px;color:'+cA+'">'+titleA+'</div>'+
      '<div style="text-align:center;font-size:10px;color:var(--text3);font-weight:600;align-self:center">PLAY TYPE (PPP)</div>'+
      '<div style="font-weight:700;font-size:13px;color:'+cB+'">'+titleB+'</div></div>';
    PLAY_TYPES.forEach(function(pt){
      var dA=ptObjA[pt]||{},dB=ptObjB[pt]||{};
      if(!dA.p&&!dB.p) return;
      var vA=dA.p?ppp(dA):null, vB=dB.p?ppp(dB):null;
      var winA=vA!==null&&vB!==null&&vA>vB, winB=vA!==null&&vB!==null&&vB>vA;
      var wA=vA?Math.min(vA/mx*100,100):0, wB=vB?Math.min(vB/mx*100,100):0;
      h+='<div style="display:grid;grid-template-columns:1fr 140px 1fr;align-items:center;gap:4px;padding:4px 0;border-bottom:1px solid var(--border)">'+
        '<div style="display:flex;align-items:center;justify-content:flex-end;gap:6px">'+
          '<span style="font-size:11px;font-weight:'+(winA?700:400)+';color:'+(winA?cA:'var(--text2)')+'">'+
            (vA!==null?f3(vA)+' <span style="color:var(--text3);font-size:9px">('+dA.p+'p)</span>':'<span style="color:var(--text3)">—</span>')+
          '</span>'+
          '<div style="width:90px;height:16px;background:var(--bg3);border-radius:3px 0 0 3px;overflow:hidden;display:flex;justify-content:flex-end">'+
            '<div style="width:'+wA.toFixed(1)+'%;height:100%;background:'+(winA?cA:'var(--border2)')+'"></div></div>'+
        '</div>'+
        '<div style="text-align:center;font-size:10px;color:var(--text2);font-weight:600;padding:0 4px">'+esc(pt)+'</div>'+
        '<div style="display:flex;align-items:center;gap:6px">'+
          '<div style="width:90px;height:16px;background:var(--bg3);border-radius:0 3px 3px 0;overflow:hidden">'+
            '<div style="width:'+wB.toFixed(1)+'%;height:100%;background:'+(winB?cB:'var(--border2)')+'"></div></div>'+
          '<span style="font-size:11px;font-weight:'+(winB?700:400)+';color:'+(winB?cB:'var(--text2)')+'">'+
            (vB!==null?f3(vB)+' <span style="color:var(--text3);font-size:9px">('+dB.p+'p)</span>':'<span style="color:var(--text3)">—</span>')+
          '</span>'+
        '</div>'+
      '</div>';
    });
    return h;
  }
  var ptOffHtml=ptButterfly(ta.pt_off,tb.pt_off,esc(ta.name),esc(tb.name),colA,colB);
  var ptDefHtml=ptButterfly(ta.pt_def,tb.pt_def,esc(ta.name),esc(tb.name),colA,colB);

  // Radar comparison
  var radarKeys=['off_ppp','off_efg','off_fg3','off_to','def_ppp','pace'];
  var radarLabels=['Off PPP','EFG%','3FG%','Ball Sec.','Defense','Pace'];
  function getRadarVals(t){
    return radarKeys.map(function(k,idx){
      var r=TR[t.id]&&TR[t.id][k]; if(!r) return 50;
      // off_to and def_ppp: lower rank = better, already computed as lb:true so rank 1 = best
      return rPct(r, N);
    });
  }
  var radarA=radarSvg(getRadarVals(ta),radarLabels,colA);
  var radarB=radarSvg(getRadarVals(tb),radarLabels,colB);

  document.getElementById('mu-content').innerHTML=
    '<div class="grid2" style="margin-bottom:4px">'+
      '<div style="font-size:22px;font-weight:800;text-align:center;color:'+colA+'">'+esc(ta.name)+'</div>'+
      '<div style="font-size:22px;font-weight:800;text-align:center;color:'+colB+'">'+esc(tb.name)+'</div>'+
    '</div>'+
    '<div class="grid2" style="text-align:center;color:var(--text2);font-size:11px;margin-bottom:16px">'+
      '<div>'+ta.gp+' games &nbsp;&middot;&nbsp; '+f3(ppp(ta.off))+' PPP off &nbsp;&middot;&nbsp; '+f3(ppp(ta.def))+' PPP def</div>'+
      '<div>'+tb.gp+' games &nbsp;&middot;&nbsp; '+f3(ppp(tb.off))+' PPP off &nbsp;&middot;&nbsp; '+f3(ppp(tb.def))+' PPP def</div>'+
    '</div>'+
    '<div class="grid2">'+
      '<div class="card"><div class="card-hdr">Performance Radar</div>'+
        '<div class="radar-wrap">'+radarA+'</div>'+
        '<div style="text-align:center;font-size:9px;color:var(--text3);padding-bottom:8px">'+esc(ta.name)+'</div></div>'+
      '<div class="card"><div class="card-hdr">Performance Radar</div>'+
        '<div class="radar-wrap">'+radarB+'</div>'+
        '<div style="text-align:center;font-size:9px;color:var(--text3);padding-bottom:8px">'+esc(tb.name)+'</div></div>'+
    '</div>'+
    '<div class="card" style="margin-bottom:16px"><div class="card-hdr">Head-to-Head Stat Comparison</div>'+
      '<div class="card-body" style="padding:12px">'+compHtml+'</div></div>'+
    '<div class="card" style="margin-bottom:16px"><div class="card-hdr">Play Type PPP — Offense</div>'+
      '<div class="card-body">'+ptOffHtml+'</div></div>'+
    '<div class="card"><div class="card-hdr">Play Type PPP — Defense <span style="font-weight:400;font-size:10px;text-transform:none;color:var(--text3)">(PPP allowed vs each play type)</span></div>'+
      '<div class="card-body">'+ptDefHtml+'</div></div>';
}

// ── TEAM INTELLIGENCE ─────────────────────────────────────────────────────────
function renderTeamIntel(){
  var tid=document.getElementById('ti-team').value;
  if(!tid){document.getElementById('ti-content').innerHTML='<div class="empty">Select a team</div>';return;}
  var t=null; for(var i=0;i<TEAMS.length;i++) if(TEAMS[i].id===tid){t=TEAMS[i];break;}
  if(!t) return;
  var o=t.off,d=t.def,N=TEAMS.length,r=TR[t.id]||{};

  var offPPP=ppp(o), defPPP=ppp(d), netPPP=net(t);
  var offRank=r['off_ppp']||0, defRank=r['def_ppp']||0, netRank=r['net']||0;
  var offPct=rPct(offRank,N), defPct=rPct(defRank,N), netPct=rPct(netRank,N);

  // Net panel
  function netBadge(pct){
    var t=tierStr(pct),col=tierCol(pct);
    return '<span class="net-tier" style="background:'+col+';color:#fff">'+t+' &mdash; '+tierLabel(pct)+'</span>';
  }
  function tierLabel(pct){
    if(pct>=90)return'Elite';if(pct>=75)return'Great';if(pct>=50)return'Above Avg';
    if(pct>=25)return'Below Avg';return'Poor';
  }
  var qualNote='';
  var netPanel=qualNote+'<div class="net-panel">'+
    '<div class="net-box">'+
      '<div class="net-label">Offensive PPP</div>'+
      '<div class="net-val" style="color:'+pppRatingColor(offPPP)+'">'+f3(offPPP)+'</div>'+
      '<div class="net-rank">#'+offRank+' of '+N+' &middot; '+pppRating(offPPP)+'</div>'+
      netBadge(offPct)+
    '</div>'+
    '<div class="net-box">'+
      '<div class="net-label">Net Rating</div>'+
      '<div class="net-val" style="color:'+(netPPP>=0?'#16a34a':'#dc2626')+'">'+
        (netPPP>=0?'+':'')+f3(netPPP)+'</div>'+
      '<div class="net-rank">#'+netRank+' of '+N+'</div>'+
      netBadge(netPct)+
    '</div>'+
    '<div class="net-box">'+
      '<div class="net-label">Defensive PPP</div>'+
      '<div class="net-val" style="color:'+(defPPP>0?pppRatingColor(1.8-defPPP):'var(--text3)')+'">'+f3(defPPP)+'</div>'+
      '<div class="net-rank">#'+defRank+' of '+N+' &middot; '+pppRating(2*LEAGUE_PPP-defPPP)+'</div>'+
      netBadge(defPct)+
    '</div>'+
    '</div>';

  // Radar
  var radarKeys2=['off_ppp','off_efg','off_fg3','off_to','def_ppp','pace','off_ftr','def_to'];
  var radarLabels2=['Off PPP','EFG%','3FG%','Ball Sec.','Defense','Pace','FT Draw','Force TO'];
  var radarVals=radarKeys2.map(function(k){var rk=r[k];return rk?rPct(rk,N):50;});
  var radar=radarSvg(radarVals,radarLabels2,countryColor(t.name));

  // Auto analysis
  var an=autoAnalysis(t);
  var strengthsHtml=an.s.length?an.s.map(function(s){return '<div class="analysis-item analysis-strength">'+s+'</div>';}).join(''):'<div style="color:var(--text3);font-size:11px">No standout strengths</div>';
  var weakHtml=an.w.length?an.w.map(function(w){return '<div class="analysis-item analysis-weakness">'+w+'</div>';}).join(''):'<div style="color:var(--text3);font-size:11px">No major weaknesses</div>';
  var analysisHtml='<div class="analysis-box">'+
    '<div class="analysis-col"><div class="analysis-col-title" style="color:var(--green)">Strengths</div>'+strengthsHtml+'</div>'+
    '<div class="analysis-col"><div class="analysis-col-title" style="color:var(--red)">Weaknesses</div>'+weakHtml+'</div>'+
    '</div>';

  // Offensive ranking panel
  var offStatDefs=[
    ['Off PPP',   f3(offPPP),     r['off_ppp']],
    ['EFG%',      fP(efg(o)),     r['off_efg']],
    ['TS%',       fP(ts(o)),      r['off_ts']],
    ['2FG%',      fP(fg2(o)),     r['off_fg2']],
    ['3FG%',      fP(fg3(o)),     r['off_fg3']],
    ['3PA Rate',  fP(rate3(o)),   r['off_3rate']],
    ['TO%',       fP(topR(o)),    r['off_to']],
    ['FT Rate',   fP(ftr(o)),     r['off_ftr']],
    ['PPS',       f3(pps(o)),     r['off_pps']],
    ['Pace',      f1(pace(t)),    r['pace']],
  ];
  var defStatDefs=[
    ['Def PPP',   f3(defPPP),     r['def_ppp']],
    ['Def EFG%',  fP(efg(d)),     r['def_efg']],
    ['Def FG%',   fP(fg(d)),      r['def_fg2']? r['def_fg2']:null],
    ['Def 2FG%',  fP(fg2(d)),     r['def_fg2']],
    ['Def 3FG%',  fP(fg3(d)),     r['def_fg3']],
    ['Force TO%', fP(topR(d)),    r['def_to']],
  ];

  var offRankHtml=''; offStatDefs.forEach(function(x){offRankHtml+=x[2]?pctRow(x[0],x[1],x[2],N):'';});
  var defRankHtml=''; defStatDefs.forEach(function(x){defRankHtml+=x[2]?pctRow(x[0],x[1],x[2],N):'';});

  // Play type tables
  function makePTTable(side, ptData){
    var totalPoss=(side==='off'?o.p:d.p)||1;
    var leaguePTavg={};
    for(var j=0;j<PLAY_TYPES.length;j++){
      var pt2=PLAY_TYPES[j]; var ptPts=0,ptP=0;
      for(var ii=0;ii<TEAMS.length;ii++){var ss=TEAMS[ii].pt_off[pt2]||{};ptPts+=(ss.pts||0);ptP+=(ss.p||0);}
      leaguePTavg[pt2]=ptP?ptPts/ptP:0;
    }
    var rows='';
    for(var j=0;j<PLAY_TYPES.length;j++){
      var pt=PLAY_TYPES[j]; var s=ptData[pt]||{};
      var pv=ppp(s); var possPct=s.p?s.p/totalPoss*100:0;
      var lgavg=leaguePTavg[pt];
      var vsLg='';
      if(s.p&&lgavg){var diff=pv-lgavg;vsLg='<span class="pt-vs '+(diff>=0?'pt-vs-up':'pt-vs-dn')+'">'+(diff>=0?'+':'')+diff.toFixed(3)+'</span>';}
      rows+='<tr>'+
        '<td>'+pt+'</td>'+
        '<td class="poss-cell">'+(s.p||0)+'</td>'+
        '<td>'+fP(possPct)+'</td>'+
        '<td>'+(s.qr||'&mdash;')+'</td>'+
        '<td class="'+(side==='off'?cPPP(pv):cPPPD(pv))+'">'+((s.p||0)?f3(pv):'&mdash;')+vsLg+'</td>'+
        '<td style="color:'+pppRatingColor(pv)+'">'+((s.p||0)?pppRating(pv):'&mdash;')+'</td>'+
        '<td>'+((s.p||0)?fP(efg(s)):'&mdash;')+'</td>'+
        '<td>'+((s.p||0)?fP(fg2(s)):'&mdash;')+'</td>'+
        '<td>'+((s.p||0)?fP(fg3(s)):'&mdash;')+'</td>'+
        '<td>'+((s.p||0)?fP(topR(s)):'&mdash;')+'</td>'+
        '<td>'+((s.p||0)?fP(ftr(s)):'&mdash;')+'</td>'+
        '</tr>';
    }
    return '<div class="tbl-wrap"><table class="pt-tbl"><thead><tr>'+
      '<th style="text-align:left">PLAY TYPE</th><th>POSS</th><th>%TIME</th><th>%TIME RK</th>'+
      '<th>PPP</th><th>RATING</th><th>EFG%</th><th>2FG%</th><th>3FG%</th><th>TO%</th><th>FT%</th>'+
      '</tr></thead><tbody>'+rows+'</tbody></table></div>';
  }

  // Roster
  var roster=PLAYERS.filter(function(p){return p.tid===tid;});
  roster.sort(function(a,b){return(b.off.p||0)-(a.off.p||0);});
  var pool=PLAYERS.filter(function(p){return p.off.p>=15;}).length;
  var rosterHtml='';
  for(var i=0;i<roster.length;i++){
    var p=roster[i]; var s=p.off;
    var pRank=PR[p.id]&&PR[p.id].ppp;
    var pv2=ppp(s); var pct2=pRank?rPct(pRank,pool):null;
    rosterHtml+='<tr>'+
      '<td style="font-weight:700">'+esc(p.name)+'</td>'+
      '<td>'+p.gp+'</td><td>'+(s.p||0)+'</td>'+
      '<td class="'+cPPP(pv2)+'">'+((s.p||0)?f3(pv2):'&mdash;')+'</td>'+
      (pct2!==null?'<td><span class="tier-chip tier-'+tierStr(pct2)+'" style="background:'+tierCol(pct2)+';color:'+tierTxtCol(pct2)+';font-size:9px;padding:1px 5px;border-radius:3px">'+tierStr(pct2)+'</span></td>':'<td>&mdash;</td>')+
      '<td>'+(s.p?fP(efg(s)):'&mdash;')+'</td>'+
      '<td>'+fP(fg2(s))+'</td><td>'+(s.a2||0)+'</td>'+
      '<td>'+fP(fg3(s))+'</td><td>'+(s.a3||0)+'</td>'+
      '<td class="'+cTO(topR(s))+'">'+((s.p||0)?fP(topR(s)):'&mdash;')+'</td>'+
      '</tr>';
  }

  var teamCol=countryColor(t.name);
  var tierSize=r['t_size']||'?';
  document.getElementById('ti-content').innerHTML=
    '<div style="font-size:28px;font-weight:800;color:'+teamCol+';margin-bottom:20px;padding-bottom:16px;border-bottom:3px solid '+teamCol+'">'+
      esc(t.name)+' '+confChip(t.conf,true)+''+
    '</div>'+
    netPanel+
    '<div class="grid2" style="margin-bottom:16px">'+
      '<div>'+
        '<div class="section-hdr">Performance Radar</div>'+
        '<div class="card"><div class="radar-wrap">'+radar+'</div>'+
        '<div style="text-align:center;font-size:9px;color:var(--text3);padding-bottom:8px">'+esc(t.name)+'</div></div>'+
      '</div>'+
      '<div>'+
        '<div class="section-hdr">Scouting Report</div>'+
        '<div class="card"><div class="card-body">'+analysisHtml+'</div></div>'+
      '</div>'+
    '</div>'+
    '<div class="grid2" style="margin-bottom:16px">'+
      '<div class="card"><div class="card-hdr accent">Offensive Rankings vs All '+N+' Teams <span style="font-weight:400;font-size:9px;text-transform:none;color:var(--text3)">&nbsp;&middot;&nbsp;'+esc(t.conf)+' rank: #'+(r['t_off_ppp']||'?')+' of '+tierSize+'</span></div><div class="card-body" style="padding:8px 16px">'+offRankHtml+'</div></div>'+
      '<div class="card"><div class="card-hdr accent">Defensive Rankings vs All '+N+' Teams <span style="font-weight:400;font-size:9px;text-transform:none;color:var(--text3)">&nbsp;&middot;&nbsp;'+esc(t.conf)+' rank: #'+(r['t_def_ppp']||'?')+' of '+tierSize+'</span></div><div class="card-body" style="padding:8px 16px">'+defRankHtml+'</div></div>'+
    '</div>'+
    '<div class="subtabs">'+
      '<button class="subtab-btn active" onclick="showSubtab(this,\'ti-pt-off\')">Play Types &mdash; Offense</button>'+
      '<button class="subtab-btn" onclick="showSubtab(this,\'ti-pt-def\')">Play Types &mdash; Defense</button>'+
      '<button class="subtab-btn" onclick="showSubtab(this,\'ti-roster\')">Roster</button>'+
    '</div>'+
    '<div class="subtab active" id="ti-pt-off"><div class="card"><div class="card-hdr">Offensive Play Types <span style="font-weight:400;text-transform:none;color:var(--text3);font-size:10px">&Delta; vs league avg</span></div>'+makePTTable('off',t.pt_off)+'</div></div>'+
    '<div class="subtab" id="ti-pt-def"><div class="card"><div class="card-hdr">Defensive Play Types (Opponent Offense)</div>'+makePTTable('def',t.pt_def)+'</div></div>'+
    '<div class="subtab" id="ti-roster"><div class="card"><div class="card-hdr">Roster &mdash; Offensive Stats</div>'+
      '<div class="tbl-wrap"><table class="pt-tbl"><thead><tr>'+
        '<th style="text-align:left">Player</th><th>GP</th><th>POSS</th>'+
        '<th>PPP</th><th>TIER</th><th>EFG%</th>'+
        '<th>2FG%</th><th>2FGA</th><th>3FG%</th><th>3FGA</th><th>TO%</th>'+
      '</tr></thead><tbody>'+rosterHtml+'</tbody></table></div></div></div>';
}

// ── PLAYER INTELLIGENCE ───────────────────────────────────────────────────────
function populatePiPlayers(){
  var tid=document.getElementById('pi-team').value;
  var sel=document.getElementById('pi-player');
  var roster=PLAYERS.filter(function(p){return p.tid===tid;});
  roster.sort(function(a,b){return a.name.localeCompare(b.name);});
  var opts='<option value="">-- Player --</option>';
  for(var i=0;i<roster.length;i++) opts+='<option value="'+esc(roster[i].id)+'">'+esc(roster[i].name)+'</option>';
  sel.innerHTML=opts;
  document.getElementById('pi-content').innerHTML='<div class="empty">Select a player</div>';
}

function renderPlayerIntel(){
  var pid=document.getElementById('pi-player').value; if(!pid) return;
  var p=null; for(var i=0;i<PLAYERS.length;i++) if(PLAYERS[i].id===pid){p=PLAYERS[i];break;}
  if(!p) return;
  var o=p.off,d=p.def;
  var pool=PLAYERS.filter(function(x){return x.off.p>=15;}); var NP=pool.length;
  var pr=PR[p.id]||{};

  // Shot profile
  var shots2Pct=o.fa>0?o.a2/o.fa*100:0, shots3Pct=o.fa>0?o.a3/o.fa*100:0;
  var shotProfile='<div style="margin-bottom:12px">'+
    '<div style="font-size:10px;color:var(--text2);margin-bottom:6px;font-weight:600">SHOT SELECTION</div>'+
    '<div style="display:flex;height:12px;border-radius:6px;overflow:hidden;margin-bottom:4px">'+
      '<div style="width:'+shots2Pct.toFixed(1)+'%;background:#d4a900"></div>'+
      '<div style="width:'+shots3Pct.toFixed(1)+'%;background:#bc8cff"></div>'+
      '<div style="flex:1;background:var(--bg3)"></div>'+
    '</div>'+
    '<div style="display:flex;gap:16px;font-size:10px;color:var(--text2)">'+
      '<span><span style="color:#d4a900">&#9632;</span> 2PT: '+fP(shots2Pct)+' ('+o.a2+' att, '+fP(fg2(o))+')</span>'+
      '<span><span style="color:#bc8cff">&#9632;</span> 3PT: '+fP(shots3Pct)+' ('+o.a3+' att, '+fP(fg3(o))+')</span>'+
    '</div></div>';

  // Stat cards with global rank
  function piStat(label, val, rankKey, fmtFn, lbetter){
    var rank=pr[rankKey]; var pctile=rank?rPct(rank,NP):null;
    var tc=pctile!==null?tierCol(pctile):'var(--border2)';
    var tt=pctile!==null?tierStr(pctile):'?';
    var ttc=pctile!==null?tierTxtCol(pctile):'#fff';
    return '<div class="pi-stat">'+
      '<div style="display:flex;justify-content:space-between;align-items:flex-start">'+
        '<div class="pi-stat-n" style="color:'+tc+'">'+val+'</div>'+
        '<div class="tier-chip tier-'+tt+'" style="background:'+tc+';color:'+ttc+'">'+tt+'</div>'+
      '</div>'+
      '<div class="pi-stat-l">'+label+'</div>'+
      (rank?'<div class="pi-stat-rank">#'+rank+' of '+NP+'</div>':'<div class="pi-stat-rank">no rank</div>')+
      '</div>';
  }

  var cardsHtml=
    piStat('PPP',(o.p?f3(ppp(o)):'—'),'ppp',f3,false)+
    piStat('EFG%',(o.fa?fP(efg(o)):'—'),'efg',fP,false)+
    piStat('TS%',(o.fa?fP(ts(o)):'—'),'ts',fP,false)+
    piStat('2FG%',(o.a2?fP(fg2(o)):'0 att'),'fg2',fP,false)+
    piStat('3FG%',(o.a3?fP(fg3(o)):'0 att'),'fg3',fP,false)+
    piStat('TO%',(o.p?fP(topR(o)):'—'),'to',fP,true)+
    piStat('Volume',o.p+' poss','vol',null,false)+
    piStat('FT Rate',(o.p?fP(ftr(o)):'—'),'ftr',fP,false);

  // Percentile bars (enhanced)
  var percDefs=[
    ['PPP','ppp',function(x){return ppp(x.off);}],
    ['EFG%','efg',function(x){return efg(x.off);}],
    ['TS%','ts',function(x){return ts(x.off);}],
    ['2FG%','fg2',function(x){return fg2(x.off);}],
    ['3FG%','fg3',function(x){return fg3(x.off);}],
    ['TO% (low=better)','to',function(x){return topR(x.off);}],
    ['FT Rate','ftr',function(x){return ftr(x.off);}],
    ['Volume','vol',function(x){return x.off.p||0;}],
  ];
  var percHtml='';
  for(var i=0;i<percDefs.length;i++){
    var pd=percDefs[i]; var rank=pr[pd[1]]; if(!rank) continue;
    var pct=rPct(rank,NP); var col=tierCol(pct); var t2=tierStr(pct); var tc2=tierTxtCol(pct);
    percHtml+='<div class="pct-row">'+
      '<div class="pct-label">'+pd[0]+'</div>'+
      '<div class="pct-rank" style="font-size:10px">#'+rank+'/'+NP+'</div>'+
      '<div class="pct-track"><div class="pct-fill" style="width:'+pct+'%;background:'+col+'"></div></div>'+
      '<div class="tier-chip tier-'+t2+'" style="background:'+col+';color:'+tc2+'">'+t2+'</div>'+
      '</div>';
  }

  // Play type table — sorted by possessions descending
  var totalP=o.p||1;
  var ptSortedOff=PLAY_TYPES.slice().sort(function(a,b){return ((p.pt_off[b]||{}).p||0)-((p.pt_off[a]||{}).p||0);});
  var ptHtml='';
  for(var j=0;j<ptSortedOff.length;j++){
    var pt=ptSortedOff[j]; var s=p.pt_off[pt]||{};
    if(!s.p){
      ptHtml+='<tr><td style="color:var(--text3)">'+pt+'</td><td colspan="10" style="color:var(--text3)">&mdash;</td></tr>';
    } else {
      var pv3=ppp(s); var pRk=s.pr; var ptPct=pRk?rPct(pRk,NP):null;
      ptHtml+='<tr>'+
        '<td>'+pt+'</td>'+
        '<td class="poss-cell">'+s.p+'</td>'+
        '<td>'+fP(s.p/totalP*100)+'</td>'+
        '<td class="'+cPPP(pv3)+'">'+f3(pv3)+'</td>'+
        '<td style="color:'+pppRatingColor(pv3)+'">'+pppRating(pv3)+'</td>'+
        (pRk?'<td><span class="tier-chip tier-'+tierStr(ptPct||0)+'" style="background:'+tierCol(ptPct||0)+';color:'+tierTxtCol(ptPct||0)+';font-size:9px;padding:1px 5px;border-radius:3px">#'+pRk+'</span></td>':'<td>&mdash;</td>')+
        '<td>'+fP(efg(s))+'</td>'+
        '<td>'+fP(fg2(s))+'</td>'+
        '<td>'+fP(fg3(s))+'</td>'+
        '<td>'+fP(topR(s))+'</td>'+
        '<td>'+fP(ftr(s))+'</td>'+
        '</tr>';
    }
  }

  // Play type distribution bars
  var maxPT=0;
  for(var j=0;j<PLAY_TYPES.length;j++){var s2=p.pt_off[PLAY_TYPES[j]]||{};if((s2.p||0)>maxPT) maxPT=s2.p||0;}
  maxPT=maxPT||1;
  var ptBars='';
  for(var j=0;j<PLAY_TYPES.length;j++){
    var pt=PLAY_TYPES[j]; var s=p.pt_off[pt]||{}; if(!s.p) continue;
    var pv4=ppp(s);
    ptBars+=hbar(pt, s.p/maxPT*100,
      s.p+' ('+fP(s.p/totalP*100)+')  '+f3(pv4)+' PPP',
      pv4>=1.0?'#3fb950':pv4>=0.85?'#d4a900':pv4>=0.70?'#d29922':'#f85149');
  }

  // Defense overall + play type breakdown
  var defHtml='';
  if(d&&d.p>0){
    var dPPP=ppp(d);
    var dTotalP=d.p||1;
    // Play type defense table — sorted by possessions descending
    var defTotalP=PLAY_TYPES.reduce(function(acc,pt){return acc+((p.pt_def[pt]||{}).p||0);},0)||1;
    var ptSortedDef=PLAY_TYPES.slice().sort(function(a,b){return ((p.pt_def[b]||{}).p||0)-((p.pt_def[a]||{}).p||0);});
    var ptDefHtml='';
    for(var j=0;j<ptSortedDef.length;j++){
      var pt=ptSortedDef[j]; var s=p.pt_def[pt]||{};
      if(!s.p){
        ptDefHtml+='<tr><td style="color:var(--text3)">'+pt+'</td><td colspan="10" style="color:var(--text3)">&mdash;</td></tr>';
      } else {
        var dv=ppp(s); var pRk=s.pr; var ptPct=pRk?rPct(pRk,NP):null;
        ptDefHtml+='<tr>'+
          '<td>'+pt+'</td>'+
          '<td class="poss-cell">'+s.p+'</td>'+
          '<td>'+fP(s.p/defTotalP*100)+'</td>'+
          '<td class="'+cPPP(dv)+'">'+f3(dv)+'</td>'+
          '<td style="color:'+pppRatingColor(dv)+'">'+pppRating(dv)+'</td>'+
          (pRk?'<td><span class="tier-chip tier-'+tierStr(ptPct||0)+'" style="background:'+tierCol(ptPct||0)+';color:'+tierTxtCol(ptPct||0)+';font-size:9px;padding:1px 5px;border-radius:3px">#'+pRk+'</span></td>':'<td>&mdash;</td>')+
          '<td>'+fP(efg(s))+'</td>'+
          '<td>'+fP(fg2(s))+'</td>'+
          '<td>'+fP(fg3(s))+'</td>'+
          '<td>'+fP(topR(s))+'</td>'+
          '<td>'+fP(ftr(s))+'</td>'+
          '</tr>';
      }
    }
    defHtml='<div class="card"><div class="card-body">'+
      '<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin-bottom:16px">'+
        '<div class="pi-stat"><div class="pi-stat-n">'+d.p+'</div><div class="pi-stat-l">Poss Defended</div></div>'+
        '<div class="pi-stat"><div class="pi-stat-n" style="color:'+pppRatingColor(1.8-dPPP)+'">'+f3(dPPP)+'</div><div class="pi-stat-l">PPP Allowed</div></div>'+
        '<div class="pi-stat"><div class="pi-stat-n">'+fP(fg(d))+'</div><div class="pi-stat-l">FG% Allowed</div></div>'+
        '<div class="pi-stat"><div class="pi-stat-n">'+fP(efg(d))+'</div><div class="pi-stat-l">EFG% Allowed</div></div>'+
        '<div class="pi-stat"><div class="pi-stat-n">'+fP(topR(d))+'</div><div class="pi-stat-l">TO% Forced</div></div>'+
      '</div></div></div>';
  }

  // Build team context — rank by PPG among teammates with ≥3 GP
  var tmContext='';
  if(p.gp>=3&&p.ppg>0){
    var teammates=PLAYERS.filter(function(x){return x.tid===p.tid&&x.id!==p.id&&x.gp>=3&&x.ppg>0;});
    var tmRank=1; teammates.forEach(function(x){if(x.ppg>p.ppg) tmRank++;});
    tmContext='<span style="color:var(--text3);font-size:11px">&nbsp;&middot;&nbsp; #'+tmRank+' on '+esc(p.team)+'</span>';
  }

  document.getElementById('pi-content').innerHTML=
    '<div style="display:flex;align-items:center;gap:10px;margin-bottom:16px">'+
      '<div>'+
        '<div style="font-size:16px;font-weight:800;color:var(--text)">'+esc(p.name)+'</div>'+
        '<div style="font-size:12px;color:var(--text2);margin-top:2px">'+esc(p.team)+' &nbsp;&middot;&nbsp; '+p.gp+' GP'+tmContext+'</div>'+
      '</div>'+
    '</div>'+
    '<div style="display:grid;grid-template-columns:repeat(8,1fr);gap:10px;margin-bottom:16px">'+cardsHtml+'</div>'+
    '<div class="grid2">'+
      '<div>'+
        '<div class="section-hdr">Global Percentile Rankings</div>'+
        '<div class="card"><div class="card-body" style="padding:8px 16px">'+(percHtml||'<div class="empty">Not enough data</div>')+'</div></div>'+
      '</div>'+
      '<div>'+
        '<div class="section-hdr">Shot & Play Type Distribution</div>'+
        '<div class="card"><div class="card-body">'+shotProfile+(ptBars||'<div class="empty">No play type data</div>')+'</div></div>'+
      '</div>'+
    '</div>'+
    '<div class="section-hdr">Play Type Breakdown</div>'+
    '<div class="card">'+
      '<div style="padding:10px 16px 0;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.8px;color:var(--canada);border-bottom:2px solid var(--canada);margin-bottom:0;display:inline-block">Offense</div>'+
      '<div class="tbl-wrap"><table class="pt-tbl"><thead><tr>'+
        '<th style="text-align:left">PLAY TYPE</th><th>POSS</th><th>%TIME</th>'+
        '<th>PPP</th><th>RATING</th><th>RANK</th>'+
        '<th>EFG%</th><th>2FG%</th><th>3FG%</th><th>TO%</th><th>FT%</th>'+
      '</tr></thead><tbody>'+ptHtml+'</tbody></table></div>'+
      '<div style="margin-top:24px;padding:10px 16px 0;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.8px;color:var(--text2);border-bottom:2px solid var(--border2);margin-bottom:0;display:inline-block">Defense (PPP Allowed)</div>'+
      '<div class="tbl-wrap"><table class="pt-tbl"><thead><tr>'+
        '<th style="text-align:left">PLAY TYPE</th><th>POSS</th><th>%TIME</th>'+
        '<th>PPP</th><th>RATING</th><th>RANK</th>'+
        '<th>EFG%</th><th>2FG%</th><th>3FG%</th><th>TO%</th><th>FT%</th>'+
      '</tr></thead><tbody>'+(ptDefHtml||'<tr><td colspan="11" class="empty" style="padding:16px">No defensive play type data — re-run scraper</td></tr>')+'</tbody></table></div>'+
    '</div>'+
    defHtml;
}

// ── Navigation helpers ────────────────────────────────────────────────────────
function navTo(tabId){
  document.querySelectorAll('.tab').forEach(function(t){t.classList.remove('active');});
  document.querySelectorAll('.nav-btn').forEach(function(b){
    var oc=b.getAttribute('onclick')||'';
    b.classList.toggle('active', oc.indexOf("'"+tabId+"'")>=0);
  });
  var el=document.getElementById('tab-'+tabId); if(el) el.classList.add('active');
}
function goTeam(tid){
  document.getElementById('search-dropdown').style.display='none';
  document.getElementById('search-input').value='';
  var sel=document.getElementById('ti-team'); sel.value=tid;
  navTo('team-intel'); renderTeamIntel();
}
function goPlayer(tid,pid){
  document.getElementById('search-dropdown').style.display='none';
  document.getElementById('search-input').value='';
  var ts=document.getElementById('pi-team'); ts.value=tid; populatePiPlayers();
  setTimeout(function(){
    var ps=document.getElementById('pi-player'); ps.value=pid;
    navTo('player-intel'); renderPlayerIntel();
  },30);
}

// ── Global search ─────────────────────────────────────────────────────────────
function globalSearch(q){
  var drop=document.getElementById('search-dropdown');
  if(!q||q.length<2){drop.style.display='none';return;}
  q=q.toLowerCase();
  var tm=TEAMS.filter(function(t){return t.name.toLowerCase().indexOf(q)>=0;}).slice(0,5);
  var pm=PLAYERS.filter(function(p){return p.name.toLowerCase().indexOf(q)>=0;}).slice(0,8);
  if(!tm.length&&!pm.length){drop.innerHTML='<div class="search-item"><div class="search-item-name" style="color:var(--text3)">No results</div></div>';drop.style.display='block';return;}
  var h='';
  if(tm.length){
    h+='<div class="search-shdr">Teams</div>';
    tm.forEach(function(t){
      var nr=TR[t.id]?TR[t.id].net:null;
      h+='<div class="search-item" onclick="goTeam(\''+t.id+'\')">'+
        '<div class="search-item-name">'+esc(t.name)+'</div>'+
        '<div class="search-item-sub">'+t.gp+' GP &middot; Net: '+(nr?'#'+nr+'/'+TEAMS.length:'—')+' &middot; Off PPP: '+f3(ppp(t.off))+'</div>'+
      '</div>';
    });
  }
  if(pm.length){
    h+='<div class="search-shdr">Players</div>';
    pm.forEach(function(p){
      h+='<div class="search-item" onclick="goPlayer(\''+p.tid+'\',\''+p.id+'\')">'+
        '<div class="search-item-name">'+esc(p.name)+'</div>'+
        '<div class="search-item-sub">'+esc(p.team)+' &middot; '+p.gp+' GP &middot; '+p.off.p+' poss &middot; PPP: '+f3(ppp(p.off))+'</div>'+
      '</div>';
    });
  }
  drop.innerHTML=h; drop.style.display='block';
}

// ── Conference filter ───────────────────────────────────────────────────────
var CONF='';
var CONFS=['CW','OUA','RSEQ','AUS'];
var CONF_NAMES={CW:'Canada West',OUA:'OUA',RSEQ:'RSEQ',AUS:'AUS'};
var CONF_COLORS={CW:'#2563eb',OUA:'#7c3aed',RSEQ:'#0891b2',AUS:'#c2410c'};
var HOME=TEAMS.filter(function(t){return /waterloo/i.test(t.name);})[0];
var HOME_ID=HOME?HOME.id:'';
var TEAM_CONF={};
TEAMS.forEach(function(t){TEAM_CONF[t.id]=t.conf;});
function inConf(t){return !CONF||t.conf===CONF;}
function pInConf(p){return !CONF||TEAM_CONF[p.tid]===CONF;}
function confChip(c,big){
  if(!c) return '';
  var st=big?'font-size:13px;padding:2px 8px;border-radius:5px;':'';
  return '<span class="tcmp-chip" style="'+st+'background:'+(CONF_COLORS[c]||'#6b7280')+';color:#fff">'+esc(c)+'</span>';
}
function setConf(c,btn){
  CONF=c;
  document.querySelectorAll('#conf-group .toggle-btn').forEach(function(b){b.classList.remove('active');});
  btn.classList.add('active');
  renderOverview(); renderTeamRank(); renderPlayerRank();
  var ptChip=document.querySelector('.pt-chip.active'); if(ptChip) ptChip.click();
}

// ── Scatter plot ──────────────────────────────────────────────────────────────
function renderScatterPlot(){
  var el=document.getElementById('ov-scatter'); if(!el) return;
  var validT=TEAMS.filter(function(t){return t.off.p>0&&t.def.p>0&&inConf(t);});
  var ghostT=TEAMS.filter(function(t){return t.off.p>0&&t.def.p>0&&!inConf(t);});
  var W=1200,H=480,pL=68,pR=24,pT=28,pB=52,iW=W-pL-pR,iH=H-pT-pB;
  var offs=validT.map(function(t){return ppp(t.off);});
  var defs=validT.map(function(t){return ppp(t.def);});
  var minO=Math.min.apply(null,offs)-0.04, maxO=Math.max.apply(null,offs)+0.04;
  var minD=Math.min.apply(null,defs)-0.04, maxD=Math.max.apply(null,defs)+0.04;
  var totalPts=0,totalPoss=0,totalDP=0,totalDPoss=0;
  validT.forEach(function(t){totalPts+=t.off.pts;totalPoss+=t.off.p;totalDP+=t.def.pts;totalDPoss+=t.def.p;});
  var avgO=totalPoss?totalPts/totalPoss:0.8, avgD=totalDPoss?totalDP/totalDPoss:0.8;
  function xS(v){return pL+(v-minO)/(maxO-minO)*iW;}
  function yS(v){return pT+(v-minD)/(maxD-minD)*iH;}
  var ax=xS(avgO), ay=yS(avgD);
  var svg='<svg width="100%" viewBox="0 0 '+W+' '+H+'" style="font-family:-apple-system,sans-serif;display:block;overflow:hidden">';
  svg+='<defs><clipPath id="plot-area"><rect x="'+pL+'" y="'+pT+'" width="'+iW+'" height="'+iH+'"/></clipPath></defs>';
  // quadrant fills
  svg+='<rect x="'+pL+'" y="'+pT+'" width="'+(ax-pL)+'" height="'+(ay-pT)+'" fill="rgba(26,86,219,.06)"/>';  // good D, below-avg O
  svg+='<rect x="'+ax+'" y="'+pT+'" width="'+(pL+iW-ax)+'" height="'+(ay-pT)+'" fill="rgba(22,163,74,.08)"/>';  // elite
  svg+='<rect x="'+pL+'" y="'+ay+'" width="'+(ax-pL)+'" height="'+(pT+iH-ay)+'" fill="rgba(220,38,38,.07)"/>';  // struggling
  svg+='<rect x="'+ax+'" y="'+ay+'" width="'+(pL+iW-ax)+'" height="'+(pT+iH-ay)+'" fill="rgba(217,119,6,.06)"/>';  // good O, poor D
  // quadrant labels
  svg+='<text x="'+(ax+6)+'" y="'+(pT+14)+'" fill="rgba(22,163,74,.8)" font-size="10" font-weight="700">ELITE</text>';
  svg+='<text x="'+(pL+4)+'" y="'+(pT+14)+'" fill="rgba(26,86,219,.7)" font-size="10" font-weight="700">DEFENSIVE</text>';
  svg+='<text x="'+(ax+6)+'" y="'+(pT+iH-6)+'" fill="rgba(217,119,6,.8)" font-size="10" font-weight="700">OFFENSIVE</text>';
  svg+='<text x="'+(pL+4)+'" y="'+(pT+iH-6)+'" fill="rgba(220,38,38,.8)" font-size="10" font-weight="700">STRUGGLING</text>';
  // grid
  for(var gi=0;gi<=4;gi++){
    var gv=minO+(maxO-minO)*gi/4, gx=xS(gv);
    svg+='<line x1="'+gx.toFixed(1)+'" y1="'+pT+'" x2="'+gx.toFixed(1)+'" y2="'+(pT+iH)+'" stroke="#d1d5db" stroke-width="1"/>';
    svg+='<text x="'+gx.toFixed(1)+'" y="'+(pT+iH+16)+'" text-anchor="middle" fill="#6b7280" font-size="9" font-weight="500">'+gv.toFixed(3)+'</text>';
    var dv=minD+(maxD-minD)*gi/4, gy=yS(dv);
    svg+='<line x1="'+pL+'" y1="'+gy.toFixed(1)+'" x2="'+(pL+iW)+'" y2="'+gy.toFixed(1)+'" stroke="#d1d5db" stroke-width="1"/>';
    svg+='<text x="'+(pL-5)+'" y="'+gy.toFixed(1)+'" text-anchor="end" dominant-baseline="middle" fill="#6b7280" font-size="9" font-weight="500">'+dv.toFixed(3)+'</text>';
  }
  // avg lines
  svg+='<line x1="'+ax.toFixed(1)+'" y1="'+pT+'" x2="'+ax.toFixed(1)+'" y2="'+(pT+iH)+'" stroke="#d4a900" stroke-width="1.5" stroke-dasharray="6,3" opacity="0.6"/>';
  svg+='<line x1="'+pL+'" y1="'+ay.toFixed(1)+'" x2="'+(pL+iW)+'" y2="'+ay.toFixed(1)+'" stroke="#d4a900" stroke-width="1.5" stroke-dasharray="6,3" opacity="0.6"/>';
  svg+='<g clip-path="url(#plot-area)">';
  // ghost dots (other conferences) — shown dim, no labels
  ghostT.forEach(function(t){
    var x=xS(ppp(t.off)), y=yS(ppp(t.def));
    svg+='<circle cx="'+x.toFixed(1)+'" cy="'+y.toFixed(1)+'" r="4" fill="#9ca3af" fill-opacity="0.3" stroke="#9ca3af" stroke-width="1" style="cursor:pointer" onclick="goTeam(\''+t.id+'\')"><title>'+esc(t.name)+' ['+t.conf+']\nOff PPP: '+f3(ppp(t.off))+'\nDef PPP: '+f3(ppp(t.def))+'</title></circle>';
  });
  // main dots
  validT.forEach(function(t){
    var x=xS(ppp(t.off)), y=yS(ppp(t.def)), n=net(t);
    var col=n>=0.10?'#16a34a':n>=-0.05?'#eab308':n>=-0.15?'#f97316':'#dc2626';
    var r=7, op=0.9, sw=1.5;
    if(t.id===HOME_ID) svg+='<circle cx="'+x.toFixed(1)+'" cy="'+y.toFixed(1)+'" r="13" fill="#FFD100" fill-opacity="0.35" stroke="#231F20" stroke-width="2.5"/>';
    svg+='<circle cx="'+x.toFixed(1)+'" cy="'+y.toFixed(1)+'" r="'+r+'" fill="'+col+'" fill-opacity="'+op+'" stroke="#fff" stroke-width="'+sw+'" style="cursor:pointer" onclick="goTeam(\''+t.id+'\')"><title>'+esc(t.name)+' ['+t.conf+']\nOff PPP: '+f3(ppp(t.off))+'\nDef PPP: '+f3(ppp(t.def))+'\nNet: '+(n>=0?'+':'')+f3(n)+'</title></circle>';
    // label everyone inside one conference; league-wide, only the extremes
    var nr=TR[t.id]?TR[t.id].net:99;
    if(CONF||t.id===HOME_ID||nr<=5||nr>=validT.length-3){
      var anchor=x>ax?'start':'end'; var lx=x>ax?x+9:x-9;
      svg+='<text x="'+lx.toFixed(1)+'" y="'+(y+3).toFixed(1)+'" text-anchor="'+anchor+'" fill="#374151" font-size="9" font-weight="600" style="pointer-events:none">'+esc(t.name)+'</text>';
    }
  });
  svg+='</g>';
  // axis labels
  svg+='<text x="'+(pL+iW/2)+'" y="'+(H-4)+'" text-anchor="middle" fill="#374151" font-size="11" font-weight="600">Offensive PPP &#8594;</text>';
  svg+='<text transform="rotate(-90)" x="'+(-(pT+iH/2))+'" y="16" text-anchor="middle" fill="#374151" font-size="11" font-weight="600">Defensive PPP allowed &#8595; (lower = better, &#8593; = elite defense)</text>';
  svg+='</svg>';
  var legend='<div style="display:flex;gap:20px;flex-wrap:wrap;margin-top:8px;font-size:11px;color:var(--text2)">';
  [{c:'#16a34a',l:'Net &ge;+0.10'},{c:'#eab308',l:'Net &minus;0.05 to +0.10'},{c:'#f97316',l:'Net &minus;0.15 to &minus;0.05'},{c:'#dc2626',l:'Net &lt;&minus;0.15'}].forEach(function(it){
    legend+='<span><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:'+it.c+';margin-right:5px;vertical-align:middle"></span>'+it.l+'</span>';
  });
  legend+='<span style="margin-left:8px;padding-left:8px;border-left:1px solid var(--border)"><svg width="10" height="10" style="vertical-align:middle;margin-right:3px"><circle cx="5" cy="5" r="4" fill="#888" stroke="#fff" stroke-width="1.5"/></svg>Tier 1 (large)</span>';
  legend+='<span><svg width="10" height="10" style="vertical-align:middle;margin-right:3px"><circle cx="5" cy="5" r="3" fill="#888" stroke="#fff" stroke-width="1.2"/></svg>Tier 2</span>';
  legend+='<span><svg width="10" height="10" style="vertical-align:middle;margin-right:3px"><circle cx="5" cy="5" r="2" fill="#9ca3af" fill-opacity="0.4" stroke="#9ca3af" stroke-width="1"/></svg>Tier 3 (dim)</span>';
  legend+='<span style="color:var(--text3)"><span style="display:inline-block;width:20px;height:2px;border-top:2px dashed #d4a900;vertical-align:middle;margin-right:5px"></span>avg (filtered set)</span></div>';
  el.innerHTML=svg+legend;
}

// ── Tier distribution ─────────────────────────────────────────────────────────
function renderTierDist(){
  var el=document.getElementById('ov-tier-dist'); if(!el) return;
  var tiers={S:0,A:0,B:0,C:0,D:0};
  var cols={S:'#ffd700',A:'#3fb950',B:'#d4a900',C:'#d29922',D:'#f85149'};
  var labels={S:'Elite (top 10%)',A:'Strong (top 25%)',B:'Average (50%)',C:'Below Avg',D:'Struggling'};
  var N=TEAMS.length;
  TEAMS.forEach(function(t){
    var r=TR[t.id]; if(!r||!r.net) return;
    var tier=tierStr(rPct(r.net,N)); tiers[tier]++;
  });
  var maxC=Math.max(tiers.S,tiers.A,tiers.B,tiers.C,tiers.D)||1;
  var h='<div style="display:flex;gap:8px;padding:8px;flex:1;min-height:200px">';
  ['S','A','B','C','D'].forEach(function(t){
    var barPct=Math.max(Math.round(tiers[t]/maxC*78),3);
    h+='<div style="flex:1;display:flex;flex-direction:column;align-items:center;gap:3px">'+
      '<div style="font-size:13px;font-weight:700;color:'+cols[t]+'">'+tiers[t]+'</div>'+
      '<div style="flex:1;display:flex;align-items:flex-end;justify-content:center;width:100%">'+
        '<div style="width:70%;height:'+barPct+'%;background:'+cols[t]+';border-radius:4px 4px 0 0;min-height:4px"></div>'+
      '</div>'+
      '<div style="font-size:14px;font-weight:800;color:'+cols[t]+'">'+t+'</div>'+
      '<div style="font-size:9px;color:var(--text3);text-align:center">'+labels[t]+'</div>'+
    '</div>';
  });
  h+='</div>';
  el.innerHTML=h;
}

// ── Shot quality ──────────────────────────────────────────────────────────────
function renderShotQuality(){
  var el=document.getElementById('ov-shot-quality'); if(!el) return;
  var validT=TEAMS.filter(function(t){return t.off.sqa>0;});
  if(!validT.length){el.innerHTML='<div class="empty">No shot quality data</div>';return;}
  // Shot quality: sq = total quality score, sqa = attempts with quality data
  // avgSQ = sq/sqa = avg quality per shot (higher = better looks)
  // actualPPS = pts/sa = actual points per shot
  // overperform = actualPPS > expected based on quality
  var rows=validT.map(function(t){
    var avgQ=t.off.sqa>0?t.off.sq/t.off.sqa:0;
    var actualPPS=t.off.sa>0?t.off.pts/t.off.sa:0;
    return {t:t, q:avgQ, pps:actualPPS, diff:actualPPS-avgQ};
  }).sort(function(a,b){return b.q-a.q;});
  var maxQ=rows[0]?rows[0].q:1;
  var h='<div style="font-size:10px;color:var(--text3);margin-bottom:8px">Shot Quality = avg synergy shot quality score per attempt (higher = better looks). PPS = actual points per shot.</div>';
  rows.slice(0,10).forEach(function(row,i){
    var col=row.diff>0?'#3fb950':'#f85149';
    h+=hbar(row.t.name, row.q/maxQ*100, 'SQ:'+row.q.toFixed(3)+' PPS:'+row.pps.toFixed(3)+' ('+(row.diff>=0?'+':'')+row.diff.toFixed(3)+')', col);
  });
  el.innerHTML=h;
}

// ── Play Type Explorer ────────────────────────────────────────────────────────
var activePTE='Transition';
var ptGPMin=0;
function setPTGP(gp,btn){
  ptGPMin=gp;
  document.querySelectorAll('#pt-gp-0,#pt-gp-3,#pt-gp-5,#pt-gp-8').forEach(function(b){b.classList.remove('active');});
  btn.classList.add('active');
  renderPlayTypeExplorer();
}

function renderPlayTypeExplorer(pt){
  if(pt) activePTE=pt;
  // Update chips
  var chips=document.getElementById('pte-chips');
  if(chips){
    var ch='';
    PLAY_TYPES.forEach(function(p){
      ch+='<div class="pt-chip'+(p===activePTE?' active':'')+'" onclick="renderPlayTypeExplorer(\''+esc(p)+'\')">'+esc(p)+'</div>';
    });
    chips.innerHTML=ch;
  }
  var tEl=document.getElementById('pte-teams');
  var pEl=document.getElementById('pte-players');
  if(!tEl||!pEl) return;

  // Team rankings
  var teams=TEAMS.filter(function(t){return t.pt_off[activePTE]&&t.pt_off[activePTE].p>0&&(t.pt_off[activePTE].gp||0)>=ptGPMin;});
  teams.sort(function(a,b){return ppp(b.pt_off[activePTE])-ppp(a.pt_off[activePTE]);});
  var lgPoss=0,lgPts=0;
  teams.forEach(function(t){var d=t.pt_off[activePTE];lgPoss+=d.p;lgPts+=d.pts;});
  var lgAvg=lgPoss?lgPts/lgPoss:0;
  var gpNote=ptGPMin>0?' &middot; min '+ptGPMin+' GP':'';
  var tHtml='<div style="font-size:10px;color:var(--text3);margin-bottom:10px">'+
    teams.length+' teams'+gpNote+' &middot; League avg PPP: <strong style="color:var(--text)">'+f3(lgAvg)+'</strong></div>';
  tHtml+='<div class="tbl-wrap"><table class="pt-tbl"><thead><tr>'+
    '<th style="text-align:left">#</th><th style="text-align:left">Team</th>'+
    '<th>POSS</th><th>FREQ%</th><th>PPP</th><th>vs Avg</th><th>EFG%</th><th>TO%</th>'+
  '</tr></thead><tbody>';
  teams.forEach(function(t,i){
    var d=t.pt_off[activePTE];
    var v=ppp(d), diff=v-lgAvg, freq=t.off.p>0?d.p/t.off.p*100:0;
    var diffCol=diff>=0?'#3fb950':'#f85149';
    tHtml+='<tr onclick="goTeam(\''+t.id+'\')" style="cursor:pointer">'+
      '<td class="rank-cell">'+(i+1)+'</td>'+
      '<td style="font-weight:600">'+esc(t.name)+'</td>'+
      '<td>'+d.p+'</td>'+
      '<td>'+freq.toFixed(1)+'%</td>'+
      '<td class="'+cPPP(v)+'">'+f3(v)+'</td>'+
      '<td><span style="color:'+diffCol+';font-weight:700;font-size:11px">'+(diff>=0?'+':'')+diff.toFixed(3)+'</span></td>'+
      '<td>'+fP(efg(d))+'</td>'+
      '<td class="'+cTO(topR(d))+'">'+fP(topR(d))+'</td>'+
    '</tr>';
  });
  tHtml+='</tbody></table></div>';
  tEl.innerHTML=tHtml;

  // Player leaders
  var minPoss=Math.max(5,ptGPMin*3);
  var players=PLAYERS.filter(function(p){return p.pt_off[activePTE]&&p.pt_off[activePTE].p>=minPoss&&(p.pt_off[activePTE].gp||0)>=ptGPMin;});
  players.sort(function(a,b){return ppp(b.pt_off[activePTE])-ppp(a.pt_off[activePTE]);});
  var pHtml='<div class="tbl-wrap"><table class="pt-tbl"><thead><tr>'+
    '<th style="text-align:left">#</th><th style="text-align:left">Player</th><th style="text-align:left">Team</th>'+
    '<th>POSS</th><th>PPP</th><th>vs Avg</th><th>EFG%</th><th>TO%</th>'+
  '</tr></thead><tbody>';
  players.slice(0,30).forEach(function(p,i){
    var d=p.pt_off[activePTE], v=ppp(d), diff=v-lgAvg;
    var diffCol=diff>=0?'#3fb950':'#f85149';
    pHtml+='<tr onclick="goPlayer(\''+p.tid+'\',\''+p.id+'\')" style="cursor:pointer">'+
      '<td class="rank-cell">'+(i+1)+'</td>'+
      '<td style="font-weight:600;color:var(--canada)">'+esc(p.name)+'</td>'+
      '<td style="color:var(--text2)">'+esc(p.team)+'</td>'+
      '<td>'+d.p+'</td>'+
      '<td class="'+cPPP(v)+'">'+f3(v)+'</td>'+
      '<td><span style="color:'+diffCol+';font-weight:700;font-size:11px">'+(diff>=0?'+':'')+diff.toFixed(3)+'</span></td>'+
      '<td>'+fP(efg(d))+'</td>'+
      '<td class="'+cTO(topR(d))+'">'+fP(topR(d))+'</td>'+
    '</tr>';
  });
  pHtml+='</tbody></table></div>';
  pEl.innerHTML=pHtml;
}

// ── Player Compare ────────────────────────────────────────────────────────────
function populatePcSelects(){
  var byTeam={};
  PLAYERS.forEach(function(p){
    if(!byTeam[p.team]) byTeam[p.team]=[];
    byTeam[p.team].push(p);
  });
  var tnames=Object.keys(byTeam).sort();
  var opts='<option value="">-- Select Player --</option>';
  tnames.forEach(function(tn){
    opts+='<optgroup label="'+esc(tn)+'">';
    byTeam[tn].sort(function(a,b){return a.name.localeCompare(b.name);}).forEach(function(p){
      opts+='<option value="'+p.id+'">'+esc(p.name)+'</option>';
    });
    opts+='</optgroup>';
  });
  ['pc-a','pc-b'].forEach(function(id){
    var el=document.getElementById(id); if(el) el.innerHTML=opts;
  });
}
function renderPlayerCompare(){
  var pidA=document.getElementById('pc-a').value;
  var pidB=document.getElementById('pc-b').value;
  var el=document.getElementById('pc-content');
  if(!pidA||!pidB){el.innerHTML='<div class="empty">Select two players to compare</div>';return;}
  if(pidA===pidB){el.innerHTML='<div class="empty">Select two different players</div>';return;}
  var pA=null,pB=null;
  PLAYERS.forEach(function(p){if(p.id===pidA)pA=p;if(p.id===pidB)pB=p;});
  if(!pA||!pB) return;
  var pool=PLAYERS.filter(function(x){return x.off.p>=15;}); var NP=pool.length;
  var prA=PR[pA.id]||{}, prB=PR[pB.id]||{};
  var oA=pA.off, oB=pB.off;

  // Radar
  var rLabels=['PPP','EFG%','TS%','2FG%','3FG%','Ball Sec.','FT Rate','Volume'];
  function rpv(pr){
    return [rPct(pr.ppp,NP)||0, rPct(pr.efg,NP)||0, rPct(pr.ts,NP)||0,
            rPct(pr.fg2,NP)||0, rPct(pr.fg3,NP)||0, rPct(pr.to,NP)||0,
            rPct(pr.ftr,NP)||0, rPct(pr.vol,NP)||0];
  }
  var colA_team=countryColor(pA.team), colB_team=countryColor(pB.team);
  var svgA=radarSvg(rpv(prA),rLabels,colA_team);
  var svgB=radarSvg(rpv(prB),rLabels,colB_team);

  // Comparison rows
  function cRow(lbl,vA,vB,rkA,rkB,lbetter){
    var pA2=rkA?rPct(rkA,NP):50, pB2=rkB?rPct(rkB,NP):50;
    var cA=rkA?colA_team:'var(--text2)', cB=rkB?colB_team:'var(--text2)';
    var wA=lbetter?(parseFloat(vA)||0)<=(parseFloat(vB)||0):(parseFloat(vA)||0)>=(parseFloat(vB)||0);
    return '<div class="cmp-row">'+
      '<div class="cmp-a" style="color:'+cA+'">'+(wA?'<span style="font-size:16px">&#9654;</span> ':'')+vA+' <span class="cmp-rank">'+(rkA?'#'+rkA:'<span style="color:var(--text3);font-size:9px">N/Q</span>')+'</span></div>'+
      '<div class="cmp-label">'+lbl+'</div>'+
      '<div class="cmp-b" style="color:'+cB+'">'+vB+' <span class="cmp-rank">'+(rkB?'#'+rkB:'<span style="color:var(--text3);font-size:9px">N/Q</span>')+'</span>'+(!wA?' <span style="font-size:16px">&#9664;</span>':'')+'</div>'+
    '</div>';
  }

  var statsHtml=
    '<div style="display:grid;grid-template-columns:1fr auto 1fr;padding:8px 0;border-bottom:2px solid var(--border)">'+
      '<div style="text-align:right;padding-right:12px;font-size:14px;font-weight:800;color:'+colA_team+'">'+esc(pA.name)+'<div style="font-size:10px;font-weight:400;color:var(--text2)">'+esc(pA.team)+' &middot; '+pA.gp+' GP &middot; '+oA.p+' poss</div></div>'+
      '<div style="text-align:center;font-size:10px;font-weight:700;color:var(--text3);padding:0 8px;align-self:center">STAT</div>'+
      '<div style="text-align:left;padding-left:12px;font-size:14px;font-weight:800;color:'+colB_team+'">'+esc(pB.name)+'<div style="font-size:10px;font-weight:400;color:var(--text2)">'+esc(pB.team)+' &middot; '+pB.gp+' GP &middot; '+oB.p+' poss</div></div>'+
    '</div>'+
    cRow('PPP', oA.p?f3(ppp(oA)):'—', oB.p?f3(ppp(oB)):'—', prA.ppp, prB.ppp, false)+
    cRow('EFG%', oA.fa?fP(efg(oA)):'—', oB.fa?fP(efg(oB)):'—', prA.efg, prB.efg, false)+
    cRow('TS%', oA.fa?fP(ts(oA)):'—', oB.fa?fP(ts(oB)):'—', prA.ts, prB.ts, false)+
    cRow('2FG%', oA.a2?fP(fg2(oA)):'0 att', oB.a2?fP(fg2(oB)):'0 att', prA.fg2, prB.fg2, false)+
    cRow('3FG%', oA.a3?fP(fg3(oA)):'0 att', oB.a3?fP(fg3(oB)):'0 att', prA.fg3, prB.fg3, false)+
    cRow('TO%', oA.p?fP(topR(oA)):'—', oB.p?fP(topR(oB)):'—', prA.to, prB.to, true)+
    cRow('FT Rate', oA.p?fP(ftr(oA)):'—', oB.p?fP(ftr(oB)):'—', prA.ftr, prB.ftr, false)+
    cRow('Possessions', oA.p||0, oB.p||0, prA.vol, prB.vol, false);

  // Play type PPP head-to-head
  // Butterfly chart for play types
  var allPPPs=[];
  PLAY_TYPES.forEach(function(pt){
    var dA=pA.pt_off[pt]||{},dB=pB.pt_off[pt]||{};
    if(dA.p) allPPPs.push(ppp(dA));
    if(dB.p) allPPPs.push(ppp(dB));
  });
  var maxPPP=allPPPs.length?Math.max.apply(null,allPPPs)*1.05:2;
  var ptRows='';
  var ptSortedOff2=PLAY_TYPES.slice().sort(function(a,b){
    return (((pB.pt_off[b]||{}).p||0)+((pA.pt_off[b]||{}).p||0))-(((pB.pt_off[a]||{}).p||0)+((pA.pt_off[a]||{}).p||0));
  });
  ptSortedOff2.forEach(function(pt){
    var dA=pA.pt_off[pt]||{},dB=pB.pt_off[pt]||{};
    if(!dA.p&&!dB.p) return;
    var vA=dA.p?ppp(dA):null, vB=dB.p?ppp(dB):null;
    var winA=vA!==null&&vB!==null&&vA>=vB;
    var winB=vA!==null&&vB!==null&&vB>vA;
    var wA=vA?Math.min(vA/maxPPP*100,100):0, wB=vB?Math.min(vB/maxPPP*100,100):0;
    var colA=winA?colA_team:'var(--border2)', colB=winB?colB_team:'var(--border2)';
    ptRows+=
      '<div style="display:grid;grid-template-columns:1fr 130px 1fr;align-items:center;gap:4px;padding:5px 0;border-bottom:1px solid var(--border)">'+
        '<div style="display:flex;align-items:center;justify-content:flex-end;gap:6px">'+
          '<span style="font-size:11px;font-weight:'+(winA?700:400)+';color:'+(winA?colA_team:'var(--text2)')+'">'+
            (vA!==null?f3(vA)+' <span style="color:var(--text3);font-size:9px">('+dA.p+'p)</span>':'<span style="color:var(--text3)">—</span>')+
          '</span>'+
          '<div style="width:80px;height:14px;background:var(--bg3);border-radius:3px 0 0 3px;overflow:hidden;display:flex;justify-content:flex-end">'+
            '<div style="width:'+wA.toFixed(1)+'%;height:100%;background:'+colA+'"></div></div>'+
        '</div>'+
        '<div style="text-align:center;font-size:10px;color:var(--text2);font-weight:600;padding:0 6px">'+esc(pt)+'</div>'+
        '<div style="display:flex;align-items:center;gap:6px">'+
          '<div style="width:80px;height:14px;background:var(--bg3);border-radius:0 3px 3px 0;overflow:hidden">'+
            '<div style="width:'+wB.toFixed(1)+'%;height:100%;background:'+colB+'"></div></div>'+
          '<span style="font-size:11px;font-weight:'+(winB?700:400)+';color:'+(winB?colB_team:'var(--text2)')+'">'+
            (vB!==null?f3(vB)+' <span style="color:var(--text3);font-size:9px">('+dB.p+'p)</span>':'<span style="color:var(--text3)">—</span>')+
          '</span>'+
        '</div>'+
      '</div>';
  });

  // Play type defense butterfly
  var allDefPPPs=[];
  PLAY_TYPES.forEach(function(pt){
    var dA=pA.pt_def[pt]||{},dB=pB.pt_def[pt]||{};
    if(dA.p) allDefPPPs.push(ppp(dA));
    if(dB.p) allDefPPPs.push(ppp(dB));
  });
  var maxDefPPP=allDefPPPs.length?Math.max.apply(null,allDefPPPs)*1.05:2;
  var ptDefRows='';
  var ptSortedDef2=PLAY_TYPES.slice().sort(function(a,b){
    return (((pB.pt_def[b]||{}).p||0)+((pA.pt_def[b]||{}).p||0))-(((pB.pt_def[a]||{}).p||0)+((pA.pt_def[a]||{}).p||0));
  });
  ptSortedDef2.forEach(function(pt){
    var dA=pA.pt_def[pt]||{},dB=pB.pt_def[pt]||{};
    if(!dA.p&&!dB.p) return;
    var vA=dA.p?ppp(dA):null, vB=dB.p?ppp(dB):null;
    // Lower PPP allowed is better for defense
    var winA=vA!==null&&vB!==null&&vA<=vB;
    var winB=vA!==null&&vB!==null&&vB<vA;
    var wA=vA?Math.min(vA/maxDefPPP*100,100):0, wB=vB?Math.min(vB/maxDefPPP*100,100):0;
    var colA_d=winA?colA_team:'var(--border2)', colB_d=winB?colB_team:'var(--border2)';
    ptDefRows+=
      '<div style="display:grid;grid-template-columns:1fr 130px 1fr;align-items:center;gap:4px;padding:5px 0;border-bottom:1px solid var(--border)">'+
        '<div style="display:flex;align-items:center;justify-content:flex-end;gap:6px">'+
          '<span style="font-size:11px;font-weight:'+(winA?700:400)+';color:'+(winA?colA_team:'var(--text2)')+'">'+
            (vA!==null?f3(vA)+' <span style="color:var(--text3);font-size:9px">('+dA.p+'p)</span>':'<span style="color:var(--text3)">—</span>')+
          '</span>'+
          '<div style="width:80px;height:14px;background:var(--bg3);border-radius:3px 0 0 3px;overflow:hidden;display:flex;justify-content:flex-end">'+
            '<div style="width:'+wA.toFixed(1)+'%;height:100%;background:'+colA_d+'"></div></div>'+
        '</div>'+
        '<div style="text-align:center;font-size:10px;color:var(--text2);font-weight:600;padding:0 6px">'+esc(pt)+'</div>'+
        '<div style="display:flex;align-items:center;gap:6px">'+
          '<div style="width:80px;height:14px;background:var(--bg3);border-radius:0 3px 3px 0;overflow:hidden">'+
            '<div style="width:'+wB.toFixed(1)+'%;height:100%;background:'+colB_d+'"></div></div>'+
          '<span style="font-size:11px;font-weight:'+(winB?700:400)+';color:'+(winB?colB_team:'var(--text2)')+'">'+
            (vB!==null?f3(vB)+' <span style="color:var(--text3);font-size:9px">('+dB.p+'p)</span>':'<span style="color:var(--text3)">—</span>')+
          '</span>'+
        '</div>'+
      '</div>';
  });

  el.innerHTML=
    '<div class="grid2" style="margin-bottom:16px">'+
      '<div style="text-align:center"><div style="font-size:12px;font-weight:700;color:'+colA_team+';margin-bottom:10px">'+esc(pA.name)+'</div><div class="radar-wrap">'+svgA+'</div></div>'+
      '<div style="text-align:center"><div style="font-size:12px;font-weight:700;color:'+colB_team+';margin-bottom:10px">'+esc(pB.name)+'</div><div class="radar-wrap">'+svgB+'</div></div>'+
    '</div>'+
    '<div class="card" style="margin-bottom:16px"><div class="card-hdr">Head-to-Head Stats (global rank vs '+NP+' qualified players)</div>'+
      '<div class="card-body">'+statsHtml+'</div></div>'+
    '<div class="card" style="margin-bottom:16px"><div class="card-hdr">Play Type PPP — Offense</div><div class="card-body">'+
      '<div style="display:grid;grid-template-columns:1fr 130px 1fr;gap:4px;padding:6px 0 8px;border-bottom:2px solid var(--border);margin-bottom:4px">'+
        '<div style="text-align:right;font-size:12px;font-weight:700;color:'+colA_team+'">'+esc(pA.name)+'</div>'+
        '<div style="text-align:center;font-size:10px;color:var(--text3);font-weight:600">PLAY TYPE (PPP)</div>'+
        '<div style="font-size:12px;font-weight:700;color:'+colB_team+'">'+esc(pB.name)+'</div>'+
      '</div>'+
      (ptRows||'<div class="empty">No play type data</div>')+
    '</div></div>'+
    '<div class="card"><div class="card-hdr">Play Type PPP — Defense <span style="font-weight:400;font-size:10px;text-transform:none;color:var(--text3)">(lower = better)</span></div><div class="card-body">'+
      '<div style="display:grid;grid-template-columns:1fr 130px 1fr;gap:4px;padding:6px 0 8px;border-bottom:2px solid var(--border);margin-bottom:4px">'+
        '<div style="text-align:right;font-size:12px;font-weight:700;color:'+colA_team+'">'+esc(pA.name)+'</div>'+
        '<div style="text-align:center;font-size:10px;color:var(--text3);font-weight:600">PPP ALLOWED</div>'+
        '<div style="font-size:12px;font-weight:700;color:'+colB_team+'">'+esc(pB.name)+'</div>'+
      '</div>'+
      (ptDefRows||'<div class="empty">No defensive play type data</div>')+
    '</div></div>';
}

// ── Init ──────────────────────────────────────────────────────────────────────
function init(){
  computeRanks();
  var teamOpts='';
  for(var i=0;i<TEAMS.length;i++) teamOpts+='<option value="'+esc(TEAMS[i].id)+'">'+esc(TEAMS[i].name)+'</option>';
  ['mu-a','mu-b','ti-team','pi-team'].forEach(function(id){
    var el=document.getElementById(id); if(el) el.innerHTML+=teamOpts;
  });
  var prTeam=document.getElementById('pr-team');
  if(prTeam) prTeam.innerHTML='<option value="">All Teams</option>'+teamOpts;
  var prPt=document.getElementById('pr-pt');
  if(prPt){
    var ptOpts='<option value="">Overall</option>';
    for(var j=0;j<PLAY_TYPES.length;j++) ptOpts+='<option value="'+PLAY_TYPES[j]+'">'+PLAY_TYPES[j]+'</option>';
    prPt.innerHTML=ptOpts;
  }
  populatePcSelects();
  renderPlayTypeExplorer('Transition');
  renderOverview(); renderTeamRank(); renderPlayerRank();
  if(HOME_ID){
    document.getElementById('ti-team').value=HOME_ID; renderTeamIntel();
    document.getElementById('mu-a').value=HOME_ID;
    document.getElementById('pi-team').value=HOME_ID; populatePiPlayers();
  }
}
init();
"""

DATA_BLOCK = ("const TEAMS="+teams_json+";\nconst PLAYERS="+players_json+";\nconst PLAY_TYPES="+pt_json+";\nconst SEASON_LABEL="+json.dumps(SEASON_LABEL)+";\n")
HTML = ('<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="UTF-8">\n'
    '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
    '<title>Waterloo Warriors WBB Analytics</title>\n'
    '<style>'+CSS+'</style>\n</head>\n<body>\n'+HTML_BODY+
    '<script>\n'+DATA_BLOCK+JS+'</script>\n</body>\n</html>\n'
).replace('{LOGO_SRC}', LOGO_SRC).replace('{SEASON}', SEASON_LABEL).replace('{UPDATED}', (' &middot; updated '+UPDATED) if UPDATED else '')

out = OUT
out.parent.mkdir(exist_ok=True)
out.write_text(HTML)
print(f'Written: {out}  ({out.stat().st_size//1024}KB)')
