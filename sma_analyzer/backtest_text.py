"""Plain-language backtest copy shared by the native card and its checks (design 2b)."""
from datetime import date

from .policy import CALENDAR_DAYS_PER_YEAR


def backtest_span(data, report, dates):
    """'Nov 2023 – Nov 2026' for real dates; simulated data has no calendar."""
    if dates:
        start, end = (date.fromisoformat(dates[index]) for index in (report.start, report.end))
        return f"{start:%b %Y} – {end:%b %Y}"
    years = (report.end - report.start + 1)/252
    return f"{years:.1f} simulated years"


def gain_phrase(ending_value, invested, prefix):
    """'+$186 gain on $1,200 contributed', or a loss, or no buys."""
    if not invested:
        return "No buys in this period"
    change = ending_value - invested
    sign = "+" if change >= 0 else "−"
    word = "gain" if change >= 0 else "loss"
    return f"{sign}{prefix}{abs(change):,.0f} {word} on {prefix}{invested:,.0f} contributed"


def calendar_years(report, dates):
    if dates:
        return (date.fromisoformat(dates[report.end]) - date.fromisoformat(dates[report.start])).days/CALENDAR_DAYS_PER_YEAR
    return (report.end - report.start + 1)/252
