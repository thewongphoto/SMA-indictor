"""Defaults must enable new saves without erasing a user's later choices."""
from pathlib import Path
import json
import sqlite3
from tempfile import TemporaryDirectory
from unittest import TestCase

from sma_analyzer.notifications import NotificationSettings
from sma_analyzer.settings import DATA_VERSION
from sma_analyzer.storage import LineStore


class NotificationDefaultsTests(TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "lines.sqlite3"
        self.store = LineStore(self.path)

    def test_fresh_user_and_saved_lines_default_to_phone_and_both_types(self):
        self.store.save("YAHOO:AAPL", "Yahoo EOD", 20, 6)
        self.store.save("YAHOO:D05.SI", "Yahoo EOD", 30, 12)
        restarted = LineStore(self.path)
        self.assertTrue(all(line.push_enabled for line in restarted.list_all_lines()))
        self.assertTrue(restarted.notification_settings().phone_buy)
        self.assertTrue(restarted.notification_settings().phone_monitor)
        self.assertFalse(any(line.email_enabled for line in restarted.list_all_lines()))
        self.assertFalse(restarted.notification_settings().email_buy)
        self.assertFalse(restarted.notification_settings().email_monitor)

    def test_explicit_off_survives_save_restart_archive_and_restore(self):
        self.store.save("YAHOO:AAPL", "Yahoo EOD", 20, 6)
        line, = self.store.list_all_lines()
        self.store.set_notifications(line.id, "phone", False)
        self.store.save_notification_settings(NotificationSettings(phone_buy=False, phone_monitor=False))
        self.store.save(line.counter, line.scenario, line.period, line.target_frequency)
        restarted = LineStore(self.path)
        self.assertFalse(restarted.get_line(line.id).push_enabled)
        self.assertFalse(restarted.notification_settings().phone_buy)
        self.assertFalse(restarted.notification_settings().phone_monitor)
        restarted.delete(line.id)
        archived, = restarted.recent_unsaved()
        restarted.restore(archived.id)
        restored, = restarted.list_all_lines()
        self.assertFalse(restored.push_enabled)
        restarted.delete(restored.id)
        restarted.save(line.counter, line.scenario, line.period, line.target_frequency)
        resaved, = restarted.list_all_lines()
        self.assertFalse(resaved.push_enabled)

    def test_new_saves_use_on_even_in_an_existing_default_zero_schema(self):
        # The installed 0.10 schema keeps its original SQL DEFAULT 0 on upgrade.
        with sqlite3.connect(self.path) as db:
            db.execute("ALTER TABLE saved_lines RENAME TO old_lines")
            db.execute("CREATE TABLE saved_lines (id INTEGER PRIMARY KEY, counter TEXT, scenario TEXT, "
                       "period INTEGER, target_frequency INTEGER, visible INTEGER DEFAULT 1, data_version INTEGER, "
                       "push_enabled INTEGER DEFAULT 0, email_enabled INTEGER DEFAULT 0, custom_name TEXT DEFAULT '', "
                       "UNIQUE(counter,scenario,period,target_frequency,data_version))")
            db.execute("INSERT INTO saved_lines(counter,scenario,period,target_frequency,data_version) "
                       "VALUES ('YAHOO:AAPL','Yahoo EOD',20,6,?)", (DATA_VERSION,))
            db.execute("DROP TABLE old_lines")
        upgraded = LineStore(self.path)
        upgraded.save("YAHOO:AAPL", "Yahoo EOD", 40, 12)
        lines = {line.period: line for line in LineStore(self.path).list_all_lines()}
        self.assertFalse(lines[20].push_enabled)
        self.assertTrue(lines[40].push_enabled)

    def test_missing_type_preferences_take_defaults_but_stored_false_is_kept(self):
        with sqlite3.connect(self.path) as db:
            db.execute("INSERT INTO preferences VALUES ('notifications',?)", (json.dumps({"phone_buy": False}),))
        settings = LineStore(self.path).notification_settings()
        self.assertFalse(settings.phone_buy)
        self.assertTrue(settings.phone_monitor)
