from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import pandas as pd

WORKBOOK = Path("LDVP - Statistiques annuelles.xlsx")
DATA_DIR = Path("data")

YEAR_SHEET_RE = re.compile(r"^LDVP - (?P<year>\d{4})$")
MONTHS = {
    "JAN": 1,
    "FEV": 2,
    "FEB": 2,
    "MAR": 3,
    "AVR": 4,
    "APR": 4,
    "MAY": 5,
    "MAI": 5,
    "JUIN": 6,
    "JUN": 6,
    "JUI": 7,
    "JUL": 7,
    "AOUT": 8,
    "AOU": 8,
    "AUG": 8,
    "SEPT": 9,
    "SEP": 9,
    "OCT": 10,
    "NOV": 11,
    "DEC": 12,
}
SUMMARY_LABELS = {
    "POT TOTAL",
    "NOMBRE DE PAYOUTS",
    "NOMBRE DE JOUEURS",
    "TOTAL",
    "TOT",
    "HOST",
    "BUY-IN",
    "POSITION",
    "PAYOUT",
    "POINTS",
    "TOT PAYOUT",
}


def clean_text(value: object) -> Optional[str]:
    if pd.isna(value):
        return None
    text = str(value).strip()
    return text or None


def to_number(value: object) -> Optional[float]:
    if pd.isna(value):
        return None
    numeric = pd.to_numeric(value, errors="coerce")
    if pd.isna(numeric):
        return None
    return float(numeric)


def to_int(value: object) -> Optional[int]:
    number = to_number(value)
    if number is None:
        return None
    return int(number)


def year_sheets(workbook: pd.ExcelFile) -> Iterable[Tuple[int, str]]:
    for sheet_name in workbook.sheet_names:
        match = YEAR_SHEET_RE.match(sheet_name)
        if match:
            yield int(match.group("year")), sheet_name


def find_marker(df: pd.DataFrame, marker: str) -> Optional[Tuple[int, int]]:
    for row_index, row in df.iterrows():
        for col_index, value in row.items():
            if clean_text(value) == marker:
                return int(row_index), int(col_index)
    return None


def find_marker_after(df: pd.DataFrame, marker: str, after_row: int) -> Optional[Tuple[int, int]]:
    for row_index in range(after_row + 1, df.shape[0]):
        row = df.iloc[row_index]
        for col_index, value in row.items():
            if clean_text(value) == marker:
                return int(row_index), int(col_index)
    return None


def find_first_marker(df: pd.DataFrame, markers: Iterable[str]) -> Optional[Tuple[int, int]]:
    for marker in markers:
        found = find_marker(df, marker)
        if found:
            return found
    return None


def normalized_label(value: object) -> str:
    return clean_text(value).upper() if clean_text(value) else ""


def is_player_name(value: object) -> bool:
    name = clean_text(value)
    if not name:
        return False
    return normalized_label(name) not in SUMMARY_LABELS


def parse_event_label(year: int, order: int, value: object) -> Dict[str, object]:
    if isinstance(value, pd.Timestamp):
        return {
            "event_order": order,
            "event_label": value.strftime("%Y-%m-%d"),
            "event_month": value.month,
            "event_day": value.day,
            "event_date": value.date().isoformat(),
        }

    text = clean_text(value)
    if not text:
        return {
            "event_order": order,
            "event_label": f"Event {order}",
            "event_month": None,
            "event_day": None,
            "event_date": None,
        }

    datetime_value = pd.to_datetime(text, errors="coerce")
    if not pd.isna(datetime_value) and re.search(r"\d{4}", text):
        return {
            "event_order": order,
            "event_label": text,
            "event_month": datetime_value.month,
            "event_day": datetime_value.day,
            "event_date": datetime_value.date().isoformat(),
        }

    match = re.match(r"([A-ZÉÛ]+)\s*(?:\((\d{1,2})\))?", text.upper())
    month = MONTHS.get(match.group(1)) if match else None
    day = int(match.group(2)) if match and match.group(2) else None
    event_date = f"{year}-{month:02d}-{day:02d}" if month and day else None
    return {
        "event_order": order,
        "event_label": text,
        "event_month": month,
        "event_day": day,
        "event_date": event_date,
    }


def event_columns(df: pd.DataFrame, marker_row: int, marker_col: int) -> List[Dict[str, object]]:
    columns: List[Dict[str, object]] = []
    event_order = 1
    for col_index in range(marker_col + 1, df.shape[1]):
        header = clean_text(df.iat[marker_row, col_index])
        if not header:
            continue
        if normalized_label(header) in {"TOTAL", "TOT", "# GAMES", "BUBBLE"}:
            break
        columns.append({"source_col": col_index, "event_order": event_order, "raw_label": header})
        event_order += 1
    return columns


