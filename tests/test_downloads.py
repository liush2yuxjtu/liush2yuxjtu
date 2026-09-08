import datetime as dt
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
spec = importlib.util.spec_from_file_location('chart', Path(__file__).resolve().parents[1] / 'scripts/update_npm_downloads.py')
chart = importlib.util.module_from_spec(spec)
spec.loader.exec_module(chart)


def record(days):
    return {'name': 'example', 'created': '2026-09-01', 'downloads': days, 'status': 'available', 'total': sum(d['downloads'] for d in days), 'color': '#ffffff'}


class DownloadsTest(unittest.TestCase):
    def test_daily_is_raw_not_smoothed(self):
        r = record([{'day': '2026-09-01', 'downloads': 10}, {'day': '2026-09-02', 'downloads': 2}])
        daily, total = chart.aligned_series(r, ['2026-09-01', '2026-09-02'])
        self.assertEqual(daily, [10, 2])
        self.assertEqual(total, [10, 12])

    def test_missing_date_is_not_zero_or_connected(self):
        r = record([{'day': '2026-09-01', 'downloads': 10}, {'day': '2026-09-03', 'downloads': 2}])
        daily, total = chart.aligned_series(r, ['2026-09-01', '2026-09-02', '2026-09-03'])
        self.assertEqual(daily, [10, None, 2])
        self.assertEqual(total, [10, None, None])

    def test_before_publication_is_unknown(self):
        daily, _ = chart.aligned_series(record([{'day': '2026-09-01', 'downloads': 0}]), ['2026-08-31', '2026-09-01'])
        self.assertEqual(daily, [None, 0])

    def test_cutoff_is_yesterday_utc(self):
        self.assertEqual(chart.CUTOFF, dt.datetime.now(dt.timezone.utc).date() - dt.timedelta(days=1))

    def test_registry_discovery_includes_new_package(self):
        def fake(url):
            return {'objects': [{'package': {'name': 'pi-design-mode', 'links': {'repository': 'git+https://github.com/liush2yuxjtu/pi-design-mode.git'}}}], 'total': 1}
        with patch.object(chart, 'fetch_json', side_effect=fake):
            self.assertEqual([p['name'] for p in chart.discover_packages()], ['pi-design-mode'])

    def test_pending_package_has_no_zero_total(self):
        def fake(url):
            return {'time': {'created': '2026-09-08T00:00:00Z'}, 'dist-tags': {'latest': '1.0'}}
        with patch.object(chart, 'CUTOFF', dt.date(2026, 9, 7)), patch.object(chart, 'fetch_json', side_effect=fake):
            r = chart.package_data({'name': 'new', 'color': '#ffffff'})
        self.assertIsNone(r['total'])
        self.assertEqual(r['status'], 'not-available')

    def test_svg_has_dates_and_raw_label(self):
        with patch.object(chart, 'CUTOFF', dt.date(2026, 9, 2)):
            svg = chart.render_svg([record([{'day': '2026-09-01', 'downloads': 10}, {'day': '2026-09-02', 'downloads': 2}])])
        ET.fromstring(svg)
        self.assertIn('每日下载', svg)
        self.assertIn('2026-09-02', svg)
        self.assertNotIn('MOVING AVERAGE', svg)
        self.assertIn('<circle', svg)

    def test_window_is_exactly_30_days_not_since_launch(self):
        days = chart.date_range(dt.date(2026, 8, 1), dt.date(2026, 9, 7))
        r = record([{'day': d, 'downloads': 1} for d in days])
        r['created'] = days[0]
        with patch.object(chart, 'CUTOFF', dt.date(2026, 9, 7)):
            svg = chart.render_svg([r])
        self.assertIn('2026-08-09', svg)
        self.assertIn('>30</text>', svg)
        self.assertIn('>38</text>', svg)

    def test_partial_and_na_are_not_counted(self):
        r = record([{'day': '2026-09-01', 'downloads': 50}])
        r.update(status='partial', total=None)
        with patch.object(chart, 'CUTOFF', dt.date(2026, 9, 2)):
            svg = chart.render_svg([r])
        self.assertIn('待统计', svg)
        self.assertNotIn('>50</text>', svg)
        self.assertIn('>N/A</text>', svg)


if __name__ == '__main__':
    unittest.main()
