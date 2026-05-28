# LDVP Poker Statistics Dashboard

This project converts `LDVP - Statistiques annuelles.xlsx` into normalized CSV files and visualizes the league results in Streamlit.

## Setup

```bash
pip install -r requirements.txt
```

## Convert the Workbook

```bash
python convert_ldvp.py
```

Generated files are written to `data/`:

- `yearly_rankings.csv`
- `player_year_stats.csv`
- `event_buyins.csv`
- `event_positions.csv`
- `event_payouts.csv`
- `events.csv`
- `lifetime_stats.csv`
- `lifetime_yearly.csv`
- `players.csv`
- `players_of_year.csv`
- `payout_rules.csv`

The converter parses the repeated table markers in each `LDVP - YYYY` sheet: annual ranking, player summary, buy-ins, positions, payouts, and event totals.

## Validate

```bash
python validate_data.py
```

The validation script checks that expected data files exist and verifies a few known workbook values.

## Run the Dashboard

```bash
streamlit run dashboard.py
```

The dashboard includes current-year leaderboards, player performance, event summaries, lifetime standings, and raw generated tables.
