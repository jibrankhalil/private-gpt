"""Automate daily manpower analytics from a live Google Sheet.

This script reads a source tab (for example: "RMD Drivers April 2026"),
aggregates driver-type and operational-status metrics, and writes the results
back to dedicated tabs in the same spreadsheet.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class SheetColumns:
    """Column configuration for the source worksheet."""

    name: str
    driver_type: str
    status: str
    location: str
    team: str | None = None


@dataclass(frozen=True)
class TabConfig:
    """Worksheet names used by the automation."""

    source: str
    summary: str
    details: str


@dataclass(frozen=True)
class AutomationConfig:
    """Configuration for the manpower automation job."""

    spreadsheet_id: str
    credentials_json: str
    tabs: TabConfig
    columns: SheetColumns
    header_row: int
    status_aliases: dict[str, str]


def col_to_index(column: str) -> int:
    """Convert an Excel-like column label (e.g. F) to a zero-based index."""
    result = 0
    for char in column.strip().upper():
        if not ("A" <= char <= "Z"):
            raise ValueError(f"Invalid column value: {column}")
        result = (result * 26) + (ord(char) - ord("A") + 1)
    return result - 1


class GoogleSheetsClient:
    """Thin wrapper around Google Sheets API v4 operations used by this script."""

    def __init__(self, credentials_path: str):
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        credentials = service_account.Credentials.from_service_account_file(
            credentials_path,
            scopes=scopes,
        )
        self._service = build("sheets", "v4", credentials=credentials)

    def read_range(self, spreadsheet_id: str, a1_range: str) -> list[list[str]]:
        response = (
            self._service.spreadsheets()
            .values()
            .get(spreadsheetId=spreadsheet_id, range=a1_range)
            .execute()
        )
        return response.get("values", [])

    def write_range(
        self,
        spreadsheet_id: str,
        a1_range: str,
        values: list[list[str]],
    ) -> None:
        (
            self._service.spreadsheets()
            .values()
            .update(
                spreadsheetId=spreadsheet_id,
                range=a1_range,
                valueInputOption="RAW",
                body={"values": values},
            )
            .execute()
        )


def normalize_status(value: str, aliases: dict[str, str]) -> str:
    """Map raw status text to normalized status buckets."""
    key = value.strip().lower()
    if not key:
        return "Unknown"
    return aliases.get(key, value.strip())


def get_cell(row: list[str], idx: int) -> str:
    """Safely read a cell from a row by index."""
    if idx < 0 or idx >= len(row):
        return ""
    return row[idx].strip()


def aggregate(
    rows: list[list[str]],
    columns: SheetColumns,
    status_aliases: dict[str, str],
) -> dict[str, Any]:
    """Aggregate daily manpower metrics from source rows."""
    name_idx = col_to_index(columns.name)
    type_idx = col_to_index(columns.driver_type)
    status_idx = col_to_index(columns.status)
    location_idx = col_to_index(columns.location)
    team_idx = col_to_index(columns.team) if columns.team else None

    type_counts: Counter[str] = Counter()
    status_counts: Counter[str] = Counter()
    location_people: dict[str, list[str]] = defaultdict(list)
    detail_rows: list[list[str]] = []

    for row in rows:
        name = get_cell(row, name_idx)
        driver_type = get_cell(row, type_idx) or "Unknown"
        status = normalize_status(get_cell(row, status_idx), status_aliases)
        location = get_cell(row, location_idx) or "Unassigned"
        team = get_cell(row, team_idx) if team_idx is not None else ""

        if not any([name, driver_type, status, location, team]):
            continue

        type_counts[driver_type] += 1
        status_counts[status] += 1

        if status.lower() in {"od", "on duty"}:
            location_people[location].append(name or "(No Name)")

        detail_rows.append([name, driver_type, status, location, team])

    return {
        "type_counts": type_counts,
        "status_counts": status_counts,
        "location_people": dict(location_people),
        "details": detail_rows,
        "total_people": len(detail_rows),
    }


def make_summary_table(aggregated: dict[str, Any], now_utc: dt.datetime) -> list[list[str]]:
    """Build a write-ready table for the summary tab."""
    type_counts: Counter[str] = aggregated["type_counts"]
    status_counts: Counter[str] = aggregated["status_counts"]
    location_people: dict[str, list[str]] = aggregated["location_people"]

    rows: list[list[str]] = [
        ["Last Updated (UTC)", now_utc.strftime("%Y-%m-%d %H:%M:%S")],
        ["Total Drivers", str(aggregated["total_people"])],
        [],
        ["Driver Type", "Count"],
    ]

    for driver_type, count in sorted(type_counts.items()):
        rows.append([driver_type, str(count)])

    rows.extend(
        [
            [],
            ["Status", "Count"],
        ],
    )
    for status, count in sorted(status_counts.items()):
        rows.append([status, str(count)])

    rows.extend(
        [
            [],
            ["OD / On Duty Location", "Workers"],
        ],
    )
    for location, workers in sorted(location_people.items()):
        rows.append([location, ", ".join(sorted(workers))])

    return rows


def load_config(path: Path) -> AutomationConfig:
    """Load YAML config from disk."""
    with path.open("r", encoding="utf-8") as file:
        raw = yaml.safe_load(file)

    return AutomationConfig(
        spreadsheet_id=raw["spreadsheet_id"],
        credentials_json=raw["credentials_json"],
        tabs=TabConfig(**raw["tabs"]),
        columns=SheetColumns(**raw["columns"]),
        header_row=int(raw.get("header_row", 1)),
        status_aliases={
            str(key).strip().lower(): str(value).strip()
            for key, value in raw.get("status_aliases", {}).items()
        },
    )


def run(config: AutomationConfig) -> dict[str, Any]:
    """Execute one full read->aggregate->write sync cycle."""
    client = GoogleSheetsClient(config.credentials_json)
    source_range = f"{config.tabs.source}!A{config.header_row + 1}:ZZ"
    rows = client.read_range(config.spreadsheet_id, source_range)

    aggregated = aggregate(rows, config.columns, config.status_aliases)
    summary_values = make_summary_table(aggregated, dt.datetime.now(dt.timezone.utc))

    client.write_range(config.spreadsheet_id, f"{config.tabs.summary}!A1", summary_values)

    detail_values: list[list[str]] = [
        ["Name", "Driver Type", "Status", "Location", "Team"]
    ] + aggregated["details"]
    client.write_range(config.spreadsheet_id, f"{config.tabs.details}!A1", detail_values)

    result = {
        "updated": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source_tab": config.tabs.source,
        "summary_tab": config.tabs.summary,
        "details_tab": config.tabs.details,
        "total_people": aggregated["total_people"],
        "driver_types": dict(aggregated["type_counts"]),
        "statuses": dict(aggregated["status_counts"]),
    }
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Automate daily manpower counts from Google Sheets"
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("scripts/manpower_config.example.yaml"),
        help="Path to YAML config file",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    result = run(config)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
