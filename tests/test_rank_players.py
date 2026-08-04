import contextlib
import csv
import io
import os
import tempfile
import unittest

import rank_players
import ratings


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


CSV_HEADER = (
    "PlayerID;FirstName;NickName;LastName;Age;AgeDays;Experience;Specialty;SpecialtyName;"
    "PlayerForm;StaminaSkill;"
    "KeeperSkill;PlaymakerSkill;ScorerSkill;PassingSkill;WingerSkill;"
    "DefenderSkill;SetPiecesSkill;"
)


def write_csv(rows: list[str]) -> str:
    fd, path = tempfile.mkstemp(suffix=".csv")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(CSV_HEADER + "\n")
        for row in rows:
            f.write(row + "\n")
    return path


class TestParsePlayers(unittest.TestCase):
    def test_parses_player_row(self):
        path = write_csv([
            "1;Danila;The Bull;Bykovskiy;21;72;5;5;H;7;8;1.0000;10.0200;2.0000;3.0000;8.0000;13.3299;3.0000;",
        ])
        self.addCleanup(os.remove, path)
        players, warnings = rank_players.parse_players(path)
        self.assertEqual(warnings, [])
        self.assertEqual(len(players), 1)
        player = players[0]
        self.assertEqual(player["name"], "Danila The Bull Bykovskiy")
        self.assertEqual(player["age"], "21.72")
        self.assertEqual(player["form"], 7.0)
        self.assertEqual(player["experience"], 5.0)
        self.assertEqual(player["specialty"], "Head")
        self.assertAlmostEqual(player["skills"]["Playmaking"], 10.02)
        self.assertAlmostEqual(player["skills"]["Defending"], 13.3299)
        self.assertAlmostEqual(player["skills"]["Set Pieces"], 3.0)

    def test_empty_nickname_omitted_from_name(self):
        path = write_csv([
            "2;Ako;;Jansons;21;77;4;0;;6;8;1.0;3.0;4.0;4.0;5.0;15.3045;2.0;",
        ])
        self.addCleanup(os.remove, path)
        players, _ = rank_players.parse_players(path)
        self.assertEqual(players[0]["name"], "Ako Jansons")
        self.assertEqual(players[0]["specialty"], "")

    def test_malformed_row_skipped_with_warning(self):
        path = write_csv([
            "3;Bad;;Row;21;10;3;0;;7;8;1.0;oops;4.0;4.0;5.0;15.0;2.0;",
            "4;Good;;Row;20;5;3;0;;7;8;1.0;3.0;4.0;4.0;5.0;15.0;2.0;",
        ])
        self.addCleanup(os.remove, path)
        players, warnings = rank_players.parse_players(path)
        self.assertEqual(len(players), 1)
        self.assertEqual(players[0]["name"], "Good Row")
        self.assertEqual(len(warnings), 1)
        self.assertIn("Bad", warnings[0])


ALL_ONE_WEIGHTS = {s: 1.0 for s in ["LB", "MB", "RB", "M", "LF", "MF", "RF"]}


def base_skills(**overrides):
    skills = {s: 1.0 for s in ["Goalkeeping", "Defending", "Playmaking",
                               "Passing", "Winger", "Scoring", "Set Pieces"]}
    skills.update(overrides)
    return skills


class TestOrderTotal(unittest.TestCase):
    def test_all_skills_at_one_gives_zero(self):
        total = rank_players.order_total(base_skills(), 1.0, "RWB", ALL_ONE_WEIGHTS)
        self.assertEqual(total, 0.0)

    def test_single_skill_matches_ratings_module(self):
        skills = base_skills(Defending=5.0)
        # RCD gets Defending contributions in MB and RB (Playmaking/M is zero at skill 1)
        expected = (
            ratings.calculate_sector_rating_contribution(5.0, "Defending", "MB", "RCD", 1.0)
            + ratings.calculate_sector_rating_contribution(5.0, "Defending", "RB", "RCD", 1.0)
        ) / 4.0
        total = rank_players.order_total(skills, 1.0, "RCD", ALL_ONE_WEIGHTS)
        self.assertAlmostEqual(total, expected)

    def test_sector_weights_scale_sectors(self):
        skills = base_skills(Defending=5.0)
        weights = dict(ALL_ONE_WEIGHTS, MB=2.0)
        expected = (
            2.0 * ratings.calculate_sector_rating_contribution(5.0, "Defending", "MB", "RCD", 1.0)
            + ratings.calculate_sector_rating_contribution(5.0, "Defending", "RB", "RCD", 1.0)
        ) / 4.0
        total = rank_players.order_total(skills, 1.0, "RCD", weights)
        self.assertAlmostEqual(total, expected)

    def test_form_is_passed_through(self):
        skills = base_skills(Defending=5.0)
        expected = (
            ratings.calculate_sector_rating_contribution(5.0, "Defending", "MB", "RCD", 0.925)
            + ratings.calculate_sector_rating_contribution(5.0, "Defending", "RB", "RCD", 0.925)
        ) / 4.0
        total = rank_players.order_total(skills, 0.925, "RCD", ALL_ONE_WEIGHTS)
        self.assertAlmostEqual(total, expected)


