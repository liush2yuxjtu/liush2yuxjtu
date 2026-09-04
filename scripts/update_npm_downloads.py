#!/usr/bin/env python3
"""Fetch official npm download ranges and render a dependency-free profile SVG."""

from __future__ import annotations

import datetime as dt
import html
import json
import math
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data/npm-downloads.json"
SVG_PATH = ROOT / "assets/npm-downloads.svg"
TODAY = dt.date.today()
PACKAGES = [
    {"name": "pi-subtask", "account": "liushiyumathxjtu", "color": "#d8ff65"},
    {"name": "pi-voice-mode", "account": "liushiyumathxjtu", "color": "#6ee7d8"},
    {"name": "@liushiyumathxjtu/minimax-statusline", "account": "liushiyumathxjtu", "color": "#ffad5c"},
    {"name": "pi-strict-ask-mode", "account": "liushiyumathxjtu", "color": "#f47777"},
    {"name": "lan-artifacts-pi", "account": "liushiyumathxjtu", "color": "#b5a2ff"},
    {"name": "pi-qoder-account-provider", "account": "nyn5255", "color": "#70a7ff"},
    {"name": "pi-debug-mode", "account": "nyn5255", "color": "#f2e6c9"},
]


def fetch_json(url: str) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": "liush2yuxjtu-profile-download-chart/1.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def package_data(package: dict) -> dict:
    encoded = urllib.parse.quote(package["name"], safe="")
    metadata = fetch_json(f"https://registry.npmjs.org/{encoded}")
    created = metadata["time"]["created"][:10]
    latest = metadata.get("dist-tags", {}).get("latest")
    url = f"https://api.npmjs.org/downloads/range/{created}:{TODAY.isoformat()}/{encoded}"
    try:
        payload = fetch_json(url)
        downloads = payload.get("downloads", [])
        status = "available"
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise
        downloads = []
        status = "not-available"
    return {
        **package,
        "version": latest,
        "created": created,
        "status": status,
        "downloads": downloads,
        "total": sum(int(day.get("downloads", 0)) for day in downloads),
    }


def moving_average(values: list[int], window: int = 7) -> list[float]:
    result: list[float] = []
    for index in range(len(values)):
        chunk = values[max(0, index - window + 1) : index + 1]
        result.append(sum(chunk) / len(chunk))
    return result


def cumulative(values: list[int]) -> list[int]:
    total = 0
    result = []
    for value in values:
        total += value
        result.append(total)
    return result


def aligned_series(record: dict, dates: list[str]) -> tuple[list[float | None], list[float | None]]:
    by_date = {day["day"]: int(day["downloads"]) for day in record["downloads"]}
    active_dates = [date for date in dates if date >= record["created"]]
    raw = [by_date.get(date, 0) for date in active_dates]
    daily = moving_average(raw)
    totals = cumulative(raw)
    prefix = [None] * (len(dates) - len(active_dates))
    return prefix + daily, prefix + totals


def points(values: list[float | None], x: float, y: float, width: float, height: float, maximum: float) -> str:
    if not values:
        return ""
    denominator = max(1, len(values) - 1)
    return " ".join(
        f"{x + width * i / denominator:.1f},{y + height - height * value / max(1, maximum):.1f}"
        for i, value in enumerate(values)
        if value is not None
    )


