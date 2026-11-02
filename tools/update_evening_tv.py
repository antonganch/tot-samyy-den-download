"""Read dated schedules published by Karusel and keep confirmed evening listings."""
import datetime as dt
import html
import json
from pathlib import Path
import re
import urllib.request

months = 'января февраля марта апреля мая июня июля августа сентября октября ноября декабря'.split()
source = 'https://t.me/s/karusel'
charts = Path(__file__).resolve().parents[1] / 'v1/charts'
page = source
found = 0
for _ in range(4):
    with urllib.request.urlopen(page, timeout=20) as response:
        posts = response.read().decode().split('data-post="karusel/')[1:]
    if not posts:
        break
    for post in posts:
        post_id = post.split('"')[0]
        body = html.unescape(re.sub('<[^>]+>', '', post.replace('<br/>', '\n')))
        heading = re.search(r'Программа передач на [а-яё]+, (\d+) ([а-я]+)\s*\(Мск\)', body, re.I)
        slot = re.search(r'^((?:1[89]|2[0-3]):[0-5]\d)\s+Спокойной ночи, малыши!', body, re.M)
        stamp = re.search(r'datetime="([\d-]+)T', post)
        if not heading or not slot or not stamp or heading[2] not in months:
            continue
        published = dt.date.fromisoformat(stamp[1])
        candidates = [published + dt.timedelta(days=i) for i in range(-1, 8)]
        for day in candidates:
            if day.day != int(heading[1]) or day.month != months.index(heading[2])+1:
                continue
            path = charts / f'{day.year}.json'
            data = json.loads(path.read_text()) if path.exists() else {}
            rows = {r['airDate']: r for r in data.get('karusel', [])}
            rows[day.isoformat()] = dict(country='Россия', audience='children', genre='kids-show',
                program='Спокойной ночи, малыши!', channel='Карусель', airDate=day.isoformat(),
                time=slot[1]+' МСК', url='https://t.me/karusel/'+post_id)
            data['karusel'] = [rows[k] for k in sorted(rows)]
            path.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':'))+'\n')
            found += 1
    page = source+'?before='+posts[0].split('"')[0]
if not found:
    raise SystemExit('No dated evening listings found')
