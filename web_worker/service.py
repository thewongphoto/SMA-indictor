"""Reuse the Android model in a dedicated single-user worker with durable storage.

Run on a persistent host, not inside a Vercel function. The Next.js server
authenticates the browser and forwards a server-only bearer credential here.
"""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from pathlib import Path
from threading import Event, RLock
import json
import secrets
import time

from sma_analyzer.model import AnalyzerModel
from sma_analyzer.storage import LineStore
from sma_analyzer.providers import create_provider
from sma_analyzer.engine import optimize_sma
from sma_analyzer.backtest import compare_investments, period_sessions
from sma_analyzer.watchlist import watchlist, line_state
from sma_analyzer.palette import COLOR_NAMES, COLOR_CHOICES, line_color
from sma_analyzer.version import APP_VERSION


class Service:
    def __init__(self, directory, preview=False):
        directory = Path(directory)
        self.model = AnalyzerModel(LineStore(directory/'saved_lines.sqlite3'),
            create_provider(directory, 'android', 'preview' if preview else 'yahoo'))
        self.directory = directory
        self.lock = RLock()
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.jobs = {}
        self.preview = preview

    def state(self):
        model = self.model
        cards = []
        for card in watchlist(model):
            card = dict(card)
            card['security'] = self.security(card['security'])
            card['lines'] = [self.line(line) for line in card['lines']]
            cards.append(card)
        return dict(version=APP_VERSION, cards=cards, archive=[self.line(line) for line in model.archive_lines()],
                    settings=asdict(model.store.notification_settings()), preview=self.preview,
                    push_available=False, colors=[dict(name=name,color='#'+''.join(f'{round(v*255):02x}' for v in color[:3]))
                      for name,color in zip(COLOR_NAMES,COLOR_CHOICES)])

    @staticmethod
    def security(security):
        result = asdict(security)
        result['logo_url'] = '/logos/'+Path(security.logo_path).name if security.logo_path else ''
        return result

    def line(self, line):
        value = asdict(line)
        value['name'] = line.display_name
        value['color'] = self.model.store.color_index(line.counter,line.scenario,line.period)
        value['color_hex'] = '#'+''.join(f'{round(v*255):02x}' for v in line_color(value['color'])[:3])
        return value

    def chart(self, data, result=None, horizon='Max', years='3'):
        model = self.model
        dates = None if getattr(data,'is_simulated',True) else data.dates
        lines = []
        for line in model.store.list_lines(data.counter,data.scenario):
            try:
                saved_result = model.result_for_dataset(data,line.period,line.target_frequency)
                lines.append(dict(**self.line(line),sma=saved_result.sma))
            except ValueError:
                continue
        report = None
        if result:
            report = compare_investments(data.prices,result.sma,result.events,
                period_sessions(horizon,years,len(data.prices),dates),dates)
            from sma_analyzer.backtest_text import backtest_span
            report = dict(start=report.start,end=report.end,outperformance=report.outperformance_percent,
                span=backtest_span(data,report,dates),
                rows=[dict(key=key,**asdict(getattr(report,key)),invested=getattr(report,key).invested,
                    return_percent=getattr(report,key).return_percent,
                    difference=getattr(report,key).difference_percent(report.crossings)) for key in ('crossings','dca','random')])
        return dict(security=self.security(model.security(data.counter)),prices=data.prices,dates=data.dates,
                    currency=getattr(data,'currency',''),stale=getattr(data,'stale',False),scenario=data.scenario,
                    preview=getattr(data,'is_simulated',True),lines=lines,backtest=report,
                    result=(dict(period=result.period,target=result.target_frequency,frequency=result.actual_annual_frequency,
                                 sma=result.sma,events=[asdict(e) for e in result.events],state=line_state(data.prices,result.period)) if result else None))

    def calculate_job(self, key, target):
        # Snapshot inputs; concurrent browser navigation cannot change this job.
        security = self.model.security(key)
        data = self.model.data_provider.historical_data(security,'Oscillating')
        identifier = secrets.token_urlsafe(18)
        cancel = Event()
        job = dict(status='running',cancel=cancel,created=time.monotonic())
        self.jobs[identifier] = job
        def calculate():
            try:
                result = optimize_sma(data.prices,target,dates=None if getattr(data,'is_simulated',True) else data.dates,
                                      cancel=cancel)
                with self.lock:
                    if cancel.is_set():
                        job['status']='cancelled'
                    else:
                        job.update(status='complete',data=self.chart(data,result))
            except Exception as error:
                job.update(status='cancelled' if cancel.is_set() else 'failed',error=str(error) if isinstance(error,ValueError) else 'Calculation failed. Please retry.')
        self.executor.submit(calculate)
        return {'job':identifier}

    def handle(self, method, path, body):
        expected = ('GET','DELETE') if path.startswith('jobs/') else (('GET',) if path in ('state','log','contact-capabilities') else ('POST',))
        if method not in expected:
            raise ValueError('Method not allowed')
        with self.lock:
            # Completed results are ephemeral; saved data always lives on disk.
            self.jobs = {key:job for key,job in self.jobs.items() if job['status']=='running' or time.monotonic()-job['created']<3600}
            model = self.model
            if path == 'contact-capabilities':
                from .contact import enabled
                return {'enabled':enabled() and not self.preview}
            if path == 'contact-email':
                if self.preview: raise ValueError('Signup is disabled in previews.')
                from .contact import send
                return send(self.directory,body)
            if path == 'state': return self.state()
            if path == 'search':
                query = str(body.get('query','')).strip()[:120]
                if not query: return {'results':[]}
                return {'results':[self.security(s) for s in model.data_provider.search(query)]}
            if path == 'chart':
                security = model.security(body['key'])
                data = (model.data_provider.cached_data(security) if body.get('cached') and hasattr(model.data_provider,'cached_data') else model.data_provider.historical_data(security,'Oscillating'))
                result = model.result_for_dataset(data,int(body['period']),int(body.get('target',4))) if body.get('period') else None
                return self.chart(data,result,body.get('horizon','Max'),str(body.get('years','3')))
            if path == 'optimize':
                target = int(body['target'])
                if isinstance(body['target'],bool) or target != float(body['target']) or target < 1 or target > 2**63-1:
                    raise ValueError('Enter a positive whole-number frequency.')
                if any(job['status']=='running' for job in self.jobs.values()): raise ValueError('A calculation is already running. Cancel it or wait for it to finish.')
                return self.calculate_job(body['key'],target)
            if path.startswith('jobs/'):
                job = self.jobs.get(path.split('/')[-1])
                if not job: raise ValueError('Calculation expired or worker restarted. Please run it again.')
                if method=='DELETE': job['cancel'].set()
                return {k:v for k,v in job.items() if k not in ('cancel','created')}
            if path == 'save':
                data=model.data_provider.cached_data(model.security(body['key'])) if hasattr(model.data_provider,'cached_data') else model.data_provider.historical_data(model.security(body['key']),'Oscillating')
                model.result_for_dataset(data,int(body['period']),int(body['target']))
                model.store.save(data.counter,data.scenario,int(body['period']),int(body['target']))
            elif path == 'line':
                identifier=int(body['id']); model.store.get_line(identifier)
                if 'name' in body: model.store.rename(identifier,body['name'])
                if 'color' in body: model.store.set_color(identifier,int(body['color']))
                if 'visible' in body: model.store.set_visible(identifier,bool(body['visible']))
                if 'push_enabled' in body: model.store.set_notifications(identifier,'phone',bool(body['push_enabled']))
                for kind,field in (('buy','alert_buy'),('monitor','alert_monitor'),('monitor_start','alert_start')):
                    if field in body: model.store.set_line_alert(identifier,kind,bool(body[field]))
                if body.get('archive'): model.store.delete(identifier)
            elif path == 'restore': model.store.restore(int(body['id']))
            elif path == 'settings':
                from dataclasses import replace
                updates={k:bool(v) for k,v in body.items() if k in ('phone_buy','phone_monitor','phone_monitor_start')}
                model.store.save_notification_settings(replace(model.store.notification_settings(),**updates))
            elif path == 'clear-cache':
                if hasattr(model.data_provider,'cache'): model.data_provider.cache.clear_downloads()
            elif path == 'log': return {'events':model.data_provider.cache.diagnostic_events() if hasattr(model.data_provider,'cache') else []}
            else: raise ValueError('Unknown operation')
            return self.state()
