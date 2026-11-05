from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import sqlite3
import unittest
from unittest.mock import patch

from sma_analyzer.model import AnalyzerModel
from sma_analyzer.storage import LineStore
from sma_analyzer.palette import line_color
from sma_analyzer.yahoo import HistoricalDataset


class AnalysisReuseTests(unittest.TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name)/"lines.sqlite3"
        self.model = AnalyzerModel(LineStore(self.path))

    def test_unsaved_analysis_reused_after_restart_without_optimizer(self):
        result = self.model.calculate()
        fresh = AnalyzerModel(LineStore(self.path))
        with patch("sma_analyzer.model.optimize_sma",side_effect=AssertionError("must reuse")):
            self.assertTrue(fresh.reuse_result())
        self.assertEqual(fresh.result,result)
        self.assertFalse(fresh.viewing_saved)

    def test_saved_target_opens_exact_saved_period_even_with_new_prices(self):
        data = self.model.dataset
        self.model.store.save(data.counter,data.scenario,37,12)
        self.model.apply_dataset(replace(data,prices=data.prices[:-1]+(data.prices[-1]*1.1,)))
        self.assertTrue(self.model.reuse_result())
        self.assertEqual(self.model.result.period,37)
        self.assertTrue(self.model.viewing_saved)

    def test_cache_invalidated_by_price_dates_and_target_but_not_identical_reload(self):
        data = self.model.dataset
        self.model.calculate()
        self.model.apply_dataset(replace(data))
        self.assertTrue(self.model.reuse_result())
        self.model.set_target("6")
        self.assertFalse(self.model.reuse_result())
        self.model.set_target("12")
        self.model.apply_dataset(replace(data,prices=data.prices[:-1]+(data.prices[-1]+1,)))
        self.assertFalse(self.model.reuse_result())

    def test_cache_cannot_leak_between_securities(self):
        self.model.calculate()
        self.model.select_dataset("DEMO-US","Oscillating")
        self.assertFalse(self.model.reuse_result())

    def test_calendar_date_change_invalidates_analysis_even_with_same_prices(self):
        data = HistoricalDataset("YAHOO:AAPL",(100.,90.,105.,95.,110.),
            ("2026-01-05","2026-01-06","2026-01-07","2026-01-08","2026-01-09"),
            "USD","America/New_York",1,1)
        self.model.apply_dataset(data)
        self.model.calculate()
        self.model.apply_dataset(replace(data,fetched_at=2,revision=2))
        self.assertTrue(self.model.reuse_result())
        self.model.apply_dataset(replace(data,dates=data.dates[:-1]+("2026-01-12",)))
        self.assertFalse(self.model.reuse_result())

    def test_color_survives_focus_hide_archive_restore_and_restart(self):
        store = self.model.store
        data = self.model.dataset
        # Merely previewing a period does not reserve the first saved color.
        self.assertEqual(store.color_index(data.counter,data.scenario,99),0)
        for period in (9,29):
            store.save(data.counter,data.scenario,period,12)
        first,second = self.model.saved_lines()
        self.assertEqual(store.color_index(data.counter,data.scenario,9),0)
        self.assertEqual(store.color_index(data.counter,data.scenario,29),1)
        for selected in (first,second,first):
            self.model.view_saved_line(selected.id)
            self.assertEqual({line.period:line_color(line.color_index) for line in self.model.plot_lines()},
                             {9:line_color(0),29:line_color(1)})
        store.set_visible(second.id,False)
        store.delete(first.id)
        store.restore(store.recent_unsaved()[0].id)
        fresh = LineStore(self.path)
        self.assertEqual(fresh.color_index(data.counter,data.scenario,9),0)
        self.assertEqual(fresh.color_index(data.counter,data.scenario,29),1)
        fresh.save("DEMO-US",data.scenario,9,12)
        self.assertEqual(fresh.color_index("DEMO-US",data.scenario,9),0)

    def test_existing_saved_colors_migrate_in_save_order(self):
        store = self.model.store
        for period in (29,9,51):
            store.save("DEMO-SGX","Oscillating",period,12)
        with sqlite3.connect(self.path) as db:
            db.execute("DROP TABLE sma_colors")
        migrated = LineStore(self.path)
        self.assertEqual([migrated.color_index("DEMO-SGX","Oscillating",p) for p in (29,9,51)],
                         [0,1,2])
