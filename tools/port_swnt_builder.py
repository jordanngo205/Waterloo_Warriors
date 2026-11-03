#!/usr/bin/env python3
"""One-off: port the 5x5 SWNT dashboard builder to U SPORTS.

Replaces the competition-tier system (T1/T2/T3 + "vs T1-2 opponents" filter)
with U SPORTS conferences. Every replacement must match exactly once, so a
change upstream fails loudly instead of producing a half-ported file.

    python3 tools/port_swnt_builder.py <path/to/5x5_swnt/build_dashboard.py>
"""
import re, sys
from pathlib import Path

src = Path(sys.argv[1]).read_text()
out = Path(__file__).resolve().parent.parent / 'src' / 'build_dashboard.py'

# ---- python header: new data loader --------------------------------------
head_end = src.index("teams_json=json.dumps(TEAMS")
HEADER = r'''#!/usr/bin/env python3
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
        'gp':pr.get('gp',0),
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

def _rank_slices(items, key):
    """Re-rank every play-type slice so rank 1 is always BEST.

    The scraped pppRank is "highest PPP = 1" on both sides, which on defence
    means rank 1 is the team that ALLOWS the most -- the dashboard then called
    the worst defences elite. Rank defence ascending, offence descending, and
    store a percentile (pp, 100 = best) for the rating labels.
    """
    for side in ('pt_off', 'pt_def'):
        names = {k for it in items for k in it[side]}
        for pt in names:
            pool = [it[side][pt] for it in items if (it[side].get(pt) or {}).get('p', 0) > 0]
            pool.sort(key=lambda d: d['pts'] / d['p'], reverse=(side == 'pt_off'))
            n = len(pool)
            for i, d in enumerate(pool):
                d['pr'] = i + 1
                d['pn'] = n
                d['pp'] = round((n - 1 - i) / (n - 1) * 100) if n > 1 else 50

_rank_slices(TEAMS, 'pt')
_rank_slices(PLAYERS, 'pt')
SEASON_LABEL = META.get('season', SEASON)
UPDATED = (META.get('scraped_at') or '')[:10]
import base64
_logo = ROOT / 'assets' / 'warriors_logo.svg'
LOGO_SRC = ('data:image/svg+xml;base64,' + base64.b64encode(_logo.read_bytes()).decode()) if _logo.exists() else ''

'''
body = src[head_end:]

def rep(old, new, count=1):
    global body
    n = body.count(old)
    if n != count:
        sys.exit(f'expected {count} match(es), found {n}:\n{old[:200]}')
    body = body.replace(old, new)

def rep_re(pat, new, flags=re.S):
    global body
    body, n = re.subn(pat, new, body, flags=flags)
    if n != 1:
        sys.exit(f'regex matched {n} times: {pat[:120]}')

# ---- branding --------------------------------------------------------------
rep('    <img src="{LOGO_SRC}" alt="Canada Basketball">\n', '')
rep('<span class="logo-main">Canada Basketball</span>', '<span class="logo-main">U SPORTS</span>')
rep("<span class=\"logo-sub\">5×5 Women's Senior Analytics</span>",
    "<span class=\"logo-sub\">Women's Basketball Analytics{UPDATED}</span>")
rep('<span class="logo-badge">2025</span>', '<span class="logo-badge">{SEASON}</span>')
rep("'<title>Canada Basketball — 5×5 Women\\'s Analytics</title>\\n'",
    "'<title>U SPORTS Women\\'s Basketball</title>\\n'")
rep(").replace('{LOGO_SRC}', LOGO_SRC)",
    ").replace('{SEASON}', SEASON_LABEL).replace('{UPDATED}', (' &middot; updated '+UPDATED) if UPDATED else '')")
rep("out = DIR/'docs'/'index.html'\n", "out = OUT\n")
rep("scard(N,'Senior Teams','FIBA Women 2025')+", "scard(N,'Teams','U SPORTS Women '+SEASON_LABEL)+")
rep("scard(NP,'Players','across 81 rosters')+", "scard(NP,'Players','across '+N+' rosters')+")
rep("'#'+nr+'/81'", "'#'+nr+'/'+TEAMS.length")
rep('const PLAY_TYPES="+pt_json+";\\n")',
    'const PLAY_TYPES="+pt_json+";\\nconst SEASON_LABEL="+json.dumps(SEASON_LABEL)+";\\n")')

rep("pulse(fP(leagueDefPPP),'Avg Def PPP'", "pulse(f3(leagueDefPPP),'Avg Def PPP'")   # upstream bug: PPP shown as %

# upstream bug: .tier-chip is display:flex, so in a table cell it stretches into a full-width bar
rep("'<span class=\"tier-chip\" style=\"background:'+tc+';color:'+ttc+';font-size:9px;padding:1px 5px;border-radius:3px\">'",
    "'<span class=\"tier-chip\" style=\"display:inline-block;height:auto;background:'+tc+';color:'+ttc+';font-size:9px;padding:1px 5px;border-radius:3px\">'")

