from pathlib import Path

import pandas as pd

from convert_ldvp import DATA_DIR, WORKBOOK, parse_workbook, validate_tables

EXPECTED_FILES = [
    "yearly_rankings.csv",
    "player_year_stats.csv",
    "event_buyins.csv",
    "event_positions.csv",
    "event_payouts.csv",
    "events.csv",
    "lifetime_stats.csv",
    "lifetime_yearly.csv",
    "players.csv",
    "players_of_year.csv",
    "payout_rules.csv",
]


def assert_generated_files() -> None:
    missing = [file_name for file_name in EXPECTED_FILES if not (DATA_DIR / file_name).exists()]
    if missing:
        raise AssertionError(f"Missing generated files: {', '.join(missing)}")


def assert_known_values() -> None:
    rankings = pd.read_csv(DATA_DIR / "yearly_rankings.csv")
    stats = pd.read_csv(DATA_DIR / "player_year_stats.csv")
    events = pd.read_csv(DATA_DIR / "events.csv")

    sylvain_2026 = rankings[(rankings["year"] == 2026) & (rankings["player"] == "Sylvain Gagné")]
    if sylvain_2026.empty or float(sylvain_2026.iloc[0]["gain"]) != 240:
        raise AssertionError("Expected 2026 Sylvain Gagné ranking gain to be 240.")

    dany_2018 = stats[(stats["year"] == 2018) & (stats["player"] == "Dany MacDonald")]
    if dany_2018.empty or float(dany_2018.iloc[0]["net_gain"]) != 402.5:
        raise AssertionError("Expected 2018 Dany MacDonald net gain to be 402.5.")

    if len(events[events["year"] == 2026]) != 12:
        raise AssertionError("Expected 12 event slots for 2026.")


def main() -> None:
    if not WORKBOOK.exists():
        raise FileNotFoundError(f"Workbook not found: {WORKBOOK}")

    tables = parse_workbook(WORKBOOK)
    warnings = validate_tables(tables)
    assert_generated_files()
    assert_known_values()

    print("Validation smoke checks passed.")
    if warnings:
        print("Parser warnings:")
        for warning in warnings:
            print(f"- {warning}")


if __name__ == "__main__":
    main()
