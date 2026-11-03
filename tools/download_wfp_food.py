"""Download the seven HDX price series used by the retail importer."""
import json
from pathlib import Path
import subprocess
import sys
from urllib.parse import urlparse

countries = {'am':'armenia','az':'azerbaijan','ge':'georgia','kg':'kyrgyzstan',
             'kz':'kazakhstan','tj':'tajikistan','ua':'ukraine'}
folder = Path(sys.argv[1])
folder.mkdir(parents=True, exist_ok=True)
for code, name in countries.items():
    api = 'https://data.humdata.org/api/3/action/package_show?id=wfp-food-prices-for-' + name
    metadata = json.loads(subprocess.check_output(['curl','-fsSL','--retry','2','--max-time','60',api]))
    resources = metadata['result']['resources']
    url = next(item['url'] for item in resources if 'wfp_food_prices' in item['url'] and '.csv' in item['url'])
    if urlparse(url).scheme != 'https' or urlparse(url).hostname != 'data.humdata.org':
        raise ValueError('Unexpected HDX resource origin')
    path = folder/(code+'.csv')
    subprocess.run(['curl','-fsSL','--retry','2','--max-time','120',url,'-o',str(path)],check=True)
    with path.open() as stream:
        if 'priceflag' not in stream.readline() or not stream.readline().strip():
            raise ValueError('Incomplete price series for '+code)
