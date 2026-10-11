"""home fork: fill in nutrition for foods that have none, from the USDA SR Legacy table bundled in
cookbook/data (public domain). Recipe imports create a new food for every ingredient name Kitchen
hasn't seen ("Dark brown sugar", "Egg(s)"), and those foods start with no properties, so the recipe's
calories come out incomplete. fill_food() gives such a food its properties (per 100 g) and the USDA
portion weights as unit conversions (1 cup = 220 g, 1 pcs = 50 g), so cups and counts work too.

Matching order: a curated name (ALIASES), then another food in the same space with the same name
that already has properties, then a word match against the USDA descriptions. A food is only filled
when the match is clear; otherwise it is left for a person (the property editor still shows it).
"""
import gzip
import logging
import json
import os
import re
from decimal import Decimal
from functools import lru_cache

log = logging.getLogger(__name__)

DATA = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'home_usda_sr_legacy.json.gz')

# words that describe the form or quality, not the food: dropped before matching
DESCRIPTORS = {
    'fresh', 'large', 'small', 'medium', 'whole', 'chopped', 'minced', 'sliced', 'diced', 'grated', 'crushed',
    'ground', 'dried', 'dry', 'toasted', 'plain', 'extra', 'virgin', 'extravirgin', 'good', 'quality', 'best',
    'organic', 'homemade', 'store', 'bought', 'storebought', 'finely', 'coarsely', 'roughly', 'thinly', 'packed',
    'softened', 'melted', 'cold', 'warm', 'room', 'temperature', 'optional', 'about', 'of', 'and', 'or', 'the', 'a',
    'for', 'to', 'taste', 'serving', 'garnish', 'pure', 'natural', 'premium', 'high', 'fine', 'coarse', 'kosher',
    'shredded', 'fillet', 'sprig', 'stalk', 'piece', 'chunk', 'cube', 'boneless', 'skinless', 'baby', 'leaves',
}
# USDA words that mean a prepared or unusual version: a match containing them ranks lower
# unless the ingredient name asks for them
PENALTY = {
    'cooked', 'boiled', 'fried', 'baked', 'roasted', 'braised', 'stewed', 'broiled', 'grilled', 'microwaved',
    'canned', 'frozen', 'prepared', 'imitation', 'reduced', 'low', 'lowfat', 'nonfat', 'fat-free', 'light', 'lite',
    'dehydrated', 'sweetened', 'unsweetened', 'enriched', 'unenriched', 'fortified', 'babyfood', 'infant', 'formula',
    'restaurant', 'fast', 'school', 'lunch', 'mix', 'industrial', 'commercial', 'substitute', 'drained', 'solids',
    'liquids', 'heated', 'free', 'topping', 'spread', 'flavored', 'diet', 'refrigerated', 'pickled', 'salted', 'smoked', 'cured', 'glazed', 'stuffed', 'breaded',
}
SKIP_CATEGORIES = {'Baby Foods', 'Fast Foods', 'Restaurant Foods', 'Meals, Entrees, and Side Dishes', 'American Indian/Alaska Native Foods'}

