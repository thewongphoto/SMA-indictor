from pathlib import Path
from tempfile import TemporaryDirectory
import sqlite3
from unittest import TestCase

from sma_analyzer.model import AnalyzerModel
from sma_analyzer.storage import LineStore


class LineNameTests(TestCase):
    def setUp(self):
        temp=TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.path=Path(temp.name)/"lines.sqlite3"
        self.store=LineStore(self.path)
        self.store.save("DEMO-SGX","Trending",9,12)
        self.line=self.store.list_all_lines()[0]

    def test_name_survives_reopen_unsave_restore_and_toggle_save(self):
        self.store.rename(self.line.id," Recovery   plan ")
        self.assertEqual(LineStore(self.path).get_line(self.line.id).custom_name,"Recovery plan")
        self.store.delete(self.line.id)
        entry=self.store.recent_unsaved()[0]
        self.assertEqual(entry.display_name,"Recovery plan")
        self.store.restore(entry.id)
        line=self.store.list_all_lines()[0]
        self.store.delete(line.id)
        self.store.save(line.counter,line.scenario,line.period,line.target_frequency)
        self.assertEqual(self.store.list_all_lines()[0].custom_name,"Recovery plan")

    def test_names_do_not_change_colors_or_identity_and_blank_resets_default(self):
        before=self.store.color_index(self.line.counter,self.line.scenario,self.line.period)
        self.store.rename(self.line.id,"長期 Recovery")
        line=self.store.get_line(self.line.id)
        self.assertEqual((line.id,line.period,line.target_frequency),(self.line.id,9,12))
        self.assertEqual(self.store.color_index(line.counter,line.scenario,line.period),before)
        self.store.rename(line.id,"")
        self.assertEqual(self.store.get_line(line.id).display_name,"SMA (9 days)")

    def test_invalid_names_do_not_overwrite_current_name(self):
        self.store.rename(self.line.id,"My line")
        for name in ("x"*61,"Hidden\x00name"):
            with self.assertRaises(ValueError): self.store.rename(self.line.id,name)
        self.assertEqual(self.store.get_line(self.line.id).custom_name,"My line")

    def test_model_summary_and_overlay_use_saved_name(self):
        self.store.rename(self.line.id,"My recovery SMA")
        model=AnalyzerModel(self.store)
        model.view_saved_line(self.line.id)
        self.assertEqual(model.summary()["period"],"My recovery SMA")
        self.assertEqual(model.current_line_name(),"My recovery SMA")
        self.assertEqual(model.plot_lines()[0].name,"My recovery SMA")

    def test_old_schema_gains_empty_names_without_losing_parameters(self):
        with sqlite3.connect(self.path) as db:
            db.execute("ALTER TABLE saved_lines DROP COLUMN custom_name")
            db.execute("ALTER TABLE unsaved_lines DROP COLUMN custom_name")
        migrated=LineStore(self.path)
        self.assertEqual(migrated.get_line(self.line.id).custom_name,"")
        self.assertEqual(migrated.get_line(self.line.id).period,9)
