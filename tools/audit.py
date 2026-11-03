#!/usr/bin/env python3
"""Consistency audit of a scraped season. No network calls.

    python3 tools/audit.py [season] [games.json]

Checks that the numbers agree with each other: point identities, players vs
team totals, offence vs defence league-wide, play-type sums vs overall, games
played vs the game list, conference sizes.
"""
import json, sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'src'))
from config import DEFAULT_SEASON
season = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SEASON
D = ROOT / 'data' / season
T = json.loads((D / 'teams_all.json').read_text())
P = json.loads((D / 'players_all.json').read_text())
games_file = Path(sys.argv[2]) if len(sys.argv) > 2 else D / 'games.json'
G = json.loads(games_file.read_text()) if games_file.exists() else None

fails = 0
def check(ok, msg):
    global fails
    print(('  ok   ' if ok else '  FAIL ') + msg)
    fails += (not ok)

def warn(ok, msg, why):
    """Known Synergy-side quirks: reported, not counted as failures."""
    print(('  ok   ' if ok else '  warn ') + msg + ('' if ok else f'\n         ({why})'))

pts = lambda d: 2 * d['shot2Made'] + 3 * d['shot3Made'] + d['ftMade']
print(f'== {season}: {len(T)} teams, {len(P)} players')

conf = Counter(t['team']['conf'] for t in T)
check(dict(conf) == {'OUA': 18, 'CW': 17, 'AUS': 8, 'RSEQ': 5}, f'conference sizes {dict(conf)}')
check(len({t['team']['id'] for t in T}) == len(T), 'no duplicate teams')
check(len({p['player']['id'] for p in P}) == len(P), 'no duplicate players')

# 1. points identity
for side in ('offense', 'defense'):
    bad = [t['team']['name'] for t in T if pts(t['overall'][side]) != t['overall'][side]['pointMade']]
    check(not bad, f'team {side}: 2*2PM+3*3PM+FTM == points ({len(T)-len(bad)}/{len(T)}) {bad[:3]}')
po = [p for p in P if p['overall'].get('offense')]
bad = [p['player']['name'] for p in po if pts(p['overall']['offense']) != p['overall']['offense']['pointMade']]
check(not bad, f'player offense points identity ({len(po)-len(bad)}/{len(po)}) {bad[:3]}')

# 2. players sum to team
by_team = defaultdict(lambda: Counter())
for p in po:
    o = p['overall']['offense']
    by_team[p['team']['id']].update({'pts': o['pointMade'], 'poss': o['possessions']})
print('  players vs team totals (offense):')
worst = []
for t in T:
    o = t['overall']['offense']; s = by_team[t['team']['id']]
    dp = s['pts'] - o['pointMade']; dq = s['poss'] - o['possessions']
    worst.append((abs(dp) + abs(dq), t['team']['name'], dp, dq, o['pointMade'], o['possessions']))
worst.sort(reverse=True)
exact = sum(1 for w in worst if w[0] == 0)
warn(exact == len(T), f'player pts & poss sum exactly to team ({exact}/{len(T)})',
     'Synergy credits some team possessions to no player; the full leaderboard was verified to contain no more records')
for w in worst[:6]:
    if w[0]: print(f'         {w[1]:<40} pts {w[2]:+d} of {w[4]}   poss {w[3]:+d} of {w[5]}')

# 3. league offence == league defence (closed league, mostly)
op = sum(t['overall']['offense']['pointMade'] for t in T); dp = sum(t['overall']['defense']['pointMade'] for t in T)
oq = sum(t['overall']['offense']['possessions'] for t in T); dq = sum(t['overall']['defense']['possessions'] for t in T)
check(abs(op - dp) / op < 0.01, f'league points scored {op} vs allowed {dp} ({(op-dp)/op:+.2%})')
check(abs(oq - dq) / oq < 0.01, f'league possessions off {oq} vs def {dq} ({(oq-dq)/oq:+.2%})')

# 4. play types partition the overall possessions
print('  play-type possessions as share of overall (offense):')
shares = []
for t in T:
    tot = t['overall']['offense']['possessions']
    s = sum(v['possessions'] for v in t['play_types']['offense'].values())
    shares.append((s / tot if tot else 0, t['team']['name']))
shares.sort()
print(f'         min {shares[0][0]:.1%} ({shares[0][1]})  max {shares[-1][0]:.1%} ({shares[-1][1]})')
check(all(x <= 1.001 for x, _ in shares), 'play types never exceed overall')

# 5. games played
gp_team = {t['team']['id']: t['team']['gp'] for t in T}
bad = [p['player']['name'] for p in P if p['gp'] > gp_team.get(p['team']['id'], 0)]
warn(not bad, f'no player has more GP than her team {bad[:3]}',
     'Synergy player GP can count one extra game; totals still sum, so only PPG is slightly low')
if G:
    done = Counter()
    comp = defaultdict(Counter)
    for g in G:
        # Synergy only aggregates games whose possession tagging (phase2) is done
        if str(g.get('status')) != '2' or (g.get('phase2') or {}).get('status') != 2 \
                or (g.get('competition') or {}).get('name') == 'Exhibition Game':
            continue
        for side in ('homeTeam', 'awayTeam'):
            tid = g[side]['id']
            done[tid] += 1
            comp[tid][(g.get('competition') or {}).get('name')] += 1
    diff = [(t['team']['name'], t['team']['gp'], done[t['team']['id']], dict(comp[t['team']['id']]))
            for t in T if t['team']['gp'] != done[t['team']['id']]]
    check(not diff, f'team GP == fully-tagged non-exhibition games ({len(T)-len(diff)}/{len(T)})')
    untagged = sum(1 for g in G if str(g.get('status')) == '2' and (g.get('phase2') or {}).get('status') != 2
                   and (g.get('competition') or {}).get('name') != 'Exhibition Game')
    print(f'         ({untagged} completed games not yet tagged by Synergy, so not in any stats)')
    for d in diff[:12]:
        print(f'         {d[0]:<40} synergy gp {d[1]}  completed games {d[2]}  {d[3]}')
else:
    print('  (no games.json -- GP vs schedule check skipped)')

# 6. sanity ranges
ppp = sorted((t['overall']['offense']['pointMade'] / t['overall']['offense']['possessions'], t['team']['name']) for t in T)
print(f'  team off PPP range {ppp[0][0]:.3f} ({ppp[0][1]}) .. {ppp[-1][0]:.3f} ({ppp[-1][1]})')
ppg = sorted(((p['overall']['offense']['pointMade'] / p['gp']), p['player']['name'], p['team']['name'], p['gp'])
             for p in po if p['gp'] >= 3)
print('  top PPG (3+ GP):', '; '.join(f'{n} ({tm.split()[0]}) {v:.1f} in {g}' for v, n, tm, g in ppg[-5:][::-1]))
print(f'\n{fails} check(s) failed')