# Everyday cooking names that the word match gets wrong or can't find: normalized name -> the exact
# USDA description. Some are stand-ins with near-identical nutrition (potato starch -> potato flour,
# glucose syrup -> light corn syrup, Shaoxing wine -> sake); MSG counts as nothing.
ALIASES = {
    'butter': 'Butter, without salt', 'unsalted butter': 'Butter, without salt', 'salted butter': 'Butter, salted',
    'egg': 'Egg, whole, raw, fresh', 'large egg': 'Egg, whole, raw, fresh',
    'egg white': 'Egg, white, raw, fresh', 'egg yolk': 'Egg, yolk, raw, fresh',
    'sugar': 'Sugars, granulated', 'granulated sugar': 'Sugars, granulated', 'white sugar': 'Sugars, granulated',
    'caster sugar': 'Sugars, granulated', 'superfine sugar': 'Sugars, granulated',
    'dextrose': 'Sugars, granulated', 'glucose': 'Sugars, granulated', 'dry glucose': 'Sugars, granulated',
    'brown sugar': 'Sugars, brown', 'dark brown sugar': 'Sugars, brown', 'light brown sugar': 'Sugars, brown',
    'powdered sugar': 'Sugars, powdered', 'icing sugar': 'Sugars, powdered', 'confectioner sugar': 'Sugars, powdered',
    'glucose syrup': 'Syrups, corn, light', 'corn syrup': 'Syrups, corn, light', 'light corn syrup': 'Syrups, corn, light',
    'honey': 'Honey', 'acacia honey': 'Honey', 'maple syrup': 'Syrups, maple',
    'salt': 'Salt, table', 'kosher salt': 'Salt, table', 'sea salt': 'Salt, table', 'flake sea salt': 'Salt, table',
    'table salt': 'Salt, table', 'msg': 'Salt, table', 'monosodium glutamate': 'Salt, table',
    'black pepper': 'Spices, pepper, black', 'pepper': 'Spices, pepper, black', 'white pepper': 'Spices, pepper, white',
    'flour': 'Wheat flour, white, all-purpose, enriched, bleached',
    'all purpose flour': 'Wheat flour, white, all-purpose, enriched, bleached',
    'allpurpose flour': 'Wheat flour, white, all-purpose, enriched, bleached',
    'bread flour': 'Wheat flour, white, bread, enriched', 'cake flour': 'Wheat flour, white, cake, enriched',
    'pastry flour': 'Wheat flour, white, cake, enriched', 'whole wheat flour': "Wheat flour, whole-grain (Includes foods for USDA's Food Distribution Program)",
    'diastatic malt powder': 'Barley malt flour', 'malt powder': 'Barley malt flour',
    'potato starch': 'Potato flour', 'cornstarch': 'Cornstarch', 'corn starch': 'Cornstarch',
    'milk': 'Milk, whole, 3.25% milkfat, with added vitamin D', 'whole milk': 'Milk, whole, 3.25% milkfat, with added vitamin D',
    'heavy cream': 'Cream, fluid, heavy whipping', 'whipping cream': 'Cream, fluid, heavy whipping',
    'double cream': 'Cream, fluid, heavy whipping',
    'nonfat dry milk powder': 'Milk, dry, nonfat, regular, with added vitamin A and vitamin D',
    'milk powder': 'Milk, dry, nonfat, regular, with added vitamin A and vitamin D',
    'buttermilk': 'Milk, buttermilk, fluid, whole',
    'yogurt': 'Yogurt, plain, whole milk', 'plain whole milk yogurt': 'Yogurt, plain, whole milk',
    'whole milk yogurt': 'Yogurt, plain, whole milk', 'cottage cheese': 'Cheese, cottage, creamed, large or small curd',
    'olive oil': 'Oil, olive, salad or cooking', 'oil': 'Oil, canola', 'neutral oil': 'Oil, canola',
    'vegetable oil': 'Oil, canola', 'canola oil': 'Oil, canola', 'pistachio oil': 'Oil, walnut',
    'sesame oil': 'Oil, sesame, salad or cooking', 'toasted sesame oil': 'Oil, sesame, salad or cooking',
    'water': 'Beverages, water, tap, drinking', 'ice': 'Beverages, water, tap, drinking',
    'garlic': 'Garlic, raw', 'garlic clove': 'Garlic, raw', 'ginger': 'Ginger root, raw',
    'onion': 'Onions, raw', 'red onion': 'Onions, raw', 'yellow onion': 'Onions, raw', 'shallot': 'Shallots, raw',
    'scallion': 'Onions, spring or scallions (includes tops and bulb), raw',
    'green onion': 'Onions, spring or scallions (includes tops and bulb), raw',
    'lemon juice': 'Lemon juice, raw', 'lime juice': 'Lime juice, raw',
    'orange zest': 'Orange peel, raw', 'orange peel': 'Orange peel, raw', 'lemon zest': 'Lemon peel, raw',
    'soy sauce': 'Soy sauce made from soy and wheat (shoyu)', 'light soy sauce': 'Soy sauce made from soy and wheat (shoyu)',
    'dark soy sauce': 'Soy sauce made from soy and wheat (shoyu)',
    'vinegar': 'Vinegar, distilled', 'distilled vinegar': 'Vinegar, distilled', 'white vinegar': 'Vinegar, distilled',
    'rice vinegar': 'Vinegar, distilled', 'cider vinegar': 'Vinegar, cider', 'apple cider vinegar': 'Vinegar, cider',
    'mirin': 'Alcoholic beverage, rice (sake)', 'sake': 'Alcoholic beverage, rice (sake)',
    'shaoxing wine': 'Alcoholic beverage, rice (sake)', 'rice wine': 'Alcoholic beverage, rice (sake)',
    'whiskey': 'Alcoholic beverage, distilled, whiskey, 86 proof', 'whisky': 'Alcoholic beverage, distilled, whiskey, 86 proof',
    'bourbon': 'Alcoholic beverage, distilled, whiskey, 86 proof',
    'rum': 'Alcoholic beverage, distilled, rum, 80 proof', 'vodka': 'Alcoholic beverage, distilled, vodka, 80 proof',
    'gin': 'Alcoholic beverage, distilled, all (gin, rum, vodka, whiskey) 80 proof',
    'vanilla extract': 'Vanilla extract', 'vanilla': 'Vanilla extract',
    'baking soda': 'Leavening agents, baking soda',
    'baking powder': 'Leavening agents, baking powder, double-acting, straight phosphate',
    'active dry yeast': "Leavening agents, yeast, baker's, active dry", 'instant dry yeast': "Leavening agents, yeast, baker's, active dry",
    'yeast': "Leavening agents, yeast, baker's, active dry",
    'jasmine rice': 'Rice, white, long-grain, regular, raw, enriched', 'white rice': 'Rice, white, long-grain, regular, raw, enriched',
    'rice': 'Rice, white, long-grain, regular, raw, enriched', 'basmati rice': 'Rice, white, long-grain, regular, raw, enriched',
    'medjool date': 'Dates, medjool', 'date': 'Dates, medjool',
    'basil': 'Basil, fresh', 'cilantro': 'Coriander (cilantro) leaves, raw', 'parsley': 'Parsley, fresh',
    'bay leaf': 'Spices, bay leaf', 'bay leave': 'Spices, bay leaf',
    'cardamom': 'Spices, cardamom', 'green cardamom pod': 'Spices, cardamom', 'cardamom pod': 'Spices, cardamom',
    'clove': 'Spices, cloves, ground', 'coriander': 'Spices, coriander seed', 'coriander seed': 'Spices, coriander seed',
    'cumin': 'Spices, cumin seed', 'cumin seed': 'Spices, cumin seed', 'turmeric': 'Spices, turmeric, ground',
    'cinnamon': 'Spices, cinnamon, ground', 'nutmeg': 'Spices, nutmeg, ground', 'paprika': 'Spices, paprika',
    'chili powder': 'Spices, chili powder', 'kashmiri chili powder': 'Spices, pepper, red or cayenne',
    'cayenne': 'Spices, pepper, red or cayenne', 'facing heaven chile': 'Spices, pepper, red or cayenne',
    'dried chile': 'Spices, pepper, red or cayenne', 'fenugreek leave': 'Spices, fenugreek seed',
    'fenugreek leave kasoori methi': 'Spices, fenugreek seed', 'kasoori methi': 'Spices, fenugreek seed',
    'miso': 'Miso', 'white miso paste': 'Miso', 'miso paste': 'Miso', 'white miso': 'Miso',
    'tomato paste': "Tomato products, canned, paste, without salt added (Includes foods for USDA's Food Distribution Program)",
    'fire roasted canned tomato': 'Tomatoes, red, ripe, canned, packed in tomato juice',
    'canned tomato': 'Tomatoes, red, ripe, canned, packed in tomato juice',
    'pistachio paste': 'Nuts, pistachio nuts, raw', 'sicilian pistachio paste': 'Nuts, pistachio nuts, raw',
    'chicken bouillon powder': 'Soup, chicken broth or bouillon, dry', 'totole chicken bouillon powder': 'Soup, chicken broth or bouillon, dry',
    'ice cream stabilizer': 'Gums, seed gums (includes locust bean, guar)', 'xanthan gum': 'Gums, seed gums (includes locust bean, guar)',
    'rolled oat': 'Cereals, oats, regular and quick, not fortified, dry', 'oat': 'Cereals, oats, regular and quick, not fortified, dry',
    'old fashioned oat': 'Cereals, oats, regular and quick, not fortified, dry', 'quick oat': 'Cereals, oats, regular and quick, not fortified, dry',
    'dark chocolate': 'Chocolate, dark, 60-69% cacao solids', 'bittersweet chocolate': 'Chocolate, dark, 60-69% cacao solids',
    'semisweet chocolate': 'Candies, semisweet chocolate', 'chocolate chip': 'Candies, semisweet chocolate',
    'semisweet chocolate chip': 'Candies, semisweet chocolate', 'unsweetened chocolate': 'Baking chocolate, unsweetened, squares',
    'cocoa powder': 'Cocoa, dry powder, unsweetened', 'unsweetened cocoa powder': 'Cocoa, dry powder, unsweetened',
    'dutch process cocoa powder': 'Cocoa, dry powder, unsweetened, processed with alkali',
    'almond': 'Nuts, almonds', 'walnut': 'Nuts, walnuts, english', 'pistachio': 'Nuts, pistachio nuts, raw',
    'parmesan': 'Cheese, parmesan, hard', 'parmigiano reggiano': 'Cheese, parmesan, hard', 'mozzarella': 'Cheese, mozzarella, whole milk',
    'cream cheese': 'Cheese, cream', 'sour cream': 'Cream, sour, cultured',
    'lemon': 'Lemons, raw, without peel', 'lime': 'Limes, raw', 'tomato': 'Tomatoes, red, ripe, raw, year round average',
    'potato': 'Potatoes, flesh and skin, raw', 'carrot': 'Carrots, raw', 'celery': 'Celery, raw',
    'chicken breast': 'Chicken, broiler or fryers, breast, skinless, boneless, meat only, raw',
    'pasta': 'Pasta, dry, enriched', 'spaghetti': 'Pasta, dry, enriched',
    'yellow mustard': 'Mustard, prepared, yellow', 'mustard': 'Mustard, prepared, yellow', 'dijon mustard': 'Mustard, prepared, yellow',
    'ketchup': 'Catsup', 'worcestershire sauce': 'Sauce, worcestershire', 'fish sauce': 'Sauce, fish, ready-to-serve',
    'garlic powder': 'Spices, garlic powder', 'onion powder': 'Spices, onion powder', 'oregano': 'Spices, oregano, dried',
    'dried oregano': 'Spices, oregano, dried', 'dried thyme': 'Spices, thyme, dried', 'thyme': 'Thyme, fresh', 'rosemary': 'Rosemary, fresh',
    'smoked paprika': 'Spices, paprika', 'sweet paprika': 'Spices, paprika',
    'coconut milk': 'Nuts, coconut milk, canned (liquid expressed from grated meat and water)',
    'bacon': 'Pork, cured, bacon, unprepared', 'molasses': 'Molasses', 'coconut oil': 'Oil, coconut',
    'shortening': 'Shortening, vegetable, household, composite', 'balsamic vinegar': 'Vinegar, balsamic',
    'ghee': 'Butter oil, anhydrous', 'clarified butter': 'Butter oil, anhydrous',
    'panko': 'Bread, crumbs, dry, grated, plain', 'panko breadcrumb': 'Bread, crumbs, dry, grated, plain',
    'breadcrumb': 'Bread, crumbs, dry, grated, plain', 'bread crumb': 'Bread, crumbs, dry, grated, plain',
    'tahini': 'Seeds, sesame butter, tahini, from roasted and toasted kernels (most common type)',
    'red wine': 'Alcoholic beverage, wine, table, red', 'dry red wine': 'Alcoholic beverage, wine, table, red',
    'white wine': 'Alcoholic beverage, wine, table, white', 'dry white wine': 'Alcoholic beverage, wine, table, white',
}

