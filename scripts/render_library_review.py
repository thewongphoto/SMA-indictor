"""Build full-app review boards from captured unreleased Kivy screens.

Only uses published design inputs; it does not import unreleased app modules.
Run after placing the PNG captures in docs/design/library-first-review/screens.
"""
import base64
from html import escape
from pathlib import Path
import textwrap

ROOT=Path(__file__).resolve().parents[1]/"docs"/"design"/"library-first-review"
INK="#20384a"; MUTED="#607789"; ACCENT="#238b7b"; DARK="#131f31"


class Canvas:
    def __init__(self,w,h,title):
        self.w,self.h=w,h
        self.p=[f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img"><title>{escape(title)}</title>',
          '<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0 0L8 4L0 8" fill="#328a7c"/></marker></defs>']
        self.rect(0,0,w,h,"#f1f5f4",0)
    def rect(self,x,y,w,h,color,r=14,stroke="none"):
        self.p.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{color}" stroke="{stroke}"/>')
    def text(self,x,y,text,size=15,color=INK,bold=False):
        self.p.append(f'<text x="{x}" y="{y}" font-family="DejaVu Sans,Arial,sans-serif" font-size="{size}" font-weight="{700 if bold else 400}" fill="{color}">{escape(str(text))}</text>')
    def lines(self,x,y,lines,size=15,color=MUTED,step=24):
        for n,line in enumerate(lines):self.text(x,y+n*step,line,size,color)
    def arrow(self,path,dashed=False):
        self.p.append(f'<path d="{path}" fill="none" stroke="#328a7c" stroke-width="2" marker-end="url(#arrow)"'+(' stroke-dasharray="7 5"' if dashed else '')+'/>')
    def node(self,x,y,w,h,title,lines):
        self.rect(x+2,y+5,w,h,"#dce7e3")
        self.rect(x,y,w,h,"#ffffff",14,"#c8d9d1")
        self.rect(x,y,w,40,DARK,12)
        self.text(x+16,y+27,title,16,"#eaf6f3",True)
        self.lines(x+16,y+68,lines,14,step=23)
    def finish(self):return '\n'.join(self.p+['</svg>'])+'\n'


