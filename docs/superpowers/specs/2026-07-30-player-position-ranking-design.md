# Player Position Ranking Script — Design

Date: 2026-07-30

## Purpose

A CLI script, `rank_players.py`, that reads a player CSV export (semicolon-separated
game format) and a position name, and ranks all players in the file by their rating
contribution for that position. Reuses the existing `contributions.py` table and
`ratings.calculate_sector_rating_contribution` from this repo.

## Input

1. **CSV file** — semicolon-separated, header row, one player per row. Relevant columns:
   - `FirstName`, `NickName`, `LastName` — player identity
   - `Age`, `AgeDays` — shown in output
   - `PlayerForm` — form on the 1–8 scale
   - Skill columns mapped to skill names used by `contributions.py`:
     | CSV column | Skill name |
     |---|---|
     | `KeeperSkill` | Goalkeeping |
     | `DefenderSkill` | Defending |
     | `PlaymakerSkill` | Playmaking |
     | `PassingSkill` | Passing |
     | `WingerSkill` | Winger |
     | `ScorerSkill` | Scoring |
     | `SetPiecesSkill` | Set Pieces |
   - Decimal skill values are used as-is (sub-skill precision preserved).
2. **Position** — one of (case-insensitive): `goalkeeper`, `wingback`,
   `central defender`, `inner midfielder`, `winger`, `forward`.

All rows in the CSV are ranked for the requested position, regardless of the
position/category recorded in the file.

## Position → order variants

Left/right contribution entries are symmetric; one side (right) is used.

| Position | Orders (contribution-table codes) |
|---|---|
| goalkeeper | GK |
| wingback | RWB (normal), RWBD (defensive), RWBM (towards middle), RWBO (offensive) |
| central defender | RCD (normal), RCDTW (towards wing), ROCD (offensive) |
| inner midfielder | RIM (normal), RIMD (defensive), RIMO (offensive), RIMTW (towards wing) |
| winger | RW (normal), RWD (defensive), RWTM (towards middle), RWO (offensive) |
| forward | RFW (normal), RDF (defensive), RFTW (towards wing) |

## Calculation

Per player, per order:

```
total(order) = Σ over (skill, sector) pairs the order contributes to:
    sector_weight[sector] × calculate_sector_rating_contribution(
        skill_level, skill, sector, order_code, form_multiplier)
```

where `calculate_sector_rating_contribution` is the existing
`((skill − 1) × form × positional_factor × sector_factor)^1.2`.

The (skill, sector) pairs for an order are discovered from the contributions
table (all entries whose position code matches the order).

### Form multiplier

`PlayerForm` (1–8) maps to a multiplier via this table, with linear
interpolation between points:

| Form | Multiplier | | Form | Multiplier |
|---|---|---|---|---|
| 8.0 | 1.000 | | 4.5 | 0.707 |
| 7.5 | 0.964 | | 4.0 | 0.655 |
| 7.0 | 0.925 | | 3.5 | 0.598 |
| 6.5 | 0.885 | | 3.0 | 0.534 |
| 6.0 | 0.844 | | 2.5 | 0.462 |
| 5.5 | 0.800 | | 2.0 | 0.379 |
| 5.0 | 0.755 | | 1.5 | 0.282 |

Form values below 1.5 clamp to the 1.5 multiplier; above 8 clamp to 1.0.

### Ignored factors

Loyalty, experience, and stamina are ignored. Any rating-related factor not
present in the CSV (e.g. team spirit) is assumed to be at its best value,
which means it contributes no relative difference and is omitted.

## Ranking

For each player, the per-order totals are sorted descending into a tuple.
Players are compared lexicographically on that tuple: highest total first;
if equal, the second-highest breaks the tie, and so on.

## CLI

```
python rank_players.py <csv_file> <position> [--weights LB=1,MB=1.2,...] [--out ranked.csv]
```

- `<position>` — case-insensitive; multi-word names may be quoted
  (`"central defender"`) or joined with `_`/`-` (`central_defender`).
- `--weights` — comma-separated `SECTOR=value` overrides; sectors are
  `LB, MB, RB, M, LF, MF, RF`; every sector defaults to 1.0.
- `--out` — additionally write the ranked result to a CSV file.

## Output

Ranked table to stdout: rank, player name, age (years.days), form, one column
per order total (best order marked). With `--out`, the same data is written as
a CSV file.

## Error handling

- Unknown position → error listing valid position names.
- Row with malformed/missing skill or form values → skipped with a warning
  naming the player; ranking continues with the rest.

## Components

- `rank_players.py` (new) — CSV parsing, form mapping, ranking, CLI, output.
- `contributions.py` (existing, unchanged) — contribution table.
- `ratings.py` (existing, unchanged) — sector rating contribution formula.
