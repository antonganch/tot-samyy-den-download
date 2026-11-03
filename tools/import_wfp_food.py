"""Merge measured WFP retail prices (downloaded HDX country CSVs) into the almanac.

Run: python3 tools/import_wfp_food.py /path/to/country-csv-directory /path/to/places.json
Each CSV is named for its app country code. Product rates are per kg, litre or 10 eggs.
"""
import csv
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import median
import sys

source, gazetteer = map(Path, sys.argv[1:])
places = json.loads(gazetteer.read_text())
out = Path(__file__).resolve().parents[1] / 'v1/food'
currencies = dict(am='AMD', az='AZN', ge='GEL', kg='KGS', kz='KZT', tj='TJS', ua='UAH')
names = {
    'Apples':'apple', 'Apples (red)':'apple', 'Beetroots':'beet', 'Bread':'bread',
    'Bread (rye)':'bread', 'Bread (first grade flour)':'bread', 'Bread (wheat)':'bread',
    'Buckwheat':'buckwheat', 'Butter':'butter', 'Cabbage':'cabbage', 'Carrots':'carrot',
    'Curd':'curd', 'Eggs':'eggs', 'Garlic':'garlic', 'Meat (beef)':'beef',
    'Meat (chicken)':'chicken', 'Meat (chicken, whole)':'chicken', 'Milk':'milk',
    'Onions':'onion', 'Potatoes':'potato', 'Rice':'rice', 'Rice (white)':'rice',
    'Sour cream':'sourcream', 'Sugar':'sugar', 'Tea (black)':'tea',
    'Wheat flour':'flour', 'Wheat flour (first grade)':'flour',
}
aliases = {'Nur-Sultan':'Астана','Kyiv city':'Киев','Gharm':'Гарм','Bokhtar':'Бохтар','Khorog':'Хорог'}
for cc, currency in currencies.items():
    csv_path = source / (cc+'.csv')
    if not csv_path.exists():
        continue
    cities = {r[5].lower():r[0] for r in reversed(places) if r[4]==cc and r[5]}
    monthly = defaultdict(lambda: defaultdict(list))
    with csv_path.open() as f:
        for row in csv.DictReader(f):
            if row['pricetype']!='Retail' or row['priceflag'] not in ('actual','aggregate') or row['currency']!=currency:
                continue
            year, month = map(int, row['date'][:7].split('-'))
            name = row['market']
            if cc=='ua' and name not in ('National Average','Kyiv city'):
                continue
            city = '' if name=='National Average' else aliases.get(name) or cities.get(name.lower())
            key = names.get(row['commodity'])
            if city is None or not key:
                continue
            scale = {'KG':1,'150 G':1/.15,'200 G':5,'500 G':2,'50 KG':1/50}.get(row['unit'])
            if key=='eggs':
                scale={'Unit':10,'10 pcs':1}.get(row['unit'])
            if key=='milk':
                scale = 1 if row['unit']=='L' else None
            price = float(row['price'])
            if scale and math.isfinite(price) and price>0:
                monthly[(year,city,key)][month].append(price*scale)
    path=out/(cc+'.json')
    data=json.loads(path.read_text()) if path.exists() else {}
    annual=defaultdict(dict)
    for (year,city,key), months in monthly.items():
        annual[(year,city)][key]=round(median(median(v) for v in months.values()),3)
    for (year,city), prices in annual.items():
        rec=data.setdefault(str(year),{'currency':currency})
        if rec['currency']!=currency:
            continue
        if city:
            rec.setdefault('cities',{})[city]={'region':cc,'start':f'{year}-01-01','retail':prices,
                'note':f'Ориентир для чека — розничные цены за {year} год. Город наблюдения — {city}.'}
        else:
            # Prefer existing published monthly or annual retail figures.
            if not rec.get('retail'):
                rec['retail']=prices
                rec['note']=f'Оценка по розничным наблюдениям в стране за {year} год.'
    path.write_text(json.dumps(data,ensure_ascii=False,separators=(',',':'))+'\n')
    print(cc,len(monthly),len(annual))
