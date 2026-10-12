"""
home fork: where a food lives in the store and at home.

  aisle(food)        the SupermarketCategory a food belongs in (Produce, Dairy, ...), from its USDA
                     category, or from words in its name when it has no USDA match
  storage(food)      where it goes when you bring it home and how many days it usually keeps:
                     ('Fridge', 7), ('Pantry', None) ...
  STORE_ORDER        the order of the aisles in a typical walk through a Canadian grocery store

Used by the groceries screen (cookbook/views/home_groceries.py), by new foods (fill_new_food) and
by `manage.py home_shop_setup`, which sets up the household's store and fills in missing aisles.
"""
from cookbook.helper.home_nutrition import singular, table, words

# produce and the fresh counters around the outside first, then the middle aisles, frozen last
STORE_ORDER = ['Produce', 'Bakery', 'Deli', 'Meat', 'Fish and Seafood', 'Cheese', 'Dairy',
               'Noodles', 'Dry Goods', 'Canned', 'Condiments and Sauces', 'Oil and Vinegar', 'Herbs and Spices',
               'Baking', 'Cereal', 'Savory Spreads', 'Sweet Spreads', 'Sweets', 'Coffee and Tea', 'Juices',
               'Alcohol', 'Frozen']

USDA_AISLE = {
    'Dairy and Egg Products': 'Dairy', 'Spices and Herbs': 'Herbs and Spices', 'Fats and Oils': 'Oil and Vinegar',
    'Poultry Products': 'Meat', 'Soups, Sauces, and Gravies': 'Canned', 'Sausages and Luncheon Meats': 'Deli',
    'Breakfast Cereals': 'Cereal', 'Fruits and Fruit Juices': 'Produce', 'Pork Products': 'Meat',
    'Vegetables and Vegetable Products': 'Produce', 'Nut and Seed Products': 'Dry Goods', 'Beef Products': 'Meat',
    'Beverages': 'Coffee and Tea', 'Finfish and Shellfish Products': 'Fish and Seafood',
    'Legumes and Legume Products': 'Dry Goods', 'Lamb, Veal, and Game Products': 'Meat', 'Baked Products': 'Bakery',
    'Sweets': 'Sweets', 'Cereal Grains and Pasta': 'Dry Goods', 'Snacks': 'Sweets', 'Alcoholic Beverages': 'Alcohol',
}

# name words that decide the aisle before (or instead of) the USDA category; the first match wins
WORD_AISLE = [
    ({'canned', 'tinned'}, 'Canned'),
    ({'frozen'}, 'Frozen'),
    ({'wine', 'sherry', 'beer', 'rum', 'brandy', 'bourbon', 'sake', 'whiskey', 'whisky', 'vodka', 'gin', 'liqueur'}, 'Alcohol'),
    ({'cheese', 'parmesan', 'gruyere', 'mozzarella', 'cheddar', 'ricotta', 'mascarpone', 'feta'}, 'Cheese'),
    ({'sauce', 'ketchup', 'mustard', 'mayonnaise', 'mirin', 'sriracha', 'vinegar', 'stock', 'broth', 'bouillon', 'miso'},
     'Condiments and Sauces'),
    ({'oil', 'shortening'}, 'Oil and Vinegar'),
    ({'salt', 'pepper', 'cinnamon', 'cumin', 'paprika', 'garam', 'masala', 'turmeric', 'nutmeg', 'clove', 'msg', 'peel',
      'kashmiri', 'cardamom', 'coriander', 'bay'}, 'Herbs and Spices'),
    ({'flour', 'sugar', 'yeast', 'vanilla', 'cocoa', 'chocolate', 'cornstarch', 'starch', 'gelatin', 'molasses', 'dextrin',
      'dextrose', 'glucose', 'malt', 'stabilizer', 'pistachio', 'baking'}, 'Baking'),
    ({'pasta', 'noodle', 'spaghetti', 'ramen', 'udon', 'macaroni'}, 'Noodles'),
    ({'rice', 'lentil', 'quinoa', 'oat', 'bean'}, 'Dry Goods'),
    ({'juice'}, 'Juices'),
    ({'coffee', 'tea', 'espresso'}, 'Coffee and Tea'),
    ({'bread', 'bun', 'baguette', 'tortilla'}, 'Bakery'),
    ({'jam', 'honey', 'syrup', 'nutella'}, 'Sweet Spreads'),
    ({'egg', 'milk', 'cream', 'butter', 'yogurt', 'buttermilk'}, 'Dairy'),
    ({'chicken', 'beef', 'pork', 'lamb', 'steak', 'bacon', 'turkey', 'sausage'}, 'Meat'),
    ({'fish', 'salmon', 'shrimp', 'tuna', 'cod', 'prawn', 'scallop'}, 'Fish and Seafood'),
    ({'onion', 'garlic', 'ginger', 'lemon', 'lime', 'tomato', 'potato', 'carrot', 'apple', 'cilantro', 'parsley',
      'basil', 'scallion', 'shallot', 'chili', 'zest', 'date'}, 'Produce'),
]