PIECE_WORDS = ('large', 'medium', 'whole', 'clove', 'each', 'pod', 'leaf', 'fruit', 'date', 'egg', 'steak', 'piece', 'item')


def singular(w):
    if len(w) > 4 and w.endswith('ies'):
        return w[:-3] + 'y'
    if len(w) > 4 and w.endswith('oes'):
        return w[:-2]
    if len(w) > 3 and w.endswith('es') and w[-3] in 'sxz':
        return w[:-2]
    if len(w) > 3 and w.endswith('s') and not w.endswith('ss'):
        return w[:-1]
    return w


def words(text):
    text = re.sub(r'\(s\)', '', text.lower())
    text = re.sub(r'\([^)]*\)', ' ', text)
    return [singular(w) for w in re.findall(r'[a-z]+', text)]


def norm(name):
    return ' '.join(words(name))


@lru_cache(maxsize=1)
def table():
    with gzip.open(DATA, 'rt', encoding='utf-8') as f:
        data = json.load(f)
    cats = {int(k): v for k, v in data['categories'].items()}
    foods = []
    for fdc, desc, cat, nutrients, portions in data['foods']:
        foods.append({'fdc_id': fdc, 'description': desc, 'category': cats.get(cat, ''), 'nutrients': nutrients,
                      'portions': portions, 'words': set(words(desc)), 'head': set(words(desc.split(',')[0]))})
    return foods, {f['fdc_id']: f for f in foods}


