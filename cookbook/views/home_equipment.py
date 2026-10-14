"""
home fork: kitchen equipment (cookbook/helper/home_equipment.py).

  GET    /api/home/equipment/                 every piece: owned, where it came from, how many recipes need it
  POST   /api/home/equipment/                 {name} find or add a piece
  PATCH  /api/home/equipment/<id>/            {owned, hidden, general (id or null), name}
  DELETE /api/home/equipment/<id>/            remove it (and from the recipes that list it)
  GET    /api/home/equipment/recipe/<id>/     what a recipe needs, whether you have each, and suggestions from its steps
  PUT    /api/home/equipment/recipe/<id>/     {items: [{id | name, optional, note}]} replace a recipe's equipment
"""
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from cookbook.helper import home_equipment as he
from cookbook.models import Equipment, Recipe, RecipeEquipment
from cookbook.views.home_pantry import PERMS


def image_url(eq):
    try:
        return eq.image.url if eq.image else None
    except ValueError:
        return None


def item(eq, kitchen, recipes=None):
    got = kitchen.have(eq)
    general = kitchen.all.get(eq.general_id) if eq.general_id else None
    out = {
        'id': eq.id, 'name': eq.name, 'owned': eq.owned, 'hidden': eq.hidden, 'homebox': bool(eq.homebox_id),
        'image': image_url(eq), 'general': {'id': general.id, 'name': general.name} if general else None,
        'kind': eq.general_id is None and eq.name.lower() in he.BY_NAME,
        'basic': bool(he.BY_NAME.get(eq.name.lower(), (0, False))[1]) if eq.general_id is None else False,
        'have': got is not None, 'via': got.name if got is not None and got.id != eq.id else None,
    }
    if recipes is not None:
        out['recipes'] = recipes.get(eq.id, 0)
    return out


def visible_recipes(request):
    return Recipe.objects.filter(space=request.space).filter(Q(private=False) | Q(created_by=request.user) | Q(shared=request.user)).distinct()


@api_view(['GET', 'POST'])
@permission_classes(PERMS)
def equipment(request):
    if request.method == 'POST':
        name, _, _ = he.tidy(str(request.data.get('name') or ''))
        if not name:
            return Response({'error': 'Give the equipment a name.'}, status=400)
        eq = he.find_or_create(request.space, name)
        return Response(item(eq, he.Kitchen(request.space)))

    he.ensure_all(request.space)
    kitchen = he.Kitchen(request.space)
    counts = dict(RecipeEquipment.objects.filter(space=request.space, recipe__in=visible_recipes(request))
                  .values('equipment').annotate(n=Count('recipe', distinct=True)).values_list('equipment', 'n'))
    return Response({'equipment': [item(e, kitchen, counts) for e in sorted(kitchen.all.values(), key=lambda e: e.name.lower())]})


@api_view(['PATCH', 'DELETE'])
@permission_classes(PERMS)
def equipment_detail(request, pk):
    eq = get_object_or_404(Equipment, space=request.space, pk=pk)
    if request.method == 'DELETE':
        eq.delete()
        return Response(status=204)
    d = request.data
    if 'owned' in d and not eq.homebox_id:  # Homebox decides for what it tracks
        eq.owned = bool(d['owned'])
    if 'hidden' in d:
        eq.hidden = bool(d['hidden'])
    if 'name' in d and str(d['name']).strip():
        eq.name = str(d['name']).strip()[:128]
    if 'general' in d:
        g = d['general']
        if g in (None, ''):
            eq.general = None
        else:
            top = get_object_or_404(Equipment, space=request.space, pk=g, general__isnull=True)
            if top.id == eq.id or eq.specific.exists():
                return Response({'error': 'A general kind of equipment can’t go under another one.'}, status=400)
            eq.general = top
    eq.save()
    return Response(item(eq, he.Kitchen(request.space)))


def recipe_state(request, recipe):
    kitchen = he.Kitchen(request.space)
    lines = list(RecipeEquipment.objects.filter(recipe=recipe).select_related('equipment'))
    # kinds the list already covers, directly or as a stand-in ("Air fryer" when a Smart Oven Air Fryer is listed)
    kinds = set()
    for l in lines:
        top = kitchen.all.get(l.equipment.general_id) if l.equipment.general_id else l.equipment
        kinds.add(top.name.lower())
        kinds.update(k.lower() for k in he.BY_NAME.get(top.name.lower(), (None, None, None, []))[3])
    text = ' '.join(f'{s.name or ""} {s.instruction or ""}' for s in recipe.steps.all())
    suggestions = []
    for kind, _ in he.detect(text):
        basic, also = he.BY_NAME[kind.lower()][1], he.BY_NAME[kind.lower()][3]
        if basic or kind.lower() in kinds or any(a.lower() in kinds for a in also):
            continue  # basics would be noise next to a recipe's own list
        suggestions.append(kind)
    return {
        'items': [{**item(l.equipment, kitchen), 'optional': l.optional, 'note': l.note} for l in lines],
        'suggestions': suggestions,
    }


@api_view(['GET', 'PUT'])
@permission_classes(PERMS)
def recipe_equipment(request, pk):
    recipe = get_object_or_404(visible_recipes(request), pk=pk)
    changed = he.ensure(recipe)
    if request.method == 'PUT':
        items = []
        for x in request.data.get('items') or []:
            if x.get('id'):
                eq = Equipment.objects.filter(space=request.space, pk=x['id']).first()
            else:
                name, note, _ = he.tidy(str(x.get('name') or ''))
                eq = he.find_or_create(request.space, name) if name else None
                x.setdefault('note', note)
            if eq:
                items.append((eq, bool(x.get('optional')), str(x.get('note') or '')))
        he.set_lines(recipe, items)
    return Response({**recipe_state(request, recipe), 'converted': changed})
