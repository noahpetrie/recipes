# home fork: fill in nutrition for every food that has none (see cookbook/helper/home_nutrition.py),
# and fold stray units such as "grams" into the space's real g unit so their amounts convert.
#   manage.py fill_nutrition --dry-run     show what would happen
#   manage.py fill_nutrition               do it
from django.core.management.base import BaseCommand
from django.db import transaction
from django_scopes import scopes_disabled

from cookbook.helper import home_nutrition
from cookbook.models import Food, Ingredient, InventoryEntry, ShoppingListEntry, Space, StockCountLine, Unit, UnitConversion


class Command(BaseCommand):
    help = 'Fill USDA nutrition for foods without properties and merge synonym units (grams -> g)'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--space', type=int, help='only this space id')
        parser.add_argument('--all-foods', action='store_true', help='also foods no recipe uses yet')

    def handle(self, *args, **opts):
        dry = opts['dry_run']
        with scopes_disabled(), transaction.atomic():
            spaces = Space.objects.filter(id=opts['space']) if opts['space'] else Space.objects.all()
            for space in spaces:
                self.merge_units(space, dry)
                # foods with no properties, or only some (complete_food adds the rest)
                foods = Food.objects.filter(space=space)
                if not opts['all_foods']:
                    foods = foods.filter(ingredient__isnull=False)
                filled, left = 0, []
                for food in foods.distinct().order_by('name'):
                    entry, how = home_nutrition.fill_food(food, dry_run=dry)
                    if how == 'has properties already':
                        continue
                    if entry:
                        filled += 1
                        self.stdout.write(f'  {food.name} -> {entry["description"]} ({how})')
                    else:
                        left.append(f'{food.name} ({how})')
                self.stdout.write(self.style.SUCCESS(f'{space.name}: {"would fill" if dry else "filled"} {filled}'))
                for line in left:
                    self.stdout.write(f'  not filled: {line}')
            if dry:
                transaction.set_rollback(True)

    def merge_units(self, space, dry):
        for unit in Unit.objects.filter(space=space, base_unit__isnull=True):
            target = home_nutrition.known_unit(space, unit.name)
            if not target or target.id == unit.id:
                continue
            n = Ingredient.objects.filter(space=space, unit=unit).count()
            self.stdout.write(f'  unit "{unit.name}" -> "{target.name}" ({n} ingredients)')
            if dry:
                continue
            # every table that points at a unit (models.py), so deleting the stray one loses nothing
            for model in (Ingredient, ShoppingListEntry, InventoryEntry):
                model.objects.filter(space=space, unit=unit).update(unit=target)
            StockCountLine.objects.filter(count__space=space, unit=unit).update(unit=target)
            for field in ('properties_food_unit', 'preferred_unit', 'preferred_shopping_unit'):
                Food.objects.filter(space=space, **{field: unit}).update(**{field: target})
            UnitConversion.objects.filter(space=space, base_unit=unit).update(base_unit=target)
            UnitConversion.objects.filter(space=space, converted_unit=unit).update(converted_unit=target)
            unit.delete()
