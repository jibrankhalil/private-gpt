# Daily Manpower Automation (Google Sheets)

This automation reads your live `RMD Drivers April 2026` tab, calculates daily manpower totals, and writes the outputs to two tabs:

- `Daily Summary`: totals by driver type (HB/LB/PD/WR/etc), status (OD/Idle/Sick/Vacation/Rig Site/etc), and OD workers grouped by location.
- `Operations Daily`: row-by-row operational details (who is working where).

## 1) Prerequisites

1. Create a Google Cloud project and enable **Google Sheets API**.
2. Create a service account and download the JSON key.
3. Share your Google Sheet with the service account email (Editor access).
4. Install Python dependencies:

```bash
pip install pyyaml google-api-python-client google-auth
```

## 2) Configure

```bash
cp scripts/manpower_config.example.yaml scripts/manpower_config.yaml
```

Edit `scripts/manpower_config.yaml`:

- `spreadsheet_id`: from your sheet URL.
- `credentials_json`: path to service-account JSON key.
- `tabs.source`: your source tab (`RMD Drivers April 2026`).
- `columns.driver_type`: should remain `F` per your request.
- adjust status/location/team column letters to match your sheet.

## 3) Run once

```bash
python scripts/manpower_automation.py --config scripts/manpower_config.yaml
```

It will update the output tabs and print a JSON execution summary.

## 4) Fully automate daily run

Use cron (Linux/macOS) to run every day at 06:00:

```bash
0 6 * * * cd /workspace/private-gpt && /usr/bin/python3 scripts/manpower_automation.py --config scripts/manpower_config.yaml >> /tmp/manpower_automation.log 2>&1
```

## Notes

- The script normalizes status aliases (`on duty` -> `OD`, etc.).
- Add any extra aliases in `status_aliases` to keep reporting consistent.
- If there are empty rows, they are ignored automatically.
