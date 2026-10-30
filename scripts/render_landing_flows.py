"""Render the standalone SVG landing-flow design boards (no runtime dependency)."""
from html import escape
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / "docs" / "design"
THEMES = (
    dict(key="calm-home", name="Calm home", subtitle="One clear first action. Saved lines come forward when you return.",
         bg="#F7F8F3", card="#EAF0E9", ink="#203B32", muted="#61756C", accent="#28664F", light="#DDEEE3",
         stages=("First visit", "Choose a security", "Simple parameters", "Understand & save", "Return to your lines"),
         screens=("home", "search", "parameters", "results", "return"), arrows=("Start", "Select", "Analyze", "Home")),
    dict(key="guided-example", name="Learn with an example", subtitle="An optional three-step sample teaches the idea before the first personal analysis.",
         bg="#FAF8FE", card="#EEE9F8", ink="#342653", muted="#776B8C", accent="#7053AB", light="#E8DFF9",
         stages=("A friendly invitation", "Optional worked example", "Make it yours", "Understand & save", "Skip the lesson on return"),
         screens=("welcome", "demo", "parameters", "results", "return"), arrows=("Try it", "Ready", "Analyze", "Home")),
    dict(key="library-first", name="Library first", subtitle="The same home grows from a helpful empty state into a fast personal library.",
         bg="#131F31", card="#1F3048", ink="#EFF6FF", muted="#B2C2D7", accent="#83DDD0", light="#263F4C",
         stages=("A useful empty library", "Find your security", "Simple parameters", "Understand & save", "Your library, populated"),
         screens=("empty", "search", "parameters", "results", "return"), arrows=("New", "Select", "Analyze", "Home")),
)