# ---- PPP cutoffs: calibrate to this league, not FIBA ------------------------
# The colour/label thresholds (1.10 "Elite", 0.78 "hot" defence, ...) are fixed
# numbers tuned for FIBA, whose league PPP is ~0.81. U SPORTS runs ~0.66 under
# Synergy's possession counting, so fixed cutoffs paint every defence elite and
# every offence poor. Scale every cutoff by league PPP / 0.81 instead.
rep("// ── Color helpers ─", """// League PPP calibration: thresholds below were tuned at a league PPP of 0.81.
var LEAGUE_PPP=(function(){var p=0,n=0;TEAMS.forEach(function(t){p+=t.off.pts||0;n+=t.off.p||0;});return n?p/n:0.81;})();
var PPP_SCALE=LEAGUE_PPP/0.81;
// ── Color helpers ─""")
for fn in ('cPPP', 'cPPPD', 'pppRating', 'pppRatingColor'):
    rep("function "+fn+"(v){", "function "+fn+"(v){ v=v/PPP_SCALE;")
# defence was mirrored as 1.8-PPP (FIBA-only); mirror around the league average
rep("pppRating(1.8-defPPP)", "pppRating(2*LEAGUE_PPP-defPPP)")

# ---- global filter bar: quality toggle -> conference toggle ----------------
rep_re(r'<div class="qual-bar">.*?<span id="qual-label"[^\n]*\n</div>\n',
'''<div class="qual-bar">
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
''')
rep_re(r'\n    <div style="display:flex;gap:6px">\n      <button class="toggle-btn" id="ov-t3".*?</div>\n', '\n')
rep_re(r'\n      <div style="display:flex;gap:6px">\n        <button class="toggle-btn" id="sct-t3".*?</div>\n', '\n')
rep_re(r'\n    <span style="margin-left:8px;font-size:11px;color:var\(--text2\)">Tier:</span>\n    <button class="toggle-btn" id="tr-t3".*?id="tr-t1"[^\n]*\n', '\n')
rep_re(r'\n    <span style="margin-left:8px;font-size:11px;color:var\(--text2\)">Tier:</span>\n    <button class="toggle-btn" id="pr-t3".*?id="pr-t1"[^\n]*\n', '\n')
rep_re(r'  <div id="pt-qual-note".*?</div>\n', '')
rep("<th onclick=\"sortPR('team')\">Team</th><th>Tier</th>", "<th onclick=\"sortPR('team')\">Team</th><th>Conf</th>")
rep("<option value=\"6\" selected>6+</option>", "<option value=\"6\">6+</option>")
rep("<option value=\"0\">All</option><option value=\"3\">3+</option>\n        <option value=\"6\">6+</option>",
    "<option value=\"0\" selected>All</option><option value=\"3\">3+</option>\n        <option value=\"6\">6+</option>")

# ---- ranks within conference instead of within tier ------------------------
rep_re(r"    // Within-tier ranks\n    \[1,2,3\]\.forEach\(function\(tier\)\{\n      var tierT=validT\.filter\(function\(t\)\{return t\.tier===tier;\}\);",
       "    // Within-conference ranks\n    CONFS.forEach(function(cf){\n      var tierT=validT.filter(function(t){return t.conf===cf;});")

# ---- filters ---------------------------------------------------------------
rep("TEAMS.filter(function(t){return t.off.p>0&&t.tier<=ovTierMax;});", "TEAMS.filter(function(t){return t.off.p>0&&inConf(t);});")
rep("// Player leaders — filtered by same tier as the rest of overview\n  var ovPlayers=PLAYERS.filter(function(p){return (TEAM_TIER[p.tid]||3)<=ovTierMax;});",
    "// Player leaders — filtered by the conference selector\n  var ovPlayers=PLAYERS.filter(pInConf);")
rep("var trSide='off',trSort='ppp',trAsc=false,trTierMax=2;", "var trSide='off',trSort='ppp',trAsc=false;")
rep_re(r"function setTRTier\(tier,btn\)\{.*?\n\}\n", '')
rep("t.gp>=minGP&&t.tier<=trTierMax;", "t.gp>=minGP&&inConf(t);")
rep("        '<span class=\"tcmp-chip tcmp-'+t.tier+'\">T'+t.tier+'</span> '+", "        confChip(t.conf)+' '+")
rep("    var ptier=TEAM_TIER[p.tid]||3;\n    if(ptier>prTierMax) return false;", "    if(!pInConf(p)) return false;")
rep("    var ptier=TEAM_TIER[p.tid]||3;\n", "")
rep("'<td><span class=\"tcmp-chip tcmp-'+ptier+'\">T'+ptier+'</span></td>'+", "'<td>'+confChip(TEAM_CONF[p.tid])+'</td>'+")
rep_re(r"  var qualNote=useQual&&t\.qgp\?.*?:'';\n", "  var qualNote='';\n")
rep(" <span class=\"tcmp-chip tcmp-'+t.tier+'\" style=\"font-size:13px;padding:2px 8px;border-radius:5px;vertical-align:middle\">T'+t.tier+'</span>",
    " '+confChip(t.conf,true)+'")
