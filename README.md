# U SPORTS Women's Basketball Dashboard

Team and player analytics for U SPORTS women's basketball, built from Synergy Sports data.
Same layout as the Canada Basketball 5x5 SWNT dashboard, with conferences
(Canada West / OUA / RSEQ / AUS) in place of competition tiers.

## Run

```bash
pip install -r requirements.txt
# .env at the repo root: SYNERGY_USERNAME=... / SYNERGY_PASSWORD=...

python3 src/synergy_auth.py          # is there a live session?
python3 src/do_auth.py               # only if not -- one interactive login
python3 src/scrape_usports.py        # -> data/2026-2027/
python3 src/build_dashboard.py       # -> docs/index.html (GitHub Pages)
```

Pass a season to either script for another year, e.g. `2025-2026` (ids in `src/config.py`).

## Notes

- **Don't log in to Synergy in a browser while a scrape is running.** It ends the script's
  session, and repeated logins lock the account. The token is at `~/.synergy/uwaterloo.json`.
- U SPORTS sits inside Synergy's "College Women" league as competition `CEE`. The leaderboard
  also returns US colleges that played U SPORTS teams in preseason, so teams are filtered by
  conference from the game list.
- Field goals are `shot2* + shot3*`; Synergy's `fgMade`/`fgAttempt` are something else.
- `tools/port_swnt_builder.py` generated `src/build_dashboard.py` from the SWNT builder.
