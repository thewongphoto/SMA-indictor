"""Real browser Python, frozen window persistence and screen 24 on both engines."""
import json,os,subprocess,time,urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from sma_analyzer.mock_data import generate_mock_data
from sma_analyzer.history_window import optimize_history

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/history-web';ORIGIN='http://127.0.0.1:3190'
def main():
    OUT.mkdir(parents=True,exist_ok=True)
    sample=generate_mock_data('DEMO-US','Oscillating',sessions=1700)
    security=dict(key='YAHOO:VOO',ticker='VOO',name='Vanguard S&P 500 ETF',region='US',currency='USD',logo_url='/logos/vanguard.png')
    data=dict(security=security,prices=sample.prices,dates=sample.dates,preview=False,stale=False,currency='USD',scenario='Yahoo EOD',fetched_at=time.time())
    a,b=sample.dates[200],sample.dates[-200]
    expected=optimize_history(sample.prices,4,dates=sample.dates,history_start=a,history_end=b)
    env=dict(os.environ)
    for key in ('PYTHON_API_URL','PYTHON_API_TOKEN','RESEND_API_KEY','SUPABASE_URL','SUPABASE_SECRET_KEY'):env.pop(key,None)
    with (OUT/'server.log').open('w') as log:
        server=subprocess.Popen(['node','node_modules/next/dist/bin/next','start','--hostname','127.0.0.1','--port','3190'],cwd=ROOT/'web',env=env,stdout=log,stderr=log)
        try:
            for _ in range(100):
                try:urllib.request.urlopen(ORIGIN,timeout=1);break
                except OSError:time.sleep(.2)
            with sync_playwright() as p:
                for engine in ('chromium','webkit'):
                    options={'args':['--no-sandbox']} if engine=='chromium' else ({'executable_path':os.environ['SMA_WEBKIT_EXECUTABLE']} if os.environ.get('SMA_WEBKIT_EXECUTABLE') else {})
                    browser=getattr(p,engine).launch(**options)
                    context=browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True,color_scheme='dark',service_workers='block')
                    page=context.new_page();page.set_default_timeout(30000);errors=[];market=[]
                    page.on('pageerror',lambda e:(errors.append(str(e)),print('BROWSER ERROR',engine,str(e),flush=True)))
                    page.route('**/api/market/search',lambda route:(market.append('search'),route.fulfill(json={'results':[security]})))
                    page.route('**/api/market/history',lambda route:(market.append('history'),route.fulfill(json=data)))
                    page.goto(ORIGIN);page.get_by_role('button',name='Find a security',exact=True).click()
                    page.get_by_placeholder('Company name or ticker').fill('voo');page.get_by_role('button',name='Search',exact=True).click();page.get_by_role('button',name='Vanguard S&P 500 ETF').click()
                    builder=page.locator('.preference-builder');expect(builder).to_be_visible()
                    builder.get_by_role('button',name='4',exact=True).click()
                    expect(builder.locator('.history-row')).to_contain_text('All available')
                    before=len(market)
                    page.locator('.history-row').click()
                    sheet=page.get_by_role('dialog',name='Price history used',exact=True)
                    sheet.get_by_role('button',name='Last 3 years',exact=True).click()
                    sheet.get_by_role('button',name='Cancel',exact=True).click()
                    expect(builder.locator('.history-row')).to_contain_text('All available')
                    def choose(start,end):
                        page.locator('.target-preference .history-row').click()
                        sheet=page.get_by_role('dialog',name='Price history used',exact=True)
                        sheet.get_by_role('button',name='Custom dates',exact=True).click()
                        sheet.get_by_label('From',exact=True).fill(start);sheet.get_by_label('To',exact=True).fill(end)
                        return sheet
                    sheet=choose(sample.dates[-2],sample.dates[-1])
                    expect(sheet.get_by_role('button',name='Use this history')).to_be_disabled()
                    expect(sheet.get_by_role('status')).to_contain_text('4 trading days')
                    sheet.get_by_label('From',exact=True).fill(a);sheet.get_by_label('To',exact=True).fill(b)
                    expect(sheet.get_by_role('button',name='Use this history')).to_be_enabled()
                    page.set_viewport_size({'width':320,'height':640})
                    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                    page.screenshot(path=str(OUT/f'{engine}-narrow-picker.png'))
                    page.set_viewport_size({'width':390,'height':844})
                    page.screenshot(path=str(OUT/f'{engine}-picker.png'))
                    sheet.get_by_role('button',name='Use this history').click()
                    expect(page.locator('.history-row')).to_contain_text('custom')
                    assert len(market)==before
                    page.get_by_role('button',name='Find best SMA for 4 signals / year').click()
                    page.get_by_role('button',name='Save',exact=True).wait_for(timeout=180000)
                    expect(page.get_by_text(f'Price is {"above" if sample.prices[-1]>expected.sma[-1] else "below"} its {expected.period}-day line',exact=True)).to_be_visible()
                    expect(page.locator('.history-caption')).to_contain_text('dimmed prices were not used')
                    expect(page.locator('.history-dimming')).to_have_count(1)
                    page.get_by_role('button',name='Save',exact=True).click();expect(page.get_by_role('button',name='Saved',exact=True)).to_be_visible()
                    signals=page.locator('.target-preference').bounding_box()
                    saved=page.locator('section.card').filter(has=page.get_by_role('heading',name='SAVED LINES ·',exact=False)).bounding_box()
                    assert signals['y']<saved['y']
                    page.get_by_role('button',name='Edit',exact=True).click();page.get_by_label('Name',exact=True).fill('Frozen plan');page.get_by_role('button',name='Rose',exact=True).click();page.get_by_role('button',name='Done',exact=True).click()
                    page.get_by_role('button',name='Alerts',exact=True).click();page.get_by_role('switch',name='Alerts for Frozen plan',exact=True).click()
                    page.get_by_role('button',name='Charts',exact=True).click()
                    page.locator('.history-row').click();sheet=page.get_by_role('dialog',name='Price history used',exact=True)
                    sheet.get_by_role('button',name='All available',exact=True).click();sheet.get_by_role('button',name='Use this history').click()
                    expect(page.get_by_text('The period has changed',exact=True)).to_be_visible();expect(page.get_by_role('button',name='Saved',exact=True)).to_be_disabled()
                    assert len(market)==before
                    page.get_by_role('button',name='Recalculate for 4 signals / year').click();page.get_by_role('button',name='Save',exact=True).wait_for(timeout=180000)
                    page.get_by_role('button',name='Save',exact=True).click()
                    choice=page.get_by_role('dialog',name='This line is already saved',exact=True)
                    expect(choice).to_contain_text('Keeps both. The new line starts with alerts on.')
                    choice.get_by_role('button',name='Cancel',exact=True).click()
                    expect(choice).to_have_count(0)
                    page.get_by_role('button',name='Save',exact=True).click()
                    page.screenshot(path=str(OUT/f'{engine}-save-choice.png'))
                    choice.get_by_role('button',name='Update this line').click();expect(choice).to_have_count(0)
                    expect(page.get_by_role('button',name='Saved',exact=True)).to_be_visible()
                    page.get_by_role('button',name='Alerts',exact=True).click();expect(page.get_by_role('switch',name='Alerts for Frozen plan',exact=True)).to_have_attribute('aria-checked','false')
                    page.get_by_role('button',name='Charts',exact=True).click()
                    sheet=choose(a,b);sheet.get_by_role('button',name='Use this history').click();page.get_by_role('button',name='Recalculate for 4 signals / year').click();page.get_by_role('button',name='Save',exact=True).wait_for(timeout=180000)
                    page.get_by_role('button',name='Save',exact=True).click();choice.get_by_role('button',name='Save as a new line').click();expect(choice).to_have_count(0)
                    expect(page.get_by_role('button',name='Saved',exact=True)).to_be_visible()
                    page.get_by_role('button',name='Alerts',exact=True).click()
                    switches=page.get_by_role('switch',name='Alerts for ')
                    assert switches.count()==2
                    assert switches.nth(0).get_attribute('aria-checked')=='false' and switches.nth(1).get_attribute('aria-checked')=='true'
                    page.get_by_role('button',name='Home',exact=True).click();page.get_by_role('button',name='Vanguard S&P 500 ETF').click()
                    expect(page.locator('.history-tag')).to_have_count(1)
                    page.screenshot(path=str(OUT/f'{engine}-home.png'))
                    page.reload();page.get_by_role('button',name='Vanguard S&P 500 ETF').click()
                    expect(page.locator('.history-tag')).to_have_count(1)
                    page.locator('.saved-row').filter(has=page.locator('.history-tag')).click()
                    page.get_by_role('button',name='Edit',exact=True).nth(1).click()
                    page.get_by_role('button',name='Archive line',exact=True).click()
                    page.get_by_role('button',name='Save',exact=True).click()
                    expect(page.get_by_role('dialog',name='This line is already saved',exact=True)).to_have_count(0)
                    expect(page.get_by_role('button',name='Saved',exact=True)).to_be_visible()
                    page.get_by_role('button',name='Settings',exact=True).click()
                    expect(page.get_by_role('heading',name='MARKET DATA',exact=True)).to_have_count(0)
                    expect(page.get_by_role('link',name='Owner server setup',exact=True)).to_have_count(0)
                    expect(page.get_by_role('heading',name='SAVED LINES',exact=True)).to_be_visible()
                    expect(page.get_by_role('button',name='Export saved parameters')).to_be_visible()
                    page.screenshot(path=str(OUT/f'{engine}-settings.png'))
                    assert not errors,errors
                    browser.close()
        finally:
            server.terminate()
            try:server.wait(timeout=5)
            except subprocess.TimeoutExpired:server.kill();server.wait()
    print('PASS: actual Chromium/WebKit Python uses custom history, rejects short dates, never fetches/recalculates on selection, preserves Update settings, saves a second line with alerts ON, labels and persists frozen dates.')
if __name__=='__main__':main()
