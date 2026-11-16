"""Native controls for the shared frozen history-window contract."""
from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.metrics import dp,sp
from kivy.graphics import Line,Rectangle
from .appearance import Color
from .theme import BG,PRICE,ACCENT,CONTROL,TEXT,MUTED
from .history_window import label,preset,validate,bounds

class HistoryMini(Widget):
    def __init__(self,data,**kw):
        super().__init__(size_hint_y=None,height=dp(64),**kw)
        self.data=data;self.window=('','');self.bind(pos=self.draw,size=self.draw)
    def draw(self,*_):
        import math
        self.canvas.clear();prices=self.data.prices;good=[v for v in prices if v is not None and math.isfinite(v)]
        if not good:return
        low,high=min(good),max(good);points=[]
        with self.canvas:
            Color(*PRICE)
            for i,p in enumerate(prices):
                if p is None or not math.isfinite(p):
                    if len(points)>3:Line(points=points,width=dp(1))
                    points=[];continue
                points.extend((self.x+i/max(1,len(prices)-1)*self.width,self.y+(p-low)/max(.01,high-low)*self.height))
            if len(points)>3:Line(points=points,width=dp(1))
            try:left,right=bounds(self.data.dates,*self.window)
            except ValueError:return
            Color(*BG[:3],.8)
            x=self.x+left/max(1,len(prices)-1)*self.width
            r=self.x+right/max(1,len(prices)-1)*self.width
            Rectangle(pos=self.pos,size=(x-self.x,self.height));Rectangle(pos=(r,self.y),size=(self.right-r,self.height))

