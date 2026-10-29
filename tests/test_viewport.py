import unittest

from sma_analyzer.viewport import ChartViewport, RangeSelection, available_timelines


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

    def test_timeline_options_only_offer_complete_longer_ranges(self):
        self.assertEqual(available_timelines(100), ("1Y", "Max"))
        self.assertEqual(available_timelines(755), ("1Y", "Max"))
        self.assertEqual(available_timelines(756), ("1Y", "3Y", "Max"))
        self.assertEqual(available_timelines(1259), ("1Y", "3Y", "Max"))
        self.assertEqual(available_timelines(1260), ("1Y", "3Y", "5Y", "Max"))

    def test_timeline_windows_show_latest_sessions(self):
        view = ChartViewport(1260)
        for label, bounds in [("1Y", (1008,1259)), ("3Y", (504,1259)),
                              ("5Y", (0,1259)), ("Max", (0,1259))]:
            view.show_timeline(label)
            self.assertEqual(view.bounds, bounds)
            self.assertFalse(view.is_zoomed)

    def test_zoom_reset_restores_selected_timeline(self):
        view = ChartViewport(1260)
        view.show_timeline("1Y")
        view.select(1100, 1200)
        self.assertTrue(view.is_zoomed)
        view.reset()
        self.assertEqual(view.bounds, (1008,1259))
        self.assertFalse(view.is_zoomed)
        view.show_timeline("Max")
        self.assertEqual(view.bounds, (0,1259))

    def test_short_and_empty_history_timeline_handling(self):
        for count, bounds in [(0,(0,0)), (100,(0,99))]:
            view = ChartViewport(count)
            view.show_timeline("1Y")
            self.assertEqual(view.bounds, bounds)
            with self.assertRaises(ValueError):
                view.show_timeline("3Y")
            with self.assertRaises(ValueError):
                view.show_timeline("5Y")


class PinchTests(unittest.TestCase):
    def test_spread_and_contract_are_inverse_around_anchor(self):
        view = ChartViewport(1260)
        view.show_timeline('1Y')
        initial = view.bounds
        anchor = view.index_at(0.5)
        self.assertTrue(view.pinch(initial, anchor, .5, 2))
        self.assertLess(view.end-view.start, initial[1]-initial[0])
        self.assertAlmostEqual((view.start+view.end)/2, anchor, delta=1)
        zoomed = view.bounds
        view.pinch(zoomed, anchor, .5, .5)
        self.assertAlmostEqual(view.end-view.start, initial[1]-initial[0], delta=2)

    def test_pinch_bounds_and_minimum_span(self):
        view = ChartViewport(10)
        view.pinch((0, 9), 0, .9, .001)
        self.assertEqual(view.bounds, (0, 9))
        view.pinch((0, 9), 9, .1, 1000)
        self.assertEqual(view.bounds, (8, 9))
