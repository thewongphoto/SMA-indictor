"""Optional welcome/signup flow using intercepted delivery; sends no real email."""
import os
from pathlib import Path
import subprocess
import time
import urllib.request
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'artifacts/signup-web'
ORIGIN = 'http://127.0.0.1:3177'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, 'APP_PASSWORD': 'signup-fixture', 'AUTH_SECRET': 'signup-fixture-auth'}
    for key in ('RESEND_API_KEY', 'PYTHON_API_URL', 'PYTHON_API_TOKEN', 'SUPABASE_URL', 'SUPABASE_SECRET_KEY'):
        env.pop(key, None)
    with (OUT / 'server.log').open('w') as log:
        server = subprocess.Popen(['node', 'node_modules/next/dist/bin/next', 'start', '--hostname', '127.0.0.1', '--port', '3177'], cwd=ROOT/'web', env=env, stdout=log, stderr=log)
        try:
            for _ in range(100):
                try:
                    urllib.request.urlopen(ORIGIN, timeout=1)
                    break
                except OSError:
                    time.sleep(.2)
            with sync_playwright() as p:
                browser = p.chromium.launch(args=['--no-sandbox'])
                context = browser.new_context(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True, color_scheme='dark', service_workers='block')
                page = context.new_page()
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                # Real unconfigured API hides the welcome page and requires no email.
                page.goto(ORIGIN)
                expect(page.get_by_label('Access password')).to_be_visible()
                assert page.request.get(ORIGIN+'/api/contact-capabilities').json() == {'enabled': False}
                assert page.request.get(ORIGIN+'/api/contact-status').status == 401
                assert page.request.post(ORIGIN+'/api/contact-email', data={'email': 'fixture@example.com'}).status == 503
                page.route('**/api/contact-capabilities', lambda route: route.fulfill(json={'enabled': True}))
                sends = []
                state = {'fail': True}
                def deliver(route):
                    sends.append(route.request.post_data_json)
                    if state['fail']:
                        route.fulfill(status=503, json={'error': 'Fixture service unavailable. You can skip for now.'})
                    else:
                        route.fulfill(json={'sent': True})
                page.route('**/api/contact-email', deliver)
                page.goto(ORIGIN+'/?welcome=1')
                expect(page.get_by_role('heading', name='Welcome to SMA Stock Analyzer')).to_be_visible()
                page.get_by_role('button', name='Skip for now').click()
                expect(page.get_by_label('Access password')).to_be_visible()
                assert not sends
                page.goto(ORIGIN+'/?welcome=1')
                page.get_by_role('button', name='Continue', exact=True).click()
                expect(page.locator('#contact-error')).to_contain_text('Enter a valid email')
                assert not sends
                page.get_by_label('Email address').fill('volunteer@example.com')
                page.get_by_role('button', name='Continue', exact=True).click()
                expect(page.locator('#contact-error')).to_contain_text('Fixture service unavailable')
                expect(page.get_by_role('heading', name='Welcome to SMA Stock Analyzer')).to_be_visible()
                assert page.evaluate('localStorage.getItem("sma-contact-email")') is None
                first = sends[0]
                page.reload()
                page.get_by_label('Email address').fill('volunteer@example.com')
                state['fail'] = False
                page.get_by_role('button', name='Continue', exact=True).click()
                expect(page.get_by_role('status')).to_contain_text('Email saved and forwarded')
                assert sends[1]['request_id'] == first['request_id']
                assert sends[1]['install_id'] == first['install_id']
                page.screenshot(path=str(OUT/'confirmed.png'), full_page=True)
                page.get_by_role('button', name='Use a different email').click()
                page.get_by_role('button', name='Continue', exact=True).click()
                expect(page.get_by_role('status')).to_contain_text('already saved')
                assert len(sends) == 2
                page.get_by_role('button', name='Use a different email').click()
                page.get_by_label('Email address').fill('changed@example.com')
                page.get_by_role('button', name='Continue', exact=True).click()
                expect(page.get_by_role('status')).to_contain_text('Email saved and forwarded')
                assert sends[-1]['request_id'] != first['request_id']
                assert page.evaluate('localStorage.getItem("sma-contact-email")') == 'changed@example.com'
                page.get_by_role('button', name='Open the app', exact=True).click()
                expect(page.get_by_label('Access password')).to_be_visible()
                # A fresh installation shows the full design at small phone widths.
                page.evaluate('localStorage.clear()')
                page.goto(ORIGIN+'/?welcome=1')
                for width in (320, 390, 768):
                    page.set_viewport_size({'width': width, 'height': 844})
                    expect(page.get_by_role('button', name='Skip for now')).to_be_visible()
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), width
                    page.screenshot(path=str(OUT/f'welcome-{width}.png'), full_page=True)
                # Owner setup instructions and separate SQL remain available.
                page.route('**/api/contact-status', lambda route: route.fulfill(json={'ready': True, 'provider_configured': True, 'schema_ready': True, 'recipient': 'kelwong98@gmail.com', 'sender': 'onboarding@resend.dev', 'signed_up_installations': 2, 'accepted_submissions': 3}))
                page.goto(ORIGIN+'/setup/email')
                expect(page.get_by_text('Configuration is ready.', exact=False)).to_be_visible()
                page.get_by_role('button', name='Prepare email SQL').click()
                sql = page.get_by_label('Email setup SQL').input_value()
                assert 'sma_claim_contact' in sql and 'cron.schedule' not in sql
                assert 'RESEND_API_KEY' not in sql
                page.get_by_role('button', name='Check email setup', exact=True).click()
                expect(page.locator('.setup-result')).to_contain_text('Accepted submissions, including changes: 3')
                assert not errors, errors
                browser.close()
            print('PASS: disabled service, optional Skip, validation, failed/retried intent, acceptance confirmation, address changes, same-address deduplication, 320px welcome and owner SQL/setup; no real emails.')
        finally:
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()


if __name__ == '__main__':
    main()
