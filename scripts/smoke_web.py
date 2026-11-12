"""Exercise the built iPhone web UI against an isolated, simulated Python worker."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import urllib.request
from playwright.sync_api import sync_playwright, expect

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/web-ui'

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    env={**os.environ,'PYTHON_API_TOKEN':'sma-browser-fixture-token-not-production',
         'APP_PASSWORD':'sma-browser-fixture','AUTH_SECRET':'sma-browser-fixture-auth-not-production',
         'PYTHON_API_URL':'http://127.0.0.1:8111'}
    with tempfile.TemporaryDirectory() as data, (OUT/'servers.log').open('w') as log:
        worker=subprocess.Popen([sys.executable,'-m','web_worker.server','--preview','--data',data,'--port','8111'],cwd=ROOT,env=env,stdout=log,stderr=log)
        web=subprocess.Popen(['node','node_modules/next/dist/bin/next','start','--hostname','127.0.0.1','--port','3111'],cwd=ROOT/'web',env=env,stdout=log,stderr=log)
        try:
            for _ in range(100):
                try:urllib.request.urlopen('http://127.0.0.1:3111',timeout=1);break
                except OSError:time.sleep(.2)
            with sync_playwright() as playwright:
                browser=playwright.chromium.launch(args=['--no-sandbox'])
                context=browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True,color_scheme='dark')
                page=context.new_page();page.set_default_timeout(20000)
                errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
                page.goto('http://127.0.0.1:3111')
                page.get_by_label('Access password').fill(env['APP_PASSWORD'])
                page.get_by_role('button',name='Continue',exact=True).click()
                expect(page.get_by_text('No saved SMA lines yet')).to_be_visible()
                expect(page.get_by_text('OPTIONAL RELEASE UPDATES')).to_have_count(0)
                page.screenshot(path=str(OUT/'home-empty.png'))
                page.get_by_role('button',name='Find a security',exact=True).click()
                searches=[];page.on('request',lambda request:searches.append(request.url) if request.url.endswith('/api/search') else None)
                page.get_by_placeholder('Company name or ticker').fill('Apple')
                page.wait_for_timeout(300);assert searches==[]
                page.get_by_role('button',name='Search',exact=True).click()
                page.get_by_role('button',name='Apple Inc.').click()
                page.get_by_role('button',name='Find best SMA for 4 signals / year').click()
                page.get_by_role('button',name='Save',exact=True).wait_for(timeout=60000)
                page.get_by_role('button',name='Save',exact=True).click()
                expect(page.get_by_role('button',name='Saved',exact=True)).to_be_visible()
                page.screenshot(path=str(OUT/'chart.png'))
                page.locator('section.backtest').screenshot(path=str(OUT/'backtest.png'))
                page.get_by_role('button',name='Edit',exact=True).click()
                page.get_by_label('Name',exact=True).fill('Long-term trend')
                page.get_by_role('button',name='Rose',exact=True).click()
                page.screenshot(path=str(OUT/'edit-line.png'))
                page.get_by_role('button',name='Done',exact=True).click()
                expect(page.get_by_role('dialog')).to_have_count(0)
                visibility=page.get_by_role('switch',name='Show Long-term trend')
                visibility.click();expect(visibility).to_have_attribute('aria-checked','false')
                page.get_by_role('button',name='Alerts',exact=True).click()
                expect(page.get_by_role('switch',name='Alerts for Long-term trend')).to_have_attribute('aria-checked','true')
                buy=page.get_by_role('switch',name='Buy signal for Long-term trend')
                expect(buy).to_have_attribute('aria-checked','true')
                buy.click();expect(buy).to_have_attribute('aria-checked','false')
                expect(page.get_by_role('switch',name='Impending buy signal (End of trading) for Long-term trend')).to_have_attribute('aria-checked','true')
                page.reload();page.get_by_role('button',name='Alerts',exact=True).click()
                expect(page.get_by_role('switch',name='Buy signal for Long-term trend')).to_have_attribute('aria-checked','false')
                page.screenshot(path=str(OUT/'alerts.png'))
                page.get_by_role('button',name='Settings',exact=True).click()
                page.get_by_role('button',name='Light',exact=True).click()
                expect(page.locator('html')).to_have_attribute('data-theme','light')
                page.screenshot(path=str(OUT/'settings-light.png'))
                page.get_by_role('button',name='Dark',exact=True).click()
                page.get_by_role('button',name='Home',exact=True).click()
                page.get_by_role('button',name='Apple Inc.').click()
                page.screenshot(path=str(OUT/'home-saved.png'))
                page.get_by_role('button',name='Long-term trend').click()
                expect(page.get_by_role('switch',name='Show Long-term trend')).to_have_attribute('aria-checked','false')
                page.get_by_role('button',name='Edit',exact=True).click()
                expect(page.get_by_role('button',name='Rose',exact=True)).to_have_attribute('aria-pressed','true')
                page.get_by_role('button',name='Cancel',exact=True).click()
                for width in (320,390,768):
                    page.set_viewport_size({'width':width,'height':844})
                    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),width
                    page.screenshot(path=str(OUT/f'chart-{width}.png'))
                page.get_by_role('button',name='Home',exact=True).click()
                context.set_offline(True)
                expect(page.get_by_text('You are offline',exact=True)).to_be_visible()
                page.get_by_role('button',name='Long-term trend').click()
                expect(page.get_by_role('switch',name='Show Long-term trend')).to_be_visible()
                context.set_offline(False)
                page.get_by_role('button',name='Edit',exact=True).click()
                page.get_by_role('button',name='Archive line',exact=True).click()
                expect(page.get_by_role('dialog')).to_have_count(0)
                page.get_by_role('button',name='Settings',exact=True).click()
                page.get_by_role('button',name='Archived lines').click()
                page.get_by_role('button',name='Restore',exact=True).click()
                expect(page.get_by_text('No archived lines.')).to_be_visible()
                assert not errors,errors
                browser.close()
            print('PASS: private login, submit-only search, Python calculation, save/edit/colour, visibility vs alerts, per-line signal types, themes, narrow layouts, offline reopening, archive/restore; email hidden without server configuration.')
        finally:
            for process in (web,worker):
                process.terminate()
                try:process.wait(timeout=5)
                except subprocess.TimeoutExpired:process.kill();process.wait()

if __name__=='__main__':main()
