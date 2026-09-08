#!/usr/bin/env python3
"""Fetch verified npm observations and render the approved profile chart."""
from __future__ import annotations

import datetime as dt
import json
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from render_curve import render

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / 'data/npm-downloads.json'
SVG_PATH = ROOT / 'assets/npm-downloads.svg'
CUTOFF = dt.datetime.now(dt.timezone.utc).date() - dt.timedelta(days=1)
ACCOUNTS = ['liushiyumathxjtu', 'nyn5255']


def fetch_json(url: str) -> dict:
    request = urllib.request.Request(url, headers={'User-Agent': 'liush2yuxjtu-profile-download-chart/2.0'})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def discover_packages() -> list[dict]:
    found = {}
    for account in ACCOUNTS:
        offset = 0
        while True:
            query = urllib.parse.urlencode({'text': f'maintainer:{account}', 'size': 250, 'from': offset})
            payload = fetch_json('https://registry.npmjs.org/-/v1/search?' + query)
            objects = payload.get('objects', [])
            for entry in objects:
                package = entry['package']
                repository = package.get('links', {}).get('repository', '')
                if not repository.removeprefix('git+').startswith('https://github.com/liush2yuxjtu/'):
                    continue
                found.setdefault(package['name'], {'name': package['name'], 'account': account, 'repository': repository})
            offset += len(objects)
            if offset >= payload.get('total', 0) or not objects:
                break
    if not found:
        raise ValueError('npm returned no verified packages; refusing to overwrite the chart')
    return [found[name] for name in sorted(found)]


def date_range(start: dt.date, end: dt.date) -> list[str]:
    return [(start + dt.timedelta(days=i)).isoformat() for i in range(max(0, (end - start).days + 1))]


def package_data(package: dict) -> dict:
    encoded = urllib.parse.quote(package['name'], safe='')
    metadata = fetch_json(f'https://registry.npmjs.org/{encoded}')
    created = metadata['time']['created'][:10]
    start = dt.date.fromisoformat(created)
    downloads, urls = [], []
    available = start <= CUTOFF
    # Bounded queries remain valid when packages are older than one year.
    while start <= CUTOFF:
        end = min(start + dt.timedelta(days=364), CUTOFF)
        url = f'https://api.npmjs.org/downloads/range/{start}:{end}/{encoded}'
        urls.append(url)
        try:
            payload = fetch_json(url)
        except urllib.error.HTTPError as error:
            if error.code != 404:
                raise
            available = False
            break
        rows = payload.get('downloads', [])
        for day in rows:
            count = day.get('downloads')
            if type(count) is not int or count < 0 or not (str(start) <= day['day'] <= str(end)):
                raise ValueError(f'Invalid npm data for {package["name"]}')
        downloads.extend(rows)
        start = end + dt.timedelta(days=1)
    by_date = {row['day']: row['downloads'] for row in downloads}
    if len(by_date) != len(downloads):
        raise ValueError('Duplicate npm dates')
    expected = date_range(dt.date.fromisoformat(created), CUTOFF)
    complete = available and bool(expected) and set(by_date) == set(expected)
    status = 'available' if complete else ('partial' if downloads else 'not-available')
    return {**package, 'version': metadata.get('dist-tags', {}).get('latest'), 'created': created,
            'status': status, 'downloads': sorted(downloads, key=lambda d: d['day']),
            'total': sum(by_date.values()) if complete else None, 'sourceUrls': urls}


def aligned_series(record: dict, dates: list[str]) -> tuple[list, list]:
    by_date = {day['day']: day['downloads'] for day in record['downloads']}
    daily, totals = [], []
    total, contiguous = 0, True
    for day in dates:
        if day < record['created']:
            daily.append(None)
            totals.append(None)
            continue
        value = by_date.get(day)
        daily.append(value)
        if value is None:
            contiguous = False
        if contiguous:
            total += value
            totals.append(total)
        else:
            totals.append(None)
    return daily, totals


def render_svg(records: list[dict]) -> str:
    if not records:
        raise ValueError('Cannot render an empty package catalog')
    return render(records, CUTOFF, date_range, aligned_series)


def main() -> None:
    records = [package_data(p) for p in discover_packages()]
    payload = {'updatedAt': dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
               'cutoffDate': str(CUTOFF), 'source': 'https://api.npmjs.org/downloads/range/',
               'knownTotal': sum(r['total'] for r in records if r['status'] == 'available'),
               'complete': all(r['status'] == 'available' for r in records), 'packages': records}
    svg = render_svg(records)
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    SVG_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n')
    SVG_PATH.write_text(svg)
    print(json.dumps({'knownTotal': payload['knownTotal'], 'complete': payload['complete'], 'packages': len(records)}))


if __name__ == '__main__':
    main()