rep("&nbsp;&middot;&nbsp;T'+t.tier+' rank:", "&nbsp;&middot;&nbsp;'+esc(t.conf)+' rank:", count=2)

# ---- quality filter + tier lookups -> conference filter ---------------------
rep_re(r"// ── Quality game filter.*?\n// ── Scatter plot ─+\n.*?\nfunction renderScatterPlot\(\)\{",
r"""// ── Conference filter ───────────────────────────────────────────────────────
var CONF='';
var CONFS=['CW','OUA','RSEQ','AUS'];
var CONF_NAMES={CW:'Canada West',OUA:'OUA',RSEQ:'RSEQ',AUS:'AUS'};
var CONF_COLORS={CW:'#2563eb',OUA:'#7c3aed',RSEQ:'#0891b2',AUS:'#c2410c'};
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
function renderScatterPlot(){""")
rep("t.off.p>0&&t.def.p>0&&t.tier<=scatterTierMax;", "t.off.p>0&&t.def.p>0&&inConf(t);")
rep("t.off.p>0&&t.def.p>0&&t.tier>scatterTierMax;", "t.off.p>0&&t.def.p>0&&!inConf(t);")
rep("// ghost dots (filtered-out tiers)", "// ghost dots (other conferences)")
rep("' [Tier '+t.tier+']", "' ['+t.conf+']", count=2)
rep("  var tierR={1:8,2:6,3:5}, tierOp={1:0.95,2:0.85,3:0.7};\n", "")
rep("    var r=tierR[t.tier]||6, op=tierOp[t.tier]||0.85;\n    var sw=t.tier===1?2:1.5;",
    "    var r=7, op=0.9, sw=1.5;")
rep("    // label T1 always; T2 only if extreme position\n", "    // label everyone inside one conference; league-wide, only the extremes\n")
rep("if(t.tier===1||(t.tier===2&&(nr<=5||nr>=validT.length-3))){", "if(CONF||nr<=5||nr>=validT.length-3){")
rep("font-weight=\"'+(t.tier===1?'700':'500')+'\"", "font-weight=\"600\"")

# ---- Waterloo Warriors branding ---------------------------------------------
# Logo colours: gold #FFD100, black #231F20. Gold fails contrast as text on
# white, so it is used for fills (with black text on top); text accents use a
# darker gold that clears 4.5:1 on white.
GOLD, INK, GOLD_TXT = '#FFD100', '#231F20', '#8a6b00'
rep("--canada:#d52b1e;--canada-dark:#a81e13;", f"--canada:{GOLD_TXT};--canada-dark:#6b5300;--gold:{GOLD};--ink:{INK};")
rep(".topbar{background:#111;border-bottom:4px solid var(--canada);", ".topbar{background:#000;border-bottom:4px solid var(--gold);")
rep(".logo-badge{font-size:11px;font-weight:700;background:var(--canada);color:#fff;", ".logo-badge{font-size:11px;font-weight:700;background:var(--gold);color:#000;")
rep(".topstat-n{font-size:18px;font-weight:800;color:var(--canada);", ".topstat-n{font-size:18px;font-weight:800;color:var(--gold);")
rep(".toggle-btn.active{background:var(--canada);color:#fff;font-weight:700}", ".toggle-btn.active{background:var(--gold);color:#000;font-weight:700}")
rep(".subtab-btn.active{background:var(--canada);border-color:var(--canada);color:#fff;", ".subtab-btn.active{background:var(--gold);border-color:var(--gold);color:#000;")
rep(".lcard::before{content:'';position:absolute;top:0;left:0;right:0;height:3px;background:var(--canada)}", ".lcard::before{content:'';position:absolute;top:0;left:0;right:0;height:3px;background:var(--gold)}")
rep(".pt-chip.active{background:var(--canada);border-color:var(--canada);", ".pt-chip.active{background:var(--gold);border-color:var(--gold);")
rep(".poss-cell{background:rgba(213,43,30,.1);", ".poss-cell{background:rgba(255,209,0,.18);")
rep(".nav-btn.active{color:var(--canada);border-bottom-color:var(--canada);", ".nav-btn.active{color:var(--ink);border-bottom-color:var(--gold);")
body = body.replace('#f9a8b8,#d52b1e', '#ffe680,#e0b400')      # bar gradients
body = body.replace('#d52b1e', '#d4a900')                       # remaining red fills / lines
rep("function countryColor(name){ return COUNTRY_COLORS[name]||'#d4a900'; }",
    "function countryColor(name){ return 'var(--ink)'; }")
