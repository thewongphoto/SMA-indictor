"""Setup results stay beside the button, including failed or expired sessions."""
import os
from pathlib import Path
import subprocess
import time
import urllib.request
from playwright.sync_api import sync_playwright,expect

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/setup-feedback'

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    with (OUT/'server.log').open('w') as log:
        server=subprocess.Popen(['node','node_modules/next/dist/bin/next','start','--hostname','127.0.0.1','--port','3166'],cwd=ROOT/'web',stdout=log,stderr=log)
        try:
            for _ in range(100):
                try:urllib.request.urlopen('http://127.0.0.1:3166/setup',timeout=1);break
                except OSError:time.sleep(.2)
            with sync_playwright() as p:
                browser=p.chromium.launch(args=['--no-sandbox'])
                page=browser.new_page(viewport={'width':390,'height':844})
                scenario={'status':401,'value':{'error':'Sign in to your private app.'},'hold':False}
                held=[]
                def respond(route):
                    if scenario['hold']:held.append(route)
                    else:route.fulfill(status=scenario['status'],json=scenario['value'])
                page.route('**/api/push/config',respond)
                errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
                page.goto('http://127.0.0.1:3166/setup')
                button=page.get_by_role('button',name='Check setup',exact=True)
                button.click()
                result=page.locator('.setup-result')
                expect(result).to_contain_text('Sign in to your private app.')
                expect(result.get_by_role('link',name='Sign in to SMA in a new tab')).to_have_attribute('target','_blank')
                expect(result).to_be_in_viewport()
                page.screenshot(path=str(OUT/'signin-result.png'))
                scenario['status']=200
                scenario['value']={'database_configured':True,'schema_ready':False,'scheduled_jobs':0,'vapid_ready':True,'cron_secret_configured':True,'cron_secret_matches':False,'origin_matches':False,'ready':False,'project_url':'https://fixture.supabase.co'}
                button.click()
                expect(result).to_contain_text('Check complete — setup still needs attention.')
                expect(result).to_contain_text('Supabase → SQL Editor → New query')
                expect(result).to_be_in_viewport()
                page.screenshot(path=str(OUT/'sql-next-step.png'))
                scenario['hold']=True
                button.click()
                expect(page.get_by_role('button',name='Checking setup…',exact=True)).to_be_disabled()
                expect(result).to_contain_text('up to 20 seconds')
                ready={**scenario['value'],'schema_ready':True,'scheduled_jobs':4,'cron_secret_matches':True,'origin_matches':True,'ready':True}
                assert len(held)==1
                held.pop().fulfill(json=ready)
                expect(result).to_contain_text('Setup is ready.')
                expect(result).to_contain_text('Last checked:')
                expect(button).to_be_enabled()
                scenario['hold']=False;scenario['status']=503;scenario['value']={'error':'Fixture connection unavailable'}
                button.click()
                expect(result).to_contain_text('Fixture connection unavailable')
                expect(result).not_to_contain_text('Setup is ready.')
                expect(page.get_by_text('Server setup is ready.',exact=False)).to_have_count(0)
                assert not errors,errors
                browser.close()
            print('PASS: sign-in error is visible beside Check setup, unfinished setup gives its next step, loading disables repeated requests, successful checks show a timestamp, and failed rechecks clear stale success.')
        finally:
            server.terminate()
            try:server.wait(timeout=5)
            except subprocess.TimeoutExpired:server.kill();server.wait()

if __name__=='__main__':main()