def next_marker_row(markers: List[Optional[Tuple[int, int]]], current_row: int, fallback: int) -> int:
    later_rows = [row for found in markers if found for row, _ in [found] if row > current_row]
    return min(later_rows) if later_rows else fallback


def parse_yearly_ranking(df: pd.DataFrame, year: int, sheet_name: str) -> pd.DataFrame:
    marker = find_first_marker(df, ["Classement", "Classement General"])
    if not marker:
        return pd.DataFrame()

    start_row, start_col = marker
    ranking_metric = clean_text(df.iat[start_row - 1, start_col + 3]) if start_row > 0 and start_col + 3 < df.shape[1] else None
    if not ranking_metric:
        ranking_metric = "Gains"
    rank_rows = []
    for row_index in range(start_row + 1, df.shape[0]):
        rank = to_int(df.iat[row_index, start_col])
        player = clean_text(df.iat[row_index, start_col + 1]) if start_col + 1 < df.shape[1] else None
        gain = to_number(df.iat[row_index, start_col + 2]) if start_col + 2 < df.shape[1] else None
        back = to_number(df.iat[row_index, start_col + 3]) if start_col + 3 < df.shape[1] else None
        if rank is None and player is None and gain is None:
            if rank_rows:
                break
            continue
        if rank is None or player is None:
            continue
        rank_rows.append(
            {
                "year": year,
                "sheet": sheet_name,
                "rank": rank,
                "player": player,
                "ranking_metric": ranking_metric,
                "gain": gain,
                "gap": back,
            }
        )
    return pd.DataFrame(rank_rows)


def parse_player_year_stats(df: pd.DataFrame, year: int, sheet_name: str) -> pd.DataFrame:
    marker = find_marker(df, "Rank")
    if not marker:
        return pd.DataFrame()

    start_row, start_col = marker
    header = [clean_text(df.iat[start_row, col]) for col in range(start_col, df.shape[1])]
    metric_map = {
        "Rank": "rank",
        "Overall": "player",
        "OVERALL": "player",
        "Gain net": "net_gain",
        "AVG Buy-in": "avg_buyin",
        "% Argent": "money_pct",
        "# Victoire": "wins",
        "Pos moy": "avg_position",
        "# Game jouer": "games_played",
        "Host": "hosted",
        "Bubble": "bubbles",
        "Gains a vie": "lifetime_gain",
        "Tot Points": "total_points",
        "Rank Points": "points_rank",
        "Nombre de kill": "kills",
        "# Bubble": "bubbles",
    }
    columns = {
        col_index: metric_map[label]
        for col_index, label in enumerate(header, start=start_col)
        if label in metric_map
    }

    next_markers = [
        find_marker(df, "BUY-IN"),
        find_marker(df, "POSITION"),
        find_marker(df, "PAYOUT"),
    ]
    end_row = next_marker_row(next_markers, start_row, df.shape[0])
    rows = []
    for row_index in range(start_row + 1, end_row):
        player_col = next((col for col, name in columns.items() if name == "player"), None)
        player = clean_text(df.iat[row_index, player_col]) if player_col is not None else None
        if not player:
            continue
        row = {"year": year, "sheet": sheet_name, "player": player}
        for col_index, name in columns.items():
            if name == "player":
                continue
            row[name] = to_number(df.iat[row_index, col_index])
        rows.append(row)
    return pd.DataFrame(rows)


def parse_event_table(
    df: pd.DataFrame,
    year: int,
    sheet_name: str,
    marker: str,
    value_name: str,
    stop_markers: List[Optional[Tuple[int, int]]],
) -> pd.DataFrame:
    found = find_marker(df, marker)
    if not found:
        return pd.DataFrame()

    marker_row, marker_col = found
    columns = event_columns(df, marker_row, marker_col)
    for column in columns:
        column.update(parse_event_label(year, int(column["event_order"]), column["raw_label"]))

    host_row = marker_row - 1
    end_row = next_marker_row(stop_markers, marker_row, df.shape[0])
    rows = []
    for row_index in range(marker_row + 1, end_row):
        player = clean_text(df.iat[row_index, marker_col])
        if not is_player_name(player):
            continue
        for column in columns:
            value = to_number(df.iat[row_index, int(column["source_col"])])
            if value is None:
                continue
            host = clean_text(df.iat[host_row, int(column["source_col"])]) if host_row >= 0 else None
            rows.append(
                {
                    "year": year,
                    "sheet": sheet_name,
                    "event_order": column["event_order"],
                    "event_label": column["event_label"],
                    "event_month": column["event_month"],
                    "event_day": column["event_day"],
                    "event_date": column["event_date"],
                    "host": host,
                    "player": player,
                    value_name: value,
                }
            )
    return pd.DataFrame(rows)


