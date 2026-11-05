"""Copyable diagnostics from controlled fields, never HTTP headers or payloads."""
from datetime import datetime, timezone
import sys

from .schedule import SGT
from .version import APP_VERSION
from .presentation import display_text,endpoint_label


def diagnostic_report(cache, platform_name, transport, dataset=None, limit=100, public_view=False):
    now = datetime.now(timezone.utc)
    lines = [
        f"SMA Stock Analyzer {APP_VERSION}",
        f"Generated: {now.astimezone(SGT):%Y-%m-%d %H:%M:%S} SGT",
        f"Platform: {platform_name}; Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        f"Transport: {transport}",
        "Times below are Singapore time (UTC+08:00); newest first.",
        "APP started/ok/failed rows share an ID; HTTP rows are wire requests.",
        "CACHE rows use no network. Validation/result rows are not extra requests.",
        "Cookies, crumbs, headers, response bodies and device/file identifiers are excluded.",
    ]
    if dataset is not None and dataset.prices:
        lines.append(f"Selected: {dataset.counter}; {dataset.currency}; "
                     f"cached {dataset.dates[0]} to {dataset.dates[-1]}; "
                     f"{len(dataset.prices)} sessions; stale={dataset.stale}")
        lines.append(f"Price basis: {getattr(dataset,'price_basis','example-close')}")
    for event in cache.diagnostic_events(limit):
        kind = "HTTP" if event["operation"] == "http" else "CACHE" if event["status"] == "cache_hit" else "APP"
        stamp = datetime.fromtimestamp(event["at"],SGT).strftime("%m-%d %H:%M:%S")
        identity = event["request_id"][:8] or "-"
        code = f" HTTP {event['http_status']}" if event["http_status"] is not None else ""
        duration = f" {event['duration_ms']:.0f}ms" if event["duration_ms"] is not None else ""
        lines.append(f"\n{stamp} [{kind} {identity}] {event['operation']} · "
                     f"{event['symbol']} · {event['status']}{code}{duration}")
        if event["endpoint"]:
            lines.append(endpoint_label(event["endpoint"]) if public_view else event["endpoint"])
        if event["detail"]:
            lines.append(event["detail"])
    if not cache.diagnostic_events(1):
        lines.append("\nNo recorded events yet.")
    report = "\n".join(lines)
    return display_text(report) if public_view else report
