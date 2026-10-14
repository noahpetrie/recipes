"""
home fork: "Ready to Cook" — every recipe scored against what's in the kitchen.

An ingredient counts as in the kitchen when
  - the pantry has stock of that food (an InventoryEntry with an amount), or
  - it's a staple: marked on hand for the household (Tandoor's Food.onhand_users, the same flag
    the shopping list uses), or
  - one of its substitutes (Food.substitute / substitute_siblings / substitute_children) is.
Ingredients with no amount ("as needed", "for serving"), optional ones, headers and foods set to
ignore shopping (water) don't count either way.

  GET  /api/home/cookable/            recipes with have/total, what's missing and what it uses up
  GET  /api/home/staples/             every food the recipes use, flagged on hand / in stock / suggested
  POST /api/home/staples/             {food: id | foods: [ids], on_hand: bool} mark staples for the household
"""
import datetime
import re
from collections import defaultdict

from django.db.models import Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from cookbook.helper import home_equipment, home_nutrition, home_products
from cookbook.helper.permission_helper import CustomIsUser, CustomTokenHasReadWriteScope, get_household_user_ids
from cookbook.models import Food, Ingredient, InventoryEntry, Recipe, RecipeEquipment

PERMS = [CustomIsUser & CustomTokenHasReadWriteScope]
SOON_DAYS = 7  # same window as the home page's "Use it up"

# foods most kitchens always have; offered as staples, never set without asking
STAPLE_CATEGORIES = {'Spices and Herbs', 'Fats and Oils'}
PERISHABLE = {'butter', 'milk', 'cream', 'egg', 'cheese', 'yogurt', 'meat', 'chicken', 'bell', 'fresh'}
STAPLE_WORDS = {'salt', 'pepper', 'oil', 'sugar', 'flour', 'baking soda', 'baking powder', 'vanilla extract',
                'soy sauce', 'vinegar', 'cream of tartar', 'honey', 'msg', 'cornstarch'}


def counted(ingredient):
    """does this line decide whether you can make the recipe?"""
    if ingredient.is_header or ingredient.food is None or ingredient.food.ignore_shopping or ingredient.food.name.lower() == 'water':
        return False
    if ingredient.no_amount or not ingredient.amount:
        return False
    return 'optional' not in (ingredient.note or '').lower()


def substitutes_of(food):
    q = Q(id__in=food.substitute.all())
    if food.substitute_siblings and food.depth > 1:
        q |= Q(path__startswith=food.path[:Food.steplen * (food.depth - 1)], depth=food.depth)
    if food.substitute_children:
        q |= Q(path__startswith=food.path, depth__gt=food.depth)
    return Food.objects.filter(q).exclude(id=food.id)


def kitchen(request):
    """(in stock {food id: soonest expiry still to come or None}, staple food ids); general foods count when a product under them is in stock"""
    stock = {}
    today = datetime.date.today()
    for e in InventoryEntry.objects.filter(space=request.space, food__isnull=False, amount__gt=0):
        # already past its date: still on the shelf, but not something to "use up" (the pantry flags it as expired)
        expires = e.expires if e.expires and e.expires >= today else None
        prev = stock.get(e.food_id, 'none')
        if prev == 'none' or (expires and (prev is None or expires < prev)):
            stock[e.food_id] = expires if prev == 'none' or expires else prev
    # a product in stock counts as the general food it sits under (Eggs Omega 3 -> Egg(s))
    for fid, ups in home_products.general_foods(request.space, list(stock)).items():
        for up in ups:
            prev, mine = stock.get(up, 'none'), stock[fid]
            stock[up] = mine if prev == 'none' or (mine and (prev is None or mine < prev)) else prev
    users = get_household_user_ids(request.user_space)
    staples = set(Food.objects.filter(space=request.space, onhand_users__id__in=users).values_list('id', flat=True))
    return stock, staples


def image_url(recipe):
    try:
        return recipe.image.url if recipe.image else None
    except ValueError:
        return None


@api_view(['GET'])
@permission_classes(PERMS)
def cookable(request):
    stock, staples = kitchen(request)
    have_ids = set(stock) | staples
    today = datetime.date.today()
    soon = today + datetime.timedelta(days=SOON_DAYS)

    lines = defaultdict(list)
    for i in (Ingredient.objects.filter(space=request.space, step__recipe__isnull=False)
              .select_related('food').prefetch_related('step_set__recipe_set')):
        if not counted(i):
            continue
        for step in i.step_set.all():
            for r in step.recipe_set.all():
                lines[r.id].append(i.food)

    sub_cache = {}

    def have(food):
        if food.id in have_ids:
            return True
        if food.id not in sub_cache:
            sub_cache[food.id] = any(s.id in have_ids for s in substitutes_of(food))
        return sub_cache[food.id]

    # equipment the recipe needs (not optional) that the kitchen doesn't have
    home_equipment.ensure_all(request.space)
    gear = home_equipment.Kitchen(request.space)
    no_gear = defaultdict(list)
    for l in RecipeEquipment.objects.filter(space=request.space, optional=False, recipe_id__in=lines.keys()).select_related('equipment'):
        eq = gear.all.get(l.equipment_id)
        if eq and not eq.hidden and gear.have(eq) is None:
            no_gear[l.recipe_id].append({'id': eq.id, 'name': eq.name})

    out = []
    for r in Recipe.objects.filter(space=request.space, id__in=lines.keys()).filter(Q(private=False) | Q(created_by=request.user) | Q(shared=request.user)).distinct():
        foods = {f.id: f for f in lines[r.id]}.values()
        missing = [{'id': f.id, 'name': f.name} for f in foods if not have(f)]
        expiring = sorted(({'id': f.id, 'name': f.name, 'expires': stock[f.id].isoformat()}
                           for f in foods if f.id in stock and stock[f.id] and stock[f.id] <= soon), key=lambda x: x['expires'])
        total = len(foods)
        out.append({'id': r.id, 'name': r.name, 'image': image_url(r), 'total': total, 'have': total - len(missing),
                    'missing': sorted(missing, key=lambda x: x['name'].lower()), 'expiring': expiring,
                    'equipment_missing': no_gear.get(r.id, []),
                    'working_time': r.working_time, 'waiting_time': r.waiting_time})

    # recipes that use something about to expire first, then the fewest things to buy
    out.sort(key=lambda x: (0 if x['expiring'] else 1, x['expiring'][0]['expires'] if x['expiring'] else '',
                            len(x['missing']) + len(x['equipment_missing']), -x['have'] / max(x['total'], 1), x['name'].lower()))
    return Response({'recipes': out, 'staples': len(staples), 'in_stock': len(stock), 'soon_days': SOON_DAYS})