def parse_event_summaries(df: pd.DataFrame, year: int, sheet_name: str) -> pd.DataFrame:
    marker = find_marker(df, "BUY-IN")
    if not marker:
        return pd.DataFrame()

    marker_row, marker_col = marker
    columns = event_columns(df, marker_row, marker_col)
    for column in columns:
        column.update(parse_event_label(year, int(column["event_order"]), column["raw_label"]))

    rows = []
    for column in columns:
        col = int(column["source_col"])
        rows.append(
            {
                "year": year,
                "sheet": sheet_name,
                "event_order": column["event_order"],
                "event_label": column["event_label"],
                "event_month": column["event_month"],
                "event_day": column["event_day"],
                "event_date": column["event_date"],
                "host": clean_text(df.iat[marker_row - 1, col]) if marker_row > 0 else None,
                "pot_total": find_summary_value(df, "POT Total", marker_col, col),
                "payout_count": find_summary_value(df, "Nombre de Payouts", marker_col, col),
                "player_count": find_summary_value(df, "Nombre de Joueurs", marker_col, col),
            }
        )
    return pd.DataFrame(rows)


def find_summary_value(df: pd.DataFrame, label: str, label_col: int, value_col: int) -> Optional[float]:
    for row_index in range(df.shape[0]):
        if clean_text(df.iat[row_index, label_col]) == label:
            return to_number(df.iat[row_index, value_col])
    return None


def parse_lifetime_stats(workbook: pd.ExcelFile) -> Tuple[pd.DataFrame, pd.DataFrame]:
    if "Stats a vie" not in workbook.sheet_names:
        return pd.DataFrame(), pd.DataFrame()

    df = workbook.parse("Stats a vie", header=None, dtype=object)
    header_row = None
    for row_index, row in df.iterrows():
        if any(clean_text(value) == "Gains" for value in row):
            header_row = int(row_index)
            break
    if header_row is None:
        return pd.DataFrame(), pd.DataFrame()

    labels = [clean_text(df.iat[header_row, col]) for col in range(df.shape[1])]
    player_col = labels.index("Gains")
    year_cols = [(col, to_int(label)) for col, label in enumerate(labels) if to_int(label)]
    total_col = labels.index("Total") if "Total" in labels else None

    totals = []
    yearly = []
    for row_index in range(header_row + 1, df.shape[0]):
        player = clean_text(df.iat[row_index, player_col])
        if not player:
            continue
        total = to_number(df.iat[row_index, total_col]) if total_col is not None else None
        totals.append({"player": player, "total_gain": total})
        for col, year in year_cols:
            yearly.append(
                {
                    "player": player,
                    "year": year,
                    "gain": to_number(df.iat[row_index, col]),
                }
            )
    return pd.DataFrame(totals), pd.DataFrame(yearly)


def parse_players(workbook: pd.ExcelFile) -> pd.DataFrame:
    if "Joueurs" not in workbook.sheet_names:
        return pd.DataFrame()
    df = workbook.parse("Joueurs", dtype=object)
    df = df.rename(columns={"Nom": "player", "Sort By": "preferred_sort"})
    return df[["player", "preferred_sort"]].dropna(subset=["player"]).reset_index(drop=True)


def parse_players_of_year(workbook: pd.ExcelFile) -> pd.DataFrame:
    sheet = "List des joueurs de l'annee"
    if sheet not in workbook.sheet_names:
        return pd.DataFrame()
    df = workbook.parse(sheet, header=None, dtype=object)
    rows = []
    for _, row in df.iterrows():
        year = to_int(row.iloc[0])
        player = clean_text(row.iloc[1]) if len(row) > 1 else None
        if year and player:
            rows.append({"year": year, "player": player})
    return pd.DataFrame(rows)


def parse_payout_rules(workbook: pd.ExcelFile) -> pd.DataFrame:
    if "Liste de payouts" not in workbook.sheet_names:
        return pd.DataFrame()
    df = workbook.parse("Liste de payouts", header=None, dtype=object)
    header = [clean_text(value) for value in df.iloc[0]]
    rows = []
    for row_index in range(1, df.shape[0]):
        pot_total = to_number(df.iat[row_index, 0])
        if pot_total is None:
            continue
        for col_index in range(1, df.shape[1]):
            position = to_int(header[col_index]) if col_index < len(header) else None
            value = clean_text(df.iat[row_index, col_index])
            if position and value:
                rows.append({"pot_total": pot_total, "position": position, "payout": value})
    return pd.DataFrame(rows)


