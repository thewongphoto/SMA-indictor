"""Brand-neutral display helpers; persistent provider identities remain intact."""
import re
from urllib.parse import urlsplit


def display_text(value):
    text = str(value).replace("YAHOO:", "")
    text = re.sub(r"yahoo(?:\s+finance)?|yfinance", "Market data", text, flags=re.I)
    return re.sub(r"\bsimulated\b", "example", text, flags=re.I)


def endpoint_label(endpoint):
    parsed = urlsplit(endpoint if "://" in endpoint else "//"+endpoint)
    path = parsed.path
    if "/finance/search" in path:
        return "Security search"
    if "/finance/chart/" in path:
        return "Daily closes · "+path.rsplit("/",1)[-1]
    if "/test/getcrumb" in path:
        return "Data session token"
    if parsed.hostname and parsed.hostname.startswith("fc."):
        return "Data session setup"
    return display_text(path or "Market data connection")
