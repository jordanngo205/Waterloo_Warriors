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