rep(".matchup-bar-row{", ".home-row td{background:rgba(255,209,0,.16)}\n.matchup-bar-row{")

# logo + titles
rep('<div class="logo">\n', '<div class="logo">\n    <img src="{LOGO_SRC}" alt="Waterloo Warriors">\n')
rep('<span class="logo-main">U SPORTS</span>', '<span class="logo-main">Waterloo Warriors</span>')
rep("Women's Basketball Analytics{UPDATED}", "Women's Basketball &middot; U SPORTS Analytics{UPDATED}")
rep("'<title>U SPORTS Women\\'s Basketball</title>\\n'", "'<title>Waterloo Warriors WBB Analytics</title>\\n'")
rep(".replace('{SEASON}', SEASON_LABEL)", ".replace('{LOGO_SRC}', LOGO_SRC).replace('{SEASON}', SEASON_LABEL)")

# radar fill was colour+'22' (hex alpha), which breaks for anything but #rrggbb;
# use fill-opacity instead. Radar in gold; two-sided comparisons are gold vs black.
rep("""fill="'+color+'22" stroke="'+color+'" stroke-width="2"/>';""",
    """fill="'+color+'" fill-opacity="0.28" stroke="'+color+'" stroke-width="2.5"/>';""")
rep("var radar=radarSvg(radarVals,radarLabels2,countryColor(t.name));",
    "var radar=radarSvg(radarVals,radarLabels2,'#e0b400');")
rep("var colA=countryColor(ta.name), colB=countryColor(tb.name);", "var colA='#a88600', colB='#231F20';")
rep("var colA_team=countryColor(pA.team), colB_team=countryColor(pB.team);", "var colA_team='#a88600', colB_team='#231F20';")

# League-average net rating is ~0 by construction (every point scored is one
# allowed), so the card said nothing. Dropped; the pulse grid is auto-fit.
rep("""'&#8805;35% 3PA rate')+
    pulse(f1(avgNet),'Avg Net Rating','off PPP minus def PPP');""",
    """'&#8805;35% 3PA rate');""")

# ---- play-type ratings: rank-based, correct on defence -----------------------
# The RATING column used fixed PPP cutoffs (so high-scoring play types like
# putbacks were "Elite" for most teams) and, on defence, called a HIGH PPP
# allowed elite. Rate by percentile within the play type instead, and flag
# small samples.
rep("// ── Color helpers ─", """function ptRatingCell(s,min){
  if(!s||!s.p) return '<td>&mdash;</td>';
  if(s.p<min) return '<td style="color:var(--text3)">Low sample</td>';
  var p=s.pp, l=p>=90?'Elite':p>=75?'Very Good':p>=50?'Above Avg':p>=25?'Below Avg':'Poor';
  var c=p>=90?'#16a34a':p>=75?'#22c55e':p>=50?'#6b7280':p>=25?'#c2410c':'#dc2626';
  return '<td style="color:'+c+';font-weight:600">'+l+'</td>';
}
// ── Color helpers ─""")
rep("""        '<td style="color:'+pppRatingColor(pv)+'">'+((s.p||0)?pppRating(pv):'&mdash;')+'</td>'+""",
    """        ptRatingCell(s,15)+""")
rep("""        '<td style="color:'+pppRatingColor(pv3)+'">'+pppRating(pv3)+'</td>'+""",
    """        ptRatingCell(s,10)+""")
rep("""          '<td style="color:'+pppRatingColor(dv)+'">'+pppRating(dv)+'</td>'+""",
    """          ptRatingCell(s,10)+""")
rep("""          '<td class="'+cPPP(dv)+'">'+f3(dv)+'</td>'+""", """          '<td class="'+cPPPD(dv)+'">'+f3(dv)+'</td>'+""")
rep("var pv3=ppp(s); var pRk=s.pr; var ptPct=pRk?rPct(pRk,NP):null;", "var pv3=ppp(s); var pRk=s.pr; var ptPct=pRk?s.pp:null;")
rep("var dv=ppp(s); var pRk=s.pr; var ptPct=pRk?rPct(pRk,NP):null;", "var dv=ppp(s); var pRk=s.pr; var ptPct=pRk?s.pp:null;")
rep("""vsLg='<span class="pt-vs '+(diff>=0?'pt-vs-up':'pt-vs-dn')+'">'""",
    """vsLg='<span class="pt-vs '+((side==='def'?-diff:diff)>=0?'pt-vs-up':'pt-vs-dn')+'">'""")

