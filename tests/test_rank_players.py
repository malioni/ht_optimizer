import unittest

import rank_players


class TestFormMultiplier(unittest.TestCase):
    def test_exact_table_points(self):
        self.assertAlmostEqual(rank_players.form_multiplier(8.0), 1.0)
        self.assertAlmostEqual(rank_players.form_multiplier(7.0), 0.925)
        self.assertAlmostEqual(rank_players.form_multiplier(5.5), 0.8)
        self.assertAlmostEqual(rank_players.form_multiplier(1.5), 0.282)

    def test_linear_interpolation_between_points(self):
        # midpoint of 6.0 (0.844) and 6.5 (0.885)
        self.assertAlmostEqual(rank_players.form_multiplier(6.25), 0.8645)

    def test_clamping(self):
        self.assertAlmostEqual(rank_players.form_multiplier(1.0), 0.282)
        self.assertAlmostEqual(rank_players.form_multiplier(9.0), 1.0)


if __name__ == "__main__":
    unittest.main()
