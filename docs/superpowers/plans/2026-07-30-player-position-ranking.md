# Player Position Ranking Script Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A CLI script `rank_players.py` that reads a semicolon-separated player CSV export and a position name, and ranks all players by their rating contribution for that position, per the spec in `docs/superpowers/specs/2026-07-30-player-position-ranking-design.md`.

**Architecture:** One new module `rank_players.py` at the repo root reusing the existing `contributions.py` table and `ratings.calculate_sector_rating_contribution`. Pure helper functions (form mapping, CSV parsing, per-order totals, ranking) plus an argparse CLI. Tests use stdlib `unittest` (the repo venv is broken and pytest is not installed — do NOT add dependencies).

**Tech Stack:** Python 3 stdlib only (`csv`, `argparse`, `unittest`). Run everything from the repo root `/Users/matiss/Documents/Optimization_git` with system `python3`.

**Important repo quirks:**
- The repo root contains `logging.py` which shadows stdlib logging. `rank_players.py` must NOT import `logging`.
- CSV files are `;`-separated with a trailing empty column; `csv.DictReader(f, delimiter=";")` handles this fine.
- All test commands are `python3 -m unittest tests.test_rank_players -v` from the repo root; `tests/__init__.py` makes `tests` a package so this works.

---

### Task 1: Form multiplier

**Files:**
- Create: `rank_players.py`
- Create: `tests/__init__.py` (empty)
- Test: `tests/test_rank_players.py`

- [ ] **Step 1: Write the failing test**

Create empty `tests/__init__.py`, then `tests/test_rank_players.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run from repo root: `python3 -m unittest tests.test_rank_players -v`
Expected: FAIL/ERROR with `ModuleNotFoundError: No module named 'rank_players'`

- [ ] **Step 3: Write minimal implementation**

Create `rank_players.py`:

```python
"""Rank players from a CSV export by rating contribution for a position."""

FORM_TABLE = [
    (1.5, 0.282), (2.0, 0.379), (2.5, 0.462), (3.0, 0.534),
    (3.5, 0.598), (4.0, 0.655), (4.5, 0.707), (5.0, 0.755),
    (5.5, 0.800), (6.0, 0.844), (6.5, 0.885), (7.0, 0.925),
    (7.5, 0.964), (8.0, 1.000),
]


