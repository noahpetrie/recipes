# home fork: builds home_usda_sr_legacy.json.gz from the USDA FoodData Central SR Legacy CSVs
# (https://fdc.nal.usda.gov/download-datasets, "SR Legacy" CSV). Usage: python build_usda_table.py <csv dir> <out.json.gz>
import csv, gzip, json, sys, collections
src, out = sys.argv[1], sys.argv[2]
NUTRIENTS = {'1008', '1003', '1004', '1005', '1079', '2000', '1093', '1258'}
rd = lambda n: csv.DictReader(open(f'{src}/{n}', newline='', encoding='utf-8'))
units = {r['id']: r['name'] for r in rd('measure_unit.csv')}
nut = collections.defaultdict(dict)
for r in rd('food_nutrient.csv'):
    if r['nutrient_id'] in NUTRIENTS and r['amount'] != '':
        nut[r['fdc_id']][r['nutrient_id']] = round(float(r['amount']), 3)
por = collections.defaultdict(list)
for r in rd('food_portion.csv'):
    u = units.get(r['measure_unit_id'], '')
    por[r['fdc_id']].append([float(r['amount'] or 1), '' if u == 'undetermined' else u, r['modifier'], round(float(r['gram_weight']), 2)])
foods = []
for r in rd('food.csv'):
    foods.append([int(r['fdc_id']), r['description'], int(r['food_category_id'] or 0), nut.get(r['fdc_id'], {}), por.get(r['fdc_id'], [])])
cats = {int(r['id']): r['description'] for r in rd('food_category.csv')}
with gzip.open(out, 'wt', encoding='utf-8') as f:
    json.dump({'source': 'USDA FoodData Central, SR Legacy (April 2018), public domain', 'categories': cats, 'foods': foods}, f, separators=(',', ':'))
print(len(foods), 'foods')
