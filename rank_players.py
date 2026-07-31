"""Rank players from a CSV export by rating contribution for a position."""

import argparse
import csv
import sys

import contributions
import ratings

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


SECTORS = ["LB", "MB", "RB", "M", "LF", "MF", "RF"]

# Experience adds a flat per-sector bonus after form; coefficients differ by line.
EXP_SECTOR_COEFF = {
    "LB": 0.36, "RB": 0.36, "M": 0.36,
    "MB": 0.36 * 7 / 8, "LF": 0.36 * 7 / 8, "RF": 0.36 * 7 / 8,
    "MF": 0.36 * 4 / 5,
}


def experience_effect(exp: float, sector: str) -> float:
    return EXP_SECTOR_COEFF[sector] * (1 - 0.85 ** exp)

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
                experience = float(row["Experience"])
            except (KeyError, TypeError, ValueError) as exc:
                warnings.append(f"skipping {name or '<unnamed row>'}: bad or missing value ({exc})")
                continue
            players.append({
                "name": name,
                "age": f"{row.get('Age', '?')}.{row.get('AgeDays', '?')}",
                "form": form,
                "experience": experience,
                "skills": skills,
            })
    return players, warnings


def order_total(skills: dict[str, float], form_mult: float,
                order_code: str, weights: dict[str, float],
                exp: float = 0.0) -> float:
    """Weighted sum of a player's sector rating contributions for one order.

    Experience adds a flat bonus (independent of form) to every sector the
    order contributes to; sectors the order does not touch get nothing, which
    reproduces the game rule that e.g. a central defender's experience reaches
    side attack only with the towards-wing order.

    The total is divided by 4, matching the team-rating scale used in
    ratings.calculate_team_ratings (rating**1.2 / 4 + 1).
    """
    total = 0.0
    exp_sectors = set()
    for (position, skill, sector) in contributions.contributions:
        if position != order_code:
            continue
        exp_sectors.add(sector)
        total += weights[sector] * ratings.calculate_sector_rating_contribution(
            skill_level=skills[skill],
            skill_type=skill,
            sector=sector,
            position=order_code,
            form=form_mult,
        )
    for sector in exp_sectors:
        total += weights[sector] * (
            experience_effect(exp, sector) * ratings.get_sector_factor(sector)) ** 1.2
    return total / 4.0


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
            label: order_total(player["skills"], form_mult, code, weights,
                               exp=player["experience"])
            for label, code in orders.items()
        }
        entry = dict(player)
        entry["totals"] = totals
        entry["best_order"] = max(totals, key=totals.get)
        ranked.append(entry)
    ranked.sort(key=lambda e: sorted(e["totals"].values(), reverse=True), reverse=True)
    return ranked


def format_table(ranked: list[dict], order_labels: list[str]) -> str:
    headers = ["Rank", "Player", "Age", "Form", "Exp"] + order_labels + ["Best"]
    rows = []
    for rank, entry in enumerate(ranked, start=1):
        rows.append(
            [str(rank), entry["name"], entry["age"], f"{entry['form']:g}",
             f"{entry['experience']:g}"]
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
        writer.writerow(["Rank", "Player", "Age", "Form", "Exp"] + order_labels + ["Best"])
        for rank, entry in enumerate(ranked, start=1):
            writer.writerow(
                [rank, entry["name"], entry["age"], entry["form"], entry["experience"]]
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
