from __future__ import annotations

import html
import shutil
import time
from datetime import datetime
from numbers import Number
from pathlib import Path
from urllib.parse import quote

import altair as alt
import pandas as pd
import streamlit as st

from convert_ldvp import parse_workbook, validate_tables, write_tables

DATA_DIR = Path("data")
UPLOAD_STAGING_DIR = Path("data_upload_staging")
UPLOAD_BACKUP_DIR = Path("data_backups")
TABLE_HEADER_HEIGHT = 34
TABLE_ROW_HEIGHT = 36
LEADERBOARD_ROW_HEIGHT = 41
REQUIRED_TABLES = {
    "yearly_rankings": "yearly_rankings.csv",
    "player_year_stats": "player_year_stats.csv",
    "event_buyins": "event_buyins.csv",
    "event_positions": "event_positions.csv",
    "event_payouts": "event_payouts.csv",
    "events": "events.csv",
    "lifetime_stats": "lifetime_stats.csv",
    "lifetime_yearly": "lifetime_yearly.csv",
    "players": "players.csv",
    "players_of_year": "players_of_year.csv",
    "payout_rules": "payout_rules.csv",
}

METRICS = {
    "Net gain": "net_gain",
    "Total points": "total_points",
    "Wins": "wins",
    "Games played": "games_played",
    "Average position": "avg_position",
    "Money %": "money_pct",
    "Bubbles": "bubbles",
}

RANKING_METRIC_ALIASES = {
    "gain": "Net gain",
    "gains": "Net gain",
    "netgain": "Net gain",
    "point": "Total points",
    "points": "Total points",
    "totalpoints": "Total points",
    "totpoints": "Total points",
}

COLUMN_LABELS = {
    "avg_buyin": "Avg Buy-In",
    "avg_position": "Avg Finish",
    "bubbles": "Bubbles",
    "buyin": "Buy-In",
    "event_date": "Date",
    "event_day": "Day",
    "event_label": "Event",
    "event_month": "Month",
    "event_order": "Event #",
    "gain": "Gain",
    "games_played": "Games Played",
    "gap": "Gap",
    "host": "Host",
    "hosted": "Hosted",
    "kills": "Kills",
    "money_pct": "Money %",
    "net": "Net",
    "net_gain": "Net Gain",
    "payout": "Payout",
    "payout_count": "Paid Places",
    "player": "Player",
    "player_count": "Players",
    "points_rank": "Points Rank",
    "position": "Position",
    "pot_total": "Prize Pool",
    "rank": "Rank",
    "ranking_metric": "Ranked By",
    "sheet": "Sheet",
    "source_col": "Source Column",
    "total_gain": "Lifetime Gain",
    "total_points": "Total Points",
    "wins": "Wins",
    "year": "Year",
}

IDENTIFIER_COLUMNS = {
    "event_day",
    "event_month",
    "event_order",
    "games_played",
    "hosted",
    "kills",
    "paid_places",
    "payout_count",
    "player_count",
    "points_rank",
    "position",
    "rank",
    "source_col",
    "wins",
    "year",
}


st.set_page_config(page_title="LDVP Poker Stats", layout="wide")

