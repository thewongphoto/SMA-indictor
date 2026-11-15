"""Password-free clients cannot read owner APIs; no live market/mail/push calls."""
import os
from pathlib import Path
import subprocess
import time
import urllib.request

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts/public-access-web"
ORIGIN = "http://127.0.0.1:3188"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for configured in (True, False):
        env = dict(os.environ)
        for key in ("APP_PASSWORD", "AUTH_SECRET", "PYTHON_API_URL", "PYTHON_API_TOKEN",
                    "SUPABASE_URL", "SUPABASE_SECRET_KEY", "RESEND_API_KEY",
                    "VAPID_PUBLIC_KEY", "VAPID_PRIVATE_KEY", "CRON_SECRET"):
            env.pop(key, None)
        if configured:
            env.update(APP_PASSWORD="owner-access-fixture", AUTH_SECRET="owner-session-fixture")
        with (OUT / f"server-{configured}.log").open("w") as log:
            server = subprocess.Popen(
                ["node", "node_modules/next/dist/bin/next", "start", "--hostname", "127.0.0.1", "--port", "3188"],
                cwd=ROOT / "web", env=env, stdout=log, stderr=log,
            )
            try:
                for _ in range(100):
                    try:
                        urllib.request.urlopen(ORIGIN, timeout=1)
                        break
                    except OSError:
                        time.sleep(.2)
                with sync_playwright() as p:
                    browser = p.chromium.launch(args=["--no-sandbox"])
                    context = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
                    page = context.new_page()
                    errors = []
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    page.goto(ORIGIN)
                    expect(page.get_by_text("No saved SMA lines yet")).to_be_visible()
                    expect(page.locator('input[type="password"]')).to_have_count(0)
                    assert not context.cookies()
                    api = page.request
                    assert api.get(ORIGIN + "/api/session").json() == {"storage": "local", "owner": False}
                    public = api.get(ORIGIN + "/api/push/public-config")
                    assert public.status == 200
                    assert public.json() == {"ready": False, "public_key": "", "owner": False}
                    for path in ("contact-status", "push/config", "push/status", "state", "log"):
                        assert api.get(ORIGIN + "/api/" + path).status == 401, path
                    assert api.post(ORIGIN + "/api/push/check").status == 401
                    # Invalid market/device input is validated without sign-in or
                    # any network fetch/delivery; cross-site writes still fail.
                    for path, body in (("market/search", {"query": ""}), ("market/history", {"key": "invalid"}),
                                       ("push/sync", {}), ("push/disable", {}), ("push/test", {})):
                        response = api.post(ORIGIN + "/api/" + path, data=body)
                        assert response.status == 503, (path, response.status)
                        assert api.post(ORIGIN + "/api/" + path, data=body,
                                        headers={"Origin": "https://other.example"}).status == 403
                    page.screenshot(path=str(OUT / f"home-{configured}.png"))
                    page.goto(ORIGIN + "/setup/login?next=https://other.example")
                    page.get_by_label("Owner password").fill("wrong-fixture-password")
                    page.get_by_role("button", name="Sign in", exact=True).click()
                    expect(page.locator('.login [role="alert"]')).to_contain_text(
                        "Incorrect access password" if configured else "Private access has not been configured.")
                    if configured:
                        page.get_by_label("Owner password").fill(env["APP_PASSWORD"])
                        page.get_by_role("button", name="Sign in", exact=True).click()
                        page.wait_for_url(ORIGIN + "/setup")
                        assert api.get(ORIGIN + "/api/session").json() == {"storage": "local", "owner": True}
                        assert api.get(ORIGIN + "/api/push/config").status == 200
                        # A separate installation never inherits owner access.
                        visitor = browser.new_context()
                        assert visitor.request.get(ORIGIN + "/api/push/config").status == 401
                        visitor.close()
                        page.goto(ORIGIN + "/setup/login")
                        page.get_by_role("button", name="Sign out of owner setup").click()
                        expect(page.get_by_label("Owner password")).to_be_visible()
                        assert api.get(ORIGIN + "/api/push/config").status == 401
                        # Expired and forged owner cookies must still be rejected.
                        for cookie in ("1.invalid", "9999999999999.forged"):
                            context.add_cookies([{"name": "sma_session", "value": cookie, "url": ORIGIN}])
                            assert api.get(ORIGIN + "/api/push/config").status == 401
                        context.clear_cookies()
                    page.goto(ORIGIN)
                    expect(page.get_by_text("No saved SMA lines yet")).to_be_visible()
                    expect(page.locator('input[type="password"]')).to_have_count(0)
                    assert not errors, errors
                    browser.close()
            finally:
                server.terminate()
                try:
                    server.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait()
    print("PASS: password-free opening with/without owner credentials; owner APIs, legacy state, scheduler and cross-origin writes stay protected; owner login/logout and safe return navigation work.")


if __name__ == "__main__":
    main()
