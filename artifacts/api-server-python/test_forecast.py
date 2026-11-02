from pathlib import Path
import sys
import unittest
from datetime import datetime, timedelta
sys.path.insert(0, str(Path(__file__).resolve().parent))
from src.analyzer import SalesRow, analyze


class ForecastTests(unittest.TestCase):
    def forecast(self, weekly_revenue):
        start = datetime(2024, 1, 1)
        rows = [SalesRow(start + timedelta(weeks=i), 'A', revenue, 1, 'North') for i, revenue in enumerate(weekly_revenue)]
        return analyze(rows).forecast

    def test_stable(self):
        f = self.forecast([100, 100, 100, 100])
        self.assertEqual((f.nextWeek, f.nextMonth, f.growthTrend), (100, 400, 'Stable'))

    def test_growing(self):
        f = self.forecast([100, 200, 300, 400])
        self.assertEqual(f.nextWeek, 500)
        self.assertEqual(f.nextMonth, 500 + 600 + 700 + 800)

    def test_declining_preserves_positive_weeks(self):
        f = self.forecast([1000, 800, 600, 400])
        self.assertEqual(f.nextWeek, 200)
        self.assertEqual(f.nextMonth, 200)

    def test_moderate_decline(self):
        f = self.forecast([1000, 900, 800, 700])
        self.assertEqual(f.nextMonth, 600 + 500 + 400 + 300)

    def test_zero_is_still_possible(self):
        f = self.forecast([900, 600, 300, 0])
        self.assertEqual((f.nextWeek, f.nextMonth), (0, 0))

    def test_single_week(self):
        f = self.forecast([500])
        self.assertEqual((f.nextWeek, f.nextMonth), (500, 2000))


if __name__ == '__main__':
    unittest.main()
