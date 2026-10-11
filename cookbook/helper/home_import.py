"""
home fork: tidying recipes imported from websites (recipe_url_import.get_from_scraper, used by the
import page and the "Add to Kitchen" extension).

Upstream puts every ingredient in the first step and parses "3 to 4 large onions" as amount 3,
unit "to". Here:
  - ranges ("3 to 4", "8-12", "1 or 2") use the low number and keep the range in the note
  - sizes and prep words that land in the unit or the front of the food ("large", "grated")
    move to the note
  - unit spellings map to the space's units ("tablespoons" -> tbsp, "quarts" -> qt)
  - each ingredient goes to the first step that mentions it; anything no step mentions stays
    in the first step
"""
import re

from cookbook.helper.home_nutrition import singular, words

RANGE = re.compile(r'^\s*(\d+(?:[.,]\d+)?|\d+/\d+|[¼½¾⅓⅔⅛])\s*(?:-|–|—|to|or)\s*(\d+(?:[.,]\d+)?|\d+/\d+|[¼½¾⅓⅔⅛])\s+(.*)$', re.I)
SIZES = {'small', 'medium', 'large', 'extra-large', 'jumbo', 'big', 'heaping', 'scant', 'generous', 'whole', 'level'}
PREP = {'grated', 'shredded', 'chopped', 'minced', 'diced', 'sliced', 'thinly', 'finely', 'coarsely', 'roughly', 'freshly',
        'peeled', 'crushed', 'softened', 'melted', 'cold', 'warm', 'room-temperature', 'packed', 'sifted', 'toasted', 'ground'}
# words that don't identify an ingredient in step text
FILLER = {'and', 'or', 'of', 'the', 'a', 'an', 'for', 'to', 'taste', 'more', 'plus', 'about', 'inch', 'from', 'red', 'yellow',
          'white', 'dry', 'fresh', 'large', 'small', 'medium', 'unsalted', 'salted', 'kosher', 'extra', 'virgin', 'whole',
          'low', 'sodium', 'french'} | PREP
# what recipes call an ingredient in the method when the list names it differently
SAME = {'stock': {'broth'}, 'broth': {'stock'}, 'scallion': {'green onion'}, 'cilantro': {'coriander'},
        'confectioner': {'powdered sugar', 'icing sugar'}}
COUNT_WORDS = {'slice', 'slices', 'clove', 'cloves', 'sprig', 'sprigs', 'stalk', 'stalks', 'piece', 'pieces', 'leaf', 'leaves',
               'head', 'heads', 'bunch', 'bunches', 'can', 'cans', 'stick', 'sticks'}
PIECES = {'slice', 'slices', 'clove', 'cloves', 'sprig', 'sprigs', 'stalk', 'stalks', 'piece', 'pieces', 'leaf', 'leaves'}


def split_range(text):
    """'3 to 4 large onions' -> ('3 large onions', '3 to 4'), else (text, '')"""
    m = RANGE.match(text)
    if not m:
        return text, ''
    low, high, rest = m.groups()
    return f'{low} {rest}', f'{low}–{high}'


def tidy(ingredient, space):
    """an ingredient dict from get_from_scraper, cleaned in place"""
    from cookbook.helper import home_nutrition
    span = ingredient.pop('range', '')
    notes = []
    unit = ingredient.get('unit')
    food = (ingredient.get('food') or {}).get('name') or ''

    if unit and (unit.get('name', '').lower() in SIZES or unit.get('name', '').startswith('(')):
        notes.append(unit['name'].strip('()'))
        ingredient['unit'] = unit = None
    if unit and (known := home_nutrition.known_unit(space, unit['name'])):
        unit['name'] = known.name

    # leading sizes / prep words on the food go to the note: "grated Gruyère cheese" -> "Gruyère cheese"
    parts = food.split()
    lead = []
    while len(parts) > 1 and parts[0].lower().strip(',') in SIZES | PREP:
        lead.append(parts.pop(0).strip(','))
    if lead:
        notes.append(' '.join(lead))
    # "slices French bread" with no unit: the count word is the unit
    if not unit and len(parts) > 1 and parts[0].lower() in COUNT_WORDS:
        ingredient['unit'] = unit = {'name': parts.pop(0).lower()}
    # slices, cloves, sprigs… are pieces, which the USDA piece weights cover
    if unit and unit['name'].lower() in PIECES:
        notes.insert(0, unit['name'].lower())
        unit['name'] = 'pcs'
    food = ' '.join(parts)
    # "(about 3 pounds)" left in the name goes to the note
    if m := re.search(r'\s*\(([^)]*)\)\s*$', food):
        notes.append(m.group(1))
        food = food[:m.start()]
    if food and food[0].islower():
        food = food[0].upper() + food[1:]
    if ingredient.get('food'):
        ingredient['food']['name'] = food[:128]

    if notes or span:
        ingredient['note'] = ', '.join(n for n in [span, *notes, ingredient.get('note') or ''] if n)[:256]
    return ingredient


def keys(food_name):
    """words to look for in step text: the food's main noun first"""
    ws = [w for w in words(food_name.replace('é', 'e').replace('è', 'e')) if len(w) > 2 and w not in FILLER]
    found = []
    for w in reversed(ws):  # "beef stock" -> stock, beef
        found.append(w)
        found.extend(SAME.get(w, ()))
    return found


def mentions(text, key):
    t = ' ' + re.sub(r'[^a-z ]', ' ', text.lower().replace('é', 'e').replace('è', 'e')) + ' '
    return any(f' {k}{s} ' in t for k in [key] for s in ('', 's', 'es')) or (' ' in key and key in t)


def spread(steps):
    """move the first step's ingredients to the steps that use them"""
    if len(steps) < 2 or not steps[0].get('ingredients') or any(s.get('ingredients') for s in steps[1:]):
        return steps
    keep = []
    for ing in steps[0]['ingredients']:
        name = (ing.get('food') or {}).get('name') or ''
        ks = keys(name)
        target = next((s for s in steps if any(mentions(s.get('instruction') or '', k) for k in ks)), None)
        if target is None or target is steps[0]:
            keep.append(ing)
        else:
            target['ingredients'].append(ing)
    steps[0]['ingredients'] = keep
    return steps