# ---- relative colouring ------------------------------------------------------
# Every cell colour used fixed cutoffs (FG% "hot" at 50%, EFG% at 55%, ...) tuned
# for FIBA, and the Defense views reused the offence colours, so a HIGH FG%
# allowed showed green. Colour by percentile within the relevant U SPORTS pool
# instead, flipped wherever lower is better.
rep("// ── Color helpers ─", """var STATF={ppp:ppp,fg:fg,efg:efg,fg2:fg2,fg3:fg3,to:topR,ts:ts};
var _POOL={};
function _pool(key,items,fn){
  if(!_POOL[key]) _POOL[key]=items.map(fn).filter(function(x){return isFinite(x);}).sort(function(a,b){return a-b;});
  return _POOL[key];
}
// percentile (100 = best) of v within a sorted pool
function pctIn(arr,v,lowerBetter){
  if(!arr.length||!isFinite(v)) return null;
  var lo=0,hi=arr.length; while(lo<hi){var m=(lo+hi)>>1; if(arr[m]<v) lo=m+1; else hi=m;}
  var hi2=lo; while(hi2<arr.length&&arr[hi2]===v) hi2++;
  var p=((lo+hi2)/2)/arr.length*100;          // mid-rank, so ties land in the middle
  return lowerBetter?100-p:p;
}
function cRel(p){ if(p===null||p===undefined) return ''; return p>=80?'hot':p>=60?'warm':p>=40?'':p>=20?'cool':'cold'; }
// team cell: side 'off'|'def'. On defence lower is better, except forcing turnovers.
function tC(stat,side,d){
  if(!d||!d.p) return '';
  var lb=side==='def'?(stat!=='to'):(stat==='to');
  var arr=_pool('T'+side+stat,TEAMS.filter(function(t){return t[side].p>0;}),function(t){return STATF[stat](t[side]);});
  return cRel(pctIn(arr,STATF[stat](d),lb));
}
// player cell (offence), pool = players with 15+ poss overall, or 5+ in a play type
function pC(stat,d,pt){
  if(!d||!d.p) return '';
  var key='P'+(pt||'')+stat;
  var arr=_pool(key,PLAYERS.filter(function(p){var x=pt?p.pt_off[pt]:p.off;return x&&x.p>=(pt?5:15);}),
    function(p){return STATF[stat](pt?p.pt_off[pt]:p.off);});
  return cRel(pctIn(arr,STATF[stat](d),stat==='to'));
}
// ── Color helpers ─""")
# team rankings table (offense or defense view)
rep("""      '<td class="'+(isD?cPPPD(pv):cPPP(pv))+'">'+f3(pv)+'</td>'+
      '<td class="'+cPct(fg(s),50,33)+'">'+fP(fg(s))+'</td>'+
      '<td class="'+cPct(efg(s),55,38)+'">'+fP(efg(s))+'</td>'+
      '<td class="'+cPct(fg2(s),52,36)+'">'+fP(fg2(s))+'</td>'+
      '<td class="'+cPct(fg3(s),38,25)+'">'+fP(fg3(s))+'</td>'+""",
"""      '<td class="'+tC('ppp',trSide,s)+'">'+f3(pv)+'</td>'+
      '<td class="'+tC('fg',trSide,s)+'">'+fP(fg(s))+'</td>'+
      '<td class="'+tC('efg',trSide,s)+'">'+fP(efg(s))+'</td>'+
      '<td class="'+tC('fg2',trSide,s)+'">'+fP(fg2(s))+'</td>'+
      '<td class="'+tC('fg3',trSide,s)+'">'+fP(fg3(s))+'</td>'+""")
rep("""      '<td class="'+cTO(topR(s))+'">'+fP(topR(s))+'</td>'+
      '<td>'+fP(ftr(s))+'</td>'+""", """      '<td class="'+tC('to',trSide,s)+'">'+fP(topR(s))+'</td>'+
      '<td>'+fP(ftr(s))+'</td>'+""")
# player rankings table
rep("""      '<td class="'+cPPP(pv)+'">'+f3(pv)+(pRank""", """      '<td class="'+pC('ppp',d,ptF)+'">'+f3(pv)+(pRank""")
rep("""      '<td class="'+cPct(fg(d),50,33)+'">'+fP(fg(d))+'</td>'+
      '<td class="'+cPct(ev,55,38)+'">'+fP(ev)+'</td>'+
      '<td class="'+cPct(fg2(d),52,36)+'">'+fP(fg2(d))+'</td>'+""",
"""      '<td class="'+pC('fg',d,ptF)+'">'+fP(fg(d))+'</td>'+
      '<td class="'+pC('efg',d,ptF)+'">'+fP(ev)+'</td>'+
      '<td class="'+pC('fg2',d,ptF)+'">'+fP(fg2(d))+'</td>'+""")
