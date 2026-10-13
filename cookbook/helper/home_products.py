"""
home fork: products grouped under a general food.

A scanned product ("Eggs Omega 3", barcode 065651000533, 1 package) can sit under a general food
("Egg(s)") in Tandoor's food tree. The product keeps its barcode, picture and its own stock; the
general food is what recipes ask for. Then:

  - the pantry shows one line for the general food, its products' stock added up in the general
    food's unit (1 package = 12 pcs, from a unit conversion on the product)   -> group()
  - a product in stock counts as its general food for Ready to Cook and shopping -> with_general()

Grouping is done from the pantry's product details (cookbook/views/home_pantry.py group_product).
"""
from decimal import Decimal

from cookbook.models import Food, UnitConversion


def _ancestor_paths(path):
    return [path[:Food.steplen * d] for d in range(1, len(path) // Food.steplen)]


def general_foods(space, food_ids):
    """{food id: [ids of the general foods it sits under, top first]} for foods that sit under one"""
    rows = list(Food.objects.filter(space=space, id__in=food_ids, depth__gt=1).values_list('id', 'path'))
    wanted = {p for _, path in rows for p in _ancestor_paths(path)}
    by_path = dict(Food.objects.filter(space=space, path__in=wanted).values_list('path', 'id'))
    return {fid: [by_path[p] for p in _ancestor_paths(path) if p in by_path] for fid, path in rows}


def with_general(space, food_ids):
    """the food ids plus every general food they sit under"""
    ids = set(food_ids)
    for ups in general_foods(space, ids).values():
        ids.update(ups)
    return ids


def convert(amount, unit, target, foods):
    """amount in unit -> amount in target using the foods' own conversions (then space-wide ones); None if unknown"""
    if unit is None or target is None:
        return amount if unit == target else None
    if unit.id == target.id:
        return amount
    for food in [*foods, None]:
        for c in UnitConversion.objects.filter(space=target.space, food=food, base_unit=unit, converted_unit=target):
            if c.base_amount:
                return amount * c.converted_amount / c.base_amount
        for c in UnitConversion.objects.filter(space=target.space, food=food, base_unit=target, converted_unit=unit):
            if c.converted_amount:
                return amount * c.base_amount / c.converted_amount
    return None


def general_unit(general):
    """the unit a general food is counted in: its preferred unit, else the unit of its own stock"""
    if general.preferred_unit_id:
        return general.preferred_unit
    own = general.inventoryentry_set.filter(amount__gt=0, unit__isnull=False).select_related('unit').first()
    return own.unit if own else None


def group(entry, cache):
    """
    for a stock entry of a product that sits under a general food:
    {'food': {id, name, product_image}, 'amount', 'unit'} (amount/unit None when there's no conversion);
    None for everything else. cache is a dict shared across one response.
    """
    food = entry.food
    if food is None or food.depth <= 1:
        return None
    key = food.path[:Food.steplen]
    if key not in cache:
        top = Food.objects.filter(space=food.space, path=key).select_related('preferred_unit').first()
        cache[key] = (top, general_unit(top) if top else None)
    top, unit = cache[key]
    if top is None:
        return None
    amount = convert(Decimal(entry.amount), entry.unit, unit, [food, top])
    info = top.product_info or {}
    return {
        'food': {'id': top.id, 'name': top.name, 'product_image': info.get('image') or (food.product_info or {}).get('image') or ''},
        'amount': f'{round(amount, 4).normalize():f}' if amount is not None else None,
        'unit': {'id': unit.id, 'name': unit.name, 'plural_name': unit.plural_name or unit.name} if amount is not None and unit else None,
    }