def parse_workbook(path: Path) -> Dict[str, pd.DataFrame]:
    with pd.ExcelFile(path) as workbook:
        tables: Dict[str, List[pd.DataFrame]] = {
            "yearly_rankings": [],
            "player_year_stats": [],
            "event_buyins": [],
            "event_positions": [],
            "event_payouts": [],
            "events": [],
        }

        for year, sheet_name in year_sheets(workbook):
            df = workbook.parse(sheet_name, header=None, dtype=object)
            buyin_marker = find_marker(df, "BUY-IN")
            position_marker = find_marker(df, "POSITION")
            payout_marker = find_marker(df, "PAYOUT")
            points_marker = find_marker_after(df, "Points", payout_marker[0]) if payout_marker else None

            tables["yearly_rankings"].append(parse_yearly_ranking(df, year, sheet_name))
            tables["player_year_stats"].append(parse_player_year_stats(df, year, sheet_name))
            tables["event_buyins"].append(
                parse_event_table(df, year, sheet_name, "BUY-IN", "buyin", [position_marker, payout_marker])
            )
            tables["event_positions"].append(
                parse_event_table(df, year, sheet_name, "POSITION", "position", [payout_marker])
            )
            tables["event_payouts"].append(
                parse_event_table(df, year, sheet_name, "PAYOUT", "payout", [points_marker])
            )
            tables["events"].append(parse_event_summaries(df, year, sheet_name))

        lifetime_stats, lifetime_yearly = parse_lifetime_stats(workbook)
        output = {
            name: pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
            for name, frames in tables.items()
        }
        output["lifetime_stats"] = lifetime_stats
        output["lifetime_yearly"] = lifetime_yearly
        output["players"] = parse_players(workbook)
        output["players_of_year"] = parse_players_of_year(workbook)
        output["payout_rules"] = parse_payout_rules(workbook)
    return output


def validate_tables(tables: Dict[str, pd.DataFrame]) -> List[str]:
    warnings: List[str] = []
    yearly = tables.get("yearly_rankings", pd.DataFrame())
    stats = tables.get("player_year_stats", pd.DataFrame())
    buyins = tables.get("event_buyins", pd.DataFrame())
    payouts = tables.get("event_payouts", pd.DataFrame())

    if yearly.empty:
        warnings.append("No yearly rankings were extracted.")
    if stats.empty:
        warnings.append("No player-year stats were extracted.")
    if buyins.empty:
        warnings.append("No event buy-ins were extracted.")
    if payouts.empty:
        warnings.append("No event payouts were extracted.")

    if not yearly.empty and not stats.empty:
        merged = yearly.merge(stats, on=["year", "player"], how="inner", suffixes=("_ranking", "_stats"))
        gains_only = merged[merged["ranking_metric"].str.lower().eq("gains")]
        mismatches = gains_only[(gains_only["gain"].fillna(0) - gains_only["net_gain"].fillna(0)).abs() > 0.01]
        if not mismatches.empty:
            warnings.append(f"{len(mismatches)} ranking gains do not match player summary net gains.")

    if not buyins.empty and not payouts.empty:
        buyin_totals = buyins.groupby(["year", "player"], as_index=False)["buyin"].sum()
        payout_totals = payouts.groupby(["year", "player"], as_index=False)["payout"].sum()
        net = buyin_totals.merge(payout_totals, on=["year", "player"], how="outer").fillna(0)
        net["computed_net"] = net["payout"] - net["buyin"]
        if not stats.empty and "net_gain" in stats.columns:
            check = net.merge(stats[["year", "player", "net_gain"]], on=["year", "player"], how="inner")
            mismatches = check[(check["computed_net"] - check["net_gain"]).abs() > 0.01]
            if not mismatches.empty:
                examples = ", ".join(
                    f"{int(row.year)} {row.player}" for row in mismatches.head(5).itertuples()
                )
                warnings.append(
                    f"{len(mismatches)} buy-in/payout totals do not reconcile with net gains ({examples})."
                )

    return warnings


def write_tables(tables: Dict[str, pd.DataFrame], output_dir: Path) -> None:
    output_dir.mkdir(exist_ok=True)
    for name, table in tables.items():
        output_path = output_dir / f"{name}.csv"
        table.to_csv(output_path, index=False, encoding="utf-8-sig")
        print(f"Wrote {output_path}: {len(table):,} rows")


def summarize(tables: Dict[str, pd.DataFrame], warnings: List[str]) -> None:
    print("=== Summary ===")
    for name, table in tables.items():
        print(f"{name}: {len(table):,} rows")
    if warnings:
        print("\n=== Validation warnings ===")
        for warning in warnings:
            print(f"- {warning}")
    else:
        print("\nValidation passed.")


if __name__ == "__main__":
    if not WORKBOOK.exists():
        raise FileNotFoundError(f"Workbook not found: {WORKBOOK}")
    parsed_tables = parse_workbook(WORKBOOK)
    validation_warnings = validate_tables(parsed_tables)
    summarize(parsed_tables, validation_warnings)
    write_tables(parsed_tables, DATA_DIR)