def render_svg(records: list[dict]) -> str:
    width, height = 1200, 760
    left, chart_width = 76, 1080
    panel_height = 210
    top_a, top_b = 185, 470
    available = [record for record in records if record["status"] == "available"]
    first_day = min(dt.date.fromisoformat(record["created"]) for record in records)
    dates = [(first_day + dt.timedelta(days=offset)).isoformat() for offset in range((TODAY - first_day).days + 1)]
    aligned = [aligned_series(record, dates) for record in available]
    daily_series = [series[0] for series in aligned]
    cumulative_series = [series[1] for series in aligned]
    daily_max = max([max((value for value in series if value is not None), default=0) for series in daily_series] + [1])
    cumulative_max = max([max((value for value in series if value is not None), default=0) for series in cumulative_series] + [1])
    known_total = sum(record["total"] for record in available)
    unavailable = [record["name"] for record in records if record["status"] != "available"]

    grid = []
    for panel_top, maximum in [(top_a, daily_max), (top_b, cumulative_max)]:
        for step in range(5):
            yy = panel_top + panel_height * step / 4
            value = maximum * (4 - step) / 4
            grid.append(f'<line x1="{left}" y1="{yy:.1f}" x2="{left + chart_width}" y2="{yy:.1f}" class="grid"/>')
            grid.append(f'<text x="{left - 12}" y="{yy + 4:.1f}" text-anchor="end" class="axis">{value:.0f}</text>')

    curves = []
    for record, daily, totals in zip(available, daily_series, cumulative_series):
        safe_name = html.escape(record["name"])
        curves.append(f'<polyline points="{points(daily, left, top_a, chart_width, panel_height, daily_max)}" stroke="{record["color"]}" class="curve"><title>{safe_name}: 7-day average</title></polyline>')
        curves.append(f'<polyline points="{points(totals, left, top_b, chart_width, panel_height, cumulative_max)}" stroke="{record["color"]}" class="curve"><title>{safe_name}: {record["total"]} cumulative downloads</title></polyline>')

    legend = []
    for index, record in enumerate(records):
        column = index % 4
        row = index // 4
        x = 76 + column * 278
        y = 120 + row * 25
        suffix = f'{record["total"]:,}' if record["status"] == "available" else "N/A"
        display_name = record["name"].removeprefix("@liushiyumathxjtu/")
        legend.append(f'<circle cx="{x}" cy="{y - 4}" r="4" fill="{record["color"]}"/>')
        legend.append(f'<text x="{x + 11}" y="{y}" class="legend">{html.escape(display_name)} · {suffix}</text>')

    note = "All package statistics available."
    if unavailable:
        note = "Unavailable from npm Downloads API: " + ", ".join(unavailable) + ". N/A is never treated as zero."

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="760" viewBox="0 0 1200 760" role="img" aria-labelledby="title desc">
<title id="title">npm package download curves</title>
<desc id="desc">Seven package download curves using official npm data, updated {TODAY.isoformat()}.</desc>
<style>
.bg{{fill:#11120f}}.grid{{stroke:#34362f;stroke-width:1}}.axis{{fill:#74786d;font:11px ui-monospace,SFMono-Regular,Menlo,monospace}}.curve{{fill:none;stroke-width:2.4;stroke-linecap:round;stroke-linejoin:round}}.legend{{fill:#c9ccc1;font:12px ui-monospace,SFMono-Regular,Menlo,monospace}}.label{{fill:#8e9286;font:11px ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:1.5px}}.heading{{fill:#f3f1e9;font:700 34px Georgia,serif}}.metric{{fill:#d8ff65;font:700 28px ui-monospace,SFMono-Regular,Menlo,monospace}}.note{{fill:#898d82;font:11px ui-monospace,SFMono-Regular,Menlo,monospace}}
</style>
<rect class="bg" width="1200" height="760" rx="18"/>
<text x="48" y="52" class="label">PUBLIC NPM PACKAGES · OFFICIAL DOWNLOADS API</text>
<text x="48" y="91" class="heading">Shipping in public, measured daily.</text>
<text x="1152" y="54" text-anchor="end" class="metric">{known_total:,}</text>
<text x="1152" y="76" text-anchor="end" class="label">KNOWN CUMULATIVE DOWNLOADS</text>
{''.join(legend)}
<text x="{left}" y="{top_a - 18}" class="label">DAILY DOWNLOADS · 7-DAY MOVING AVERAGE · {dates[0]} TO {dates[-1]}</text>
{''.join(grid)}
{''.join(curves)}
<text x="{left}" y="{top_b - 18}" class="label">CUMULATIVE DOWNLOADS SINCE EACH PACKAGE LAUNCH</text>
<text x="48" y="735" class="note">Updated {TODAY.isoformat()} · {html.escape(note)}</text>
</svg>'''


def main() -> None:
    records = [package_data(package) for package in PACKAGES]
    payload = {
        "updatedAt": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "source": "https://api.npmjs.org/downloads/range/",
        "knownTotal": sum(record["total"] for record in records if record["status"] == "available"),
        "complete": all(record["status"] == "available" for record in records),
        "packages": records,
    }
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    SVG_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    SVG_PATH.write_text(render_svg(records))
    print(json.dumps({"knownTotal": payload["knownTotal"], "complete": payload["complete"]}))


if __name__ == "__main__":
    main()
