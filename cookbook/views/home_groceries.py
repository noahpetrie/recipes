"""
home fork: "Add groceries" — put a whole shop into the pantry at once.

  GET  /api/home/groceries/          foods to pick from (what the recipes use, what was bought before),
                                     each with where it usually goes and how long it keeps
  POST /api/home/groceries/match/    {text} a pasted receipt or online order -> one suggestion per line
  POST /api/home/groceries/          {items: [{food_id | food_name, amount, unit_id, location_id, expires}],
                                     request_id} adds every item through the pantry's own "add" booking
                                     (cookbook/views/home_pantry.py), so each one is logged and can be undone

Where things go and how long they keep come from cookbook/helper/home_aisles.py.
"""
import datetime
import re
from collections import Counter

from django.core.cache import caches
from django.db import transaction
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from cookbook.helper import home_aisles, home_nutrition
from cookbook.helper.home_nutrition import words
from cookbook.helper.permission_helper import get_household_user_ids
from cookbook.models import Food, Ingredient, InventoryEntry, InventoryLocation, Unit
from cookbook.views import home_pantry
from cookbook.views.home_pantry import PERMS, unit_json

IDEMPOTENCY_SECONDS = 15 * 60
# receipt words that never name a food
NOISE = {'pc', 'org', 'organic', 'ns', 'nf', 'kg', 'lb', 'ea', 'each', 'pk', 'pack', 'x', 'g', 'ml', 'l', 'oz', 'ct', 'count',
         'hst', 'gst', 'tax', 'item', 'large', 'medium', 'small', 'fresh', 'whole', 'brand', 'the', 'of', 'and', 'with', 'no',
         'name', 'select', 'blue', 'menu', 'president', 'choice', 'compliment', 'great', 'value', 'kirkland', 'signature'}
NOT_FOOD = re.compile(r'^\s*(sub ?total|total|tax|hst|gst|change|cash|visa|mastercard|debit|balance|points|savings|you saved|'
                      r'thank|store|tel|phone|date|time|cashier|order|delivery|tip|fee|bag fee|deposit|eco)', re.I)


def defaults(food, locations, units):
    place, days = home_aisles.storage(food)
    loc = locations.get(place.lower()) or next(iter(locations.values()), None)
    # produce is counted (3 onions); everything else comes in a package
    counted = food.supermarket_category_id and food.supermarket_category.name == 'Produce'
    unit = food.preferred_unit or units.get('pcs' if counted else 'package') or units.get('package')
    return {'location_id': loc.id if loc else None, 'days': days, 'unit': unit_json(unit)}


def context(space, user_space):
    locations = {l.name.lower(): l for l in InventoryLocation.objects.filter(space=space).order_by('id')}
    units = {u.name.lower(): u for u in Unit.objects.filter(space=space)}
    staples = set(Food.objects.filter(space=space, onhand_users__id__in=get_household_user_ids(user_space)).values_list('id', flat=True))
    stock = set(InventoryEntry.objects.filter(space=space, amount__gt=0).values_list('food_id', flat=True))
    return locations, units, staples, stock


def food_row(food, locations, units, staples, stock, recipes=0, bought=0):
    return {'id': food.id, 'name': food.name, 'aisle': food.supermarket_category.name if food.supermarket_category_id else None,
            'recipes': recipes, 'bought': bought, 'staple': food.id in staples, 'in_stock': food.id in stock,
            **defaults(food, locations, units)}


@api_view(['GET', 'POST'])
@permission_classes(PERMS)
def groceries(request):
    if request.method == 'POST':
        return add(request)
    space = request.space
    locations, units, staples, stock = context(space, request.user_space)
    recipes = Counter(Ingredient.objects.filter(space=space, step__recipe__isnull=False, food__isnull=False, is_header=False)
                      .values_list('food_id', flat=True))
    bought = Counter(InventoryEntry.objects.filter(space=space).values_list('food_id', flat=True))
    foods = Food.objects.filter(space=space, id__in=set(recipes) | set(bought), ignore_shopping=False).select_related('supermarket_category', 'preferred_unit')
    rows = [food_row(f, locations, units, staples, stock, recipes[f.id], bought[f.id]) for f in foods]
    rows.sort(key=lambda r: (home_aisles.STORE_ORDER.index(r['aisle']) if r['aisle'] in home_aisles.STORE_ORDER else 99, r['name'].lower()))
    return Response({
        'foods': rows,
        'locations': [{'id': l.id, 'name': l.name} for l in locations.values()],
        'units': [unit_json(u) for u in sorted(units.values(), key=lambda u: u.name.lower())],
        'today': datetime.date.today().isoformat(),
    })


