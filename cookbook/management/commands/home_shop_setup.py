# home fork: set up shopping for this household (see cookbook/helper/home_aisles.py).
#   - removes the sample supermarkets Tandoor's open data adds (Tesco, H-E-B, Albert Heijn...) when
#     no shopping list uses them
#   - adds one "Grocery store" whose aisles follow a typical store walk (rename it in Database > Supermarkets)
#   - gives every food without an aisle the one its name or USDA category points to
#   - keeps water off shopping lists
#   manage.py home_shop_setup --dry-run     show what would happen
#   manage.py home_shop_setup               do it
from django.core.management.base import BaseCommand
from django.db import transaction
from django_scopes import scopes_disabled

from cookbook.helper.home_aisles import STORE_ORDER, aisle, word_aisle
from cookbook.models import Food, Space, Supermarket, SupermarketCategory, SupermarketCategoryRelation

STORE_NAME = 'Grocery store'


class Command(BaseCommand):
    help = 'Replace the sample supermarkets with one store and fill in missing food aisles'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--space', type=int, help='only this space id')

    def handle(self, *args, **opts):
        dry = opts['dry_run']
        with scopes_disabled(), transaction.atomic():
            spaces = Space.objects.filter(id=opts['space']) if opts['space'] else Space.objects.all()
            for space in spaces:
                self.stdout.write(f'{space.name}:')
                samples = Supermarket.objects.filter(space=space, open_data_slug__isnull=False, shopping_lists__isnull=True)
                self.stdout.write(f'  removing {samples.count()} sample supermarkets')
                samples.delete()

                store = Supermarket.objects.filter(space=space, name=STORE_NAME).first()
                if store is None:
                    store = Supermarket.objects.create(space=space, name=STORE_NAME, description='Aisles in the order you walk the store')
                    self.stdout.write(f'  added "{STORE_NAME}"')
                for i, name in enumerate(STORE_ORDER):
                    cat, _ = SupermarketCategory.objects.get_or_create(space=space, name=name)
                    SupermarketCategoryRelation.objects.update_or_create(supermarket=store, category=cat, defaults={'order': i})

                # open data files some baking supplies under Bakery (bread): "Baking Powder", "Nutritional yeast"
                for food in Food.objects.filter(space=space, supermarket_category__name='Bakery').select_related('supermarket_category'):
                    if (name := word_aisle(food)) == 'Baking':
                        self.stdout.write(f'  {food.name}: {food.supermarket_category.name} -> {name}')
                        food.supermarket_category = SupermarketCategory.objects.get(space=space, name=name)
                        food.save(update_fields=['supermarket_category'])

                # tap water never goes on a shopping list
                for food in Food.objects.filter(space=space, name__iexact='water', ignore_shopping=False):
                    food.ignore_shopping = True
                    food.save(update_fields=['ignore_shopping'])
                    self.stdout.write(f'  {food.name}: left off shopping lists')

                filled, left = 0, []
                for food in Food.objects.filter(space=space, supermarket_category__isnull=True).order_by('name'):
                    if cat := aisle(food):
                        food.supermarket_category = cat
                        food.save(update_fields=['supermarket_category'])
                        filled += 1
                        if food.ingredient_set.exists():
                            self.stdout.write(f'  {food.name} -> {cat.name}')
                    elif food.ingredient_set.exists():
                        left.append(food.name)
                self.stdout.write(f'  aisles filled for {filled} foods; recipe foods left without one: {", ".join(left) or "none"}')
            if dry:
                transaction.set_rollback(True)
                self.stdout.write('(dry run, nothing saved)')