class TestRankPlayers(unittest.TestCase):
    def test_orders_by_best_total(self):
        players = [
            {"name": "Weak", "age": "20.1", "form": 7.0, "experience": 0.0,
             "skills": base_skills(Defending=5.0)},
            {"name": "Strong", "age": "20.1", "form": 7.0, "experience": 0.0,
             "skills": base_skills(Defending=10.0)},
        ]
        ranked = rank_players.rank_players(players, "central defender", ALL_ONE_WEIGHTS)
        self.assertEqual([p["name"] for p in ranked], ["Strong", "Weak"])
        self.assertEqual(set(ranked[0]["totals"]), {"normal", "towards wing", "offensive"})
        top = ranked[0]
        self.assertEqual(top["best_order"], max(top["totals"], key=top["totals"].get))

    def test_tie_on_best_broken_by_second_best(self):
        # Stub order_total to force an exact tie on the best total so the
        # second-highest total must decide the order.
        fake_totals = {
            "PlainCD": {"RCD": 10.0, "RCDTW": 5.0, "ROCD": 3.0},
            "WingCD": {"RCD": 10.0, "RCDTW": 7.0, "ROCD": 3.0},
        }
        original = rank_players.order_total
        rank_players.order_total = (
            lambda skills, fm, code, w, exp=0.0: fake_totals[skills["who"]][code])
        self.addCleanup(setattr, rank_players, "order_total", original)
        players = [
            {"name": "PlainCD", "age": "20.1", "form": 7.0, "experience": 0.0,
             "skills": {"who": "PlainCD"}},
            {"name": "WingCD", "age": "20.1", "form": 7.0, "experience": 0.0,
             "skills": {"who": "WingCD"}},
        ]
        ranked = rank_players.rank_players(players, "central defender", ALL_ONE_WEIGHTS)
        self.assertEqual([p["name"] for p in ranked], ["WingCD", "PlainCD"])
        self.assertEqual(ranked[0]["totals"]["normal"], ranked[1]["totals"]["normal"])


class TestExperienceEffect(unittest.TestCase):
    def test_sector_formulas(self):
        decay = 1 - 0.85 ** 4
        self.assertAlmostEqual(rank_players.experience_effect(4.0, "LB"), 0.36 * decay)
        self.assertAlmostEqual(rank_players.experience_effect(4.0, "RB"), 0.36 * decay)
        self.assertAlmostEqual(rank_players.experience_effect(4.0, "M"), 0.36 * decay)
        self.assertAlmostEqual(rank_players.experience_effect(4.0, "MB"), 0.36 * 7 / 8 * decay)
        self.assertAlmostEqual(rank_players.experience_effect(4.0, "LF"), 0.36 * 7 / 8 * decay)
        self.assertAlmostEqual(rank_players.experience_effect(4.0, "RF"), 0.36 * 7 / 8 * decay)
        self.assertAlmostEqual(rank_players.experience_effect(4.0, "MF"), 0.36 * 4 / 5 * decay)

    def test_zero_experience_gives_zero(self):
        for sector in ["LB", "MB", "RB", "M", "LF", "MF", "RF"]:
            self.assertEqual(rank_players.experience_effect(0.0, sector), 0.0)

    def test_order_total_adds_experience_only_to_contributing_sectors(self):
        # Skills all at 1 -> skill terms are zero; RCD contributes to MB, RB, M only.
        expected = sum(
            (rank_players.experience_effect(5.0, sector)
             * ratings.get_sector_factor(sector)) ** 1.2
            for sector in ["MB", "RB", "M"]
        ) / 4.0
        total = rank_players.order_total(base_skills(), 1.0, "RCD", ALL_ONE_WEIGHTS, exp=5.0)
        self.assertAlmostEqual(total, expected)

    def test_cd_towards_wing_gets_side_attack_experience(self):
        # RCDTW also contributes to RF (Winger), so its experience reaches side attack.
        rcd = rank_players.order_total(base_skills(), 1.0, "RCD", ALL_ONE_WEIGHTS, exp=5.0)
        rcdtw = rank_players.order_total(base_skills(), 1.0, "RCDTW", ALL_ONE_WEIGHTS, exp=5.0)
        rf_term = (rank_players.experience_effect(5.0, "RF")
                   * ratings.get_sector_factor("RF")) ** 1.2 / 4.0
        self.assertAlmostEqual(rcdtw - rcd, rf_term)

    def test_experience_term_not_affected_by_form(self):
        low_form = rank_players.order_total(base_skills(), 0.5, "RCD", ALL_ONE_WEIGHTS, exp=5.0)
        high_form = rank_players.order_total(base_skills(), 1.0, "RCD", ALL_ONE_WEIGHTS, exp=5.0)
        self.assertAlmostEqual(low_form, high_form)


