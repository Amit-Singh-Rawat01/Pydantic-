import statistics
import unittest

from robust_stats import robust_baseline


class RobustBaselineTests(unittest.TestCase):
    def test_large_spikes_do_not_move_the_baseline(self):
        normal = [8, 9, 7, 10, 6, 8, 9, 7] * 7
        values = normal + [1200, 1180, 1210, 1190]

        median, sigma = robust_baseline(values)

        self.assertEqual(median, 8)
        self.assertAlmostEqual(sigma, 8**0.5)
        self.assertAlmostEqual((100 - median) / sigma, 32.53, places=2)

    def test_empty_values_raise_statistics_error(self):
        with self.assertRaises(statistics.StatisticsError):
            robust_baseline([])


if __name__ == "__main__":
    unittest.main()