def line_amount(line):
    """'2 x Bananas', 'Bananas x2', 'Eggs (12) 2 @ 3.99' -> (2, rest) ; default 1"""
    m = re.match(r'^\s*(\d{1,2})\s*(?:x|×|@)?\s+(.*)$', line, re.I) or re.match(r'^(.*?)\s*(?:x|×|qty:?)\s*(\d{1,2})\b.*$', line, re.I)
    if not m:
        return 1, line
    a, b = m.groups()
    return (int(a), b) if a.isdigit() else (int(b), a)


def clean(line):
    line = re.sub(r'\$?\d+[.,]\d{2}\b.*$', '', line)          # prices and whatever follows
    line = re.sub(r'\b\d{5,}\b', '', line)                     # product codes
    line = re.sub(r'\b\d+(\.\d+)?\s*(kg|g|lb|ml|l|oz|ct)\b', '', line, flags=re.I)  # sizes
    return re.sub(r'\s+', ' ', line).strip(' -*:,')


def best_food(text, foods, used):
    """
    the food whose name's words all appear in the line (most words wins, then foods the recipes or
    pantry already use), else a short name sharing the line's main noun
    """
    ws = set(words(text)) - NOISE
    if not ws:
        return None
    best, score = None, (0, 0)
    for f, fw in foods:
        if fw and fw <= ws and (len(fw), f.id in used) > score:
            best, score = f, (len(fw), f.id in used)
    if best:
        return best
    for f, fw in sorted(foods, key=lambda x: x[0].id not in used):  # "Bananas, organic" vs food "Banana"
        head = list(fw)[-1:] if fw else []
        if head and head[0] in ws and len(fw) <= 2:
            return f
    return None


@api_view(['POST'])
@permission_classes(PERMS)
def match(request):
    space = request.space
    text = str(request.data.get('text') or '')[:20000]
    locations, units, staples, stock = context(space, request.user_space)
    foods = [(f, set(words(f.name)) - NOISE) for f in Food.objects.filter(space=space).select_related('supermarket_category', 'preferred_unit')]
    used = set(Ingredient.objects.filter(space=space, food__isnull=False).values_list('food_id', flat=True)) | \
        set(InventoryEntry.objects.filter(space=space).values_list('food_id', flat=True))
    out = []
    for raw in text.splitlines():
        if not raw.strip() or NOT_FOOD.match(raw):
            continue
        amount, rest = line_amount(raw)
        name = clean(rest)
        if len(name) < 2 or not re.search(r'[a-zA-Z]{2}', name):
            continue
        food = best_food(name, foods, used)
        row = {'line': raw.strip()[:120], 'amount': amount, 'name': name[:128]}
        if food:
            row['food'] = food_row(food, locations, units, staples, stock)
        out.append(row)
    return Response({'lines': out})


def add(request):
    d = request.data
    rid = str(d.get('request_id') or '')[:64]
    cache = caches['default']
    key = f'home_groceries_req_{request.space.id}_{request.user.id}_{rid}'
    if rid and (hit := cache.get(key)):
        return Response(hit['body'], status=hit['status'])
    items = d.get('items') or []
    if not isinstance(items, list) or not items:
        return Response({'error': 'Choose at least one item.'}, status=400)
    added = []
    try:
        with transaction.atomic():
            for n, it in enumerate(items[:200], 1):
                food_id = it.get('food_id')
                if not food_id:
                    name = str(it.get('food_name') or '').strip()[:128]
                    if not name:
                        raise ValueError(f'Item {n} has no food.')
                    food = Food.objects.filter(space=request.space, name__iexact=name).first()
                    if food is None:
                        food = Food.objects.create(space=request.space, name=name[0].upper() + name[1:])
                        home_nutrition.fill_new_food(food)
                    food_id = food.id
                body, status = home_pantry._adjust(request, {
                    'action': 'add', 'food_id': food_id, 'unit_id': it.get('unit_id'), 'amount': it.get('amount') or 1,
                    'location_id': it.get('location_id'), 'expires': it.get('expires')})
                if status >= 400:
                    raise ValueError(body.get('error') or f'Item {n} could not be added.')
                added.append(body.get('message') or '')
    except ValueError as e:
        body, status = {'error': str(e)}, 400
    else:
        body, status = {'added': len(added), 'messages': added}, 200
    if rid:
        cache.set(key, {'body': body, 'status': status}, IDEMPOTENCY_SECONDS)
    return Response(body, status=status)