class TestRankOptions(unittest.TestCase):
    def make_players(self):
        return [
            {"name": "GoodForm", "age": "20.1", "form": 8.0, "experience": 3.0,
             "specialty": "", "skills": base_skills(Defending=10.0)},
            {"name": "BadForm", "age": "20.1", "form": 4.0, "experience": 3.0,
             "specialty": "", "skills": base_skills(Defending=10.0)},
        ]

    def test_use_form_false_treats_all_forms_as_max(self):
        ranked = rank_players.rank_players(
            self.make_players(), "central defender", ALL_ONE_WEIGHTS, use_form=False)
        self.assertEqual(ranked[0]["totals"], ranked[1]["totals"])

    def test_use_form_true_separates_players(self):
        ranked = rank_players.rank_players(
            self.make_players(), "central defender", ALL_ONE_WEIGHTS, use_form=True)
        self.assertEqual(ranked[0]["name"], "GoodForm")
        self.assertNotEqual(ranked[0]["totals"], ranked[1]["totals"])

    def test_orders_filter_limits_totals_and_best(self):
        ranked = rank_players.rank_players(
            self.make_players(), "central defender", ALL_ONE_WEIGHTS,
            orders=["normal", "offensive"])
        self.assertEqual(set(ranked[0]["totals"]), {"normal", "offensive"})
        self.assertIn(ranked[0]["best_order"], {"normal", "offensive"})

    def test_unknown_order_raises(self):
        with self.assertRaises(ValueError) as ctx:
            rank_players.rank_players(
                self.make_players(), "central defender", ALL_ONE_WEIGHTS,
                orders=["normal", "sweeper"])
        self.assertIn("towards wing", str(ctx.exception))

    def test_average_is_mean_of_enabled_order_totals(self):
        ranked = rank_players.rank_players(
            self.make_players(), "central defender", ALL_ONE_WEIGHTS)
        entry = ranked[0]
        expected = sum(entry["totals"].values()) / len(entry["totals"])
        self.assertAlmostEqual(entry["average"], expected)


FULL_ROW = "1;Ako;;Jansons;21;77;4;2;Q;7;8;1.0;3.0;4.0;4.0;5.0;15.3045;2.0;"
FULL_ROW_2 = "2;Weak;;Player;19;10;2;0;;5;6;1.0;2.0;2.0;2.0;3.0;6.0;1.0;"


class TestMain(unittest.TestCase):
    def run_main(self, argv):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            rank_players.main(argv)
        return stdout.getvalue()

    def test_prints_ranked_table(self):
        path = write_csv([FULL_ROW_2, FULL_ROW])
        self.addCleanup(os.remove, path)
        out = self.run_main([path, "wingback"])
        lines = [line for line in out.splitlines() if line.strip()]
        self.assertIn("normal", lines[0])
        self.assertIn("towards middle", lines[0])
        ako_line = next(line for line in lines if "Ako Jansons" in line)
        weak_line = next(line for line in lines if "Weak Player" in line)
        self.assertLess(lines.index(ako_line), lines.index(weak_line))
        self.assertTrue(ako_line.strip().startswith("1"))

    def test_out_writes_csv(self):
        path = write_csv([FULL_ROW, FULL_ROW_2])
        self.addCleanup(os.remove, path)
        out_path = path + ".ranked.csv"
        self.addCleanup(os.remove, out_path)
        self.run_main([path, "wingback", "--out", out_path])
        with open(out_path, encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["Player"], "Ako Jansons")
        self.assertEqual(rows[0]["Rank"], "1")
        self.assertIn("normal", rows[0])

    def test_weights_change_ranking_totals(self):
        path = write_csv([FULL_ROW])
        self.addCleanup(os.remove, path)
        plain = self.run_main([path, "winger"])
        weighted = self.run_main([path, "winger", "--weights", "RF=5"])
        self.assertNotEqual(plain, weighted)

    def test_orders_flag_limits_columns(self):
        path = write_csv([FULL_ROW])
        self.addCleanup(os.remove, path)
        out = self.run_main([path, "wingback", "--orders", "normal,defensive"])
        header = out.splitlines()[0]
        self.assertIn("normal", header)
        self.assertIn("defensive", header)
        self.assertNotIn("towards middle", header)

    def test_ignore_form_flag_runs(self):
        path = write_csv([FULL_ROW, FULL_ROW_2])
        self.addCleanup(os.remove, path)
        out = self.run_main([path, "wingback", "--ignore-form"])
        self.assertIn("Ako Jansons", out)

    def test_table_includes_spec_and_avg_columns(self):
        path = write_csv([FULL_ROW])
        self.addCleanup(os.remove, path)
        out = self.run_main([path, "wingback"])
        header = out.splitlines()[0]
        self.assertIn("Spec", header)
        self.assertIn("Avg", header)
        self.assertIn("Quick", out)

    def test_unknown_position_exits_with_error(self):
        path = write_csv([FULL_ROW])
        self.addCleanup(os.remove, path)
        with self.assertRaises(SystemExit):
            with contextlib.redirect_stderr(io.StringIO()):
                self.run_main([path, "libero"])


if __name__ == "__main__":
    unittest.main()