def overview():
    c=Canvas(1600,1600,"Library-first full application flow — unreleased review")
    c.text(55,48,"SMA / SELECTED LIBRARY-FIRST DESIGN",13,MUTED,True)
    c.text(55,92,"The whole app, from launch to returning to a saved line",29,INK,True)
    c.text(55,125,"Unreleased review · 3 November 2026 · simulated prices · fixed top controls · no Home / Saved / Learn bottom bar",15,MUTED)
    c.rect(590,158,420,45,DARK)
    c.text(612,187,"Launch → Are any SMAs saved on this device?",15,"#eaf6f3",True)
    c.arrow('M650 203V225H350V250');c.text(365,240,"NO",12,ACCENT,True)
    c.arrow('M950 203V225H1250V250');c.text(1265,240,"YES",12,ACCENT,True)
    c.node(100,250,500,180,"01 / First visit — empty library",[
      "First card: New to moving averages and upward",
      "crossing buy signals? → guided example",
      "New analysis → security search",
      "Recently unsaved → archive; gear → Settings"])
    c.node(1000,250,500,180,"05 / Returning visit — populated library",[
      "Always the launch state when at least one SMA exists.",
      "Logo / company / ticker groups expand into saved lines.",
      "View → exact saved chart; New analysis → search.",
      "Heart / Hide / phone controls; history → archive."])
    c.arrow('M300 430V560');c.text(315,500,"New analysis",14,ACCENT,True)
    c.arrow('M1200 430V480H300',True);c.text(790,467,"New analysis",14,ACCENT,True)
    c.arrow('M1430 430V520H1325V560');c.text(1442,485,"View",14,ACCENT,True)
    c.node(100,560,350,190,"02 / Choose a security",[
      "Partial ticker / company query.","Enter or Submit → local matches.",
      "Logo / ticker / name → select.","No-match / failure → retry here.","Typing alone makes no request."])
    c.node(600,560,350,190,"03 / Parameters + Custom",[
      "Company logo and name.","Target upward crossings / year.",
      "Custom expands simulation settings.","Optimize; invalid input stays here.","Loading disables conflicting actions."])
    c.node(1100,560,350,190,"04 / Results",[
      "Company logo/name; exact SMA.","1Y / 3Y / 5Y / Max chart ranges.",
      "One finger: EOD/date/SMA popup.","Two fingers: pinch zoom; Zoom out.","Save / Hide / Change parameters."])
    c.arrow('M450 650H600');c.text(470,620,"Select match",13,ACCENT,True);c.text(470,640,"load history",12,MUTED)
    c.arrow('M950 650H1100');c.text(972,635,"Optimize",14,ACCENT,True)
    c.arrow('M1220 750V800H775V750');c.text(800,788,"Change parameters",13,ACCENT,True)
    c.arrow('M100 335H48V990H100');c.text(58,925,"Guide",12,ACCENT,True)
    c.node(100,920,350,195,"06 / Guided example",[
      "Three-year chart with many crossings.","Recovery may follow; losses can too.",
      "SMA lag / false signals explained.","Frequency → real sample SMA +", "$100-per-buy investment comparisons.","Choose own security → Search."])
    c.arrow('M275 920V750');c.text(287,860,"Choose own",13,ACCENT,True)
    c.node(600,920,350,195,"07 / Saved SMA sheet",[
      "Same company groups as Library.","View restores exact period/target.","Hide/Show changes chart visibility.",
      "Phone On/Off; heart → unsave.","Swipe / backdrop / Back dismisses.","Library button returns to launch view."])
    c.arrow('M1160 750V850H775V920');c.text(794,841,"Save / Saved SMAs menu",13,ACCENT,True)
    c.node(1100,920,350,195,"08 / Backtesting in Results",[
      "1Y / 3Y / 5Y / Max / Custom years.","a. N upward-crossing buys",
      "b. N equal-period (DCA) buys",
      "c. N random buys: 500-sample mode",
      "Ending values, b/c % vs a; info help.","View all upward crossings → details."])
    c.arrow('M1375 750V920');c.text(1390,865,"Scroll",13,ACCENT,True)
    c.node(100,1240,350,190,"09 / Phone Settings",[
      "Gear from Library or Results.","Phone buy / monitor preferences.","Test EOD preview + permission test.",
      "Allow / deny → clear status; retry.","Back returns to the prior screen.","Email functionality stays removed."])
    c.node(600,1240,350,190,"10 / Recently unsaved archive",[
      "Last 10 unsaved configurations.","Small company logo and name.","Restore → saved library, exact SMA.",
      "Original visibility / phone flags kept.","Last unsave → empty Library state.","Close / Back returns to prior view."])
    c.node(1100,1240,350,190,"11 / All upward crossings",[
      "Full event list for the selected SMA.","Estimated crossing price and SMA.","Scrollable details remain separate.",
      "Back returns to the same Results.","DCA / random info dialogs dismiss", "without changing the comparison."])
    c.arrow('M550 430V445H28V1330H100');c.text(38,1210,"Gear",12,ACCENT,True)
    c.arrow('M775 1115V1240');c.text(791,1180,"History / restore",13,ACCENT,True)
    c.arrow('M1325 1115V1240');c.text(1340,1180,"Details",13,ACCENT,True)
    c.arrow('M775 1430V1485H1550V340H1500',True)
    c.text(1020,1515,"Restore → populated Library with exact saved parameters",14,ACCENT,True)
    c.text(55,1565,"Back closes help/keyboard/sheets first, then returns along the page stack. The optimizer matches frequency, not investment profit.",14,MUTED)
    return c.finish()


