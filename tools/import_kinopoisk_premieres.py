"""Import release dates from the Russian premiere calendar for the supplied years."""
import concurrent.futures
from datetime import date
from html import unescape
import json
from pathlib import Path
import re
import subprocess
import sys

charts = Path(__file__).resolve().parents[1] / 'v1/charts'


def load_month(period):
    year, month = period
    url = f'https://www.kinopoisk.ru/premiere/ru/{year}/month/{month}/'
    result = subprocess.run(['curl', '-fsSL', '--max-time', '12', '-A', 'Googlebot', url], capture_output=True)
    films = {}
    for item in result.stdout.decode('utf8', 'replace').split('class="premier_item"')[1:]:
        title = re.search(r'itemprop="name"><a href="/film/(\d+)/">([^<]+)</a>', item)
        start = re.search(r'itemprop="startDate" content="([\d-]+)"', item)
        if not title or not start or not start[1].startswith(f'{year}-{month:02}-'):
            continue
        release = date.fromisoformat(start[1]).isoformat()
        votes = re.search(r'Рейтинг фильма:<u>[^<]*<b>(.*?)</b>', item)
        score = int(re.sub(r'\D', '', unescape(votes[1])) or 0) if votes else 0
        if release not in films or score > films[release][0]:
            films[release] = score, [release, unescape(title[2]), title[1]]
    return [row for score, row in films.values()]


if __name__ == '__main__':
    with concurrent.futures.ThreadPoolExecutor(12) as pool:
        for year in map(int, sys.argv[1:]):
            path = charts / f'{year}.json'
            data = json.loads(path.read_text()) if path.exists() else {}
            previous = {row[0]: row for row in data.get('premieres', [])}
            for rows in pool.map(load_month, [(year, m) for m in range(1, 13)]):
                previous.update({row[0]: row for row in rows})
            if previous:
                data['premieres'] = sorted(previous.values())
                path.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':'))+'\n')
            print(year, len(previous), flush=True)
