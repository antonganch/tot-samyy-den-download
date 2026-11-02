"""Refresh Kyiv's dated metro tariff rows from the payment-history table."""
import calendar
import json
import re
from datetime import date, timedelta
from pathlib import Path
from urllib.request import urlopen

url = 'https://www.metropoliten.kiev.ua/price.php?lang=2'
html = urlopen(url, timeout=15).read().decode('cp1251')
changes = re.findall(r'<td>(\d{2})\.(\d{4})</td>\s*<td>([\d ]+)\s+(kop\.|krb\.)</td>', html)
if len(changes) < 12:
    raise ValueError('Unexpected fare table format')
path = Path(__file__).resolve().parents[1] / 'v1/everyday/records.json'
archive = json.loads(path.read_text())
rows = [r for r in archive['fares'] if r.get('url') != url]
for (month, year, amount, unit), (next_month, next_year, *_) in zip(changes, changes[1:]):
    # Month-only change dates cannot establish which tariff applied inside that month.
    m, y = int(month), int(year)
    start = date(y, m, calendar.monthrange(y, m)[1]) + timedelta(days=1)
    end = date(int(next_year), int(next_month), 1) - timedelta(days=1)
    if start > end or start.year == 1996 and m == 9:
        continue
    rows.append(dict(city='Киев', region='ua', start=str(start), end=str(end),
                     place='Киев · метро', price=amount.strip() + (' коп.' if unit=='kop.' else ' крб.'),
                     detail='Одна поездка в Киевском метрополитене.', url=url))
archive['fares'] = rows
path.write_text(json.dumps(archive, ensure_ascii=False, indent=2)+'\n')