def search(name, limit=3):
    """best USDA entries for an ingredient name: list of (score, entry), highest first. When nothing
    has every word, the leading words are dropped one at a time ("smoked paprika" -> "paprika"), at a cost."""
    q = [w for w in words(name) if w not in DESCRIPTORS] or words(name)
    for dropped in range(len(q)):
        found = _search(q[dropped:], set(words(name)), limit)
        if found:
            return [(score - 3 * dropped, f) for score, f in found]
    return []


def _search(q, asked, limit):
    if not q:
        return []
    results = []
    for f in table()[0]:
        if f['category'] in SKIP_CATEGORIES or '1008' not in f['nutrients']:
            continue
        if not all(w in f['words'] for w in q):
            continue
        extra = len(f['words'] - set(q) - {'raw'})
        score = 10.0
        score += 3 * sum(1 for w in q if w in f['head'])          # the food itself, not "with x"
        score -= 0.6 * extra                                       # shorter, plainer descriptions first
        score -= 4 * len((f['words'] & PENALTY) - asked)           # prepared versions last
        score += 2 if 'raw' in f['words'] else 0
        if 'with' in f['words'] and 'with' not in asked:
            score -= 3
        results.append((round(score, 2), f))
    results.sort(key=lambda r: (-r[0], r[1]['fdc_id']))
    return results[:limit]