st.markdown(
    """
    <style>
    :root {
        --bg: #07111f;
        --panel: #0f1b2e;
        --panel-2: #13243a;
        --border: #203553;
        --text: #e5edf7;
        --muted: #8ea2bd;
        --cyan: #21d4d8;
        --magenta: #f02fa6;
        --green: #2dd489;
        --orange: #ff7a3d;
    }
    .stApp {
        background: linear-gradient(135deg, #07111f 0%, #0a1526 46%, #111827 100%);
        color: var(--text);
    }
    .block-container {
        max-width: 1500px;
        padding-top: 3rem;
    }
    h1 {
        color: var(--text);
        font-size: 2rem !important;
        letter-spacing: 0 !important;
        margin-bottom: 0.35rem !important;
    }
    h2, h3 {
        color: var(--text);
        letter-spacing: 0 !important;
    }
    p, label, span, div {
        color: inherit;
    }
    [data-testid="stHeader"] {
        background: transparent;
        border-bottom: 0;
    }
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, rgba(19, 36, 58, 0.98), rgba(13, 25, 43, 0.98));
        border: 1px solid var(--border);
        border-radius: 10px;
        box-shadow: 0 16px 36px rgba(0, 0, 0, 0.22);
        min-height: 112px;
        padding: 1rem 1.05rem;
        position: relative;
    }
    [data-testid="stMetric"]::after {
        background: linear-gradient(90deg, var(--cyan), var(--magenta));
        border-radius: 999px;
        bottom: 0.65rem;
        content: "";
        height: 2px;
        left: 1rem;
        position: absolute;
        width: 58px;
    }
    [data-testid="stMetricLabel"] p {
        color: var(--muted) !important;
        font-size: 0.8rem;
        text-transform: uppercase;
    }
    [data-testid="stMetricValue"] {
        color: var(--text) !important;
        font-family: "Segoe UI", system-ui, sans-serif;
        font-size: 1.85rem !important;
        font-weight: 700;
    }
    .leader-card {
        background: linear-gradient(135deg, rgba(19, 36, 58, 0.98), rgba(13, 25, 43, 0.98));
        border: 1px solid var(--border);
        border-radius: 10px;
        box-shadow: 0 16px 36px rgba(0, 0, 0, 0.22);
        min-height: 112px;
        padding: 1rem 1.05rem 1.25rem;
        position: relative;
    }
    .leader-card::after {
        background: linear-gradient(90deg, var(--cyan), var(--magenta));
        border-radius: 999px;
        bottom: 0.65rem;
        content: "";
        height: 2px;
        left: 1rem;
        position: absolute;
        width: 58px;
    }
    .leader-label {
        color: var(--muted);
        font-size: 0.8rem;
        font-weight: 600;
        line-height: 1.2;
        margin-bottom: 0.5rem;
        text-transform: uppercase;
    }
    .leader-name {
        color: var(--text);
        font-size: clamp(1.25rem, 1.8vw, 1.65rem);
        font-weight: 750;
        line-height: 1.12;
        overflow-wrap: anywhere;
    }
    .leader-amount {
        color: var(--cyan);
        font-size: 1rem;
        font-weight: 700;
        line-height: 1.2;
        margin-top: 0.35rem;
    }
    [data-testid="stVerticalBlock"] > [style*="flex-direction: column;"] {
        gap: 1rem;
    }
    [data-testid="stTabs"] [role="tablist"] {
        border-bottom: 1px solid var(--border);
        gap: 0.35rem;
    }
    [data-testid="stTabs"] [role="tab"] {
        color: var(--muted);
        padding: 0.65rem 1rem;
    }
    [data-testid="stTabs"] [aria-selected="true"] {
        color: var(--text);
        border-bottom-color: var(--magenta);
    }
    div[data-baseweb="select"] > div {
        background: var(--panel-2);
        border: 1px solid var(--border);
        border-radius: 8px;
        color: var(--text);
    }
    div[data-baseweb="select"] svg {
        color: var(--cyan);
    }
    button[kind="secondary"] {
        background: var(--panel-2);
        border: 1px solid var(--border);
        color: var(--text);
    }
    button[kind="secondary"]:hover {
        border-color: var(--cyan);
        color: var(--cyan);
    }
    [data-testid="stDataFrame"] {
        background: var(--panel);
        border: 1px solid var(--border);
        border-radius: 10px;
        overflow: hidden;
    }
    hr {
        border-color: var(--border);
    }
    .app-kicker {
        color: var(--cyan);
        font-size: 2.05rem;
        font-weight: 800;
        letter-spacing: 0;
        line-height: 1.15;
        margin: 0 0 1.25rem;
    }
    .year-label {
        color: var(--muted);
        font-size: 1.1rem;
        font-weight: 700;
        line-height: 2.5rem;
        margin: 0;
    }
    .section-panel {
        background: rgba(15, 27, 46, 0.7);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 1rem;
    }
    .linked-table {
        border-collapse: collapse;
        font-size: 0.875rem;
        width: 100%;
        background: var(--panel);
        border: 1px solid var(--border);
        border-radius: 10px;
        box-shadow: 0 18px 42px rgba(0, 0, 0, 0.2);
        overflow: hidden;
    }
    .linked-table th,
    .linked-table td {
        border-bottom: 1px solid rgba(32, 53, 83, 0.86);
        box-sizing: border-box;
        height: 36px;
        padding: 0.42rem 0.55rem;
        text-align: left;
        vertical-align: middle;
    }
    .linked-table th {
        background: #0b1728;
        color: var(--muted);
        font-weight: 600;
        text-transform: uppercase;
        font-size: 0.72rem;
        height: 34px;
    }
    .linked-table tr:hover td {
        background: rgba(33, 212, 216, 0.08);
    }
    .player-link {
        color: var(--cyan);
        display: inline-block;
        font-weight: 600;
        text-decoration: none;
        transition: color 120ms ease, transform 120ms ease;
    }
    .player-link:hover {
        color: var(--magenta);
        text-decoration: underline;
        transform: translateX(2px);
    }
    #vg-tooltip-element {
        background: linear-gradient(135deg, rgba(15, 27, 46, 0.98), rgba(10, 21, 38, 0.98)) !important;
        border: 1px solid var(--border) !important;
        border-radius: 10px !important;
        box-shadow: 0 18px 42px rgba(0, 0, 0, 0.32) !important;
        color: var(--text) !important;
        font-family: "Segoe UI", system-ui, sans-serif !important;
        font-size: 0.85rem !important;
        padding: 0.7rem 0.85rem !important;
    }
    #vg-tooltip-element table {
        color: var(--text) !important;
        margin: 0 !important;
    }
    #vg-tooltip-element td.key {
        color: var(--muted) !important;
        font-weight: 600 !important;
        padding-right: 1rem !important;
    }
    #vg-tooltip-element td.value {
        color: var(--text) !important;
        font-weight: 700 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def load_tables() -> dict[str, pd.DataFrame]:
    missing = [name for name in REQUIRED_TABLES.values() if not (DATA_DIR / name).exists()]
    if missing:
        raise FileNotFoundError(f"Missing generated files: {', '.join(missing)}")

    tables = {}
    read_errors = []
    for table_name, file_name in REQUIRED_TABLES.items():
        try:
            tables[table_name] = pd.read_csv(DATA_DIR / file_name)
        except pd.errors.EmptyDataError:
            read_errors.append(f"{file_name} is empty")
        except Exception as exc:
            read_errors.append(f"{file_name} could not be read ({exc})")
    if read_errors:
        raise ValueError("; ".join(read_errors))

    core_empty = [
        REQUIRED_TABLES[table_name]
        for table_name in ("yearly_rankings", "player_year_stats", "events")
        if tables[table_name].empty
    ]
    if core_empty:
        raise ValueError(f"Generated data has no dashboard rows: {', '.join(core_empty)}")

    for table in ("event_buyins", "event_positions", "event_payouts", "events"):
        if "event_date" in tables[table].columns:
            tables[table]["event_date"] = pd.to_datetime(tables[table]["event_date"], errors="coerce")
    return tables


def money(value: float | int | None) -> str:
    if pd.isna(value):
        return "-"
    return f"${value:,.0f}"


def number(value: float | int | None) -> str:
    if pd.isna(value):
        return "-"
    return f"{value:,.0f}"


def pct(value: float | int | None) -> str:
    if pd.isna(value):
        return "-"
    return f"{value:.0%}"


def style_chart(chart: alt.Chart) -> alt.Chart:
    return (
        chart.configure_view(stroke=None)
        .configure(background="transparent")
        .configure_axis(
            domainColor="#203553",
            gridColor="#203553",
            gridOpacity=0.55,
            labelColor="#8ea2bd",
            titleColor="#c9d8ec",
        )
        .configure_legend(
            labelColor="#c9d8ec",
            titleColor="#8ea2bd",
            orient="bottom",
        )
        .configure_title(color="#e5edf7")
    )


def tooltip_format(column: str) -> str:
    if column == "money_pct":
        return ".0%"
    if column in {"avg_position", "total_points"}:
        return ".2f"
    if column in IDENTIFIER_COLUMNS:
        return ".0f"
    return ",.0f"


def chart_tooltips(data: pd.DataFrame, x_col: str, y_col: str, metric_label: str) -> list[alt.Tooltip]:
    tooltips = [alt.Tooltip(f"{y_col}:N", title=format_column_label(y_col))]
    tooltips.append(
        alt.Tooltip(
            f"{x_col}:Q",
            title=metric_label,
            format=tooltip_format(x_col),
        )
    )
    for column in ("rank", "games_played"):
        if column in data.columns and column != x_col:
            tooltips.append(
                alt.Tooltip(
                    f"{column}:Q",
                    title=format_column_label(column),
                    format=tooltip_format(column),
                )
            )
    return tooltips


def diverging_bar(data: pd.DataFrame, x_col: str, y_col: str, title: str, height: int = 420):
    chart = (
        alt.Chart(data)
        .mark_bar()
        .encode(
            x=alt.X(f"{x_col}:Q", title=title),
            y=alt.Y(f"{y_col}:N", sort="-x", title=None),
            color=alt.condition(
                alt.datum[x_col] >= 0,
                alt.value("#2dd489"),
                alt.value("#ff7a3d"),
            ),
            tooltip=chart_tooltips(data, x_col, y_col, title),
        )
        .properties(height=height)
    )
    st.altair_chart(style_chart(chart), use_container_width=True)


def merge_event_results(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    keys = ["year", "event_order", "player"]
    event_lookup = tables["events"][["year", "event_order", "event_label", "event_date", "host"]]
    buyins = tables["event_buyins"][keys + ["buyin"]]
    positions = tables["event_positions"][keys + ["position"]]
    payouts = tables["event_payouts"][keys + ["payout"]]
    results = buyins.merge(positions, on=keys, how="outer")
    results = results.merge(payouts, on=keys, how="outer")
    results = results.merge(event_lookup, on=["year", "event_order"], how="left")
    results["buyin"] = results["buyin"].fillna(0)
    results["payout"] = results["payout"].fillna(0)
    results["net"] = results["payout"] - results["buyin"]
    return results


def player_anchor(player: object) -> str:
    if pd.isna(player):
        return ""
    player_name = str(player)
    return (
        f'<a class="player-link" href="?player={quote(player_name)}">'
        f"{html.escape(player_name)}</a>"
    )


def format_column_label(column: object) -> str:
    column_name = str(column)
    lookup_key = column_name.lower()
    if lookup_key in COLUMN_LABELS:
        return COLUMN_LABELS[lookup_key]
    return column_name.replace("_", " ").title()


def normalize_metric_label(value: object) -> str:
    return "".join(char for char in str(value).lower() if char.isalnum())


def default_leaderboard_metric(year_ranking: pd.DataFrame, available_metrics: dict[str, str]) -> str:
    fallback = "Net gain" if "Net gain" in available_metrics else next(iter(available_metrics))
    if year_ranking.empty or "ranking_metric" not in year_ranking.columns:
        return fallback

    ranked_by = year_ranking["ranking_metric"].dropna()
    if ranked_by.empty:
        return fallback

    official_metric = normalize_metric_label(ranked_by.iloc[0])
    metric_label = RANKING_METRIC_ALIASES.get(official_metric)
    if metric_label in available_metrics:
        return metric_label

    available_by_normalized_label = {normalize_metric_label(label): label for label in available_metrics}
    return available_by_normalized_label.get(official_metric, fallback)


def format_table_value(value: object, column: str) -> str:
    if pd.isna(value):
        return ""
    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d") if not pd.isna(value) else ""
    if column.lower() in {"money %", "money_pct"}:
        return f"{float(value):.0%}"
    if isinstance(value, Number):
        number_value = float(value)
        if column.lower() in IDENTIFIER_COLUMNS:
            return f"{number_value:.0f}" if number_value.is_integer() else f"{number_value:.2f}"
        if number_value.is_integer():
            return f"{number_value:,.0f}"
        return f"{number_value:,.2f}"
    return html.escape(str(value))


def styled_table(df: pd.DataFrame, player_column: str | None = None, max_rows: int | None = None) -> None:
    table = df.head(max_rows).copy() if max_rows else df.copy()
    headers = "".join(f"<th>{html.escape(format_column_label(column))}</th>" for column in table.columns)
    rows = []
    for _, row in table.iterrows():
        cells = []
        for column in table.columns:
            if player_column and column == player_column:
                value = player_anchor(row[column])
            else:
                value = format_table_value(row[column], str(column))
            cells.append(f"<td>{value}</td>")
        rows.append(f"<tr>{''.join(cells)}</tr>")
    st.markdown(
        f"<table class=\"linked-table\"><thead><tr>{headers}</tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>",
        unsafe_allow_html=True,
    )


def linked_player_table(df: pd.DataFrame, player_column: str, max_rows: int | None = None) -> None:
    styled_table(df, player_column=player_column, max_rows=max_rows)


def query_value(name: str) -> str | None:
    value = st.query_params.get(name)
    if isinstance(value, list):
        return value[0] if value else None
    return value


def is_upload_view() -> bool:
    return query_value("view") == "upload" or query_value("page") == "upload" or "upload" in st.query_params


def validate_generated_output(output_dir: Path) -> list[str]:
    issues = []
    for file_name in REQUIRED_TABLES.values():
        output_path = output_dir / file_name
        if not output_path.exists():
            issues.append(f"Missing generated file: {file_name}")
            continue
        if output_path.stat().st_size == 0:
            issues.append(f"Generated file is empty: {file_name}")
            continue
        try:
            pd.read_csv(output_path)
        except Exception as exc:
            issues.append(f"Generated file cannot be read: {file_name} ({exc})")
    return issues


def remove_directory(path: Path, attempts: int = 5) -> None:
    for attempt in range(attempts):
        if not path.exists():
            return
        try:
            shutil.rmtree(path)
            return
        except PermissionError:
            if attempt == attempts - 1:
                raise
            time.sleep(0.25)


def replace_data_dir(staging_dir: Path) -> Path | None:
    backup_dir = None
    if DATA_DIR.exists():
        UPLOAD_BACKUP_DIR.mkdir(exist_ok=True)
        backup_dir = UPLOAD_BACKUP_DIR / f"data_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copytree(DATA_DIR, backup_dir)

    try:
        DATA_DIR.mkdir(exist_ok=True)
        for file_name in REQUIRED_TABLES.values():
            shutil.copy2(staging_dir / file_name, DATA_DIR / file_name)
    except Exception:
        if backup_dir and backup_dir.exists():
            for file_name in REQUIRED_TABLES.values():
                backup_file = backup_dir / file_name
                if backup_file.exists():
                    shutil.copy2(backup_file, DATA_DIR / file_name)
        raise

    if backup_dir and backup_dir.exists():
        remove_directory(backup_dir)
        try:
            UPLOAD_BACKUP_DIR.rmdir()
        except OSError:
            pass

    load_tables.clear()
    return None


def render_upload_page() -> None:
    st.markdown('<p class="app-kicker">La Ligue du Vieux Poele</p>', unsafe_allow_html=True)
    st.subheader("Upload Workbook")
    st.write("Upload a new LDVP Excel workbook. The current dashboard data is replaced only after parsing succeeds.")

    uploaded_file = st.file_uploader("Workbook", type=["xlsx"])
    if not uploaded_file:
        st.session_state.pop("upload_result", None)
        if st.button("Back to Dashboard"):
            st.query_params.clear()
            st.rerun()
        st.stop()

    if st.button("Validate and Refresh Data", type="primary"):
        uploaded_path = UPLOAD_STAGING_DIR / Path(uploaded_file.name).name
        try:
            if UPLOAD_STAGING_DIR.exists():
                shutil.rmtree(UPLOAD_STAGING_DIR)
            UPLOAD_STAGING_DIR.mkdir(exist_ok=True)
            uploaded_path.write_bytes(uploaded_file.getbuffer())

            parsed_tables = parse_workbook(uploaded_path)
            parser_warnings = validate_tables(parsed_tables)
            write_tables(parsed_tables, UPLOAD_STAGING_DIR)
            output_issues = validate_generated_output(UPLOAD_STAGING_DIR)
            if output_issues:
                issue_list = "\n".join(f"- {issue}" for issue in output_issues)
                raise ValueError(f"The uploaded workbook generated incomplete data:\n{issue_list}")

            backup_dir = replace_data_dir(UPLOAD_STAGING_DIR)
        except Exception as exc:
            st.session_state.pop("upload_result", None)
            st.error("The uploaded workbook was not applied. Existing dashboard data was left unchanged.")
            st.exception(exc)
            st.stop()
        finally:
            remove_directory(UPLOAD_STAGING_DIR)

        st.session_state["upload_result"] = {
            "warnings": parser_warnings,
            "backup_dir": str(backup_dir) if backup_dir else None,
        }
        st.rerun()

    upload_result = st.session_state.get("upload_result")
    if upload_result:
        st.success("Data refreshed successfully.")
        parser_warnings = upload_result.get("warnings", [])
        backup_dir = upload_result.get("backup_dir")
        if parser_warnings:
            st.warning("Parser warnings were found. The data was still applied because parsing completed.")
            for warning in parser_warnings:
                st.write(f"- {warning}")
        if backup_dir:
            st.caption(f"Previous data backup: {backup_dir}")
        if st.button("Open Dashboard"):
            st.session_state.pop("upload_result", None)
            st.query_params.clear()
            st.rerun()

    st.stop()


def render_empty_data_page(details: str) -> None:
    st.markdown('<p class="app-kicker">La Ligue du Vieux Poele</p>', unsafe_allow_html=True)
    st.subheader("No Dashboard Data")
    st.write("Upload an LDVP Excel workbook to build the dashboard data.")
    with st.expander("Details"):
        st.write(details)

    upload_col, _ = st.columns([0.18, 0.82])
    with upload_col:
        if st.button("Upload Workbook", type="primary", use_container_width=True):
            st.query_params["view"] = "upload"
            st.rerun()

    st.stop()


if is_upload_view():
    render_upload_page()


try:
    tables = load_tables()
except (FileNotFoundError, ValueError) as exc:
    render_empty_data_page(str(exc))

stats = tables["player_year_stats"].copy()
rankings = tables["yearly_rankings"].copy()
events = tables["events"].copy()
lifetime = tables["lifetime_stats"].copy()
lifetime_yearly = tables["lifetime_yearly"].copy()
event_results = merge_event_results(tables)

years = sorted(stats["year"].dropna().astype(int).unique(), reverse=True)

if "selected_player" not in st.session_state:
    st.session_state["selected_player"] = None
query_player = st.query_params.get("player")
if isinstance(query_player, list):
    query_player = query_player[0] if query_player else None
if query_player:
    st.session_state["selected_player"] = query_player

st.markdown(
    """
    <p class="app-kicker">La Ligue du Vieux Poele</p>
    """,
    unsafe_allow_html=True,
)

year_label_col, year_select_col, _ = st.columns([0.045, 0.13, 0.825], gap="small")
with year_label_col:
    st.markdown('<p class="year-label">Year</p>', unsafe_allow_html=True)
with year_select_col:
    selected_year = st.selectbox("Year", years, index=0, label_visibility="collapsed")

year_ranking = rankings[rankings["year"] == selected_year].sort_values("rank")
official_players = year_ranking["player"].dropna().unique()
year_stats_all = stats[stats["year"] == selected_year].copy()
if len(official_players):
    year_stats = year_stats_all[year_stats_all["player"].isin(official_players)].copy()
else:
    year_stats = year_stats_all.copy()

metric_scope = year_stats.copy()
available_metrics = {
    label: column
    for label, column in METRICS.items()
    if column in metric_scope.columns and metric_scope[column].notna().any()
}
if not available_metrics:
    available_metrics = {"Net gain": "net_gain"}
default_metric_label = default_leaderboard_metric(year_ranking, available_metrics)
default_metric_index = list(available_metrics.keys()).index(default_metric_label)

year_events = events[events["year"] == selected_year].copy()
year_results = event_results[event_results["year"] == selected_year].copy()
completed_events = year_events[year_events["player_count"].fillna(0) > 0]

if "pot_total" in completed_events.columns and completed_events["pot_total"].notna().any():
    total_prize_pool = completed_events["pot_total"].fillna(0).sum()
else:
    total_prize_pool = year_results["buyin"].sum()
total_buyins = total_prize_pool
total_payouts = total_prize_pool

selected_player = st.session_state["selected_player"]
if selected_player:
    player_years = stats[stats["player"] == selected_player].copy()
    player_lifetime = lifetime[lifetime["player"] == selected_player].copy()
    player_current = stats[(stats["year"] == selected_year) & (stats["player"] == selected_player)].copy()
    player_results = event_results[
        (event_results["year"] == selected_year) & (event_results["player"] == selected_player)
    ].copy()

    title_col, clear_col = st.columns([0.86, 0.14])
    with title_col:
        st.subheader(f"{selected_player}")
    with clear_col:
        if st.button("Back to Dashboard", use_container_width=True):
            st.session_state["selected_player"] = None
            if "player" in st.query_params:
                del st.query_params["player"]
            st.rerun()

    lifetime_gain = player_lifetime["total_gain"].iloc[0] if not player_lifetime.empty else None
    current_net = player_current["net_gain"].iloc[0] if not player_current.empty else None
    current_games = player_current["games_played"].iloc[0] if not player_current.empty else None
    current_wins = player_current["wins"].iloc[0] if not player_current.empty else None
    current_avg_position = player_current["avg_position"].iloc[0] if not player_current.empty else None
    current_money_pct = player_current["money_pct"].iloc[0] if not player_current.empty else None
    player_buyins = player_results["buyin"].sum()
    player_payouts = player_results["payout"].sum()

    p1, p2, p3, p4 = st.columns(4)
    p1.metric("Lifetime gain", money(lifetime_gain))
    p2.metric(f"{selected_year} net", money(current_net))
    p3.metric(f"{selected_year} games", number(current_games))
    p4.metric(f"{selected_year} wins", number(current_wins))
    p5, p6, p7, p8 = st.columns(4)
    p5.metric(f"{selected_year} buy-ins", money(player_buyins))
    p6.metric(f"{selected_year} payouts", money(player_payouts))
    p7.metric("Avg finish", f"{current_avg_position:.2f}" if not pd.isna(current_avg_position) else "-")
    p8.metric("Money %", pct(current_money_pct))

    player_col1, player_col2 = st.columns([1.1, 1])
    with player_col1:
        trend_data = lifetime_yearly[
            (lifetime_yearly["player"] == selected_player) & lifetime_yearly["gain"].notna()
        ].copy()
        trend = (
            alt.Chart(trend_data)
            .mark_line(point=True, color="#21d4d8")
            .encode(
                x=alt.X("year:O", title="Year"),
                y=alt.Y("gain:Q", title="Gain"),
                tooltip=["year", "gain"],
            )
            .properties(height=280)
        )
        st.altair_chart(style_chart(trend), use_container_width=True)
    with player_col2:
        player_cols = [
            "year",
            "rank",
            "net_gain",
            "games_played",
            "wins",
            "avg_position",
            "money_pct",
            "bubbles",
            "total_points",
        ]
        styled_table(
            player_years[[col for col in player_cols if col in player_years.columns]].sort_values(
                "year", ascending=False
            )
        )

    st.subheader(f"{selected_year} Event Results")
    styled_table(
        player_results[["event_order", "event_label", "position", "buyin", "payout", "net", "host"]].sort_values(
            "event_order"
        )
    )
    st.stop()

top_player = year_stats.sort_values("net_gain", ascending=False).head(1)
top_name = top_player["player"].iloc[0] if not top_player.empty else "-"
top_gain = top_player["net_gain"].iloc[0] if not top_player.empty else None

metric1, metric2, metric3, metric4 = st.columns(4)
metric1.metric("Events", number(len(completed_events)))
metric2.metric("Buy-ins", money(total_buyins))
metric3.metric("Payouts", money(total_payouts))
with metric4:
    st.markdown(
        f"""
        <div class="leader-card">
            <div class="leader-label">Leader</div>
            <div class="leader-name">{html.escape(str(top_name)) if top_gain is not None else "-"}</div>
            <div class="leader-amount">{money(top_gain) if top_gain is not None else ""}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

overview_tab, players_tab, events_tab, lifetime_tab, data_tab = st.tabs(
    ["Overview", "Players", "Events", "Lifetime", "Data"]
)

with overview_tab:
    col1, col2 = st.columns([1.2, 1])
    with col1:
        metric_col_control, title_col, _ = st.columns([0.22, 0.36, 0.42])
        with metric_col_control:
            metric_label = st.selectbox(
                "Leaderboard metric",
                list(available_metrics.keys()),
                index=default_metric_index,
                key=f"leaderboard_metric_{selected_year}",
                label_visibility="collapsed",
            )
        with title_col:
            st.subheader(f"{selected_year} Leaderboard")
        metric_col = available_metrics[metric_label]
        leaderboard = year_stats.dropna(subset=[metric_col]).sort_values(metric_col, ascending=False)
        if not leaderboard.empty:
            leaderboard_rows = len(leaderboard.head(20))
            st.markdown(f'<div style="height: {TABLE_HEADER_HEIGHT}px;"></div>', unsafe_allow_html=True)
            diverging_bar(
                leaderboard.head(20),
                metric_col,
                "player",
                metric_label,
                height=leaderboard_rows * LEADERBOARD_ROW_HEIGHT,
            )
        else:
            st.info(f"No {metric_label.lower()} data is available for the current filters.")

    with col2:
        st.subheader("Official Standings")
        year_ranking_display = year_ranking[["rank", "player", "ranking_metric", "gain", "gap"]].rename(
            columns={
                "rank": "Rank",
                "player": "Player",
                "ranking_metric": "Ranked by",
                "gain": "Value",
                "gap": "Gap",
            }
        )
        linked_player_table(year_ranking_display, "Player", max_rows=20)

with players_tab:
    st.subheader(f"{selected_year} Player Table")
    display_cols = [
        "rank",
        "player",
        "net_gain",
        "avg_buyin",
        "money_pct",
        "wins",
        "avg_position",
        "games_played",
        "hosted",
        "bubbles",
        "total_points",
        "points_rank",
        "kills",
    ]
    available_cols = [col for col in display_cols if col in year_stats.columns]
    player_table = year_stats[available_cols].sort_values(["net_gain", "games_played"], ascending=[False, False])
    linked_player_table(player_table, "player")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Wins")
        wins = year_stats.dropna(subset=["wins"]).sort_values("wins", ascending=False).head(15)
        diverging_bar(wins, "wins", "player", "Wins", height=360)
    with col2:
        st.subheader("Average Finish")
        finishes = year_stats.dropna(subset=["avg_position"])
        finishes = finishes.sort_values("avg_position", ascending=True).head(15)
        chart = (
            alt.Chart(finishes)
            .mark_bar(color="#21d4d8")
            .encode(
                x=alt.X("avg_position:Q", title="Average position"),
                y=alt.Y("player:N", sort="x", title=None),
                tooltip=["player", "avg_position", "games_played"],
            )
            .properties(height=360)
        )
        st.altair_chart(style_chart(chart), use_container_width=True)

with events_tab:
    st.subheader(f"{selected_year} Event Summary")
    event_display = year_events[
        [
            "event_order",
            "event_label",
            "event_date",
            "host",
            "pot_total",
            "player_count",
            "payout_count",
        ]
    ].sort_values("event_order")
    styled_table(event_display)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Pot Size")
        pot_chart = (
            alt.Chart(year_events)
            .mark_bar(color="#2dd489")
            .encode(
                x=alt.X("event_label:N", sort=list(year_events.sort_values("event_order")["event_label"]), title=None),
                y=alt.Y("pot_total:Q", title="Pot"),
                tooltip=["event_label", "event_date", "host", "pot_total", "player_count"],
            )
            .properties(height=320)
        )
        st.altair_chart(style_chart(pot_chart), use_container_width=True)
    with col2:
        st.subheader("Player Count")
        players_chart = (
            alt.Chart(year_events)
            .mark_line(point=True, color="#f02fa6")
            .encode(
                x=alt.X("event_label:N", sort=list(year_events.sort_values("event_order")["event_label"]), title=None),
                y=alt.Y("player_count:Q", title="Players"),
                tooltip=["event_label", "event_date", "host", "player_count"],
            )
            .properties(height=320)
        )
        st.altair_chart(style_chart(players_chart), use_container_width=True)

    st.subheader("Event Results")
    result_cols = ["event_order", "event_label", "player", "position", "buyin", "payout", "net", "host"]
    event_results_table = year_results[result_cols].sort_values(["event_order", "position", "player"])
    linked_player_table(event_results_table, "player")

with lifetime_tab:
    st.subheader("Lifetime Leaderboard")
    lifetime_chart_data = lifetime.sort_values("total_gain", ascending=False)
    diverging_bar(
        lifetime_chart_data,
        "total_gain",
        "player",
        "Lifetime gain",
        height=max(360, min(760, len(lifetime_chart_data) * 24)),
    )
    lifetime_table = lifetime_chart_data.rename(columns={"player": "Player", "total_gain": "Lifetime gain"})
    linked_player_table(lifetime_table, "Player")

    st.subheader("Year-by-Year Heatmap")
    heatmap_source = lifetime_yearly.dropna(subset=["gain"]).copy()
    heatmap_source = heatmap_source[heatmap_source["player"].isin(lifetime.nlargest(20, "total_gain")["player"])]
    heatmap = (
        alt.Chart(heatmap_source)
        .mark_rect()
        .encode(
            x=alt.X("year:O", title="Year"),
            y=alt.Y("player:N", sort="-x", title=None),
            color=alt.Color(
                "gain:Q",
                scale=alt.Scale(domainMid=0, range=["#ff7a3d", "#13243a", "#2dd489"]),
                title="Gain",
            ),
            tooltip=["player", "year", "gain"],
        )
        .properties(height=max(360, min(720, heatmap_source["player"].nunique() * 26)))
    )
    st.altair_chart(style_chart(heatmap), use_container_width=True)

with data_tab:
    st.subheader("Generated Tables")
    selected_table = st.selectbox("Table", list(tables.keys()))
    styled_table(tables[selected_table], max_rows=500)
