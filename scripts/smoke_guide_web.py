"""Compare the actual web guide with the native guide over the same price fixture."""
import json,os,subprocess,time,urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from scripts.yahoo_test_data import bars_ending
from types import SimpleNamespace
from sma_analyzer.guide import calculate_lesson

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/guide-web'

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    bars=bars_ending()
    for bar in bars[:-100]:bar['adj_close']*=.97
    security=dict(key='YAHOO:VOO',ticker='VOO',name='Vanguard S&P 500 ETF',region='US',currency='USD',logo_url='/logos/vanguard.png')
    data=dict(security=security,prices=[b['adj_close'] for b in bars],dates=[b['date'] for b in bars],
              preview=False,stale=False,currency='USD',scenario='Yahoo EOD')
    expected=calculate_lesson(4,SimpleNamespace(prices=data['prices'],dates=data['dates'],is_simulated=False))
    env=dict(os.environ)
    for key in ('PYTHON_API_URL','PYTHON_API_TOKEN','RESEND_API_KEY','SUPABASE_URL','SUPABASE_SECRET_KEY'):env.pop(key,None)
    reports={}
    with (OUT/'server.log').open('w') as log:
        server=subprocess.Popen(['node','node_modules/next/dist/bin/next','start','--hostname','127.0.0.1','--port','3193'],cwd=ROOT/'web',env=env,stdout=log,stderr=log)
        try:
            for _ in range(100):
                try:urllib.request.urlopen('http://127.0.0.1:3193',timeout=1);break
                except OSError:time.sleep(.2)
            with sync_playwright() as p:
                for engine in ('chromium','webkit'):
                    options={'args':['--no-sandbox']} if engine=='chromium' else ({'executable_path':os.environ['SMA_WEBKIT_EXECUTABLE']} if os.environ.get('SMA_WEBKIT_EXECUTABLE') else {})
                    browser=getattr(p,engine).launch(**options)
                    context=browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True,color_scheme='light',service_workers='block')
                    page=context.new_page();page.set_default_timeout(30000)
                    page.route('**/api/market/search',lambda r:r.fulfill(json={'results':[security]}))
                    page.route('**/api/market/history',lambda r:r.fulfill(json=data))
                    page.goto('http://127.0.0.1:3193')
                    page.get_by_role('button',name='Try the guided example',exact=True).click()
                    expect(page.get_by_role('heading',name='Guided example',exact=True)).to_be_visible()
                    page.get_by_role('button',name='Find best SMA for 4 signals / year',exact=True).click()
                    page.locator('.backtest-value strong').first.wait_for(timeout=180000)
                    expect(page.locator('.price')).to_have_text(f"${data['prices'][-1]:,.2f}")
                    expect(page.locator('.status')).to_contain_text('day line')
                    expect(page.locator('.target-preference .history-row')).to_contain_text('All available')
                    expect(page.locator('.backtest .segments button[aria-pressed="true"]')).to_have_text('Max')
                    assert page.locator('.backtest-row').count()==3
                    assert page.locator('.backtest-row .bar').count()==3
                    assert page.locator('.chart-plot').count()==1 and page.locator('.ranges button').count()==7
                    assert 'Vanguard S&P 500 ETF' in page.locator('.chart-identity').inner_text()
                    assert 'buys each' in page.locator('.backtest-summary').inner_text()
                    assert page.get_by_text('All upward crossings',exact=True).count()==1
                    assert 'random samples' in page.locator('.backtest').inner_text()
                    expect(page.get_by_role('button',name='Save',exact=True)).to_have_count(0)
                    import re
                    period=int(re.search(r'(\d+)-day',page.locator('.status').inner_text()).group(1))
                    reports[engine]=dict(target=4,period=period,horizon='Max',price=page.locator('.price').inner_text(),
                        ending_values=page.locator('.backtest-value strong').all_inner_texts(),
                        intro=True,status=True,chart=True,ranges=True,history=True,signals=True,
                        backtest=True,gains=True,random_stat=True,crossing_list=True)
                    assert period==expected.result.period
                    assert reports[engine]['ending_values']==[f'${getattr(expected.report,k).ending_value:,.0f}' for k in ('crossings','dca','random')]
                    for width in (320,390):
                        page.set_viewport_size({'width':width,'height':844})
                        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                        page.locator('.content').evaluate('(el)=>el.scrollTop=0')
                        page.screenshot(path=str(OUT/f'{engine}-{width}-top.png'))
                        page.locator('.backtest').scroll_into_view_if_needed()
                        page.screenshot(path=str(OUT/f'{engine}-{width}-backtest.png'))
                    page.get_by_role('button',name='Finish example',exact=True).click()
                    expect(page.get_by_text('No saved SMA lines yet',exact=True)).to_be_visible()
                    browser.close()
        finally:
            server.terminate()
            try:server.wait(timeout=5)
            except subprocess.TimeoutExpired:server.kill();server.wait()
    (OUT/'reference.json').write_text(json.dumps(reports,indent=2))
    native=ROOT/'artifacts/guide-ui/reference.json'
    if native.exists():
        reference=json.loads(native.read_text())
        for engine,value in reports.items():assert value==reference,(engine,value,reference)
    print('PASS: real Chromium/WebKit guide shows complete detail/backtest controls and matches native fixture values when its reference is present.')

if __name__=='__main__':main()
