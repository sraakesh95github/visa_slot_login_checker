"""
check_login.py
Attempts to log in to usvisascheduling.com via its Azure AD B2C SUSI flow.
Login is considered SUCCESSFUL only when the Security Questions page appears
(URL contains 'SelfAsserted/confirmed' or page shows security question fields).

On success a push notification is sent via Claude Code's PushNotification tool
(requires Remote Control to be connected for mobile delivery).

Dependencies: playwright (pip install playwright && playwright install chromium)
Usage:
    python check_login.py           # headless
    python check_login.py --headed  # watch the browser
"""

import sys
import time
import subprocess
import urllib.request
import urllib.parse
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# ── credentials ────────────────────────────────────────────────────────────────
USERNAME = "sraakesh1995"
PASSWORD = "Visa2025!"

# ── entry URL ──────────────────────────────────────────────────────────────────
LOGIN_URL = (
    "https://atlasauth.b2clogin.com/f50ebcfb-eadd-41d8-9099-a7049d073f5c/"
    "b2c_1a_atoproduction_atlas_susi/oauth2/v2.0/authorize"
    "?client_id=607d08d6-b63b-4735-ad82-05dfcff7efa4"
    "&redirect_uri=https%3A%2F%2Fwww.usvisascheduling.com%2Fsignin-aad-b2c_1"
    "&response_type=code%20id_token"
    "&scope=openid"
    "&state=OpenIdConnect.AuthenticationProperties%3DatdL5Xgm3BqT6Rx-ZkbOVcJHtk3ELKPkttkr0pwhKL_LcrsxO3EMmLaNxnpkAMrtxalB_CFpOmQqrpk6oPePBVJbxF9YQ4GZ2-8oqb28l3nQHnk94PuOQ_srGdDtmV1w5loZnnwdDa6xyec06RkRFO-DM6RWnJ-7knCSlkj7hjG4Mzi5iZbMvZDbRpp1i3ALQ8wgjJ2gNuBi0AfEe6ilMU-zgLkBEx7ovRK9vXXV7hPllUKuBIKCHIYUH2QJD7CLtYt8AUx06qyHEYebvnMmZPNKxuulgIpBrrDQyUxeSQMcKxXCxJlJBExvKc_rhIDHFqG1sFOECcNy0jHUloo8rlRhuOBWcD49UNbffvn1bRaHJl5Rm31GUqK77OXHWWgFAx3or71JhAAhec1gwVTUllVlPJIIbEkYmvWWUNgtPaTtkp5Rclfudu2005nObDJEzllVJK9R76S7brEKxOqapa9frjtvYrFOb4JKXROk8o9JafXfUZGrcFMmzhWatZQrR0j80Y1B-aJC39tEimjOecgs0i1DxQN822GWmzo448EwWAJLQ5bNvBCZBnAfxmcNdVm28n4Z0Fxkon5b-iUpvzIakuZgslXMuo5gltoSs7yPWdRYEBDHLZimicQWpI7ukcv84Nb1Rt6zPeeqA-0YoL4v-xOK8VN7YQBI55lyBs4"
    "&response_mode=form_post"
    "&nonce=639153186480817641.Zjg2ZjcxMjUtZDQ2My00OGY5LTlmOWMtNjI5YTE1NThjNGM1ODkwYTgwOTYtMzNhZC00YzdjLWE5MDEtOGJmYWIwNmUzMWE0"
    "&ui_locales=en-US"
    "&x-client-SKU=ID_NET472"
    "&x-client-ver=6.35.0.0"
)

TIMEOUT_MS = 30_000


def _is_security_questions_page(page) -> bool:
    """Return True if the current page is the security questions step."""
    url = page.url
    # URL pattern seen on the security questions page
    if "SelfAsserted/confirmed" in url:
        return True
    # Fallback: look for both security question input fields on the page
    try:
        body = page.inner_text("body")
        sq_keywords = ["security question", "least favorite", "first job", "maiden name",
                       "childhood", "pet", "mother", "born"]
        hits = sum(1 for kw in sq_keywords if kw.lower() in body.lower())
        if hits >= 1:
            # Also confirm there are answer input fields
            inputs = page.query_selector_all("input[type='text'], input[type='password']")
            if len(inputs) >= 1:
                return True
    except Exception:
        pass
    return False


PUSHOVER_TOKEN = "atnyrpx4yrn8g3dcw1c9so35ngdhr1"
PUSHOVER_USERS = [
    "upcscqtgbhzmtnrax8asirvyzocbdj",
    "ube59dzs3x5nq5b2xcypjzkqau2pdp",
]