def match(name):
    """(entry, how) for a food name, or (None, reason)"""
    foods, by_id = table()
    n = norm(name)
    by_desc = {f['description']: f for f in foods}
    for key in (n, ' '.join(w for w in n.split() if w not in DESCRIPTORS)):
        if key in ALIASES and ALIASES[key] in by_desc:
            return by_desc[ALIASES[key]], 'alias'
    found = search(name)
    if not found:
        return None, 'no USDA match'
    best = found[0]
    if best[0] < 8:
        return None, f'weak match ({best[1]["description"]})'
    if len(found) > 1 and found[1][0] == best[0] and found[1][1]['head'] != best[1]['head']:
        return None, f'ambiguous ({best[1]["description"]} / {found[1][1]["description"]})'
    return best[1], 'search'


def piece_grams(entry):
    """weight of one piece (one large egg, one clove, one date) from the USDA portions"""
    best = None
    for amount, unit, modifier, grams in entry['portions']:
        text = f'{unit} {modifier}'.lower()
        if unit in ('cup', 'tablespoon', 'teaspoon', 'fl oz', 'oz', 'lb', 'g', 'ml', 'liter') or re.search(
                r'\b(cups?|tbsp|tablespoons?|tsp|teaspoons?|oz|ounces?|lbs?|pounds?|slices?|packages?|servings?|containers?|pats?)\b', text):
            continue
        if any(w in text for w in PIECE_WORDS) and amount:
            rank = 0 if 'large' in text else 1 if any(w in text for w in ('clove', 'whole', 'medium', 'each', 'date', 'pod')) else 2
            if best is None or rank < best[0]:
                best = (rank, grams / amount)
    return best[1] if best else None