rep("""      '<td class="'+cPct(fg3(d),38,25)+'">'+fP(fg3(d))+'</td>'+""", """      '<td class="'+pC('fg3',d,ptF)+'">'+fP(fg3(d))+'</td>'+""")
rep("""      '<td class="'+cTO(topR(d))+'">'+fP(topR(d))+'</td>'+
      '<td>'+fP(ts(d))+'</td>'+""", """      '<td class="'+pC('to',d,ptF)+'">'+fP(topR(d))+'</td>'+
      '<td>'+fP(ts(d))+'</td>'+""")
# team intel: play-type tables (offence + defence) -> percentile within the play type
rep("""        '<td class="'+(side==='off'?cPPP(pv):cPPPD(pv))+'">'+((s.p||0)?f3(pv):'&mdash;')+vsLg+'</td>'+""",
    """        '<td class="'+((s.p||0)>=15?cRel(s.pp):'')+'">'+((s.p||0)?f3(pv):'&mdash;')+vsLg+'</td>'+""")
# team intel: roster (player offence)
rep("""      '<td class="'+cPPP(pv2)+'">'+((s.p||0)?f3(pv2):'&mdash;')+'</td>'+""", """      '<td class="'+pC('ppp',s)+'">'+((s.p||0)?f3(pv2):'&mdash;')+'</td>'+""")
rep("""      '<td class="'+cTO(topR(s))+'">'+((s.p||0)?fP(topR(s)):'&mdash;')+'</td>'+""", """      '<td class="'+pC('to',s)+'">'+((s.p||0)?fP(topR(s)):'&mdash;')+'</td>'+""")
# player intel: play-type tables
rep("""        '<td class="'+cPPP(pv3)+'">'+f3(pv3)+'</td>'+""", """        '<td class="'+(s.p>=10?cRel(s.pp):'')+'">'+f3(pv3)+'</td>'+""")
rep("""          '<td class="'+cPPPD(dv)+'">'+f3(dv)+'</td>'+""", """          '<td class="'+(s.p>=10?cRel(s.pp):'')+'">'+f3(dv)+'</td>'+""")
# play-type explorer: conference filter + relative colours
rep("var teams=TEAMS.filter(function(t){return t.pt_off[activePTE]&&", "var teams=TEAMS.filter(function(t){return inConf(t)&&t.pt_off[activePTE]&&")
rep("var players=PLAYERS.filter(function(p){return p.pt_off[activePTE]&&", "var players=PLAYERS.filter(function(p){return pInConf(p)&&p.pt_off[activePTE]&&")
rep("""      '<td class="'+cPPP(v)+'">'+f3(v)+'</td>'+
      '<td><span style="color:'+diffCol+';font-weight:700;font-size:11px">'+(diff>=0?'+':'')+diff.toFixed(3)+'</span></td>'+
      '<td>'+fP(efg(d))+'</td>'+
      '<td class="'+cTO(topR(d))+'">'+fP(topR(d))+'</td>'+
    '</tr>';
  });
  tHtml+=""", """      '<td class="'+cRel(d.pp)+'">'+f3(v)+'</td>'+
      '<td><span style="color:'+diffCol+';font-weight:700;font-size:11px">'+(diff>=0?'+':'')+diff.toFixed(3)+'</span></td>'+
      '<td>'+fP(efg(d))+'</td>'+
      '<td class="'+tC('to','off',d)+'">'+fP(topR(d))+'</td>'+
    '</tr>';
  });
  tHtml+=""")
rep("""      '<td class="'+cPPP(v)+'">'+f3(v)+'</td>'+
      '<td><span style="color:'+diffCol+';font-weight:700;font-size:11px">'+(diff>=0?'+':'')+diff.toFixed(3)+'</span></td>'+
      '<td>'+fP(efg(d))+'</td>'+
      '<td class="'+cTO(topR(d))+'">'+fP(topR(d))+'</td>'+
    '</tr>';
  });
  pHtml+=""", """      '<td class="'+pC('ppp',d,activePTE)+'">'+f3(v)+'</td>'+
      '<td><span style="color:'+diffCol+';font-weight:700;font-size:11px">'+(diff>=0?'+':'')+diff.toFixed(3)+'</span></td>'+
      '<td>'+fP(efg(d))+'</td>'+
      '<td class="'+pC('to',d,activePTE)+'">'+fP(topR(d))+'</td>'+
    '</tr>';
  });
  pHtml+=""")
# ---- direction / pairing fixes found in the full sweep -----------------------
# Team Intel: Def FG% was shown with the 2FG% rank; add a real def_fg rank.
rep("  {key:'def_fg2',  lb:true,  fn:function(t){return fg2(t.def);}},",
    "  {key:'def_fg2',  lb:true,  fn:function(t){return fg2(t.def);}},\n  {key:'def_fg',   lb:true,  fn:function(t){return fg(t.def);}},")
