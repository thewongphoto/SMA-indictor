from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
import colorsys
import sqlite3

from sma_analyzer.model import AnalyzerModel
from sma_analyzer.palette import COLOR_CHOICES,COLOR_NAMES,line_color
from sma_analyzer.storage import LineStore


class SavedColorChoicesTests(TestCase):
    def setUp(self):
        temp=TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.path=Path(temp.name)/"lines.sqlite3"
        self.store=LineStore(self.path)
        self.store.save("DEMO-US","Trending",20,6)
        self.line,=self.store.list_all_lines()

    def test_twelve_distinct_named_colors_round_trip(self):
        self.assertEqual((len(COLOR_CHOICES),len(COLOR_NAMES),len(set(COLOR_CHOICES))),(12,12,12))
        for index,rgba in enumerate(COLOR_CHOICES):
            self.store.set_color(self.line.id,index)
            fresh=LineStore(self.path)
            self.assertEqual(line_color(fresh.color_index("DEMO-US","Trending",20)),rgba)

    def test_choice_survives_hidden_rename_archive_restore_without_changing_the_line(self):
        self.store.set_color(self.line.id,10)
        self.store.rename(self.line.id,"Recovery")
        self.store.set_visible(self.line.id,False)
        self.store.delete(self.line.id)
        self.store.restore(self.store.recent_unsaved()[0].id)
        line,=LineStore(self.path).list_all_lines()
        self.assertEqual((line.period,line.target_frequency,line.custom_name,line.visible),(20,6,"Recovery",False))
        self.assertEqual(line_color(self.store.color_index(line.counter,line.scenario,line.period)),COLOR_CHOICES[10])

    def test_company_and_period_isolation_and_default_allocation_order(self):
        self.store.set_color(self.line.id,11)
        self.store.save("DEMO-US","Trending",40,12)
        self.store.save("DEMO-SGX","Trending",20,6)
        self.assertEqual(self.store.color_index("DEMO-US","Trending",40),1)
        self.assertEqual(self.store.color_index("DEMO-SGX","Trending",20),0)
        # Previously allocated HSV colors must not change when adding presets.
        self.assertEqual(line_color(9),(*colorsys.hsv_to_rgb((9*.61803398875+.13)%1,.52,.98),1))

    def test_validation_and_deleted_saved_line_cannot_change_other_lines(self):
        for bad in (-1,12,True,1.5,"2"):
            with self.assertRaises(ValueError):self.store.set_color(self.line.id,bad)
        self.store.delete(self.line.id)
        with self.assertRaises(ValueError):self.store.set_color(self.line.id,0)

    def test_old_color_table_migration_retains_allocations(self):
        with sqlite3.connect(self.path) as db:
            db.execute("DROP TABLE sma_colors")
            db.execute("CREATE TABLE sma_colors(counter TEXT,scenario TEXT,period INTEGER,color_index INTEGER,"
                       "PRIMARY KEY(counter,scenario,period))")
            db.execute("INSERT INTO sma_colors VALUES ('DEMO-US','Trending',20,9)")
        upgraded=LineStore(self.path)
        self.assertEqual(upgraded.color_index("DEMO-US","Trending",20),9)
        upgraded.set_color(self.line.id,5)
        self.assertEqual(line_color(upgraded.color_index("DEMO-US","Trending",20)),COLOR_CHOICES[5])

    def test_color_changes_do_not_change_analysis_or_signal_identity(self):
        model=AnalyzerModel(self.store)
        model.select_dataset(self.line.counter,self.line.scenario)
        model.view_saved_line(self.line.id)
        fingerprint=model.data_fingerprint()
        result=model.result
        self.store.set_color(self.line.id,3)
        self.assertEqual(model.data_fingerprint(),fingerprint)
        self.assertIs(model.result,result)
        self.assertEqual(line_color(model.plot_lines()[0].color_index),COLOR_CHOICES[3])

    def test_concurrent_ui_and_worker_upgrade_preserves_saved_colors(self):
        with sqlite3.connect(self.path) as db:
            db.execute("DROP TABLE sma_colors")
            db.execute("CREATE TABLE sma_colors(counter TEXT,scenario TEXT,period INTEGER,color_index INTEGER,"
                       "PRIMARY KEY(counter,scenario,period))")
            db.execute("INSERT INTO sma_colors VALUES ('DEMO-US','Trending',20,9)")
        gate=Barrier(4)
        def open_store(_):
            gate.wait()
            store=LineStore(self.path)
            return store.color_index("DEMO-US","Trending",20)
        with ThreadPoolExecutor(max_workers=4) as pool:
            self.assertEqual(list(pool.map(open_store,range(4))),[9]*4)
        self.store.set_color(self.line.id,1)
        self.assertEqual(line_color(LineStore(self.path).color_index("DEMO-US","Trending",20)),COLOR_CHOICES[1])
