"""
home fork: what to buy again, where to buy it, and "I have it".

  GET  /api/home/restock/       foods that are due again by how often they're bought (product_info.orders
                                dates from past store orders), not in stock and not on the shopping list;
                                fresh ones are held back when the meal plan shows you away soon
  GET  /api/home/store-links/   {food id: {name, url, image}} the store product usually bought, for each
                                food on the shopping list (Loblaws links built from the order's product code)
  POST /api/home/have/          {food_id} "I have it": books a sensible amount into the pantry (enough for
                                any recipe that uses it) and takes the food off the shopping list
"""
import datetime
import math
import re
import statistics

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from cookbook.helper import home_aisles
from cookbook.models import Food, Ingredient, InventoryEntry, InventoryLocation, MealPlan, ShoppingListEntry, Unit
from cookbook.views import home_pantry
from cookbook.views.home_pantry import PERMS, get_obj, num

AWAY = re.compile(r'travel|away|trip|vacation|holiday|cottage|out of town', re.I)
AWAY_SOON_DAYS = 4      # fresh food bought now would sit through an absence starting this soon
FRESH_DAYS = 21         # keeps this many days or fewer: fresh


def _orders(food):
    return (food.product_info or {}).get('orders') or []


def _top(path):
    return path[:Food.steplen]


def away_soon(space):
    """the next meal plan entry that looks like being away, if it starts within a few days"""
    now = timezone.now()
    plans = MealPlan.objects.filter(space=space, to_date__gte=now, from_date__lte=now + datetime.timedelta(days=AWAY_SOON_DAYS)) \
        .select_related('recipe').order_by('from_date')
    for m in plans:
        if AWAY.search(m.title or '') or (m.recipe and AWAY.search(m.recipe.name)):
            return {'title': m.title or m.recipe.name, 'from': m.from_date.date().isoformat(), 'to': m.to_date.date().isoformat()}
    return None


def best_order(foods):
    """(food, order) bought most recently among foods, preferring orders with a store link"""
    best = None
    for f in foods:
        for o in _orders(f):
            key = (bool(o.get('url')), o.get('last') or '')
            if best is None or key > best[0]:
                best = (key, f, o)
    return (best[1], best[2]) if best else (None, None)


def link_json(food, order):
    return {'name': order.get('name') or food.name, 'url': order.get('url') or '', 'store': order.get('store') or '',
            'image': order.get('image') or (food.product_info or {}).get('image') or ''}


@api_view(['GET'])
@permission_classes(PERMS)
def restock(request):
    space = request.space
    today = timezone.localdate()
    bought = [f for f in Food.objects.filter(space=space, product_info__has_key='orders').select_related('supermarket_category')]
    groups = {}
    for f in bought:
        groups.setdefault(_top(f.path), []).append(f)
    stocked = {_top(p) for p in InventoryEntry.objects.filter(space=space, amount__gt=0).values_list('food__path', flat=True) if p}
    listed = {_top(p) for p in ShoppingListEntry.objects.filter(space=space, checked=False).values_list('food__path', flat=True) if p}
    tops = {f.path: f for f in Food.objects.filter(space=space, path__in=groups.keys()).select_related('supermarket_category')}
    away = away_soon(space)

    items = []
    for path, foods in groups.items():
        top = tops.get(path)
        if top is None or path in stocked or path in listed:
            continue
        days = sorted({datetime.date.fromisoformat(d) for f in foods for o in _orders(f) for d in (o.get('dates') or [o.get('last')]) if d})
        if len(days) < 3 or (today - days[-1]).days > 400:
            continue
        every = statistics.median((b - a).days for a, b in zip(days, days[1:]))
        since = (today - days[-1]).days
        if every <= 0 or since < every * .85:
            continue
        keeps = home_aisles.storage(top)[1]
        fresh = keeps is not None and keeps <= FRESH_DAYS
        product, order = best_order(foods)
        items.append({
            'food': {'id': top.id, 'name': top.name, 'image': (top.product_info or {}).get('image') or (product.product_info or {}).get('image') or '',
                     'aisle': top.supermarket_category.name if top.supermarket_category_id else None},
            'product': link_json(product, order),
            'every_days': round(every), 'since_days': since, 'last_bought': days[-1].isoformat(),
            'times': len(days), 'recent': sum(1 for d in days if (today - d).days <= 365),
            'fresh': fresh, 'hold': bool(away and fresh),
        })
    # most overdue first, among things still bought this year
    items.sort(key=lambda i: (i['hold'], -min(i['since_days'] / i['every_days'], 4) * (1 + min(i['recent'], 10) / 10)))
    return Response({'away': away, 'items': [i for i in items if i['recent']][:24]})


