import unittest
from sma_analyzer.guide import lesson_dataset, calculate_lesson, RECOVERY_HELP, RISK_HELP


class GuideTests(unittest.TestCase):
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
