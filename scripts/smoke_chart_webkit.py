"""WebKit presentation/inspection parity over controlled Python chart fixtures."""
import os
from pathlib import Path
import subprocess
import time
import urllib.request
from bisect import bisect_left
from datetime import date,timedelta
from playwright.sync_api import sync_playwright,expect
from sma_analyzer.mock_data import generate_mock_data
from sma_analyzer.version import APP_VERSION
from web.python.browser import calculate

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/chart-webkit'

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    sample=generate_mock_data('DEMO-US','Oscillating',sessions=900)
    security=dict(key='YAHOO:VOO',ticker='VOO',symbol='VOO',name='Vanguard S&P 500 ETF',region='US',exchange='US',currency='USD',timezone='America/New_York',logo_url='/logos/vanguard.png')
    lines=[dict(id=1,counter=security['key'],period=50,target_frequency=12,name='Quick swing',visible=True,color_hex='#66C2FF',push_enabled=False),dict(id=2,counter=security['key'],period=200,target_frequency=4,name='Long-term trend',visible=True,color_hex='#FFBD5C',push_enabled=False)]
    data=dict(security=security,prices=sample.prices,dates=sample.dates,currency='USD',scenario='Yahoo EOD',preview=False,stale=False)
    chart=calculate(dict(data=data,lines=lines,period=200,target=4))
    card=dict(counter=security['key'],security=security,price=sample.prices[-1],change=1.2,lines=lines,states={'1':'Above','2':'Above'},below=0)
    state=dict(version=APP_VERSION,cards=[card],archive=[],settings={},colors=[],preview=False)
    env={**os.environ,'APP_PASSWORD':'webkit-fixture','AUTH_SECRET':'webkit-fixture-secret'}
    with (OUT/'server.log').open('w') as log:
        server=subprocess.Popen(['node','node_modules/next/dist/bin/next','start','--hostname','127.0.0.1','--port','3188'],cwd=ROOT/'web',env=env,stdout=log,stderr=log)
        try:
            for _ in range(100):
                try:urllib.request.urlopen('http://127.0.0.1:3188',timeout=1);break
                except OSError:time.sleep(.2)
            with sync_playwright() as p:
                options={'executable_path':os.environ['SMA_WEBKIT_EXECUTABLE']} if os.environ.get('SMA_WEBKIT_EXECUTABLE') else {}
                browser=p.webkit.launch(**options)
                context=browser.new_context(viewport={'width':390,'height':844},device_scale_factor=2,is_mobile=True,has_touch=True,color_scheme='dark',locale='en-US',service_workers='block')
                page=context.new_page();page.set_default_timeout(20000)
                errors=[];calls=[]
                page.on('pageerror',lambda error:errors.append(str(error)))
                def respond(route):
                    path=route.request.url.split('/api/',1)[-1];calls.append(path)
                    values={'session':{'storage':'worker'},'state':state,'chart':chart,'contact-capabilities':{'enabled':False},'login':{'ok':True}}
                    route.fulfill(json=values.get(path,{}))
                page.route('**/api/**',respond)
                page.goto('http://127.0.0.1:3188')
                page.get_by_role('button',name='Vanguard S&P 500 ETF').click()
                page.get_by_role('button',name='Long-term trend').click()
                expect(page.locator('.chart-identity')).to_contain_text(security['name'])
                expect(page.locator('.chart-identity img')).to_have_attribute('src','/logos/vanguard.png')
                expect(page.locator('.price')).to_have_text(f'${sample.prices[-1]:,.2f}')
                page.evaluate('document.fonts.ready')
                assert page.evaluate('document.fonts.check("700 14px Manrope")')
                plot=page.locator('.chart-plot');plot.scroll_into_view_if_needed()
                start=bisect_left(sample.dates,(date.fromisoformat(sample.dates[-1])-timedelta(days=365)).isoformat())
                end=len(sample.prices)-1
                for line in chart['lines']:
                    markers=[event['position'] if event['position'] is not None else event['index'] for event in line['events'] if start<=(event['position'] if event['position'] is not None else event['index'])<=end]
                    expect(plot.locator(f'[data-crossing="saved-{line["id"]}"]')).to_have_count(len(markers))
                    actual=plot.locator(f'[data-crossing="saved-{line["id"]}"]').evaluate_all('(nodes)=>nodes.map(node=>Number(node.dataset.position))')
                    assert actual==markers
                box=plot.bounding_box();scale=box['width']/640
                def point(fraction):return box['x']+(68+550*fraction)*scale,box['y']+185*scale
                page.evaluate('''document.querySelector('.chart-plot').addEventListener('pointerdown',e=>window.chartPointerX=e.clientX);
                    document.querySelector('.chart-plot').addEventListener('pointermove',e=>window.chartPointerX=e.clientX);''')
                page.touchscreen.tap(*point(.6))
                # WebKit quantizes touch positions to device pixels. Compare
                # native session selection against the actual dispatched point.
                fraction=(page.evaluate('window.chartPointerX')-box['x']-68*scale)/(550*scale)
                index=round(start+fraction*(end-start))
                inspection=page.locator('.chart-inspection')
                expect(inspection).to_contain_text(f'Adj. close: ${sample.prices[index]:,.4f}')
                for line in chart['lines']:
                    expect(inspection).to_contain_text(f'{line["name"]}: ${line["sma"][index]:,.4f}')
                # The same pointer-move path updates under WebKit; native touch tap
                # above verifies WebKit's touch/pointer capture interoperability.
                page.mouse.move(*point(.25));page.mouse.down();page.mouse.move(*point(.8),steps=10);page.mouse.up()
                fraction=(page.evaluate('window.chartPointerX')-box['x']-68*scale)/(550*scale)
                index=round(start+fraction*(end-start))
                expect(inspection).to_contain_text(f'Long-term trend: ${chart["result"]["sma"][index]:,.4f}')
                page.screenshot(path=str(OUT/'inspection.png'))
                price_path=plot.locator('[data-series="price"]')
                assert price_path.evaluate('(el)=>getComputedStyle(el).stroke')=='rgb(77, 222, 196)'
                page.evaluate('document.documentElement.dataset.theme="light"')
                assert price_path.evaluate('(el)=>getComputedStyle(el).stroke')=='rgb(8, 127, 140)'
                page.screenshot(path=str(OUT/'inspection-light.png'))
                page.evaluate('document.documentElement.dataset.theme="dark"')
                for width in (320,390,430):
                    page.set_viewport_size({'width':width,'height':844})
                    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                    page.locator('.content').evaluate('(el)=>el.scrollTop=0')
                    page.screenshot(path=str(OUT/f'chart-{width}.png'))
                for label in ('3M','1Y','Max'):
                    page.locator('.ranges').get_by_role('button',name=label,exact=True).click()
                    expect(page.locator('.ranges').get_by_role('button',name=label,exact=True)).to_have_attribute('aria-pressed','true')
                assert calls.count('chart')==1,calls
                assert not errors,errors
                browser.close()
            print('PASS: WebKit actual touch capture, close and multiple-SMA inspection, dragged pointer updates, Python fractional crossing pluses, native logos/fonts, dollar prices, both teal themes and 320/390/430 layouts; fixtures only.')
        finally:
            server.terminate()
            try:server.wait(timeout=5)
            except subprocess.TimeoutExpired:server.kill();server.wait()

if __name__=='__main__':main()
