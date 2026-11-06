"""Rolling activity window semantics, including calendar boundaries."""

import unittest

from job_search.recency import active_window_start, date_in_window


class RecencyTests(unittest.TestCase):
    def test_days_and_weeks(self):
        self.assertEqual("2026-10-07", str(active_window_start(30, "Days", as_of="2026-11-06")))
        self.assertEqual("2026-10-23", str(active_window_start(2, "Weeks", as_of="2026-11-06")))

    def test_calendar_months_and_years(self):
        self.assertEqual("2026-02-28", str(active_window_start(1, "Months", as_of="2026-03-31")))
        self.assertEqual("2024-02-28", str(active_window_start(1, "Years", as_of="2025-02-28")))
        self.assertEqual("2025-11-06", str(active_window_start(12, "Months", as_of="2026-11-06")))

    def test_inclusive_current_window_not_future(self):
        start=active_window_start(30, "Days", as_of="2026-11-06")
        self.assertTrue(date_in_window("2026-10-07", start, as_of="2026-11-06"))
        self.assertTrue(date_in_window("2026-11-06", start, as_of="2026-11-06"))
        self.assertFalse(date_in_window("2026-10-06", start, as_of="2026-11-06"))
        self.assertFalse(date_in_window("2026-11-07", start, as_of="2026-11-06"))
        self.assertFalse(date_in_window(None, start, as_of="2026-11-06"))

    def test_no_filter_and_incomplete_filter(self):
        self.assertIsNone(active_window_start(None, None))
        self.assertIsNone(active_window_start(0, ""))
        for count, unit in [(0, "Days"), (-1,"Days"), (1,None), (1,"Centuries"), (1.5,"Days")]:
            with self.subTest(count=count,unit=unit), self.assertRaises(ValueError):
                active_window_start(count,unit,as_of="2026-11-06")


if __name__ == '__main__':
    unittest.main()
