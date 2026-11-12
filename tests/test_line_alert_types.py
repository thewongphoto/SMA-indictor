"""0.14.1: each saved line chooses its own signal types, under the global switches."""
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock
import sqlite3
from contextlib import closing

from scripts.yahoo_test_data import FakeYahooClient, NOW
from sma_analyzer.daily_notifications import enabled_lines, line_wants, run_daily_notifications
from sma_analyzer.market_cache import MarketCache
from sma_analyzer.notifications import NotificationSettings, evaluate_eod, evaluate_dataset_start
from sma_analyzer.settings import DATA_VERSION
from sma_analyzer.storage import LineStore, SavedLine
from sma_analyzer.yahoo import YahooMarketDataProvider

CROSSING = [10, 10, 10, 9, 12]   # SMA(2) ends at 10.5, close 12 crossed above.
BELOW = [10, 10, 10, 11, 9]      # SMA(2) ends at 10, close 9 strictly below.
ALL_ON = NotificationSettings(phone_buy=True, phone_monitor=True, phone_monitor_start=True)


def line(**changes):
    return replace(SavedLine(1, "YAHOO:AAPL", "Yahoo EOD", 2, 12, True), **changes)


class StoreTests(TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "lines.sqlite3"

    def test_upgrade_from_0_14_0_keeps_every_type_on_and_preserves_existing_choices(self):
        with closing(sqlite3.connect(self.path)) as connection, connection:
            connection.execute("""CREATE TABLE saved_lines (id INTEGER PRIMARY KEY, counter TEXT NOT NULL,
                scenario TEXT NOT NULL, period INTEGER NOT NULL, target_frequency INTEGER NOT NULL,
                visible INTEGER NOT NULL DEFAULT 1, data_version INTEGER NOT NULL,
                push_enabled INTEGER NOT NULL DEFAULT 1, email_enabled INTEGER NOT NULL DEFAULT 0,
                custom_name TEXT NOT NULL DEFAULT '',
                UNIQUE(counter, scenario, period, target_frequency, data_version))""")
            connection.execute("INSERT INTO saved_lines(counter,scenario,period,target_frequency,visible,data_version,"
                               "push_enabled,custom_name) VALUES ('YAHOO:AAPL','Yahoo EOD',20,6,0,?,0,'Slow')",
                               (DATA_VERSION,))
        upgraded, = LineStore(self.path).list_all_lines()
        self.assertEqual((upgraded.period, upgraded.target_frequency, upgraded.custom_name), (20, 6, "Slow"))
        self.assertFalse(upgraded.visible)
        self.assertFalse(upgraded.push_enabled)
        self.assertTrue(upgraded.alert_buy and upgraded.alert_monitor and upgraded.alert_start)

    def test_per_line_choices_are_independent_and_survive_restart_archive_and_restore(self):
        store = LineStore(self.path)
        store.save("YAHOO:AAPL", "Yahoo EOD", 20, 6)
        store.save("YAHOO:AAPL", "Yahoo EOD", 50, 4)
        first, second = store.list_all_lines()
        store.set_line_alert(first.id, "buy", False)
        store.set_line_alert(first.id, "monitor_start", False)
        restarted = LineStore(self.path)
        first, second = restarted.list_all_lines()
        self.assertEqual((first.alert_buy, first.alert_monitor, first.alert_start), (False, True, False))
        self.assertEqual((second.alert_buy, second.alert_monitor, second.alert_start), (True, True, True))
        self.assertTrue(restarted.notification_settings().phone_buy)  # Global switches untouched.
        restarted.delete(first.id)
        archived = next(item for item in restarted.recent_unsaved() if item.period == 20)
        self.assertEqual((archived.alert_buy, archived.alert_start), (False, False))
        restarted.restore(archived.id)
        restored = next(item for item in restarted.list_all_lines() if item.period == 20)
        self.assertEqual((restored.alert_buy, restored.alert_monitor, restored.alert_start), (False, True, False))
        restarted.delete(restored.id)
        restarted.save("YAHOO:AAPL", "Yahoo EOD", 20, 6)
        resaved = next(item for item in restarted.list_all_lines() if item.period == 20)
        self.assertEqual((resaved.alert_buy, resaved.alert_monitor, resaved.alert_start), (False, True, False))

    def test_unknown_type_or_missing_line_is_rejected(self):
        store = LineStore(self.path)
        store.save("YAHOO:AAPL", "Yahoo EOD", 20, 6)
        saved, = store.list_all_lines()
        with self.assertRaises(ValueError):
            store.set_line_alert(saved.id, "sell", False)
        with self.assertRaises(ValueError):
            store.set_line_alert(saved.id + 99, "buy", False)


class RuleTests(TestCase):
    def test_buy_needs_the_global_and_line_switch(self):
        self.assertEqual([a.kind for a in evaluate_eod(CROSSING, line(), ALL_ON)], ["buy"])
        self.assertEqual(evaluate_eod(CROSSING, line(alert_buy=False), ALL_ON), ())
        self.assertEqual(evaluate_eod(CROSSING, line(), replace(ALL_ON, phone_buy=False)), ())

    def test_end_of_trading_monitor_needs_the_global_and_line_switch(self):
        self.assertEqual([a.kind for a in evaluate_eod(BELOW, line(), ALL_ON)], ["monitor"])
        self.assertEqual(evaluate_eod(BELOW, line(alert_monitor=False), ALL_ON), ())
        # Turning off a different type on this line does not affect it.
        self.assertEqual([a.kind for a in evaluate_eod(BELOW, line(alert_buy=False, alert_start=False), ALL_ON)],
                         ["monitor"])

    def test_opening_reminder_needs_the_global_and_line_switch(self):
        data = SimpleNamespace(is_simulated=False, prices=[10, 10, 10, 9, 12],
                               dates=["2026-11-02", "2026-11-03", "2026-11-04", "2026-11-05", "2026-11-06"],
                               source="yahoo")
        def remind(saved, settings=ALL_ON):
            return evaluate_dataset_start(data, saved, settings, "2026-11-09", "Apple Inc.", "US")
        self.assertEqual([a.kind for a in remind(line())], ["monitor_start"])
        self.assertEqual(remind(line(alert_start=False)), ())
        self.assertEqual(remind(line(), replace(ALL_ON, phone_monitor_start=False)), ())

    def test_scheduler_selection_per_phase(self):
        start_only = line(alert_buy=False, alert_monitor=False)
        self.assertTrue(line_wants(start_only, ALL_ON, "start"))
        self.assertTrue(line_wants(start_only, ALL_ON, "end"))  # Closing fetch refreshes the cache.
        none = line(alert_buy=False, alert_monitor=False, alert_start=False)
        self.assertFalse(line_wants(none, ALL_ON, "end"))
        self.assertFalse(line_wants(none, ALL_ON, "start"))
        buy_only = line(alert_monitor=False, alert_start=False)
        self.assertTrue(line_wants(buy_only, ALL_ON, "end"))
        self.assertFalse(line_wants(buy_only, ALL_ON, "start"))
        self.assertFalse(line_wants(buy_only, replace(ALL_ON, phone_buy=False), "end"))
        self.assertFalse(line_wants(line(push_enabled=False), ALL_ON, "end"))


class DailyJobTests(TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        self.store = LineStore(root / "saved_lines.sqlite3")
        self.client = FakeYahooClient()
        self.provider = YahooMarketDataProvider(MarketCache(root / "market.sqlite3"), self.client, now=lambda: NOW)
        us = self.provider.search("apple")[0]
        self.store.save(us.key, self.provider.scenario, 2, 12)
        self.line, = self.store.list_all_lines()

    def test_line_with_every_type_off_makes_no_history_request(self):
        for kind in ("buy", "monitor", "monitor_start"):
            self.store.set_line_alert(self.line.id, kind, False)
        self.assertEqual(enabled_lines(self.store, self.provider), [])
        before = len(self.client.calls)
        phone = Mock()
        self.assertEqual(run_daily_notifications(self.store, self.provider, "US", phone, NOW)["status"], "disabled")
        self.assertEqual(len(self.client.calls), before)
        phone.send.assert_not_called()

    def test_line_with_one_type_on_is_still_scheduled(self):
        self.store.set_line_alert(self.line.id, "buy", False)
        self.store.set_line_alert(self.line.id, "monitor_start", False)
        self.assertEqual([saved.id for saved, _ in enabled_lines(self.store, self.provider)], [self.line.id])
        self.assertEqual(enabled_lines(self.store, self.provider, "US", "start"), [])
