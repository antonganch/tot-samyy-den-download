import csv,io,zipfile,re,json,calendar,urllib.request,concurrent.futures
from pathlib import Path
from collections import defaultdict
import sys
# Pass the FAOSTAT Prices_E_All_Data_(Normalized).zip download as the argument.
out=Path(__file__).resolve().parents[1]/'v1/food';out.mkdir(exist_ok=True)
regions={'Armenia':('am','AMD',1994),'Azerbaijan':('az','AZN',2007),'Belarus':('by','BYN',2017),'Estonia':('ee','EUR',2011),'Georgia':('ge','GEL',1996),'Kazakhstan':('kz','KZT',1994),'Kyrgyzstan':('kg','KGS',1994),'Latvia':('lv','EUR',2014),'Lithuania':('lt','EUR',2015),'Republic of Moldova':('md','MDL',1994),'Russian Federation':('ru','RUB',1999),'Tajikistan':('tj','TJS',2001),'Turkmenistan':('tm','TMT',2010),'Ukraine':('ua','UAH',1997),'Uzbekistan':('uz','UZS',1995)}
records=defaultdict(dict)
items={'Potatoes':'potato','Carrots and turnips':'carrot','Apples':'apple','Onions and shallots, dry (excluding dehydrated)':'onion','Cabbages':'cabbage'}
with zipfile.ZipFile(sys.argv[1]) as z:
 for r in csv.DictReader(io.TextIOWrapper(z.open(z.namelist()[0]),encoding='latin1')):
  if r['Area'] not in regions or r['Element Code']!='5530' or r['Months']!='Annual value' or r['Item'] not in items or not r['Value']:continue
  reg,cur,minimum=regions[r['Area']];yr=int(r['Year'])
  if yr<minimum:
   cur=next((c for rr,c,start,end in [('lv','LVL',1994,2013),('lt','LTL',1994,2014),('ee','EEK',1993,2010),('by','BYR',2001,2015),('az','AZM',1995,2005),('ua','UAK',1994,1995),('ru','RUB',1994,1997)] if rr==reg and start<=yr<=end),None)
   if not cur:continue
  val=float(r['Value'])/1000
  if val>0:records[reg].setdefault(str(yr),dict(currency=cur,farm={} ))['farm'][items[r['Item']]]=round(val,4)
mapping=dict(potato='potato',eggs='eggs',beef='beef',poultry_chicken_carcass='chicken',apples='apple',carrot='carrot',onion='onion',cabbage_white='cabbage',beet='beet',rye_bread_ryewheat_bread='bread',rice='rice',wheat_flour='flour',sugar='sugar',butter='butter',buckwheat='buckwheat',fat_cottage_cheese='curd',vodka='vodka')
def retail(y):
 import subprocess
 s=subprocess.run(['curl','-fLs','--retry','1','--max-time','10',f'https://index.minfin.com.ua/ua/markets/product-prices/{y}/'],capture_output=True).stdout.decode()
 if f'({y})' not in s[:500]:raise ValueError(f'Unexpected retail table: {y}')
 mths=[{} for i in range(12)]
 for tr in re.findall('<tr[^>]*>(.*?)</tr>',s,re.S):
  slug=re.search(r"product-prices/(\w+)/'",tr)
  if not slug or slug[1] not in mapping:continue
  vals=re.findall(r"<td align='right'>(.*?)</td>",tr,re.S)
  for i,v in enumerate(vals[:12]):
   v=re.sub('<.*?>','',v).strip().replace(',','.')
   if re.fullmatch(r'\d+(\.\d+)?',v):mths[i][mapping[slug[1]]]=round(float(v)*(2 if slug[1]=='vodka' else 1),2)
 if any(mths):return str(y),mths
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
 for y,months in ex.map(retail,range(2018,2027)):
  if months:records['ua'].setdefault(y,{'currency':'UAH'})['monthly']=months
for i,y in enumerate(['2000','2005','2010','2014','2015','2016']):
 records['ru'].setdefault(y,{'currency':'RUB'})['retail']={k:v[i] for k,v in dict(potato=[5.19,9.72,28.94,26.66,19.91,20.25],eggs=[16.57,24.50,38.56,58.76,65.02,64.17],chicken=[48.8,81.35,105.14,136.14,133.73,138.49],bread=[7.76,14.89,28.07,36.99,41.85,44.51],sausage=[77.97,142.85,235.96,310.54,344.81,351.27],sugar=[15.62,19.69,40.62,44.97,52.14,48.78],milk=[9.7,17.35,31.99,43.81,47.61,51.44]).items()}
for reg,rows in records.items():(out/(reg+'.json')).write_text(json.dumps(rows,separators=(',',':'))+'\n')
print({k:len(v) for k,v in records.items()})