def fill_food(food, dry_run=False):
    """Give a food without properties its USDA nutrition and portion conversions.
    Returns (entry or None, how) so callers can report what happened."""
    from cookbook.models import Food, Property, PropertyType, Unit, UnitConversion

    if food.properties.exists():
        return complete_food(food, dry_run)

    entry, how = match(food.name)
    twin = None
    if not entry:
        # no USDA match: another food in the space with the same name and properties (open-data foods)
        for other in Food.objects.filter(space=food.space, properties__isnull=False).exclude(id=food.id).distinct():
            if norm(other.name) == norm(food.name) and other.properties_food_unit:
                twin, how = other, 'twin'
                break
        if not twin:
            return None, how
    if dry_run:
        return entry or {'description': f'copy of {twin.name}', 'fdc_id': twin.fdc_id}, how

    space = food.space
    if twin:
        for p in twin.properties.all():
            food.properties.add(Property.objects.create(property_type=p.property_type, property_amount=p.property_amount, space=space))
        food.properties_food_amount, food.properties_food_unit = twin.properties_food_amount, twin.properties_food_unit
        food.fdc_id = food.fdc_id or twin.fdc_id
        food.save()
        return {'description': f'copy of {twin.name}', 'fdc_id': twin.fdc_id}, how

    g = unit_for(space, 'g')
    if g is None:
        return None, 'no gram unit in this space'
    added = 0
    for pt in PropertyType.objects.filter(space=space, fdc_id__isnull=False):
        value = entry['nutrients'].get(str(pt.fdc_id))
        if value is not None:
            food.properties.add(Property.objects.create(property_type=pt, property_amount=Decimal(str(value)), space=space))
            added += 1
    if not added:
        return None, 'no matching property types'
    food.properties_food_amount, food.properties_food_unit, food.fdc_id = 100, g, entry['fdc_id']
    food.save()
    add_conversions(food, entry)
    return entry, how


def complete_food(food, dry_run=False):
    """a food with some properties but not all (Tomato paste had no calories): add the missing ones,
    only when its values are per 100 g like the USDA table"""
    from cookbook.models import Property, PropertyType
    have = set(food.properties.values_list('property_type_id', flat=True))
    missing = PropertyType.objects.filter(space=food.space, fdc_id__isnull=False).exclude(id__in=have)
    if not missing.exists():
        return None, 'has properties already'
    unit = food.properties_food_unit
    if not unit or unit.base_unit != 'g' or food.properties_food_amount != 100:
        return None, 'has properties in another unit'
    entry, how = match(food.name)
    if not entry:
        return None, how
    values = [(pt, entry['nutrients'].get(str(pt.fdc_id))) for pt in missing]
    values = [(pt, v) for pt, v in values if v is not None]
    if not values:
        return None, 'USDA has none of the missing values'
    if not dry_run:
        for pt, v in values:
            food.properties.add(Property.objects.create(property_type=pt, property_amount=Decimal(str(v)), space=food.space))
    return entry, how + ', completed ' + ', '.join(pt.name for pt, v in values)


