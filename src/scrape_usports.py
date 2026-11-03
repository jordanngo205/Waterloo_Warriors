#!/usr/bin/env python3
"""Scrape U SPORTS women's basketball team and player data from Synergy.

Everything comes from two endpoints this account is licensed for:

  /games                                    -> which teams are U SPORTS, and their conference
  /leaderboards/recordswithsparseranks      -> season totals, team + player, offense + defense,
                                               overall (playType 0) and the 11 play types

Output (data/<season>/):
  teams_all.json    one record per U SPORTS team
  players_all.json  one record per U SPORTS player
  meta.json         season, scrape time, counts

Usage:  python3 src/scrape_usports.py            # season in config.py
        python3 src/scrape_usports.py 2025-2026  # any season listed in config.SEASONS

Things that cost time to find out, kept here so they are not rediscovered:

* U SPORTS is not its own Synergy league. It lives inside "College Women"
  alongside the NCAA and NAIA, as competition key `<league>:CEE`. Every other key
  (`:ALL`, `:C`, ...) returns 401 for this account, so CEE is not a choice.
* The CEE leaderboard returns ~400 teams, not 48: US colleges that played a
  U SPORTS team in preseason come along. The U SPORTS set is the teams whose
  conference on the game list is "U Sports" (abbr US). Filter on that, never on
  names.
* fgMade / fgAttempt on the leaderboard are NOT field goals (Waterloo-sized
  numbers come back ~2.4x too large). Field goals are shot2* + shot3*. The
  points identity 2*2PM + 3*3PM + FTM == pointMade is checked below; it is the
  fastest way to tell which fields are real.
* The leaderboard silently caps a response at `take`. Page to exhaustion.
* playType 0 is total offence. The narrower codes are subsets.
* /possessionreports, /games/{id} and /leagues are 401 for this account, and
  /playerswithboxscore stops at a player's last 5 games whatever is passed, so
  none of them are used.
"""
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(DIR))
import synergy_auth  # noqa: E402
from config import (BASE, LEAGUE_ID, COMP_KEY, CONFERENCE_ID, CONFERENCE_ABBR,  # noqa: E402
                    SEASONS, DEFAULT_SEASON, PLAY_TYPES, CONF_SHORT)
from paths import DATA  # noqa: E402

PAGE = 500

# leaderboard reportType
PLAYER_OFF, PLAYER_DEF, TEAM_OFF, TEAM_DEF = 0, 1, 2, 3

FIELDS = ['possessions', 'gp', 'pointMade', 'shot2Attempt', 'shot2Made', 'shot2Miss',
          'shot3Attempt', 'shot3Made', 'shot3Miss', 'shotAttempt', 'shotMade', 'shotMiss',
          'turnover', 'ftAttempt', 'ftMade', 'ftTimes', 'ftmiss', 'score', 'plusOne',
          'shotFoul', 'shotQualityTotal', 'shotQualityAttempt']


def extract(pr):
    # Synergy omits a field when it is zero, so .get(k) or 0 is doing real work.
    d = {k: pr.get(k) or 0 for k in FIELDS}
    # Real field goals, replacing the misleading fgMade/fgAttempt.
    d['fgMade'] = d['shot2Made'] + d['shot3Made']
    d['fgAttempt'] = d['shot2Attempt'] + d['shot3Attempt']
    return d


class Client:
    def __init__(self):
        synergy_auth.audit('scrape_start', token_seconds_left=round(synergy_auth.seconds_left()))
        self.s = requests.Session()
        self.H = synergy_auth.headers()

    def _req(self, method, path, **kw):
        for attempt in range(3):
            # headers() is a file read while the token is fresh; it renews ahead
            # of expiry so a long scrape does not die mid-way.
            self.H.update(synergy_auth.headers())
            r = self.s.request(method, BASE + path, headers=self.H, timeout=120, **kw)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 401:
                # A 401 on a token that should still be valid means the session
                # was killed elsewhere (e.g. someone logged in in a browser). Do
                # not refresh or log in in a loop -- that is how accounts lock.
                left = synergy_auth.seconds_left()
                synergy_auth.audit('api_401', path=path, token_seconds_left=round(left),
                                   action='stop' if left > 120 else 'renew')
                if left > 120:
                    sys.exit(f'401 with {left / 60:.0f} min left on the token: the session was '
                             'ended elsewhere (a browser login does this). Stopping without '
                             'retrying. Close any Synergy browser tabs and wait before logging in again; '
                             'if the account is locked, a login attempt extends the lock.')
                self.H.update(synergy_auth.on_401())
                continue
            print(f'   {path} -> {r.status_code}, retrying', flush=True)
            time.sleep(3 * (attempt + 1))
        sys.exit(f'{method} {path} kept failing; last status {r.status_code}: {r.text[:200]}')

    def games(self, season_id):
        out, skip = [], 0
        while True:
            b = self._req('POST', '/games', json={
                'seasonIds': [season_id], 'conferenceIds': [CONFERENCE_ID],
                'excludeGamesWithoutCompetition': False, 'take': 500, 'skip': skip}).get('result', [])
            out += b
            if len(b) < 500:
                return out
            skip += 500

    def leaderboard(self, season_id, play_type, report_type):
        out, skip = [], 0
        while True:
            b = self._req('GET', '/leaderboards/recordswithsparseranks', params={
                'leagueId': LEAGUE_ID, 'seasonId': season_id,
                'playType': play_type, 'reportType': report_type,
                'competitionDefinitionKey': COMP_KEY,
                'competitionType': 4, 'rankingType': 4,
                'perGame': 'false', 'minPossessions': 0,
                'minPossessionsPerGame': 'false', 'ascending': 'false',
                'skip': skip, 'take': PAGE}).get('result', [])
            out += b
            if len(b) < PAGE:
                return out
            skip += PAGE
            time.sleep(0.2)