# (place, days it keeps there) per aisle; None days = no expiry worth tracking
AISLE_STORAGE = {
    'Produce': ('Fridge', 7), 'Bakery': ('Pantry', 4), 'Deli': ('Fridge', 5), 'Meat': ('Fridge', 3),
    'Fish and Seafood': ('Fridge', 2), 'Cheese': ('Fridge', 21), 'Dairy': ('Fridge', 10), 'Frozen': ('Freezer', 180),
    'Juices': ('Fridge', 7),
}
# exceptions by name word: (place, days)
WORD_STORAGE = [
    ({'egg', 'eggs'}, ('Fridge', 28)), ({'butter'}, ('Fridge', 60)), ({'onion', 'potato', 'garlic', 'shallot'}, ('Pantry', 30)),
    ({'lemon', 'lime', 'apple', 'orange'}, ('Fridge', 21)), ({'banana', 'tomato'}, ('Pantry', 5)),
    ({'herb', 'cilantro', 'parsley', 'basil', 'mint', 'scallion'}, ('Fridge', 5)), ({'yeast'}, ('Fridge', 120)),
    ({'cream', 'buttermilk'}, ('Fridge', 10)),
]


# compare like words() does: lower case, singular ("eggs" -> egg)
WORD_AISLE = [({singular(k) for k in keys}, v) for keys, v in WORD_AISLE]
WORD_STORAGE = [({singular(k) for k in keys}, v) for keys, v in WORD_STORAGE]


def _usda_category(food):
    if not food.fdc_id:
        return ''
    entry = table()[1].get(food.fdc_id)
    return entry['category'] if entry else ''


def word_aisle(food):
    ws = set(words(food.name))
    for keys, name in WORD_AISLE:
        if ws & keys:
            return name
    return None


def aisle_name(food):
    return word_aisle(food) or USDA_AISLE.get(_usda_category(food))


def aisle(food):
    """the space's SupermarketCategory for this food, or None"""
    from cookbook.models import SupermarketCategory
    name = aisle_name(food)
    return SupermarketCategory.objects.filter(space=food.space, name=name).first() if name else None


def storage(food):
    """(location name, days it keeps or None)"""
    ws = set(words(food.name))
    for keys, place in WORD_STORAGE:
        if ws & keys:
            return place
    name = food.supermarket_category.name if food.supermarket_category_id else aisle_name(food)
    return AISLE_STORAGE.get(name, ('Pantry', None))


def fill_aisle(food):
    """give a new food its aisle; never raises"""
    try:
        if not food.supermarket_category_id and (cat := aisle(food)):
            food.supermarket_category = cat
            food.save(update_fields=['supermarket_category'])
    except Exception:
        pass