@api_view(['GET'])
@permission_classes(PERMS)
def store_links(request):
    space = request.space
    on_list = {e.food_id: e.food for e in ShoppingListEntry.objects.filter(space=space, checked=False).select_related('food')}
    paths = {_top(f.path) for f in on_list.values()}
    q = Q()
    for p in paths:
        q |= Q(path__startswith=p)
    trees = {}
    if paths:
        for f in Food.objects.filter(q, space=space, product_info__has_key='orders'):
            trees.setdefault(_top(f.path), []).append(f)
    out = {}
    for fid, f in on_list.items():
        # the food itself, else its products, else the general food's group
        own = [x for x in trees.get(_top(f.path), []) if x.path.startswith(f.path)]
        product, order = best_order(own or trees.get(_top(f.path), []))
        if order and order.get('url'):
            out[fid] = link_json(product, order)
    return Response({'links': out})


def tidy(x):
    """round up to an amount you'd plausibly have: 7 -> 7, 23 -> 30, 375 -> 400, 1850 -> 1900"""
    if x <= 10:
        return math.ceil(x)
    step = 10 if x < 100 else 50 if x < 1000 else 100
    return math.ceil(x / step) * step


def have_amount(space, food):
    """(unit, amount): twice the most any recipe asks for, in the unit recipes use most sensibly; else 1 package"""
    need = {}
    for i in Ingredient.objects.filter(space=space, food=food, step__recipe__isnull=False, unit__isnull=False, amount__gt=0).select_related('unit'):
        u = need.setdefault(i.unit_id, [i.unit, 0, 0])
        u[1] = max(u[1], float(i.amount))
        u[2] += 1
    if need:
        pick = (need.get(food.preferred_unit_id)
                or next((v for v in need.values() if v[0].name.lower() in ('g', 'ml', 'kg', 'l', 'pcs')), None)
                or max(need.values(), key=lambda v: v[2]))
        return pick[0], tidy(pick[1] * 2)
    unit = food.preferred_unit or Unit.objects.filter(space=space, name__iexact='package').first()
    return unit, 1


@api_view(['POST'])
@permission_classes(PERMS)
def have(request):
    space = request.space
    try:
        food = get_obj(Food, space, request.data.get('food_id'), 'Food')
    except ValueError as e:
        return Response({'error': str(e)}, status=404)
    if food is None:
        return Response({'error': 'Food not found'}, status=404)
    unit, amount = have_amount(space, food)
    place = home_aisles.storage(food)[0]
    location = InventoryLocation.objects.filter(space=space, name__iexact=place).first() or InventoryLocation.objects.filter(space=space).order_by('id').first()
    try:
        with transaction.atomic():
            body, status = home_pantry._adjust(request, {
                'action': 'add', 'food_id': food.id, 'unit_id': unit.id if unit else None, 'amount': str(amount),
                'location_id': location.id if location else None, 'note': 'On hand (I have it)'})
            if status < 400:
                listed = ShoppingListEntry.objects.filter(space=space, food=food, checked=False)
                removed = listed.count()
                listed.delete()
    except ValueError as e:
        return Response({'error': str(e)}, status=400)
    if status >= 400:
        return Response(body, status=status)
    return Response({**body, 'amount': num(amount), 'unit': unit.name if unit else None, 'location': location.name if location else None,
                     'removed': removed, 'message': f"{body.get('message') or 'Added'}. It’s off the shopping list."})
