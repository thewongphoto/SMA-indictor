"""Frozen training windows shared by native, browser and worker adapters.

Only scoring is restricted. The selected period's SMA and crossing series still
span downloaded history so current alerts and independent backtests keep working.
"""
from bisect import bisect_left, bisect_right
from datetime import date, timedelta
from .engine import optimize_sma, simple_moving_average, crossover_events, OptimizationResult
from .policy import maximum_sma_period, observable_comparisons, calendar_weights, observable_calendar_days


def window_dates(start='', end=''):
    start = '' if start is None else start
    end = '' if end is None else end
    if not isinstance(start,str) or not isinstance(end,str):raise ValueError('Use valid From and To dates.')
    if not start and not end:return '', ''
    try:
        a,b=date.fromisoformat(start),date.fromisoformat(end)
        if a.isoformat()!=start or b.isoformat()!=end or a>b:raise ValueError()
    except (ValueError,TypeError):raise ValueError('Choose valid From and To dates, with From before To.') from None
    return start,end


def bounds(dates,start='',end=''):
    start,end=window_dates(start,end)
    if not start:return 0,len(dates)-1
    if not dates:raise ValueError('Download dated price history first.')
    if start<dates[0] or end>dates[-1]:raise ValueError(f'Choose dates between {dates[0]} and {dates[-1]}.')
    left,right=bisect_left(dates,start),bisect_right(dates,end)-1
    if right-left+1<4:raise ValueError('Choose at least 4 trading days so an SMA can warm up and be compared.')
    return left,right


def validate(prices,dates,start='',end=''):
    left,right=bounds(dates,start,end)
    values=prices[left:right+1]
    if len(values)<4:raise ValueError('Choose at least 4 trading days so an SMA can warm up and be compared.')
    cap=maximum_sma_period(len(values))
    sma=simple_moving_average(values,2)
    if observable_comparisons(values,sma)<len(values)-cap:
        raise ValueError('Choose a wider period with enough consecutive complete closing prices.')
    return left,right


def preset(dates,years=None):
    if years is None:return '', ''
    if not dates:raise ValueError('Download dated price history first.')
    return max(dates[0],(date.fromisoformat(dates[-1])-timedelta(days=365*years)).isoformat()),dates[-1]


def label(start='',end='',short=False):
    if not start:return ''
    if short:return f'{start[:4]}–{end[:4]}' if start[:4]!=end[:4] else f'{start} – {end}'
    def fmt(value):
        d=date.fromisoformat(value)
        return f'{d.day} {d:%b %Y}'
    return f'{fmt(start)} – {fmt(end)}'


def scoped_result(prices,dates,period,target,start='',end='',simulated=False):
    left,right=bounds(dates,start,end)
    average=tuple(simple_moving_average(prices,period))
    values=prices[left:right+1]
    score_sma=tuple(simple_moving_average(values,period))
    comparisons=observable_comparisons(values,score_sma)
    if not comparisons:raise ValueError('Not enough observable history to display this SMA in the selected period.')
    exposure=observable_calendar_days(values,score_sma,calendar_weights(None if simulated else dates[left:right+1],len(values)))
    return OptimizationResult(period,target,len(values),comparisons,average,crossover_events(prices,average),exposure,
        start,end,len(crossover_events(values,score_sma)) if start else None)


def optimize_history(prices,target,*,dates=None,history_start='',history_end='',cancel=None,use_fast=True,simulated=False):
    start,end=window_dates(history_start,history_end)
    if not start:return optimize_sma(prices,target,dates=None if simulated else dates,cancel=cancel,use_fast=use_fast)
    left,right=validate(prices,dates,start,end)
    result=optimize_sma(prices[left:right+1],target,dates=None if simulated else dates[left:right+1],cancel=cancel,use_fast=use_fast)
    return scoped_result(prices,dates,result.period,target,start,end,simulated=simulated)