rep("['Def FG%',   fP(fg(d)),      r['def_fg2']? r['def_fg2']:null],", "['Def FG%',   fP(fg(d)),      r['def_fg']],")
# Defensive PPP colour used the FIBA-only 1.8-PPP mirror
rep("pppRatingColor(1.8-defPPP)", "pppRatingColor(2*LEAGUE_PPP-defPPP)")
# Style stats (3PA Rate, Pace) are not better-or-worse: show the rank, no grade
rep("""function pctRow(label, val, rank, total) {
  var pct = rPct(rank, total);""", """function pctRow(label, val, rank, total, neutral) {
  var pct = rPct(rank, total);
  if(neutral) return '<div class="pct-row">'+
    '<div class="pct-label">'+label+'</div>'+
    '<div class="pct-val">'+val+'</div>'+
    '<div class="pct-rank">#'+rank+'/'+total+'</div>'+
    '<div class="pct-track"><div class="pct-fill" style="width:'+pct+'%;background:var(--border2)"></div></div>'+
    '<div class="tier-chip" style="background:var(--bg4);color:var(--text3);font-size:8px" title="style, not quality">&middot;</div>'+
    '</div>';""")
rep("['3PA Rate',  fP(rate3(o)),   r['off_3rate']],", "['3PA Rate',  fP(rate3(o)),   r['off_3rate'], 1],")
rep("['Pace',      f1(pace(t)),    r['pace']],", "['Pace',      f1(pace(t)),    r['pace'], 1],")
rep("offStatDefs.forEach(function(x){offRankHtml+=x[2]?pctRow(x[0],x[1],x[2],N):'';});",
    "offStatDefs.forEach(function(x){offRankHtml+=x[2]?pctRow(x[0],x[1],x[2],N,x[3]):'';});")
# Radars: swap the Pace axis (style) for Def EFG% (quality)
rep("var radarKeys2=['off_ppp','off_efg','off_fg3','off_to','def_ppp','pace','off_ftr','def_to'];",
    "var radarKeys2=['off_ppp','off_efg','off_fg3','off_to','def_ppp','def_efg','off_ftr','def_to'];")
rep("var radarLabels2=['Off PPP','EFG%','3FG%','Ball Sec.','Defense','Pace','FT Draw','Force TO'];",
    "var radarLabels2=['Off PPP','EFG%','3FG%','Ball Sec.','Def PPP','Def EFG%','FT Draw','Force TO'];")
rep("var radarKeys=['off_ppp','off_efg','off_fg3','off_to','def_ppp','pace'];", "var radarKeys=['off_ppp','off_efg','off_fg3','off_to','def_ppp','def_efg'];")
rep("var radarLabels=['Off PPP','EFG%','3FG%','Ball Sec.','Defense','Pace'];", "var radarLabels=['Off PPP','EFG%','3FG%','Ball Sec.','Def PPP','Def EFG%'];")
# Scouting report: no pace, honest label, and only real strengths/weaknesses
rep("    {key:'pace',     s:'Pace / tempo',                 w:'Pace / tempo'},\n", "")
rep("{key:'def_efg',  s:'Perimeter defense (EFG% allowed)', w:'Perimeter defense (EFG% allowed)'},",
    "{key:'def_efg',  s:'Shooting defense (EFG% allowed)', w:'Shooting defense (EFG% allowed)'},")
rep("var strengths=scored.slice(0,TOP).map(", "var strengths=scored.filter(function(d){return d.pct>=60;}).slice(0,TOP).map(")
rep("var weaknesses=scored.slice(-TOP).reverse().map(", "var weaknesses=scored.filter(function(d){return d.pct<=40;}).slice(-TOP).reverse().map(")
# Matchup: style rows have no winner; defensive play types: lower PPP allowed wins
rep("    var aWins=lb?av<bv:av>=bv;", "    var neutral=(rkey==='pace'||rkey==='off_3rate');\n    var aWins=lb?av<bv:av>=bv, bWins=!aWins;\n    if(neutral){aWins=false;bWins=false;}")
rep("    var aBg=aWins?colA:'var(--border2)', bBg=!aWins?colB:'var(--border2)';\n    var aCol=aWins?colA:'var(--text)', bCol=!aWins?colB:'var(--text)';",
    "    var aBg=aWins?colA:'var(--border2)', bBg=bWins?colB:'var(--border2)';\n    var aCol=aWins?colA:'var(--text)', bCol=bWins?colB:'var(--text)';")
rep("function ptButterfly(ptObjA, ptObjB, titleA, titleB, cA, cB){", "function ptButterfly(ptObjA, ptObjB, titleA, titleB, cA, cB, lowerBetter){")
rep("var winA=vA!==null&&vB!==null&&vA>vB, winB=vA!==null&&vB!==null&&vB>vA;",
    "var both=vA!==null&&vB!==null, winA=both&&(lowerBetter?vA<vB:vA>vB), winB=both&&(lowerBetter?vB<vA:vB>vA);")
