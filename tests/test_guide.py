import unittest
from sma_analyzer.guide import lesson_dataset, calculate_lesson, RECOVERY_HELP, RISK_HELP


class GuideTests(unittest.TestCase):
    def test_default_max_uses_all_history_and_selected_horizons_preserve_the_sma(self):
        full=calculate_lesson(4)
        self.assertEqual(full.report.start,0)
        self.assertEqual(full.report.end,755)
        self.assertEqual(full.result.target_frequency,4)
        for period,years,start in (("1Y","",504),("Custom","1.5",378)):
            selected=calculate_lesson(4,period=period,custom_years=years)
            self.assertEqual(selected.result,full.result)
            self.assertEqual(selected.report.start,start)
            self.assertLessEqual(len(selected.report.crossings.indices),len(full.report.crossings.indices))
            self.assertEqual(len(selected.report.crossings.indices),len(selected.report.dca.indices))
            self.assertEqual(len(selected.report.crossings.indices),len(selected.report.random.indices))

    def test_three_year_sample_has_recoveries_and_false_signals(self):
        lesson = calculate_lesson(6)
        self.assertEqual(len(lesson.dataset.prices),756)
        self.assertGreater(len(lesson.result.events),5)
        prices=lesson.dataset.prices
        self.assertTrue(any(prices[min(e.index+5,755)]<e.price for e in lesson.result.events))
        self.assertTrue(any(prices[min(e.index+5,755)]>e.price for e in lesson.result.events))
        self.assertEqual(lesson.dataset,lesson_dataset())

    def test_equal_buy_counts_and_requested_frequency(self):
        lesson=calculate_lesson(12)
        self.assertEqual(lesson.result.target_frequency,12)
        report=lesson.report
        self.assertEqual(len(report.crossings.indices),len(report.dca.indices))
        self.assertEqual(len(report.crossings.indices),len(report.random.indices))
        self.assertIn('may suggest',RECOVERY_HELP)
        self.assertIn('does not guarantee',RISK_HELP)
