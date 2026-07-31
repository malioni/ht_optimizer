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


class TestNormalizePosition(unittest.TestCase):
    def test_case_and_separator_insensitive(self):
        self.assertEqual(rank_players.normalize_position("WingBack"), "wingback")
        self.assertEqual(rank_players.normalize_position("central_defender"), "central defender")
        self.assertEqual(rank_players.normalize_position("Inner-Midfielder"), "inner midfielder")

    def test_unknown_position_raises(self):
        with self.assertRaises(ValueError) as ctx:
            rank_players.normalize_position("libero")
        self.assertIn("goalkeeper", str(ctx.exception))


class TestParseWeights(unittest.TestCase):
    def test_defaults_to_all_ones(self):
        weights = rank_players.parse_weights(None)
        self.assertEqual(weights, {s: 1.0 for s in ["LB", "MB", "RB", "M", "LF", "MF", "RF"]})

    def test_partial_override(self):
        weights = rank_players.parse_weights("MB=1.2,M=3")
        self.assertEqual(weights["MB"], 1.2)
        self.assertEqual(weights["M"], 3.0)
        self.assertEqual(weights["LB"], 1.0)

    def test_unknown_sector_raises(self):
        with self.assertRaises(ValueError):
            rank_players.parse_weights("XX=2")


if __name__ == "__main__":
    unittest.main()
