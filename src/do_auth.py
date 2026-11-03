#!/usr/bin/env python3
"""
Full interactive login. Run this only when there is no usable token and no
working refresh token -- every run of this is a real username/password login,
and a handful of them in quick succession locks the Synergy account.

To extend an existing session instead, use:  python3 synergy_auth.py renew

Usage:  python3 do_auth.py
"""
import pkce, requests, os, sys
from pathlib import Path
from dotenv import load_dotenv

DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(DIR))
from paths import ENV_FILE  # noqa: E402
import synergy_functions as sf
import synergy_auth

load_dotenv(ENV_FILE)

# Check BEFORE sending credentials. This is the path a human or an agent takes
# when a scraper stops and says "log in once, then rerun" -- and when the
# session keeps dying, that advice gets followed again and again. Each run used
# to be a full, uncounted login, so the rate limiter never saw the one path most
# likely to lock the account.
try:
    synergy_auth.check_login_allowed()
except synergy_auth.LoginRateLimited as e:
    sys.exit(str(e))

session = requests.Session()
cv = pkce.generate_code_verifier(length=128)
cc = pkce.get_code_challenge(cv)

import contextlib, io


class _Tee(io.StringIO):
    """Capture what the login flow prints (its failure reasons) for the audit
    log, while still showing it on screen."""
    def write(self, s):
        sys.__stdout__.write(s)
        return super().write(s)


synergy_auth.audit('login_attempt', logins_last_hour=len(synergy_auth._recent_logins()),
                   interactive=sys.stdin.isatty(),
                   parent_pid=os.getppid())
_out = _Tee()
try:
    with contextlib.redirect_stdout(_out):
        token_type, refresh_token, access_token = sf.get_access_token(
            session, cv, cc,
            os.getenv('SYNERGY_USERNAME'), os.getenv('SYNERGY_PASSWORD'))
except Exception as e:
    # Credentials may already have been sent; an exception is still an attempt.
    synergy_auth._record_login()
    synergy_auth.record_login_failure()
    synergy_auth.audit('login_failed', reason=f'exception: {type(e).__name__}: {e}'[:300],
                       output=_out.getvalue()[-600:])
    raise
_said = _out.getvalue()

# Count the attempt whether or not it succeeded. A failed login is exactly the
# kind that locks an account, so excluding failures would leave the limiter
# blind to the only case that matters.
synergy_auth._record_login()

if not access_token:
    synergy_auth.record_login_failure()
    synergy_auth.audit('login_failed', output=_said[-600:],
                       twofa_requested='email verification' in _said)
    sys.exit('Auth failed. Do NOT rerun this immediately -- a lockout and a '
             'wrong password return the same message, and retrying extends a '
             'lockout. Check whether another project shares this token file.')

# The refresh token is the whole point of saving more than the access token:
# with it, later renewals cost a token-endpoint call instead of a login.
synergy_auth.clear_login_failure()
synergy_auth.audit('login_ok', twofa_requested='email verification' in _said,
                   refresh_token_returned=bool(refresh_token))
tok = synergy_auth.save({'token_type': token_type,
                         'access_token': access_token,
                         'refresh_token': refresh_token})

print(f'Token saved to {synergy_auth.TOKEN_FILE}')
print(f'  refresh token: {"saved" if tok["refresh_token"] else "NOT RETURNED by server"}')
print(f'  valid for: {tok["expires_in"] // 60} min '
      '(renewable without another login)')