class Board:
    def __init__(self, theme, number):
        self.t, self.number = theme, number
        self.parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="1720" height="1120" viewBox="0 0 1720 1120" role="img">',
                      f'<title>{escape(theme["name"])}: first launch and returning-user flow</title>',
                      '<desc>Five connected mobile wireframes, a direct saved-line return path, and contextual learning notes.</desc>',
                      '<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0 0L8 4L0 8" fill="#82958B"/></marker></defs>']
        self.rect(0,0,1720,1120,"#F1F3F0",0)

    def rect(self,x,y,w,h,fill,r=12,stroke="none"):
        self.parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{stroke}"/>')

    def text(self,x,y,value,size=14,color=None,bold=False):
        self.parts.append(f'<text x="{x}" y="{y}" fill="{color or self.t["ink"]}" font-family="DejaVu Sans,Arial,sans-serif" font-size="{size}" font-weight="{700 if bold else 400}">{escape(value)}</text>')

    def lines(self,x,y,values,size=14,color=None,bold=False,step=None):
        for n,value in enumerate(values):
            self.text(x,y+n*(step or size*1.5),value,size,color,bold)

    def button(self,x,y,value,secondary=False,w=224):
        self.rect(x,y,w,42,self.t["card"] if secondary else self.t["accent"],10)
        self.text(x+14,y+26,value,13,self.t["ink"] if secondary else self.t["bg"],True)

    def identity(self,x,y,name="Apple Inc.",ticker="AAPL",small=False):
        edge=24 if small else 30
        self.rect(x,y,edge,edge,"#FFFFFF",7)
        self.text(x+6,y+edge*.67,"AP" if name.startswith("Apple") else "MS",10,"#243831",True)
        self.text(x+edge+8,y+edge*.65,name,11 if small else 12,self.t["ink"],True)
        if ticker:
            self.text(x+181,y+edge*.65,ticker,10,self.t["muted"])

    def chart(self,x,y,w=224,h=118):
        self.rect(x,y,w,h,self.t["card"],10)
        for offset in (.25,.5,.75):
            self.parts.append(f'<path d="M{x+10} {y+h*offset}H{x+w-10}" stroke="{self.t["muted"]}" opacity=".12"/>')
        prices=[.7,.76,.62,.65,.51,.6,.64,.46,.53,.32,.37,.25,.36,.18]
        average=[.75,.73,.7,.67,.64,.62,.59,.56,.53,.49,.45,.41,.37,.33]
        for points,color in ((average,"#C69A43"),(prices,self.t["accent"])):
            coords=" ".join(f'{x+12+n*(w-24)/(len(points)-1)},{y+12+p*(h-24)}' for n,p in enumerate(points))
            self.parts.append(f'<polyline points="{coords}" fill="none" stroke="{color}" stroke-width="2.5"/>')

    def phone(self,x,index,screen):
        t=self.t; y=216
        self.text(x,y-23,f'{index+1:02}  {t["stages"][index]}',13,"#53665D",True)
        self.rect(x+3,y+7,264,550,"#DEE4DD",25)
        self.rect(x,y,264,550,t["bg"],25,"#C5D0C5")
        self.rect(x+104,y+12,56,5,t["muted"],3)
        self.text(x+20,y+44,"SMA",12,t["ink"],True)
        self.text(x+146,y+44,"SIMULATED DEMO",8,t["muted"])
        a,b=x+20,y+80
        if screen in ("home","welcome","empty"):
            if screen=="home":
                self.lines(a,b,["Find your", "moving average."],24,bold=True,step=31)
                self.lines(a,b+78,["Smooth a stock's daily prices.","Start with one security."],12,t["muted"])
                self.chart(a,b+132,h=112)
                self.button(a,b+270,"Start an analysis")
                self.button(a,b+322,"Try a sample",True)
                self.text(a+12,b+396,"What is an SMA?  ·  2 min",11,t["accent"],True)
            elif screen=="welcome":
                self.lines(a,b,["See one crossover.","Then try your own."],21,bold=True,step=30)
                self.lines(a,b+85,["A moving average smooths prices.","See how it works, one step at a time."],11,t["muted"])
                self.chart(a,b+140,h=110)
                self.button(a,b+275,"Try the guided example")
                self.button(a,b+327,"Choose my own security",True)
                self.text(a,b+397,"Optional. No account or quiz.",11,t["muted"])
            else:
                self.text(a,b,"My SMA library",23,bold=True)
                self.rect(a,b+38,224,175,t["card"],16)
                self.lines(a+18,b+85,["Your first line", "starts here."],22,bold=True,step=30)
                self.text(a+18,b+164,"Keep the averages you want to follow.",10,t["muted"])
                self.button(a,b+242,"New analysis")
                self.rect(a,b+308,224,88,t["light"],12)
                self.text(a+14,b+336,"New to moving averages?",12,bold=True)
                self.text(a+14,b+364,"See a worked example  →",11,t["accent"],True)
        elif screen=="search":
            self.lines(a,b,["Choose a", "security"],24,bold=True,step=30)
            self.text(a,b+82,"Ticker or company name",11,t["muted"])
            self.rect(a,b+100,224,42,t["card"],10)
            self.text(a+12,b+126,"a",13)
            self.text(a+156,b+126,"Search",12,t["accent"],True)
            self.text(a,b+167,"Matches after Enter or Search",10,t["muted"])
            for n,(company,ticker) in enumerate((("Apple Inc.","AAPL"),("Microsoft Corp.","MSFT"))):
                self.rect(a,b+190+n*70,224,58,t["card"],10)
                self.identity(a+10,b+204+n*70,company,ticker,True)
            self.lines(a,b+380,["Select a match to load its history.","No searching while you type."],11,t["muted"])
        elif screen=="parameters":
            self.text(a,b,"Set your preference",19,bold=True)
            self.text(a,b+35,"1 security. 1 simple choice.",11,t["muted"])
            self.rect(a,b+61,224,55,t["card"],10)
            self.identity(a+10,b+74,ticker="")
            self.text(a,b+152,"Upward crossings / year",12,bold=True)
            self.parts.append(f'<circle cx="{a+213}" cy="{b+148}" r="6" fill="none" stroke="{t["muted"]}"/>')
            self.text(a+211.5,b+151,"i",9,t["muted"],True)
            self.lines(a,b+179,["How often price moves from below", "to above its moving average."],11,t["muted"])
            for n,value in enumerate(("1","6","12")):
                self.rect(a+n*76,b+225,68,42,t["accent"] if value=="12" else t["card"],10)
                self.text(a+n*76+25,b+251,value,14,t["bg"] if value=="12" else t["ink"],True)
            self.text(a,b+306,"Advanced options                         +",11,t["muted"])
            self.button(a,b+355,"Find my SMA")
            self.text(a,b+424,"Optimizes frequency, not returns.",10,t["muted"])
        elif screen=="demo":
            self.text(a,b,"A crossover, explained",18,bold=True)
            self.text(a,b+35,"EXAMPLE  ·  1 OF 3",10,t["accent"],True)
            self.chart(a,b+65,h=158)
            self.lines(a,b+257,["When price rises through the average,", "that is an upward crossing."],11)
            self.lines(a,b+309,["Next: choose how often you want", "those crossings to happen."],11,t["muted"])
            self.button(a,b+370,"I am ready to try")
            self.text(a+13,b+424,"Skip example  ·  Help anytime",10,t["muted"])
        elif screen=="results":
            self.text(a,b,"Your moving average",19,bold=True)
            self.text(a,b+35,"EXAMPLE RESULT",10,t["muted"])
            self.text(a,b+82,"51",38,t["accent"],True)
            self.text(a+64,b+81,"sessions",14,t["muted"])
            self.chart(a,b+107,h=137)
            self.text(a,b+265,"Drag: inspect  ·  Pinch: zoom",10,t["muted"])
            self.button(a,b+294,"♡  Save SMA")
            self.button(a,b+346,"Compare strategies     +",True)
            self.text(a,b+417,"Tip: inspect a point to learn more",11,t["muted"])
        elif screen=="return":
            self.text(a,b,"My SMA library" if self.number==3 else "Welcome back",23,bold=True)
            self.text(a,b+35,"Your saved lines are one tap away.",11,t["muted"])
            self.button(a,b+62,"+  New analysis")
            self.text(a,b+137,"SAVED SMAs",10,t["muted"],True)
            self.rect(a,b+155,224,143,t["light"],12)
            self.identity(a+10,b+168,"Apple Inc.","AAPL",True)
            self.text(a+14,b+225,"SMA 51",12,bold=True)
            self.text(a+172,b+225,"View",12,t["accent"],True)
            self.text(a+14,b+269,"SMA 100",12)
            self.text(a+172,b+269,"View",12,t["accent"],True)
            self.rect(a,b+310,224,55,t["card"],12)
            self.identity(a+10,b+325,"Microsoft Corp.","MSFT",True)
            self.text(a,b+415,"View opens the exact saved line.",10,t["muted"])
        self.text(x+23,y+523,"Home",10,t["accent"],True)
        self.text(x+112,y+523,"Saved",10,t["muted"])
        self.text(x+206,y+523,"Learn",10,t["muted"])

    def render(self):
        t=self.t
        self.text(56,50,"SMA  /  LANDING EXPERIENCE EXPLORATION",12,"#61746A",True)
        self.text(56,100,f'{self.number:02}  {t["name"]}',34,"#203B32",True)
        self.text(56,133,t["subtitle"],17,"#61746A")
        if self.number==1:
            self.rect(1434,60,230,35,"#DAEBDD",17)
            self.text(1452,83,"RECOMMENDED DIRECTION",12,"#28664F",True)
        for index,screen in enumerate(t["screens"]):
            self.phone(56+index*336,index,screen)
            if index<4:
                start=56+index*336+264
                self.parts.append(f'<path d="M{start+12} 489H{start+59}" fill="none" stroke="#82958B" stroke-width="2" marker-end="url(#arrow)"/>')
                self.text(start+14,470,t["arrows"][index],10,"#61746A",True)
        self.parts.append('<path d="M1532 782V850H1196V782" fill="none" stroke="#82958B" stroke-width="2" stroke-dasharray="6 5" marker-end="url(#arrow)"/>')
        self.rect(1042,860,622,38,"#E5EDE4",10)
        self.text(1060,885,"RETURNING USER  ·  Saved View goes directly to Results",14,"#345C49",True)
        notes=(
            ("01 / Let people start",("A single primary action, an optional sample,", "and no mandatory tour or account setup.")),
            ("02 / Teach at the decision",("Explain SMA before analysis and crossing frequency", "beside its control. Keep advanced detail folded.")),
            ("03 / Make the second visit easier",("Show saved company groups on Home. View restores", "the exact line; Learn remains available anytime.")),
        )
        for n,(title,lines) in enumerate(notes):
            x=56+n*548
            self.rect(x,943,512,104,"#FFFFFF",14,"#DEE5DC")
            self.text(x+18,972,title,15,"#203B32",True)
            self.lines(x+18,999,lines,12,"#61746A",step=21)
        self.text(56,1088,"DESIGN CONCEPT ONLY  ·  Not included in APK 0.6.0  ·  Example values and simulated data",12,"#61746A")
        self.parts.append('</svg>')
        return "\n".join(self.parts)+"\n"


def main():
    ROOT.mkdir(parents=True,exist_ok=True)
    html=(ROOT.parents[1]/'scripts'/'landing_flow_template.html').read_text()
    for n,theme in enumerate(THEMES,1):
        target=ROOT/(theme['key']+'.svg')
        svg=Board(theme,n).render()
        target.write_text(svg)
        html=html.replace('{{'+theme['key']+'}}',svg)
        print(target.relative_to(ROOT.parents[1]))
    (ROOT/'landing-flow-options.html').write_text(html)


if __name__=="__main__":
    main()