def form_multiplier(form: float) -> float:
    """Map the game's 1-8 form value to a rating multiplier, interpolating linearly."""
    if form <= FORM_TABLE[0][0]:
        return FORM_TABLE[0][1]
    if form >= FORM_TABLE[-1][0]:
        return FORM_TABLE[-1][1]
    for (lo_f, lo_m), (hi_f, hi_m) in zip(FORM_TABLE, FORM_TABLE[1:]):
        if lo_f <= form <= hi_f:
            return lo_m + (hi_m - lo_m) * (form - lo_f) / (hi_f - lo_f)
    raise ValueError(f"unreachable form value: {form}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_rank_players -v`
Expected: 3 tests, OK

- [ ] **Step 5: Commit**

```bash
git add rank_players.py tests/__init__.py tests/test_rank_players.py
git commit -m "feat: add form multiplier with interpolation for player ranking"
```

---

### Task 2: Position normalization and sector weights parsing

**Files:**
- Modify: `rank_players.py`
- Test: `tests/test_rank_players.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_rank_players.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest tests.test_rank_players -v`
Expected: new tests ERROR with `AttributeError` (functions not defined); Task 1 tests still pass.

- [ ] **Step 3: Write minimal implementation**

Append to `rank_players.py`:

```python
SECTORS = ["LB", "MB", "RB", "M", "LF", "MF", "RF"]

# Order label -> contribution-table position code (right side; tables are symmetric).
POSITION_ORDERS = {
    "goalkeeper": {"normal": "GK"},
    "wingback": {"normal": "RWB", "defensive": "RWBD",
                 "towards middle": "RWBM", "offensive": "RWBO"},
    "central defender": {"normal": "RCD", "towards wing": "RCDTW", "offensive": "ROCD"},
    "inner midfielder": {"normal": "RIM", "defensive": "RIMD",
                         "offensive": "RIMO", "towards wing": "RIMTW"},
    "winger": {"normal": "RW", "defensive": "RWD",
               "towards middle": "RWTM", "offensive": "RWO"},
    "forward": {"normal": "RFW", "defensive": "RDF", "towards wing": "RFTW"},
}


def normalize_position(position: str) -> str:
    normalized = position.strip().lower().replace("_", " ").replace("-", " ")
    if normalized not in POSITION_ORDERS:
        valid = ", ".join(POSITION_ORDERS)
        raise ValueError(f"unknown position {position!r}; valid positions: {valid}")
    return normalized


def parse_weights(spec: str | None) -> dict[str, float]:
    weights = {sector: 1.0 for sector in SECTORS}
    if spec:
        for part in spec.split(","):
            sector, _, value = part.partition("=")
            sector = sector.strip().upper()
            if sector not in weights:
                raise ValueError(f"unknown sector {sector!r}; valid sectors: {', '.join(SECTORS)}")
            weights[sector] = float(value)
    return weights
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest tests.test_rank_players -v`
Expected: 8 tests, OK

- [ ] **Step 5: Commit**

```bash
git add rank_players.py tests/test_rank_players.py
git commit -m "feat: add position normalization and sector weight parsing"
```

---

### Task 3: CSV parsing

**Files:**
- Modify: `rank_players.py`
- Test: `tests/test_rank_players.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_rank_players.py` (add `import os`, `import tempfile` at the top of the file):

```python
CSV_HEADER = (
    "PlayerID;FirstName;NickName;LastName;Age;AgeDays;PlayerForm;StaminaSkill;"
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
            "1;Danila;The Bull;Bykovskiy;21;72;7;8;1.0000;10.0200;2.0000;3.0000;8.0000;13.3299;3.0000;",
        ])
        self.addCleanup(os.remove, path)
        players, warnings = rank_players.parse_players(path)
        self.assertEqual(warnings, [])
        self.assertEqual(len(players), 1)
        player = players[0]
        self.assertEqual(player["name"], "Danila The Bull Bykovskiy")
        self.assertEqual(player["age"], "21.72")
        self.assertEqual(player["form"], 7.0)
        self.assertAlmostEqual(player["skills"]["Playmaking"], 10.02)
        self.assertAlmostEqual(player["skills"]["Defending"], 13.3299)
        self.assertAlmostEqual(player["skills"]["Set Pieces"], 3.0)

    def test_empty_nickname_omitted_from_name(self):
        path = write_csv([
            "2;Ako;;Jansons;21;77;6;8;1.0;3.0;4.0;4.0;5.0;15.3045;2.0;",
        ])
        self.addCleanup(os.remove, path)
        players, _ = rank_players.parse_players(path)
        self.assertEqual(players[0]["name"], "Ako Jansons")

    def test_malformed_row_skipped_with_warning(self):
        path = write_csv([
            "3;Bad;;Row;21;10;7;8;1.0;oops;4.0;4.0;5.0;15.0;2.0;",
            "4;Good;;Row;20;5;7;8;1.0;3.0;4.0;4.0;5.0;15.0;2.0;",
        ])
        self.addCleanup(os.remove, path)
        players, warnings = rank_players.parse_players(path)
        self.assertEqual(len(players), 1)
        self.assertEqual(players[0]["name"], "Good Row")
        self.assertEqual(len(warnings), 1)
        self.assertIn("Bad", warnings[0])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest tests.test_rank_players -v`
Expected: new tests ERROR with `AttributeError: ... no attribute 'parse_players'`

- [ ] **Step 3: Write minimal implementation**

Add `import csv` at the top of `rank_players.py`, then append:

```python
SKILL_COLUMNS = {
    "KeeperSkill": "Goalkeeping",
    "DefenderSkill": "Defending",
    "PlaymakerSkill": "Playmaking",
    "PassingSkill": "Passing",
    "WingerSkill": "Winger",
    "ScorerSkill": "Scoring",
    "SetPiecesSkill": "Set Pieces",
}


def parse_players(csv_path: str) -> tuple[list[dict], list[str]]:
    """Read the player export; returns (players, warnings for skipped rows)."""
    players = []
    warnings = []
    with open(csv_path, encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter=";"):
            name = " ".join(
                part for part in (row.get("FirstName"), row.get("NickName"), row.get("LastName"))
                if part
            )
            try:
                skills = {skill: float(row[column]) for column, skill in SKILL_COLUMNS.items()}
                form = float(row["PlayerForm"])
            except (KeyError, TypeError, ValueError) as exc:
                warnings.append(f"skipping {name or '<unnamed row>'}: bad or missing value ({exc})")
                continue
            players.append({
                "name": name,
                "age": f"{row.get('Age', '?')}.{row.get('AgeDays', '?')}",
                "form": form,
                "skills": skills,
            })
    return players, warnings
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest tests.test_rank_players -v`
Expected: 11 tests, OK

- [ ] **Step 5: Commit**

```bash
git add rank_players.py tests/test_rank_players.py
git commit -m "feat: parse player CSV export with per-row error handling"
```

---

### Task 4: Per-order contribution totals

**Files:**
- Modify: `rank_players.py`
- Test: `tests/test_rank_players.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_rank_players.py` (add `import ratings` at the top of the file):

```python
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
        )
        total = rank_players.order_total(skills, 1.0, "RCD", ALL_ONE_WEIGHTS)
        self.assertAlmostEqual(total, expected)

    def test_sector_weights_scale_sectors(self):
        skills = base_skills(Defending=5.0)
        weights = dict(ALL_ONE_WEIGHTS, MB=2.0)
        expected = (
            2.0 * ratings.calculate_sector_rating_contribution(5.0, "Defending", "MB", "RCD", 1.0)
            + ratings.calculate_sector_rating_contribution(5.0, "Defending", "RB", "RCD", 1.0)
        )
        total = rank_players.order_total(skills, 1.0, "RCD", weights)
        self.assertAlmostEqual(total, expected)

    def test_form_is_passed_through(self):
        skills = base_skills(Defending=5.0)
        expected = (
            ratings.calculate_sector_rating_contribution(5.0, "Defending", "MB", "RCD", 0.925)
            + ratings.calculate_sector_rating_contribution(5.0, "Defending", "RB", "RCD", 0.925)
        )
        total = rank_players.order_total(skills, 0.925, "RCD", ALL_ONE_WEIGHTS)
        self.assertAlmostEqual(total, expected)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest tests.test_rank_players -v`
Expected: new tests ERROR with `AttributeError: ... no attribute 'order_total'`

- [ ] **Step 3: Write minimal implementation**

Add `import contributions` and `import ratings` at the top of `rank_players.py`, then append:

```python
def order_total(skills: dict[str, float], form_mult: float,
                order_code: str, weights: dict[str, float]) -> float:
    """Weighted sum of a player's sector rating contributions for one order."""
    total = 0.0
    for (position, skill, sector) in contributions.contributions:
        if position != order_code:
            continue
        total += weights[sector] * ratings.calculate_sector_rating_contribution(
            skill_level=skills[skill],
            skill_type=skill,
            sector=sector,
            position=order_code,
            form=form_mult,
        )
    return total
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest tests.test_rank_players -v`
Expected: 15 tests, OK

- [ ] **Step 5: Commit**

```bash
git add rank_players.py tests/test_rank_players.py
git commit -m "feat: compute weighted per-order rating contribution totals"
```

---

### Task 5: Ranking with lexicographic tie-break

**Files:**
- Modify: `rank_players.py`
- Test: `tests/test_rank_players.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_rank_players.py`:

```python
class TestRankPlayers(unittest.TestCase):
    def test_orders_by_best_total(self):
        players = [
            {"name": "Weak", "age": "20.1", "form": 7.0, "skills": base_skills(Defending=5.0)},
            {"name": "Strong", "age": "20.1", "form": 7.0, "skills": base_skills(Defending=10.0)},
        ]
        ranked = rank_players.rank_players(players, "central defender", ALL_ONE_WEIGHTS)
        self.assertEqual([p["name"] for p in ranked], ["Strong", "Weak"])
        self.assertEqual(set(ranked[0]["totals"]), {"normal", "towards wing", "offensive"})
        self.assertEqual(ranked[0]["best_order"], "normal")

    def test_tie_on_best_broken_by_second_best(self):
        # Identical Defending -> identical best (normal) total; higher Winger
        # only lifts the towards-wing/offensive orders, breaking the tie.
        players = [
            {"name": "PlainCD", "age": "20.1", "form": 7.0,
             "skills": base_skills(Defending=10.0, Winger=2.0)},
            {"name": "WingCD", "age": "20.1", "form": 7.0,
             "skills": base_skills(Defending=10.0, Winger=8.0)},
        ]
        ranked = rank_players.rank_players(players, "central defender", ALL_ONE_WEIGHTS)
        first_totals = sorted(ranked[0]["totals"].values(), reverse=True)
        second_totals = sorted(ranked[1]["totals"].values(), reverse=True)
        self.assertAlmostEqual(first_totals[0], second_totals[0])
        self.assertGreater(first_totals[1], second_totals[1])
        self.assertEqual(ranked[0]["name"], "WingCD")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest tests.test_rank_players -v`
Expected: new tests ERROR with `AttributeError: ... no attribute 'rank_players'`

- [ ] **Step 3: Write minimal implementation**

Append to `rank_players.py`:

```python
def rank_players(players: list[dict], position: str,
                 weights: dict[str, float]) -> list[dict]:
    """Return players sorted best-first for the position.

    Comparison is lexicographic on each player's descending per-order totals:
    highest total first, ties broken by the second-highest, and so on.
    """
    orders = POSITION_ORDERS[position]
    ranked = []
    for player in players:
        form_mult = form_multiplier(player["form"])
        totals = {
            label: order_total(player["skills"], form_mult, code, weights)
            for label, code in orders.items()
        }
        entry = dict(player)
        entry["totals"] = totals
        entry["best_order"] = max(totals, key=totals.get)
        ranked.append(entry)
    ranked.sort(key=lambda e: sorted(e["totals"].values(), reverse=True), reverse=True)
    return ranked
```

Note: `rank_players()` intentionally shares its name with the module; tests access it as `rank_players.rank_players`. Verify the tie-break test passes — if `first_totals[1]` equals `second_totals[1]`, adjust the Winger levels (the intent is: identical best total, different second total).

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest tests.test_rank_players -v`
Expected: 17 tests, OK

- [ ] **Step 5: Commit**

```bash
git add rank_players.py tests/test_rank_players.py
git commit -m "feat: rank players lexicographically by per-order totals"
```

---

### Task 6: CLI, table output, CSV output, end-to-end verification

**Files:**
- Modify: `rank_players.py`
- Test: `tests/test_rank_players.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_rank_players.py` (add `import io`, `import contextlib` at the top of the file):

```python
FULL_ROW = "1;Ako;;Jansons;21;77;7;8;1.0;3.0;4.0;4.0;5.0;15.3045;2.0;"
FULL_ROW_2 = "2;Weak;;Player;19;10;5;6;1.0;2.0;2.0;2.0;3.0;6.0;1.0;"


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

    def test_unknown_position_exits_with_error(self):
        path = write_csv([FULL_ROW])
        self.addCleanup(os.remove, path)
        with self.assertRaises(SystemExit):
            self.run_main([path, "libero"])
```

Also add `import csv` to the test file's imports (used by `test_out_writes_csv`).

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest tests.test_rank_players -v`
Expected: new tests ERROR with `AttributeError: ... no attribute 'main'`

- [ ] **Step 3: Write the implementation**

Add `import argparse` and `import sys` at the top of `rank_players.py`, then append:

```python
def format_table(ranked: list[dict], order_labels: list[str]) -> str:
    headers = ["Rank", "Player", "Age", "Form"] + order_labels + ["Best"]
    rows = []
    for rank, entry in enumerate(ranked, start=1):
        rows.append(
            [str(rank), entry["name"], entry["age"], f"{entry['form']:g}"]
            + [f"{entry['totals'][label]:.3f}" for label in order_labels]
            + [entry["best_order"]]
        )
    widths = [max(len(headers[i]), *(len(row[i]) for row in rows)) if rows else len(headers[i])
              for i in range(len(headers))]
    lines = [
        "  ".join(header.ljust(widths[i]) for i, header in enumerate(headers)),
        "  ".join("-" * width for width in widths),
    ]
    for row in rows:
        lines.append("  ".join(cell.ljust(widths[i]) for i, cell in enumerate(row)))
    return "\n".join(lines)


def write_output_csv(path: str, ranked: list[dict], order_labels: list[str]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Rank", "Player", "Age", "Form"] + order_labels + ["Best"])
        for rank, entry in enumerate(ranked, start=1):
            writer.writerow(
                [rank, entry["name"], entry["age"], entry["form"]]
                + [f"{entry['totals'][label]:.4f}" for label in order_labels]
                + [entry["best_order"]]
            )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Rank players from a CSV export by rating contribution for a position.")
    parser.add_argument("csv_file", help="semicolon-separated player export")
    parser.add_argument("position",
                        help="goalkeeper, wingback, central defender, inner midfielder, "
                             "winger or forward (case-insensitive; _ or - work as spaces)")
    parser.add_argument("--weights", default=None,
                        help="sector weight overrides, e.g. MB=1.2,M=3 "
                             "(sectors LB,MB,RB,M,LF,MF,RF; default 1.0 each)")
    parser.add_argument("--out", default=None, help="also write the ranking to this CSV file")
    args = parser.parse_args(argv)

    try:
        position = normalize_position(args.position)
        weights = parse_weights(args.weights)
    except ValueError as exc:
        parser.error(str(exc))

    players, warnings = parse_players(args.csv_file)
    for warning in warnings:
        print(f"warning: {warning}", file=sys.stderr)

    ranked = rank_players(players, position, weights)
    order_labels = list(POSITION_ORDERS[position])
    print(format_table(ranked, order_labels))
    if args.out:
        write_output_csv(args.out, ranked, order_labels)
        print(f"\nwrote {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest tests.test_rank_players -v`
Expected: 21 tests, OK

- [ ] **Step 5: End-to-end run on the real export**

Run:
```bash
python3 rank_players.py "/Users/matiss/Downloads/Players U21 Latvija, List Gen-41 CC-WC final _ WB (page 1 of 1).csv" wingback
```
Expected: a ranked table of all 34 players with columns `normal, defensive, towards middle, offensive`; no warnings; players with high Defending+Winger and good form (e.g. Artem Korasev) near the top.

Also sanity-check weights and CSV output:
```bash
python3 rank_players.py "/Users/matiss/Downloads/Players U21 Latvija, List Gen-41 CC-WC final _ WB (page 1 of 1).csv" wingback --weights MB=1.32,M=3 --out /tmp/ranked_wb.csv
```
Expected: table prints, `/tmp/ranked_wb.csv` exists with 35 lines (header + 34 players).

- [ ] **Step 6: Commit**

```bash
git add rank_players.py tests/test_rank_players.py
git commit -m "feat: add CLI with table and CSV output for player ranking"
```
