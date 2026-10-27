import unittest

from sma_analyzer.viewport import ChartViewport, RangeSelection


class ViewportTests(unittest.TestCase):
    def test_both_drag_directions_choose_same_inclusive_sessions(self):
        for first, last in [(20.4, 80.2), (80.2, 20.4)]:
            view = ChartViewport(252)
            self.assertTrue(view.select(first, last))
            self.assertEqual(view.bounds, (20, 81))
            self.assertTrue(view.is_zoomed)

    def test_crossing_anchor_reorders_boundaries(self):
        selection = RangeSelection(50, 80)
        self.assertEqual((selection.start, selection.end), (50, 80))
        selection.cursor = 20
        self.assertEqual((selection.start, selection.end), (20, 50))
        selection.cursor = 50
        self.assertEqual((selection.start, selection.end), (50, 50))

    def test_nested_zoom_clamps_and_reset_restores_full_history(self):
        view = ChartViewport(252)
        view.select(40, 120)
        self.assertEqual(view.index_at(0.5), 80)
        self.assertEqual(view.index_at(-1), 40)
        self.assertEqual(view.index_at(2), 120)
        view.select(view.index_at(0.75), view.index_at(0.25))
        self.assertEqual(view.bounds, (60, 100))
        view.reset()
        self.assertEqual(view.bounds, (0, 251))
        self.assertFalse(view.is_zoomed)

    def test_y_limits_exclude_outside_extremes_and_include_visible_sma(self):
        view = ChartViewport(6)
        prices = [1000, 10, 12, 14, 16, -1000]
        sma = [None, None, 20, 15, 18, 500]
        view.select(1, 4)
        low, high = view.y_limits(prices, [sma])
        self.assertAlmostEqual(low, 8.7)
        self.assertAlmostEqual(high, 21.3)
        self.assertEqual(view.bounds, (1, 4))

    def test_empty_flat_missing_and_tap_ranges(self):
        empty = ChartViewport()
        self.assertFalse(empty.select(0, 10))
        self.assertIsNone(empty.y_limits([]))
        view = ChartViewport(4)
        self.assertFalse(view.select(2, 2))
        self.assertFalse(view.is_zoomed)
        self.assertEqual(view.y_limits([10] * 4), (9.99, 10.01))
        self.assertIsNone(view.y_limits([None, float('nan'), None, float('inf')]))
        view.select(-100, 100)
        self.assertFalse(view.is_zoomed)
        view.select(1, 2)
        view.reset(3)
        self.assertEqual(view.bounds, (0, 2))
        self.assertFalse(view.is_zoomed)
