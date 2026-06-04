# LDVP Poker Statistics Dashboard

This project converts `LDVP - Statistiques annuelles.xlsx` into normalized CSV files and visualizes the league results in Streamlit.

## Setup

```bash
pip install -r requirements.txt
```

## Run the Dashboard

```bash
streamlit run dashboard.py
```

The dashboard includes current-year leaderboards, player performance, event summaries, lifetime standings, and raw generated tables.

If no data has been loaded yet, the dashboard shows an upload page where you can upload `LDVP - Statistiques annuelles.xlsx` directly through the browser.

## Convert the Workbook (optional CLI)

If you prefer to convert the workbook from the command line instead of through the upload page:

```bash
python convert_ldvp.py
```

This requires `LDVP - Statistiques annuelles.xlsx` to be present in the project root. Generated files are written to `data/`:

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