def suggested(food):
    ws = home_nutrition.words(food.name)
    name = ' '.join(ws)
    # whole words: "unsalted butter" isn't salt; but "cream of tartar" is a staple and "cream" isn't
    found = [w for w in STAPLE_WORDS if re.search(rf'\b{re.escape(w)}\b', name)]
    if any(' ' in w for w in found):
        return True
    if set(ws) & PERISHABLE:
        return False
    if found:
        return True
    if food.fdc_id:
        entry = home_nutrition.table()[1].get(food.fdc_id)
        return bool(entry and entry['category'] in STAPLE_CATEGORIES)
    return False


@api_view(['GET', 'POST'])
@permission_classes(PERMS)
def staples(request):
    users = get_household_user_ids(request.user_space)
    if request.method == 'POST':
        # {food: id} or {foods: [ids]}, plus on_hand
        try:
            ids = [int(x) for x in (request.data.get('foods') or [request.data.get('food')])]
        except (TypeError, ValueError):
            return Response({'error': 'No such food.'}, status=404)
        foods = list(Food.objects.filter(space=request.space, id__in=ids))
        if not foods:
            return Response({'error': 'No such food.'}, status=404)
        for food in foods:
            if request.data.get('on_hand'):
                food.onhand_users.add(*users)
            else:
                food.onhand_users.remove(*users)
        return Response({'id': foods[0].id, 'ids': [f.id for f in foods], 'on_hand': bool(request.data.get('on_hand'))})

    stock, on_hand = kitchen(request)
    used = defaultdict(int)
    for i in Ingredient.objects.filter(space=request.space, step__recipe__isnull=False).select_related('food'):
        if counted(i):
            used[i.food_id] += 1
    foods = Food.objects.filter(space=request.space, id__in=used.keys()).order_by('name')
    return Response({'foods': [{'id': f.id, 'name': f.name, 'recipes': used[f.id], 'on_hand': f.id in on_hand,
                                'in_stock': f.id in stock, 'suggested': suggested(f)} for f in foods]})


@api_view(['GET'])
@permission_classes(PERMS)
def kitchen_state(request):
    """
    food ids in the pantry and the household's staples, so shopping dialogs can leave them unticked;
    a food counts as in stock when one of its substitutes is (cardamom seeds cover pods);
    stocked = only what the pantry itself holds (the search menu opens those in the pantry)
    """
    stock, staples = kitchen(request)
    have = set(stock) | staples
    covered = set(Food.objects.filter(space=request.space, substitute__in=have).values_list('id', flat=True)) - have
    return Response({'in_stock': sorted(set(stock) | covered), 'staples': sorted(staples), 'stocked': sorted(stock)})


@api_view(['POST'])
@permission_classes(PERMS)
def shop_plan(request):
    """
    {from, to} (dates, inclusive): every planned recipe in that range that isn't on the shopping
    list yet goes on it, leaving out staples and what the pantry has (shopping_helper)
    """
    from cookbook.helper.shopping_helper import RecipeShoppingEditor
    from cookbook.models import MealPlan, ShoppingListEntry
    try:
        start = datetime.date.fromisoformat(str(request.data.get('from'))[:10])
        end = datetime.date.fromisoformat(str(request.data.get('to'))[:10])
    except ValueError:
        return Response({'error': 'Choose the days to shop for.'}, status=400)
    users = get_household_user_ids(request.user_space)
    plans = (MealPlan.objects.filter(space=request.space, recipe__isnull=False, from_date__date__lte=end, to_date__date__gte=start)
             .filter(Q(created_by__in=users) | Q(shared=request.user)).distinct().select_related('recipe').order_by('from_date'))
    stock, staples = kitchen(request)
    added, already = [], []
    for plan in plans:
        if plan.shoppinglistrecipe_set.exists():
            already.append(plan.recipe.name)
            continue
        RecipeShoppingEditor(request, space=request.space).create(mealplan=plan, servings=plan.servings)
        added.append(plan.recipe.name)
    skipped = sorted({i.food.name for p in plans for i in Ingredient.objects.filter(step__recipe=p.recipe, food__isnull=False).select_related('food')
                      if i.food_id in stock or i.food_id in staples})
    items = ShoppingListEntry.objects.filter(space=request.space, checked=False, list_recipe__mealplan__in=plans).count()
    return Response({'added': added, 'already': already, 'items': items, 'skipped': skipped})
