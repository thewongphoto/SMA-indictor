"""Pure presentation adapter for the shared engine inside a browser worker."""
from dataclasses import asdict
from types import SimpleNamespace
from sma_analyzer.engine import optimize_sma, simple_moving_average, crossover_events, OptimizationResult
from sma_analyzer.policy import observable_comparisons, observable_calendar_days, calendar_weights
from sma_analyzer.backtest import compare_investments, period_sessions
from sma_analyzer.backtest_text import backtest_span


def calculate(payload):
    data = payload['data']
    prices = data['prices']
    dates = None if data.get('preview') else data['dates']
    target = int(payload.get('target', 4))
    period = payload.get('period')
    from sma_analyzer.history_window import optimize_history, scoped_result
    start,end=payload.get('history_start',''),payload.get('history_end','')
    result = None
    if payload.get('optimize') and not period:
        result=optimize_history(prices,target,dates=data['dates'],history_start=start,history_end=end,simulated=bool(data.get('preview')))
    elif period:
        result=scoped_result(prices,data['dates'],int(period),target,start,end,simulated=bool(data.get('preview')))
    lines = []
    for line in payload.get('lines', []):
        try:
            average = simple_moving_average(prices, int(line['period']))
            lines.append(dict(line, sma=average, events=[asdict(e) for e in crossover_events(prices,average)]))
        except ValueError:
            continue
    report = None
    if result:
        comparison = compare_investments(prices, result.sma, result.events,
            period_sessions(payload.get('horizon','Max'),str(payload.get('years','3')),len(prices),dates),dates)
        report = dict(start=comparison.start,end=comparison.end,outperformance=comparison.outperformance_percent,
            span=backtest_span(SimpleNamespace(**data),comparison,dates),
            rows=[dict(key=key,**asdict(getattr(comparison,key)),invested=getattr(comparison,key).invested,
                return_percent=getattr(comparison,key).return_percent,
                difference=getattr(comparison,key).difference_percent(comparison.crossings))
                for key in ('crossings','dca','random')])
    state = None
    if result:
        price, average = prices[-1], result.sma[-1]
        state = ('Unknown' if price is None or average is None else
                 'Above' if price>average else 'Below' if price<average else 'On line')
    return dict(data,lines=lines,backtest=report,
        result=dict(history_start=result.history_start,history_end=result.history_end,period=result.period,target=result.target_frequency,frequency=result.actual_annual_frequency,
                    sma=result.sma,events=[asdict(e) for e in result.events],state=state) if result else None)
