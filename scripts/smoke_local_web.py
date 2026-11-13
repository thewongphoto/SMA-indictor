"""Real Pyodide/browser checks with intercepted market fixtures; no live push/mail."""
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.request
from playwright.sync_api import sync_playwright, expect
from sma_analyzer.mock_data import generate_mock_data
from sma_analyzer.engine import optimize_sma
from sma_analyzer.backtest import compare_investments,period_sessions
from sma_analyzer.backtest_text import backtest_span

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/local-web'

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    sample=generate_mock_data('DEMO-US','Oscillating',sessions=1700)
    security=dict(key='YAHOO:AAPL',ticker='AAPL',symbol='AAPL',name='Apple Inc.',region='US',currency='USD',timezone='America/New_York',logo_url='/logos/apple.png')
    fixture=dict(security=security,prices=sample.prices,dates=sample.dates,currency='USD',scenario='Yahoo EOD',preview=False,stale=False,source='yahoo',fetched_at=time.time())
    expected=optimize_sma(sample.prices,4,dates=sample.dates)
    short=compare_investments(sample.prices,expected.sma,expected.events,period_sessions('1Y','3',len(sample.prices),sample.dates),sample.dates)
    span=backtest_span(sample,short,sample.dates)
    env={**os.environ,'APP_PASSWORD':'sma-local-fixture','AUTH_SECRET':'sma-local-fixture-auth-secret'}
    for key in ('PYTHON_API_URL','PYTHON_API_TOKEN','SUPABASE_URL','SUPABASE_SECRET_KEY','VAPID_PRIVATE_KEY','VAPID_PUBLIC_KEY','CRON_SECRET'):env.pop(key,None)
    with (OUT/'production.log').open('w') as log:
        server=subprocess.Popen(['node','node_modules/next/dist/bin/next','start','--hostname','127.0.0.1','--port','3123'],cwd=ROOT/'web',env=env,stdout=log,stderr=log)
        try:
            for _ in range(100):
                try:urllib.request.urlopen('http://127.0.0.1:3123',timeout=1);break
                except OSError:time.sleep(.2)
            with sync_playwright() as p:
                browser=p.chromium.launch(args=['--no-sandbox'])
                context=browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True,color_scheme='dark')
                page=context.new_page();page.set_default_timeout(25000)
                errors=[];requests=[]
                page.on('pageerror',lambda error:errors.append(str(error)))
                page.on('request',lambda req:requests.append(req.url))
                page.route('**/api/market/search',lambda route:route.fulfill(json={'results':[security]}))
                page.route('**/api/market/history',lambda route:route.fulfill(json=fixture))
                page.goto('http://127.0.0.1:3123')
                page.get_by_label('Access password').fill(env['APP_PASSWORD']);page.get_by_role('button',name='Continue',exact=True).click()
                page.get_by_text('No saved SMA lines yet').wait_for()
                page.get_by_role('button',name='Find a security',exact=True).click()
                page.get_by_placeholder('Company name or ticker').fill('Apple');page.wait_for_timeout(200)
                assert not any(url.endswith('/api/market/search') for url in requests)
                page.get_by_role('button',name='Search',exact=True).click();page.get_by_role('button',name='Apple Inc.').click()
                page.get_by_role('button',name='Find best SMA for 4 signals / year').click()
                page.get_by_role('button',name='Save',exact=True).wait_for(timeout=120000)
                expect(page.get_by_text(f'Price is {"above" if sample.prices[-1]>expected.sma[-1] else "below"} its {expected.period}-day line',exact=True)).to_be_visible()
                assert not any(url.endswith('/api/optimize') or url.endswith('/api/chart') for url in requests)
                page.get_by_role('button',name='Save',exact=True).click();page.get_by_role('button',name='Saved',exact=True).wait_for()
                page.get_by_role('button',name='Edit',exact=True).click();page.get_by_label('Name',exact=True).fill('Local research');page.get_by_role('button',name='Rose',exact=True).click();page.get_by_role('button',name='Done',exact=True).click()
                expect(page.get_by_role('dialog')).to_have_count(0)
                page.get_by_role('button',name='Alerts',exact=True).click()
                expect(page.get_by_role('switch',name='Alerts for Local research')).to_have_attribute('aria-checked','true')
                page.get_by_role('switch',name='Buy signal for Local research',exact=True).click()
                page.get_by_role('button',name='Settings',exact=True).click()
                with page.expect_download() as download:page.get_by_role('button',name='Export saved parameters').click()
                backup=Path(download.value.path());exported=json.loads(backup.read_text());assert exported['cards'][0]['lines'][0]['custom_name']=='Local research';assert not exported['cards'][0]['lines'][0]['alert_buy']
                page.get_by_role('button',name='Sign out',exact=True).click();page.get_by_label('Access password').fill(env['APP_PASSWORD']);page.get_by_role('button',name='Continue',exact=True).click()
                page.get_by_role('button',name='Apple Inc.').click();page.get_by_role('button',name='Local research').click()
                page.get_by_role('button',name='Edit',exact=True).click();expect(page.get_by_role('button',name='Rose',exact=True)).to_have_attribute('aria-pressed','true');page.get_by_role('button',name='Cancel',exact=True).click()
                page.screenshot(path=str(OUT/'chart-local.png'))
                # Stop/reload the JS context to prove the runtime and data survive offline.
                page.evaluate('navigator.serviceWorker.ready');page.wait_for_timeout(600)
                context.set_offline(True);page.reload(wait_until='domcontentloaded')
                page.get_by_role('button',name='Apple Inc.').click();page.get_by_role('button',name='Local research').click()
                page.locator('.backtest').get_by_role('button',name='1Y',exact=True).click()
                expect(page.locator('.backtest-summary')).to_contain_text(span,timeout=120000)
                page.screenshot(path=str(OUT/'offline-calculation.png'))
                context.set_offline(False)
                page.get_by_role('button',name='Home',exact=True).click();page.get_by_role('button',name='Local research').click()
                page.get_by_role('button',name='Edit',exact=True).click();page.get_by_role('button',name='Archive line',exact=True).click();expect(page.get_by_role('dialog')).to_have_count(0)
                page.get_by_role('button',name='Settings',exact=True).click();page.once('dialog',lambda dialog:dialog.accept());page.get_by_label('Import saved parameters').set_input_files(str(backup));page.get_by_role('button',name='Home',exact=True).click()
                company=page.get_by_role('button',name='Apple Inc.');
                if company.get_attribute('aria-expanded')!='true':company.click()
                expect(page.get_by_role('button',name='Local research')).to_be_visible()
                page.goto('http://127.0.0.1:3123/setup');page.get_by_role('button',name='Generate keys',exact=True).click();expect(page.get_by_role('button',name='Copy VAPID_PRIVATE_KEY')).to_be_visible();page.get_by_role('button',name='Prepare setup SQL').click()
                sql=page.get_by_label('Supabase setup SQL').input_value();assert '__APP_URL__' not in sql and '__CRON_SECRET__' not in sql;assert 'http://127.0.0.1:3123' in sql
                page.screenshot(path=str(OUT/'setup.png'))
                for width in (320,390,768):
                    page.set_viewport_size({'width':width,'height':844});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),width
                assert not errors,errors
                browser.close()
            print('PASS: real Pyodide/NumPy equals Python, no server calculations, save/colour/per-line flags, sign-out persistence, cold offline runtime/backtest, backup import, key/SQL setup and narrow layouts.')
        finally:
            server.terminate()
            try:server.wait(timeout=5)
            except subprocess.TimeoutExpired:server.kill();server.wait()

if __name__=='__main__':main()