rep("var ptDefHtml=ptButterfly(ta.pt_def,tb.pt_def,esc(ta.name),esc(tb.name),colA,colB);",
    "var ptDefHtml=ptButterfly(ta.pt_def,tb.pt_def,esc(ta.name),esc(tb.name),colA,colB,true);")

# Synergy has no shot-quality data for U SPORTS: hide the panel rather than show an empty box
rep("  if(!validT.length){el.innerHTML='<div class=\"empty\">No shot quality data</div>';return;}",
    "  if(!validT.length){var col=el.parentElement.parentElement; col.style.display='none'; col.parentElement.style.gridTemplateColumns='1fr'; return;}")

# scatter legend still described FIBA tiers
rep_re(r"  legend\+='<span style=\"margin-left:8px;padding-left:8px;border-left:1px solid var\(--border\)\"><svg[^\n]*Tier 1 \(large\)</span>';\n[^\n]*Tier 2</span>';\n[^\n]*Tier 3 \(dim\)</span>';\n",
  """  legend+='<span style="margin-left:8px;padding-left:8px;border-left:1px solid var(--border)"><svg width="14" height="14" style="vertical-align:middle;margin-right:3px"><circle cx="7" cy="7" r="6" fill="#FFD100" fill-opacity="0.35" stroke="#231F20" stroke-width="1.5"/></svg>Waterloo</span>';
  legend+='<span><svg width="10" height="10" style="vertical-align:middle;margin-right:3px"><circle cx="5" cy="5" r="4" fill="#9ca3af" fill-opacity="0.3" stroke="#9ca3af" stroke-width="1"/></svg>other conferences (when filtered)</span>';
""")
# early season: a 5+ GP default hides whole conferences (RSEQ has 2-4 tagged games)
rep("""        <option value="0">All</option><option value="3">3+</option>
        <option value="5" selected>5+</option><option value="10">10+</option>""",
    """        <option value="0" selected>All</option><option value="3">3+</option>
        <option value="5">5+</option><option value="10">10+</option>""")

# home team: defaults + highlight
rep("var TEAM_CONF={};", "var HOME=TEAMS.filter(function(t){return /waterloo/i.test(t.name);})[0];\nvar HOME_ID=HOME?HOME.id:'';\nvar TEAM_CONF={};")
rep("    html+='<tr>'+\n      '<td class=\"rank-cell\">'+(i+1)+'</td>'+\n      '<td><span style=\"font-weight:700\">'",
    "    html+='<tr'+(t.id===HOME_ID?' class=\"home-row\"':'')+'>'+\n      '<td class=\"rank-cell\">'+(i+1)+'</td>'+\n      '<td><span style=\"font-weight:700\">'")
rep("    html+='<tr>'+\n      '<td class=\"rank-cell\">'+(i+1)+'</td>'+\n      '<td style=\"font-weight:700\">'+esc(p.name)+'</td>'+",
    "    html+='<tr'+(p.tid===HOME_ID?' class=\"home-row\"':'')+'>'+\n      '<td class=\"rank-cell\">'+(i+1)+'</td>'+\n      '<td style=\"font-weight:700\">'+esc(p.name)+'</td>'+")
rep("    var r=7, op=0.9, sw=1.5;", "    var r=7, op=0.9, sw=1.5;\n    if(t.id===HOME_ID) svg+='<circle cx=\"'+x.toFixed(1)+'\" cy=\"'+y.toFixed(1)+'\" r=\"13\" fill=\"#FFD100\" fill-opacity=\"0.35\" stroke=\"#231F20\" stroke-width=\"2.5\"/>';")
rep("if(CONF||nr<=5||nr>=validT.length-3){", "if(CONF||t.id===HOME_ID||nr<=5||nr>=validT.length-3){")
rep("  renderOverview(); renderTeamRank(); renderPlayerRank();\n}\ninit();",
"""  renderOverview(); renderTeamRank(); renderPlayerRank();
  if(HOME_ID){
    document.getElementById('ti-team').value=HOME_ID; renderTeamIntel();
    document.getElementById('mu-a').value=HOME_ID;
    document.getElementById('pi-team').value=HOME_ID; populatePiPlayers();
  }
}
init();""")

# The play-type explorer lists teams; respect the conference filter there too.
leftover = [m.start() for m in re.finditer(r'[a-z]\.tier\b|TierMax|TEAM_TIER|useQual|qoff|qpt_', body)]
if leftover:
    for i in leftover[:10]:
        print('leftover:', body[max(0,i-80):i+40].replace('\n',' '))
    sys.exit('tier/quality references remain')

out.write_text(HEADER + body)
print(f'wrote {out}')
