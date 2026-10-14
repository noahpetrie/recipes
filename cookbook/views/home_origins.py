"""
home fork: where recipes come from, for the food map.

  GET /api/home/origins/   {countries: [{code, recipes: [{id, name, image, region, last_cooked, times}]}]}
                           every recipe with an origin country, and whether (and how often) you've made it
"""
from django.db.models import Count, Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from cookbook.models import Recipe
from cookbook.views.home_pantry import PERMS


@api_view(['GET'])
@permission_classes(PERMS)
def origins(request):
    user, space = request.user, request.space
    qs = (Recipe.objects.filter(space=space).exclude(origin_country='')
          .filter(Q(private=False) | Q(created_by=user) | Q(shared=user)).distinct()
          .with_last_cooked(user, space)
          .annotate(times=Count('cooklog__pk', filter=Q(cooklog__created_by=user, cooklog__space=space), distinct=True))
          .order_by('name'))
    countries = {}
    for r in qs:
        countries.setdefault(r.origin_country, []).append({
            'id': r.id, 'name': r.name, 'image': r.image.url if r.image else None, 'region': r.origin_region,
            'last_cooked': r.lastcooked.isoformat() if r.lastcooked else None, 'times': r.times,
        })
    return Response({'countries': [{'code': c, 'recipes': rs} for c, rs in sorted(countries.items())]})
