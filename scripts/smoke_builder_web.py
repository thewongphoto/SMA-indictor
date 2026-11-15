"""Native builder-flow contract in Chromium/WebKit; controlled transport only."""
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.request

from playwright.sync_api import sync_playwright, expect
from sma_analyzer.mock_data import generate_mock_data
from web.python.browser import calculate

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts/builder-web"
ORIGIN = "http://127.0.0.1:3199"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "flow-review.json").unlink(missing_ok=True)
    version = json.loads((ROOT / "web/package.json").read_text())["version"]
    sample = generate_mock_data("DEMO-US", "Oscillating", sessions=900)
    securities = [dict(key="YAHOO:AAPL", ticker="AAPL", name="Apple Inc.", region="US", logo_url="/logos/apple.png"),
                  dict(key="YAHOO:VOO", ticker="VOO", name="Vanguard S&P 500 ETF", region="US", logo_url="/logos/vanguard.png")]
    data = {s["key"]: dict(security=s, prices=sample.prices, dates=sample.dates, currency="USD", preview=False, stale=False)
            for s in securities}
    results = {}
    reports = {}
    with (OUT / "server.log").open("w") as log:
        server = subprocess.Popen(["node", "node_modules/next/dist/bin/next", "start", "--hostname", "127.0.0.1", "--port", "3199"],
                                  cwd=ROOT / "web", stdout=log, stderr=log)
        try:
            for _ in range(100):
                try:
                    urllib.request.urlopen(ORIGIN, timeout=1)
                    break
                except OSError:
                    time.sleep(.2)
            with sync_playwright() as p:
                for engine in ("chromium", "webkit"):
                    options = {"args": ["--no-sandbox"]} if engine == "chromium" else (
                        {"executable_path": os.environ["SMA_WEBKIT_EXECUTABLE"]} if os.environ.get("SMA_WEBKIT_EXECUTABLE") else {})
                    browser = getattr(p, engine).launch(**options)
                    context = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True,
                                                  has_touch=True, color_scheme="dark", service_workers="block")
                    page = context.new_page()
                    page.set_default_timeout(15000)
                    def until(predicate):
                        deadline = time.monotonic() + 5
                        while not predicate():
                            assert time.monotonic() < deadline, "Fixture request did not complete"
                            page.wait_for_timeout(25)
                    calls, errors, held = [], [], []
                    jobs = {}
                    behavior = {"hold": False, "fail_history": False}
                    page.on("pageerror", lambda error: errors.append(str(error)))

                    def respond(route):
                        path = route.request.url.split("/api/")[-1]
                        body = route.request.post_data_json if route.request.method == "POST" else {}
                        calls.append((path, route.request.method, body))
                        if path == "session": value = {"storage": "worker"}
                        elif path == "contact-capabilities": value = {"enabled": False}
                        elif path == "state": value = dict(version=version, cards=[], archive=[], colors=[], settings={})
                        elif path == "search": value = {"results": [securities[1] if "voo" in body["query"].lower() else securities[0]]}
                        elif path == "chart":
                            if behavior["fail_history"]:
                                route.fulfill(status=503, json={"error": "Fixture history unavailable"})
                                return
                            value = dict(data[body["key"]], lines=[], result=None, backtest=None)
                        elif path == "optimize":
                            key = (body["key"], body["target"])
                            if key not in results:
                                results[key] = calculate(dict(data=data[key[0]], lines=[], target=key[1], optimize=True))
                            identity = str(len(jobs) + 1)
                            jobs[identity] = {"status": "running", "data": results[key]}
                            if behavior["hold"]:
                                held.append((route, identity))
                                return
                            value = {"job": identity}
                        elif path.startswith("jobs/"):
                            job = jobs[path.split("/")[-1]]
                            if route.request.method == "DELETE": job["status"] = "cancelled"
                            value = job
                        else:
                            route.fulfill(status=404, json={"error": "Unexpected fixture request"})
                            return
                        route.fulfill(json=value)

                    page.route("**/api/**", respond)
                    page.goto(ORIGIN)
                    page.get_by_role("button", name="Find a security", exact=True).click()
                    search_heading = page.get_by_role("heading", name="Find a security", exact=True)
                    expect(search_heading).to_be_visible()
                    expect(page.locator(".target-preference")).to_have_count(0)
                    field = page.get_by_placeholder("Company name or ticker")
                    field.fill("apple")
                    page.wait_for_timeout(100)
                    assert not any(path == "search" for path, _, _ in calls)
                    page.get_by_role("button", name="Search", exact=True).click()
                    page.get_by_role("button", name="Apple Inc.").click()
                    heading = page.get_by_role("heading", name="Set your preference", exact=True)
                    expect(heading).to_be_visible()
                    assert page.url.endswith("#search")
                    expect(page.locator(".chart-plot")).to_have_count(0)
                    builder = page.locator(".preference-builder")
                    expect(builder).to_contain_text("Apple Inc.")
                    expect(builder.locator("img")).to_have_attribute("src", "/logos/apple.png")
                    expect(builder.get_by_role("button", name="12", exact=True)).to_have_attribute("aria-pressed", "true")
                    expect(page.get_by_role("button", name="Charts", exact=True)).to_have_attribute("aria-current", "page")
                    observed = dict(selected_stage=heading.inner_text(),
                                    default_target=int(builder.locator('button[aria-pressed="true"]').inner_text()),
                                    presets=[int(text) for text in builder.locator('.segments button').all_inner_texts() if text.isdecimal()])
                    expect(builder).to_have_css("opacity", "1")
                    page.evaluate("() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))")
                    page.screenshot(path=str(OUT / f"{engine}-preference-default-390.png"), full_page=True, animations="disabled")
                    before = len(calls)
                    page.get_by_role("button", name="Charts", exact=True).click()
                    expect(page.locator(".chart-identity")).to_contain_text("Apple Inc.")
                    expect(page.get_by_role("button", name="Save", exact=True)).to_have_count(0)
                    page.get_by_role("button", name="‹ Back", exact=True).click()
                    expect(heading).to_be_visible()
                    builder.get_by_role("button", name="Apple Inc.").click()
                    expect(field).to_be_focused()
                    for target in (4, 6, 12):
                        button = builder.get_by_role("button", name=str(target), exact=True)
                        button.click()
                        expect(button).to_have_attribute("aria-pressed", "true")
                        expect(builder.get_by_role("button", name=f"Find best SMA for {target} signals / year")).to_be_visible()
                    assert len(calls) == before, calls[before:]
                    builder.get_by_role("button", name="Custom", exact=True).click()
                    custom = builder.get_by_label("Upward crossings per year")
                    for invalid in ("", "0", "1.5"):
                        custom.fill(invalid)
                        builder.locator('button[type="submit"], button.primary').click()
                        assert not any(path == "optimize" for path, _, _ in calls)
                    custom.fill("9")
                    for width in (320, 390, 430):
                        page.set_viewport_size({"width": width, "height": 844})
                        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), (engine, width)
                        page.screenshot(path=str(OUT / f"{engine}-preference-{width}.png"), full_page=True)
                    builder.get_by_role("button", name="Find best SMA for 9 signals / year").click()
                    dialog = page.get_by_role("dialog", name="Finding your SMA")
                    expect(dialog).to_contain_text("9 upward crossings a year for AAPL")
                    page.get_by_role("button", name="Cancel", exact=True).click()
                    expect(dialog).to_have_count(0)
                    expect(heading).to_be_visible()
                    assert page.url.endswith("#search")
                    expect(custom).to_have_value("9")
                    until(lambda: any(method == "DELETE" for _, method, _ in calls))
                    expect(page.locator(".chart-plot")).to_have_count(0)
                    assert any(method == "DELETE" for _, method, _ in calls)
                    # Complete a calculation only after preference submission.
                    builder.get_by_role("button", name="4", exact=True).click()
                    builder.get_by_role("button", name="Find best SMA for 4 signals / year").click()
                    expect(dialog).to_be_visible()
                    until(lambda: any(job["status"] == "running" for job in jobs.values()))
                    for job in jobs.values():
                        if job["status"] == "running": job["status"] = "complete"
                    expect(page.locator(".chart-plot")).to_be_visible()
                    assert page.url.endswith("#results")
                    expect(page.locator(".target-preference").get_by_role("button", name="4", exact=True)).to_have_attribute("aria-pressed", "true")
                    page.get_by_role("button", name="‹ Back", exact=True).click()
                    expect(heading).to_be_visible()
                    expect(builder.get_by_role("button", name="4", exact=True)).to_have_attribute("aria-pressed", "true")
                    page.go_forward()
                    expect(page.locator(".chart-plot")).to_be_visible()
                    before = len(calls)
                    page.locator(".target-preference").get_by_role("button", name="Custom", exact=True).click()
                    expect(heading).to_be_visible()
                    expect(builder.get_by_label("Upward crossings per year")).to_have_value("4")
                    assert len(calls) == before, calls[before:]
                    page.go_back()
                    expect(page.locator(".chart-plot")).to_be_visible()
                    page.get_by_role("button", name="‹ Back", exact=True).click()
                    expect(heading).to_be_visible()
                    expect(builder.get_by_role("button", name="Custom", exact=True)).to_have_attribute("aria-pressed", "true")
                    expect(builder.get_by_label("Upward crossings per year")).to_have_value("4")
                    # Searching for another security removes the old preference
                    # stage; a failed download never selects stale history.
                    field.fill("voo")
                    page.get_by_role("button", name="Search", exact=True).click()
                    expect(search_heading).to_be_visible()
                    behavior["fail_history"] = True
                    match = page.get_by_role("button", name="Vanguard S&P 500 ETF")
                    match.click()
                    expect(page.locator('.error[role="alert"]')).to_contain_text("Fixture history unavailable")
                    expect(builder).to_have_count(0)
                    behavior["fail_history"] = False
                    match.click()
                    expect(heading).to_be_visible()
                    expect(builder).to_contain_text("Vanguard S&P 500 ETF")
                    expect(builder.locator("img")).to_have_attribute("src", "/logos/vanguard.png")
                    # Back while job creation is in flight must cancel its late
                    # response and never navigate from Home into a stale chart.
                    behavior["hold"] = True
                    builder.get_by_role("button", name="6", exact=True).click()
                    builder.get_by_role("button", name="Find best SMA for 6 signals / year").click()
                    expect(dialog).to_be_visible()
                    until(lambda: bool(held))
                    assert len(held) == 1
                    page.go_back()
                    expect(page.get_by_role("heading", name="Home", exact=True)).to_be_visible()
                    route, identity = held.pop()
                    route.fulfill(json={"job": identity})
                    page.wait_for_timeout(750)
                    expect(page.get_by_role("heading", name="Home", exact=True)).to_be_visible()
                    assert jobs[identity]["status"] == "cancelled"
                    assert not errors, errors
                    reports[engine] = dict(passed=True, **observed, custom=9, same_search_screen=True,
                                           no_eager_optimization=True, cancel_in_place=True, back_to_preferences=True,
                                           failed_selection_retained=False, late_job_cancelled=True)
                    browser.close()
        finally:
            server.terminate()
            try: server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()
    (OUT / "flow-review.json").write_text(json.dumps(reports, indent=2))
    print("PASS: Chromium/WebKit keep selection and target on one builder screen; native defaults/presets/custom validation, explicit calculation, cancellation, Back, failed selection, stale completion and narrow layouts.")


if __name__ == "__main__":
    main()
