"""Synergy ids for U SPORTS women's basketball, in one place."""

BASE = 'https://basketball.synergysportstech.com/api'

LEAGUE_ID = '54457dce300969b132fcfb38'          # "College Women" -- U SPORTS lives inside it
COMP_KEY = f'{LEAGUE_ID}:CEE'                   # the only competition key this account can read
CONFERENCE_ID = '54457dcf300969b132fcfb7d'      # "U Sports"
CONFERENCE_ABBR = 'US'

SEASONS = {
    '2026-2027': '6a7de6fd9654df0a914765ac',
    '2025-2026': '68a4bdab3c211b288250118f',
}
DEFAULT_SEASON = '2026-2027'

# Synergy "division" name -> the label used in the dashboard
CONF_SHORT = {
    'Canada West': 'CW',
    'Ontario University Athletics': 'OUA',
    'RSEQ': 'RSEQ',
    'Atlantic University Sports': 'AUS',
}

# Same ids as the FIBA 5x5 scrapers (confirmed there against the Synergy UI).
PLAY_TYPES = [
    ('Transition',           1),
    ('Spot Up',             50),
    ('P&R Ball Handler',    11),
    ('Miscellaneous Plays', 124),
    ('Cut',                 81),
    ('Offensive Rebounds',  89),
    ('Isolation',           10),
    ('Post-Up',             15),
    ('Off Screen',          67),
    ('P&R Roll Man',        31),
    ('Handoffs',            78),
]