BOARDS=(
 ('01-start-and-learn','Start with a quiet library; learn only when you choose',
  [('empty','01 / Empty library'),('guide','06 / Three-year guide'),('search','02 / Submitted search'),('parameters','03 / Parameters')],
  ['No saved lines: the introductory sample is the first card. At least one save: launch directly into the populated library.',
   'The guide shows recoveries and false crossings, states that losses can follow a buy, and uses the actual comparison engine.',
   'Search requires Enter/Submit. Select a match to load history, then set frequency. Custom replaces Advanced options.']),
 ('02-analyze-and-compare','Inspect the selected company, then compare its chosen frequency',
  [('results','04 / Results'),('backtest','08 / Investment comparisons'),('help','08a / Random-sample help'),('crossovers','11 / All crossings')],
  ['The chart heading is the company logo followed by its name. Inspect with one finger; pinch with two; quick ranges remain.',
   'Backtesting retains $100 per buy, equal buy counts, DCA and the most common of 500 random scenarios, with ending-value deltas.',
   'Comparison help and all-crossing details return to the same analysis. Matching crossing frequency is not profit optimization.']),
 ('03-save-and-return','Keep every saved line easy to find, restore and control',
  [('populated','05 / Populated library'),('saved-sheet','07 / Saved SMA sheet'),('archive','10 / Recently unsaved'),('settings','09 / Phone Settings')],
  ['Populated Library is the launch state whenever saved SMAs exist. View opens the exact line directly without optimization.',
   'Company groups and View / Hide / heart / phone controls are shared. Unsave enters the archive; Restore preserves exact settings.',
   'Settings and Saved SMAs use top controls. There is no Home / Saved / Learn bottom bar. No email controls or live data are added.'])
)


def storyboard(title,items,notes):
    c=Canvas(1600,1200,title)
    c.text(50,50,"SMA / LIBRARY-FIRST UNRELEASED REVIEW",13,MUTED,True)
    c.text(50,95,title,28,INK,True)
    c.text(50,130,"Actual desktop Kivy captures · 440 × 920 phone layout · simulated data · proposal only, no APK release",15,MUTED)
    for n,(key,label) in enumerate(items):
        x=50+n*390
        c.text(x,181,label,16,INK,True)
        c.rect(x-4,200,354,744,"#cad9d3",22)
        data=base64.b64encode((ROOT/'screens'/(key+'.png')).read_bytes()).decode()
        c.p.append(f'<image x="{x}" y="204" width="346" height="724" preserveAspectRatio="xMidYMin meet" xlink:href="data:image/png;base64,{data}"/>')
    for n,note in enumerate(notes):
        c.rect(50,981+n*62,1516,52,"#ffffff",10)
        c.text(66,1012+n*62,note,15,MUTED)
    c.text(50,1182,"Full navigation and return paths are shown in full-app-flow.png. Individual screens are available at full resolution.",13,MUTED)
    return c.finish()


def main():
    ROOT.mkdir(parents=True,exist_ok=True)
    (ROOT/'full-app-flow.svg').write_text(overview())
    for name,title,items,notes in BOARDS:
        (ROOT/(name+'.svg')).write_text(storyboard(title,items,notes))
    # One self-contained reviewer: snapshots and linked routes, not a second app.
    titles={key:title for _,_,items,_ in BOARDS for key,title in items}
    titles['custom']='03a / Custom expanded'
    routes={
      'empty':[('Guided example','guide'),('New analysis','search'),('Recently unsaved','archive'),('Settings','settings')],
      'populated':[('View saved line','results'),('New analysis','search'),('Saved controls','saved-sheet'),('History','archive'),('Settings','settings'),('Guide','guide')],
      'guide':[('Choose my own security','search'),('Return to Library','library')],
      'search':[('Select Apple match','parameters'),('Back to Library','library')],
      'parameters':[('Open Custom','custom'),('Optimize SMA','results'),('Change security','search')],
      'custom':[('Close Custom','parameters'),('Optimize SMA','results')],
      'results':[('Save SMA','save'),('Comparisons','backtest'),('Saved SMAs','saved-sheet'),('Library','library'),('Change parameters','parameters'),('Settings','settings')],
      'backtest':[('Random explanation','help'),('All crossings','crossovers'),('Chart','results')],
      'help':[('Close help','backtest')], 'crossovers':[('Back to Results','results')],
      'saved-sheet':[('View line','results'),('Unsave example line','unsave'),('History','archive'),('Library','library')],
      'archive':[('Restore exact line','restore'),('Close','library')],
      'settings':[('Back to Library','library'),('Back to Results','results')]
    }
    images={key:base64.b64encode((ROOT/'screens'/(key+'.png')).read_bytes()).decode() for key in titles}
    import json
    html='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SMA library-first whole-app review</title>