def _send_notification(message: str) -> None:
    """Send a push notification to iPhone via Pushover, with a Windows toast as fallback."""
    # ── Pushover (iPhone) ───────────────────────────────────────────────────────
    try:
        for user_key in PUSHOVER_USERS:
            payload = urllib.parse.urlencode({
                "token":   PUSHOVER_TOKEN,
                "user":    user_key,
                "title":   "US Visa Login",
                "message": message,
                "priority": 1,
            }).encode()
            req = urllib.request.Request(
                "https://api.pushover.net/1/messages.json",
                data=payload,
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    print("[*] Pushover notification sent to iPhone.")
                else:
                    print(f"[!] Pushover returned HTTP {resp.status}")
    except Exception as exc:
        print(f"[!] Pushover failed: {exc}")

    # ── Windows toast (local fallback) ──────────────────────────────────────────
    try:
        ps_cmd = (
            f'Add-Type -AssemblyName System.Windows.Forms; '
            f'$n = New-Object System.Windows.Forms.NotifyIcon; '
            f'$n.Icon = [System.Drawing.SystemIcons]::Information; '
            f'$n.Visible = $true; '
            f'$n.ShowBalloonTip(10000, "Visa Login", "{message}", '
            f'[System.Windows.Forms.ToolTipIcon]::Info)'
        )
        subprocess.Popen(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        print(f"[*] Desktop notification sent.")
    except Exception as exc:
        print(f"[!] Desktop notification failed: {exc}")


def run(headless: bool = True) -> bool:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        ctx = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="en-US",
            viewport={"width": 1280, "height": 800},
        )
        page = ctx.new_page()

        try:
            # ── load login page ─────────────────────────────────────────────────
            print("[*] Opening login page …")
            page.goto(LOGIN_URL, wait_until="networkidle", timeout=TIMEOUT_MS)
            print(f"[*] Auth page loaded: {page.url[:80]}…")

            # ── username ────────────────────────────────────────────────────────
            print("[*] Entering username …")
            username_selectors = [
                "input[id='signInName']",
                "input[name='signInName']",
                "input[name='loginfmt']",
                "input[type='email']",
                "input[id='email']",
            ]
            username_field = None
            for sel in username_selectors:
                try:
                    page.wait_for_selector(sel, timeout=5_000)
                    username_field = sel
                    break
                except PlaywrightTimeout:
                    continue

            if not username_field:
                print("[!] Username field not found — page HTML:")
                print(page.content()[:2000])
                return False

            page.fill(username_field, USERNAME)

            # ── password ────────────────────────────────────────────────────────
            print("[*] Entering password …")
            password_selectors = [
                "input[name='passwd']",
                "input[type='password']",
                "input[id='password']",
            ]
            password_field = None
            for sel in password_selectors:
                try:
                    page.wait_for_selector(sel, timeout=5_000)
                    password_field = sel
                    break
                except PlaywrightTimeout:
                    continue

            if not password_field:
                print("[!] Password field not found — page HTML:")
                print(page.content()[:2000])
                return False

            page.fill(password_field, PASSWORD)

            # ── submit ──────────────────────────────────────────────────────────
            print("[*] Submitting credentials …")
            page.press(password_field, "Enter")
            page.wait_for_load_state("domcontentloaded", timeout=TIMEOUT_MS)
            time.sleep(2)  # allow JS redirects to settle

            post_url = page.url
            print(f"[*] Post-login URL: {post_url[:100]}…")

            # ── success = security questions page reached (check FIRST) ───────────
            if _is_security_questions_page(page):
                msg = "US Visa login SUCCESS — security questions page reached!"
                print(f"[+] {msg}")
                _send_notification(msg)
                return True

            # ── still on auth domain = wrong credentials or MFA ────────────────
            if "b2clogin.com" in post_url or "login.microsoftonline" in post_url:
                msg = "US Visa login FAILED — still on auth page (wrong credentials or MFA?)"
                print(f"[-] {msg}")
                _send_notification(msg)
                return False

            # ── landed somewhere else (unexpected) ─────────────────────────────
            msg = f"US Visa login FAILED — unexpected page: {post_url[:80]}"
            print(f"[?] {msg}")
            _send_notification(msg)
            return False

        except PlaywrightTimeout as exc:
            msg = f"US Visa login FAILED — timeout: {exc}"
            print(f"[!] {msg}")
            _send_notification(msg)
            return False
        except Exception as exc:
            msg = f"US Visa login FAILED — error: {exc}"
            print(f"[!] {msg}")
            _send_notification(msg)
            return False
        finally:
            browser.close()


if __name__ == "__main__":
    headless = "--headed" not in sys.argv and "-H" not in sys.argv
    print(f"Running in {'headed' if not headless else 'headless'} mode.\n")
    success = run(headless=headless)
    sys.exit(0 if success else 1)
