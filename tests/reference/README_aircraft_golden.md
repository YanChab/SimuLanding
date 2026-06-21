# Aircraft Golden Files

Two aircraft reference files exist and they do not have the same role.

## File Roles

- `golden_aircraft_summary.json`
  - Purpose: regression baseline consumed by `tests/test_aircraft_regression.py`.
  - Format: per-case object (`nominal`) with `summary`, `final`, `columns`.
  - Update path: regenerate only with `scripts/regen_golden_aircraft_test.py`.

- `golden_summary_aircraft.json`
  - Purpose: extracted project reference snapshot (summary-oriented artifact).
  - Format: `summary` and `summary_rows`.
  - Not consumed by `tests/test_aircraft_regression.py`.

## Important Rule

Do not overwrite `golden_aircraft_summary.json` from extraction scripts that
produce `golden_summary_aircraft.json`-style content. This causes false
regression failures.