<style>*{box-sizing:border-box}body{margin:0;background:#eef3f1;color:#20384a;font:15px/1.5 system-ui,sans-serif}header,main,footer{max-width:1200px;margin:auto;padding:26px}h1{font-size:34px;line-height:1.2}p{color:#607789}button{cursor:pointer;background:#203c49;border:0;color:#ecfff8;border-radius:9px;padding:10px 14px;font:inherit;margin:4px}button:focus-visible{outline:3px solid #238b7b;outline-offset:2px}section{display:grid;grid-template-columns:1fr 390px;gap:35px;align-items:start}#phone{display:block;width:100%;border:8px solid #cfddd7;border-radius:22px}#routes{display:flex;flex-wrap:wrap}figure{margin:32px 0}figure svg{width:100%;height:auto}summary{cursor:pointer}small{color:#607789}.pill{display:inline-block;padding:6px 12px;background:#dcebe4;border-radius:20px;font-size:12px}a{color:#1a786b}@media(max-width:800px){section{grid-template-columns:1fr}#phone{max-width:390px;margin:auto}header,main,footer{padding:18px}}</style>
<header><span class="pill">Approved UI review · 3 November 2026 · application release 0.7.0</span><h1>Library first — the complete app flow</h1><p>The first card introduces moving averages and upward crossing buy signals. Saved lines lead returning users directly to their charts. No bottom tab bar.</p><button id="first">First visit: no saved SMAs</button><button id="return">Returning user: saved SMAs exist</button><a href="#overview">Full navigation map ↓</a></header>
<main><section><div><h2 id="title"></h2><p>Review navigation is outside the app image. Use these buttons to inspect every route; the screenshots show the local Kivy implementation.</p><div id="routes"></div><p id="note"></p><small>This reviewer uses captured states, not live calculations or storage. Saving, restoring and phone permission behavior are exercised in the native preview. Real return navigation follows the page from which each screen was opened.</small></div><img id="phone" alt="Selected unreleased Kivy screen"></section><div id="overview"></div></main>
<footer><p>The approved application and tests are published for version 0.7.0. Images retain their pre-release review labels. Package identity and signing settings are preserved; prices remain simulated.</p></footer>
<script>const images=IMAGES,titles=TITLES,routes=ROUTES;let hasSaved=false;function show(key){if(key==='save'){hasSaved=true;key='saved-sheet';}if(key==='unsave'){hasSaved=false;key='archive';}if(key==='restore'){hasSaved=true;key='populated';}if(key==='library')key=hasSaved?'populated':'empty';document.getElementById('phone').src='data:image/png;base64,'+images[key];document.getElementById('title').textContent=titles[key];document.getElementById('routes').replaceChildren(...routes[key].map(([text,target])=>{const b=document.createElement('button');b.textContent=text;b.onclick=()=>show(target);return b;}));document.getElementById('note').textContent=key==='guide'?'Three simulated years, multiple crossing frequencies and comparisons; possible recovery and false signals are both explained.':key==='empty'?'No saved SMAs: show page 01. The guide is the first cell.':key==='populated'?'At least one saved SMA: always launch into page 05. View restores exact saved parameters.':'';}document.getElementById('first').onclick=()=>{hasSaved=false;show('library');};document.getElementById('return').onclick=()=>{hasSaved=true;show('library');};show('library');</script></html>'''
    html=html.replace('</style>','svg{max-width:100%;height:auto}section>*{min-width:0}</style>')
    html=html.replace('IMAGES',json.dumps(images)).replace('TITLES',json.dumps(titles)).replace('ROUTES',json.dumps(routes))
    flow=overview()
    html=html.replace('<div id="overview"></div>','<div id="overview"><h2>Complete navigation map</h2>'+flow+'</div>')
    (ROOT/'whole-app-review.html').write_text(html)


if __name__=='__main__':main()
