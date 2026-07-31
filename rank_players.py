"""Rank players from a CSV export by rating contribution for a position."""

import csv

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
