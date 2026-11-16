import unittest,tempfile,sqlite3,math
from pathlib import Path
from dataclasses import replace
from datetime import date,timedelta
from sma_analyzer.history_window import optimize_history,scoped_result,validate,preset
from sma_analyzer.engine import optimize_sma,simple_moving_average
from sma_analyzer.storage import LineStore
from sma_analyzer.model import AnalyzerModel
from sma_analyzer.mock_data import generate_mock_data
from sma_analyzer.notifications import evaluate_eod,NotificationSettings
from sma_analyzer.storage import SavedLine
from sma_analyzer.settings import DATA_VERSION

class HistoryTests(unittest.TestCase):
    def setUp(self):
        self.prices=[100+i*.01+4*math.sin(i/12) for i in range(1400)]
        self.dates=[(date(2019,1,1)+timedelta(days=i)).isoformat() for i in range(1400)]
    def test_scoring_uses_only_window_and_full_chart_keeps_daily_sma(self):
        left,right=250,1150;a,b=self.dates[left],self.dates[right]
        expected=optimize_sma(self.prices[left:right+1],4,dates=self.dates[left:right+1])
        got=optimize_history(self.prices,4,dates=self.dates,history_start=a,history_end=b)
        self.assertEqual((got.period,got.frequency,got.comparisons),(expected.period,expected.frequency,expected.comparisons))
        self.assertEqual(list(got.sma),simple_moving_average(self.prices,got.period))
        self.assertEqual(len(got.sma),len(self.prices));self.assertEqual(got.history_start,a)
        changed=self.prices[:];changed[:left]=[9999]*left;changed[right+1:]=[.1]*(len(changed)-right-1)
        other=optimize_history(changed,4,dates=self.dates,history_start=a,history_end=b)
        self.assertEqual((other.period,other.frequency),(got.period,got.frequency))
    def test_actual_limits_dates_gaps_and_default_compatibility(self):
        with self.assertRaisesRegex(ValueError,'4 trading'):validate(self.prices,self.dates,self.dates[-3],self.dates[-1])
        for a,b in [('2020-02-30','2021-01-01'),(self.dates[-1],self.dates[0]),('2010-01-01',self.dates[-1]),(False,''),('',self.dates[-1])]:
            with self.assertRaises(ValueError):validate(self.prices,self.dates,a,b)
        with self.assertRaises(ValueError):validate([None]*8,self.dates[:8])
        got=optimize_history(self.prices,4,dates=self.dates);old=optimize_sma(self.prices,4,dates=self.dates)
        self.assertEqual(got,old)
    def test_presets_are_frozen_dates_and_reconstruction_does_not_retune(self):
        a,b=preset(self.dates,3);got=optimize_history(self.prices,6,dates=self.dates,history_start=a,history_end=b)
        newer=self.prices+[999]*10;dates=self.dates+[(date.fromisoformat(self.dates[-1])+timedelta(days=i+1)).isoformat() for i in range(10)]
        view=scoped_result(newer,dates,got.period,6,a,b)
        self.assertEqual((view.period,view.history_end,view.frequency),(got.period,b,got.frequency))
    def test_legacy_sqlite_migration_and_independent_window_identity(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'legacy.db'
            with sqlite3.connect(path) as db:
                db.execute('CREATE TABLE saved_lines(id INTEGER PRIMARY KEY,counter TEXT NOT NULL,scenario TEXT NOT NULL,period INTEGER NOT NULL,target_frequency INTEGER NOT NULL,visible INTEGER NOT NULL DEFAULT 1,data_version INTEGER NOT NULL,UNIQUE(counter,scenario,period,target_frequency,data_version))')
                db.execute("INSERT INTO saved_lines VALUES (42,'A','X',20,4,0,1)")
            store=LineStore(path);self.assertEqual(store.get_line(42).history_start,'');self.assertFalse(store.get_line(42).visible)
            store.rename(42,'Plan');store.set_color(42,2);store.set_notifications(42,'phone',False)
            a,b=self.dates[20],self.dates[1000];store.save('A','X',20,4,a,b)
            self.assertEqual(len(store.list_all_lines()),2)
            other=next(l for l in store.list_all_lines() if l.id!=42);self.assertTrue(other.push_enabled)
            self.assertNotEqual(store.line_color_index(other),store.line_color_index(store.get_line(42)))
            store.delete(other.id);archive=store.recent_unsaved()[0];store.restore(archive.id)
            restored=next(l for l in store.list_all_lines() if l.history_start);self.assertEqual(restored.history_end,b)
            with self.assertRaises(ValueError):store.update_analysis(42,20,4,a,b)
            self.assertEqual(store.get_line(42).custom_name,'Plan')
            store.update_analysis(42,21,4,a,b);updated=store.get_line(42)
            self.assertEqual(updated.custom_name,'Plan');self.assertFalse(updated.push_enabled);self.assertEqual(store.line_color_index(updated),-3)
            self.assertEqual(len(LineStore(path).list_all_lines()),2)
    def test_browser_adapter_matches_same_python_scoring(self):
        from web.python.browser import calculate
        data=dict(prices=self.prices,dates=self.dates,preview=False,security={})
        a,b=self.dates[100],self.dates[-200]
        result=calculate(dict(data=data,lines=[],optimize=True,target=4,history_start=a,history_end=b))['result']
        direct=optimize_history(self.prices,4,dates=self.dates,history_start=a,history_end=b)
        self.assertEqual((result['period'],result['frequency'],result['history_end']),(direct.period,direct.actual_annual_frequency,b))

    def test_custom_alert_identity_is_separate_and_legacy_deliveries_do_not_replay(self):
        line=SavedLine(1,'DEMO-US','Oscillating',2,4,True)
        settings=NotificationSettings()
        original=evaluate_eod([4,2,5],line,settings)[0]
        self.assertEqual(original.key,repr((DATA_VERSION,'phone','buy','DEMO-US','Oscillating',2,4,3)))
        custom=replace(line,history_start='2019-01-01',history_end='2024-12-31',custom_name='Plan')
        scoped=evaluate_eod([4,2,5],custom,settings)[0]
        self.assertIn('Plan · 2019–2024',scoped.body)
        self.assertNotEqual(scoped.key,original.key)
        other=evaluate_eod([4,2,5],replace(custom,history_end='2025-12-31'),settings)[0]
        self.assertNotEqual(scoped.key,other.key)
        self.assertEqual(scoped.key,evaluate_eod([4,2,5],replace(custom,custom_name='Renamed'),settings)[0].key)

    def test_model_cache_is_scoped_and_old_result_is_not_replaced_on_selection(self):
        with tempfile.TemporaryDirectory() as d:
            model=AnalyzerModel(LineStore(Path(d)/'lines.db'))
            initial=model.calculate()
            key=model.data_fingerprint()
            dates=model.dataset.dates
            model.set_history(dates[80],dates[-80])
            self.assertTrue(model.history_stale)
            self.assertIs(model.result,initial)
            self.assertNotEqual(model.data_fingerprint(),key)
            with self.assertRaisesRegex(ValueError,'Recalculate'):model.save_current()
            scoped=model.calculate()
            self.assertEqual(scoped.history_start,dates[80])
            model.set_history('','')
            self.assertEqual(model.data_fingerprint(),key)
            self.assertEqual(model.calculate(),initial)
            model.save_current()
            saved=model.current_saved_line()
            model.view_saved_line(saved.id)
            self.assertFalse(model.toggle_current_saved())
            self.assertIsNone(model.editing_line_id)
            self.assertTrue(model.toggle_current_saved())