def volume_unit(unit, modifier):
    """'us_cup' / 'tbsp' / 'tsp' for a USDA portion; SR Legacy mostly puts it in the text ("cup packed")"""
    first = (unit or modifier or '').lower().split(' ')[0].strip(',')
    return {'cup': 'us_cup', 'cups': 'us_cup', 'tablespoon': 'tbsp', 'tbsp': 'tbsp', 'teaspoon': 'tsp', 'tsp': 'tsp'}.get(first)


def unit_for(space, base):
    from cookbook.models import Unit
    return (Unit.objects.filter(space=space, base_unit=base).order_by('id').first()
            or Unit.objects.filter(space=space, name__iexact=base).order_by('id').first())


def add_conversions(food, entry):
    """cup / tbsp / tsp / piece weights from the USDA portions, unless the food already has one"""
    from cookbook.models import Unit, UnitConversion
    space = food.space
    g = unit_for(space, 'g')
    have = set(UnitConversion.objects.filter(space=space, food=food).values_list('base_unit_id', flat=True))
    done = set()
    for amount, unit, modifier, grams in entry['portions']:
        base = volume_unit(unit, modifier)
        if not base or base in done or not amount or not grams:
            continue
        u = unit_for(space, base)
        if u and u.id not in have:
            UnitConversion.objects.create(space=space, food=food, base_amount=1, base_unit=u,
                                          converted_amount=round(Decimal(str(grams / amount)), 2), converted_unit=g, created_by=space.created_by)
            have.add(u.id)
        done.add(base)
    each = piece_grams(entry)
    pcs = piece_unit(space)
    if each and pcs and pcs.id not in have:
        UnitConversion.objects.create(space=space, food=food, base_amount=1, base_unit=pcs,
                                      converted_amount=round(Decimal(str(each)), 2), converted_unit=g, created_by=space.created_by)


def piece_unit(space):
    from cookbook.models import Unit
    return Unit.objects.filter(space=space, open_data_slug='unit-pcs').first() or Unit.objects.filter(space=space, name__iexact='pcs').first()


def fill_new_food(food):
    """called when an import or the API creates a food: never let a nutrition problem stop the save"""
    try:
        entry, how = fill_food(food)
        if entry:
            log.info('nutrition for %s from %s (%s)', food.name, entry.get('description'), how)
    except Exception:
        log.exception('could not fill nutrition for %s', food.name)


# unit names an importer may use for a unit the space already has (name -> Unit.base_unit)
UNIT_SYNONYMS = {
    'g': 'g', 'gr': 'g', 'grs': 'g', 'gram': 'g', 'grams': 'g', 'gramme': 'g', 'grammes': 'g',
    'kg': 'kg', 'kgs': 'kg', 'kilo': 'kg', 'kilos': 'kg', 'kilogram': 'kg', 'kilograms': 'kg',
    'ml': 'ml', 'mls': 'ml', 'milliliter': 'ml', 'milliliters': 'ml', 'millilitre': 'ml', 'millilitres': 'ml',
    'l': 'l', 'liter': 'l', 'liters': 'l', 'litre': 'l', 'litres': 'l',
    'oz': 'ounce', 'ounce': 'ounce', 'ounces': 'ounce', 'lb': 'pound', 'lbs': 'pound', 'pound': 'pound', 'pounds': 'pound',
    'tbsp': 'tbsp', 'tbsps': 'tbsp', 'tbs': 'tbsp', 'tablespoon': 'tbsp', 'tablespoons': 'tbsp',
    'tsp': 'tsp', 'tsps': 'tsp', 'teaspoon': 'tsp', 'teaspoons': 'tsp',
    'cup': 'us_cup', 'cups': 'us_cup', 'fl oz': 'fluid_ounce', 'fluid ounce': 'fluid_ounce', 'fluid ounces': 'fluid_ounce',
}


def known_unit(space, name):
    """the space's existing unit for a synonym such as "grams" (one with that base unit), else None"""
    from cookbook.models import Unit
    base = UNIT_SYNONYMS.get((name or '').strip().lower().rstrip('.'))
    if not base:
        return None
    return Unit.objects.filter(space=space, base_unit=base).order_by('id').first()