def usports_teams(games):
    teams = {}
    for g in games:
        for side in ('homeTeam', 'awayTeam'):
            t = g.get(side) or {}
            if (t.get('conference') or {}).get('abbr') != CONFERENCE_ABBR or not t.get('id'):
                continue
            div = (t.get('division') or {}).get('name') or ''
            teams[t['id']] = {'id': t['id'], 'name': t.get('fullName') or t.get('name'),
                              'conf': CONF_SHORT.get(div, div)}
    return teams


def assign_ranks(by_id):
    """pppRank / possRank within the U SPORTS pool for one slice."""
    items = [(k, d) for k, d in by_id.items() if d.get('possessions', 0) > 0]
    by_ppp = sorted(items, key=lambda x: x[1]['pointMade'] / x[1]['possessions'], reverse=True)
    by_poss = sorted(items, key=lambda x: x[1]['possessions'], reverse=True)
    pr = {k: i + 1 for i, (k, _) in enumerate(by_ppp)}
    qr = {k: i + 1 for i, (k, _) in enumerate(by_poss)}
    for k, d in by_id.items():
        d['pppRank'], d['possRank'] = pr.get(k), qr.get(k)


def main():
    season = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SEASON
    if season not in SEASONS:
        sys.exit(f'unknown season {season}; known: {", ".join(SEASONS)}')
    sid = SEASONS[season]
    out_dir = DATA / season
    out_dir.mkdir(parents=True, exist_ok=True)
    c = Client()

    print(f'U SPORTS women {season}')
    games = c.games(sid)
    teams = usports_teams(games)
    print(f'  {len(games)} games, {len(teams)} U SPORTS teams')
    if not teams:
        sys.exit('no U SPORTS teams found -- check CONFERENCE_ID / season')

    slices = [('Overall', 0)] + PLAY_TYPES
    T = {tid: {'team': dict(t), 'overall': {}, 'play_types': {'offense': {}, 'defense': {}}}
         for tid, t in teams.items()}
    P = {}

    for side, rt in (('offense', TEAM_OFF), ('defense', TEAM_DEF)):
        for name, pt in slices:
            recs = c.leaderboard(sid, pt, rt)
            by = {}
            for r in recs:
                pr = r.get('possessionReport') or {}
                tid = (pr.get('team') or {}).get('id')
                if tid in T:
                    by[tid] = extract(pr)
            assign_ranks(by)
            for tid, d in by.items():
                if name == 'Overall':
                    T[tid]['overall'][side] = d
                else:
                    T[tid]['play_types'][side][name] = d
            print(f'  team   {side:<8} {name:<20} {len(by):>3} of {len(recs)} records', flush=True)
            time.sleep(0.2)

    for side, rt in (('offense', PLAYER_OFF), ('defense', PLAYER_DEF)):
        for name, pt in slices:
            recs = c.leaderboard(sid, pt, rt)
            by = {}
            for r in recs:
                pr = r.get('possessionReport') or {}
                tid = (pr.get('team') or {}).get('id')
                pl = pr.get('player') or {}
                if tid not in T or not pl.get('id'):
                    continue
                pid = pl['id']
                by[pid] = extract(pr)
                if pid not in P:
                    P[pid] = {'player': {'id': pid, 'name': pl.get('name')},
                              'team': {'id': tid, 'name': teams[tid]['name']},
                              'gp': 0, 'overall': {}, 'play_types': {'offense': {}, 'defense': {}}}
            assign_ranks(by)
            for pid, d in by.items():
                if name == 'Overall':
                    P[pid]['overall'][side] = d
                    if side == 'offense':
                        P[pid]['gp'] = d['gp']
                else:
                    P[pid]['play_types'][side][name] = d
            print(f'  player {side:<8} {name:<20} {len(by):>4} of {len(recs)} records', flush=True)
            time.sleep(0.2)

    for tid, t in T.items():
        t['team']['gp'] = (t['overall'].get('offense') or {}).get('gp', 0)

    # Points identity: if this fails, the field mapping is wrong, not the data.
    bad = [t['team']['name'] for t in T.values()
           if (o := t['overall'].get('offense')) and
           2 * o['shot2Made'] + 3 * o['shot3Made'] + o['ftMade'] != o['pointMade']]
    print(f'\n  points identity: {len(T) - len(bad)}/{len(T)} teams exact'
          + (f' (off: {", ".join(bad[:5])})' if bad else ''))

    teams_out = sorted(T.values(), key=lambda t: t['team']['name'])
    players_out = sorted(P.values(), key=lambda p: (p['team']['name'], p['player']['name'] or ''))
    (out_dir / 'games.json').write_text(json.dumps(games))   # for tools/audit.py
    (out_dir / 'teams_all.json').write_text(json.dumps(teams_out, indent=1))
    (out_dir / 'players_all.json').write_text(json.dumps(players_out, indent=1))
    played = sum(1 for g in games if str(g.get('status')) == '2')
    (out_dir / 'meta.json').write_text(json.dumps({
        'season': season, 'season_id': sid, 'league_id': LEAGUE_ID, 'competition': COMP_KEY,
        'scraped_at': datetime.now(timezone.utc).isoformat(timespec='minutes'),
        'teams': len(teams_out), 'players': len(players_out), 'games_completed': played}, indent=1))
    print(f'  saved {len(teams_out)} teams, {len(players_out)} players -> {out_dir}')


if __name__ == '__main__':
    main()