class HistoryUI:
    def build_history_controls(self):
        from .app import LabButton,WrappedLabel
        self.price_history_button=LabButton(text='Price history used · All available')
        self.detail_history_button=LabButton(text='Price history used · All available')
        for button in (self.price_history_button,self.detail_history_button):
            button.height=dp(64);button.bind(on_release=self.show_history_picker,
                size=lambda b,_:setattr(b,'text_size',(b.width-dp(20),None)))
        self.preference_body.add_widget(self.price_history_button,index=1)
        self.detail_signals.add_widget(self.detail_history_button)
        self.history_chart_caption=WrappedLabel(text='',color=MUTED,font_size=sp(11))
        self.plot_panel.add_widget(self.history_chart_caption)
        self.refresh_history_controls()

    def refresh_history_controls(self):
        if not hasattr(self,'price_history_button'):return
        model=self.model;data=model.dataset
        start,end=model.history_start,model.history_end
        text='Price history used'+(' · custom' if start else '')+'\n'+(label(start,end) if start else
            'All available'+(f' · {data.dates[0]} – {data.dates[-1]}' if data.dates else ''))
        for button in (self.price_history_button,self.detail_history_button):
            button.text=text;button.color=ACCENT if start else TEXT;button.disabled=self.busy or not data.dates
        stale=model.history_stale
        self.chart.opacity=.5 if stale else 1
        self.save_button.disabled=self.busy or model.result is None or stale
        result=model.result
        self.chart.history_window=(result.history_start,result.history_end) if result else ('','')
        self.chart.redraw()
        self.history_chart_caption.text=(f'Calculated from {label(result.history_start,result.history_end)} · dimmed prices were not used'
            if result and result.history_start else '')
        if stale:
            self.detail_summary.text='The period has changed'
            self.detail_note.text=f'The line below uses {label(result.history_start,result.history_end) or "all available history"}. Recalculate to match {label(start,end) or "all available history"}.'
            for button in (self.optimize_button,self.detail_optimize_button):button.text=f'Recalculate for {model.target_frequency} signals / year'
        elif result and result.history_start:
            self.detail_note.text=self.detail_note.text.replace('This line has been crossed upward about ',f'Between {result.history_start[:4]} and {result.history_end[:4]}, this line was crossed upward about ')

    def show_history_picker(self,*_):
        from .app import WrappedLabel,LabButton,CustomValueField
        from .navigation import BottomSheet
        data=self.model.dataset
        if not data.dates:return
        body=BoxLayout(orientation='vertical',size_hint_y=None,spacing=dp(6),padding=dp(12))
        body.bind(minimum_height=body.setter('height'))
        heading=BoxLayout(size_hint_y=None,height=dp(44),spacing=dp(8))
        heading.add_widget(WrappedLabel(text=f'{self.model.security(data.counter).ticker} · prices available from {data.dates[0]}',color=MUTED))
        cancel=LabButton(text='Cancel',size_hint_x=None,width=dp(70))
        cancel.bind(on_release=lambda *_:sheet.dismiss());heading.add_widget(cancel);body.add_widget(heading)
        mini=HistoryMini(data);body.add_widget(mini)
        self.history_presets={};self.history_draft=[self.model.history_start,self.model.history_end]
        fields=BoxLayout(size_hint_y=None,height=dp(72),spacing=dp(10))
        self.history_from=CustomValueField(text=self.model.history_start or data.dates[0],input_type='text',hint_text='YYYY-MM-DD')
        self.history_to=CustomValueField(text=self.model.history_end or data.dates[-1],input_type='text',hint_text='YYYY-MM-DD')
        for name,editor in (('From',self.history_from),('To',self.history_to)):
            column=BoxLayout(orientation='vertical',spacing=dp(4))
            column.add_widget(WrappedLabel(text=name));column.add_widget(editor);fields.add_widget(column)
            editor.bind(focus=self._editor_focus)
        readout=WrappedLabel(text='',color=MUTED);self.history_readout=readout
        apply=LabButton(text='Use this history',primary=True);self.history_apply=apply
        reset=LabButton(text='Use all available history');reset.fill=BG;reset.color=ACCENT;reset._draw()
        message=WrappedLabel(text='A saved line keeps these exact dates. They do not move forward over time.',color=MUTED)
        self._history_editing=False
        def refresh(*_):
            mini.window=tuple(self.history_draft);mini.draw()
            try:
                left,right=validate(data.prices,data.dates,*self.history_draft)
                readout.text=f'Uses {right-left+1:,} trading days, {label(data.dates[left],data.dates[right])}'
                readout.color=MUTED;apply.disabled=False
                for editor in (self.history_from,self.history_to):editor._paint_field()
            except ValueError as e:
                readout.text=str(e);from .theme import NEGATIVE
                readout.color=NEGATIVE;apply.disabled=True
                for editor in (self.history_from,self.history_to):editor.field_border_color.rgba=NEGATIVE
        def choose(value):
            self._history_editing=True
            if value=='Custom dates':
                self.history_draft=[self.history_from.text,self.history_to.text]
                if fields.parent is None:body.add_widget(fields,index=body.children.index(readout)+1)
            else:
                self.history_draft=list(preset(data.dates,value))
                if fields.parent is not None:body.remove_widget(fields)
                self.history_from.text=self.history_draft[0] or data.dates[0];self.history_to.text=self.history_draft[1] or data.dates[-1]
            self._history_editing=False
            from .theme import ACCENT_TINT
            for key,button in self.history_presets.items():
                button.color=ACCENT if key==value else TEXT
                button.fill=ACCENT_TINT if key==value else CONTROL
                button._draw()
            refresh()
        for value,title in ((None,'All available'),(10,'Last 10 years'),(5,'Last 5 years'),(3,'Last 3 years'),('Custom dates','Custom dates')):
            button=LabButton(text=title);button.bind(on_release=lambda _,v=value:choose(v));body.add_widget(button);self.history_presets[value]=button
        body.add_widget(readout);body.add_widget(message);body.add_widget(reset);body.add_widget(apply)
        reset.bind(on_release=lambda *_:choose(None))
        def edited(*_):
            if not self._history_editing:self.history_draft=[self.history_from.text,self.history_to.text];refresh()
        self.history_from.bind(text=edited);self.history_to.bind(text=edited)
        def use(*_):
            if apply.disabled:return
            self.model.set_history(*self.history_draft);self.refresh();sheet.dismiss()
        apply.bind(on_release=use)
        sheet=BottomSheet(self,body,title='Price history used',height_ratio=.95,max_height=dp(900));self.price_history_sheet=sheet
        sheet.open();choose('Custom dates' if self.model.history_start else None)

    def confirm_history_save(self):
        from .app import LabButton,WrappedLabel
        from .navigation import BottomSheet
        old=self.model.store.get_line(self.model.editing_line_id);result=self.model.result
        body=BoxLayout(orientation='vertical',size_hint_y=None,spacing=dp(12),padding=dp(16));body.bind(minimum_height=body.setter('height'))
        body.add_widget(WrappedLabel(text='You recalculated it with a different period. Choose what to do with the new result.'))
        self.history_save_buttons={}
        def save(update):
            try:
                self.model.save_current(update=update);sheet.dismiss();self.refresh();self.sync_notification_schedule()
            except (ValueError,RuntimeError) as error:self.message(str(error),True)
        for title,note,update in [('Update this line',f'Replaces {old.display_name} with SMA ({result.period} days) · {label(result.history_start,result.history_end) or "all available"}. Its name, colour and alerts stay.',True),('Save as a new line','Keeps both. The new line starts with alerts on.',False)]:
            button=LabButton(text=title,primary=update);button.bind(on_release=lambda _,u=update:save(u));body.add_widget(button);body.add_widget(WrappedLabel(text=note,color=MUTED));self.history_save_buttons[title]=button
        cancel=LabButton(text='Cancel');cancel.bind(on_release=lambda *_:sheet.dismiss());body.add_widget(cancel)
        sheet=BottomSheet(self,body,title='This line is already saved',height_ratio=.7);self.history_save_sheet=sheet;sheet.open()

class HistoryTag(Widget):
    """Neutral outlined exception label; never uses ABOVE/BELOW colours."""
    def __init__(self,text,**kw):
        from .appearance import Label
        super().__init__(size_hint=(None,None),height=dp(22),**kw)
        self.label=Label(text=text,color=MUTED,font_size=sp(11));self.add_widget(self.label)
        self.label.bind(texture_size=self.paint);self.bind(pos=self.paint,size=self.paint)
        self.paint()
    def paint(self,*_):
        self.width=max(dp(65),self.label.texture_size[0]+dp(12));self.label.pos=self.pos;self.label.size=self.size
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*MUTED);Line(rounded_rectangle=(self.x,self.y,self.width,self.height,dp(4)),width=dp(.7))
