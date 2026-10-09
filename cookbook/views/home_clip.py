"""
home fork: the "Add to Kitchen" Chrome extension (browser-extension/ in this repo).

The extension reads the recipe from the tab the person is looking at (so sites they're signed in
to, like ChefSteps, give the full recipe) and posts it here:

  GET  /api/home/extension-token/   session login -> an API token for the extension
  POST /api/home/clip/              {url, html?, chefsteps?, dry_run?, force?}
                                    dry_run -> a preview; otherwise the recipe is created with its
                                    photo, step photos and source link

ChefSteps pages carry the whole recipe as JSON (Next.js page data); other sites go through
Tandoor's normal scraper (schema.org / recipe-scrapers) using the page's HTML.
"""
import html as htmllib
import io
import logging
import re
import uuid
from datetime import timedelta

from django.core.files import File
from django.db import transaction
from django.utils import timezone
from oauth2_provider.models import AccessToken
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from cookbook.helper.HelperFunctions import safe_request
from cookbook.helper.image_processing import handle_image
from cookbook.helper.permission_helper import CustomIsUser, CustomTokenHasReadWriteScope
from cookbook.models import Recipe, UserFile

log = logging.getLogger('recipes')
UA = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140 Safari/537.36'}


# ---- token for the extension -----------------------------------------------------------------

@api_view(['GET'])
@permission_classes([CustomIsUser])
def extension_token(request):
    """a long-lived read/write token for the extension, handed out to a signed-in browser session"""
    if request.auth is not None:
        return Response({'error': 'Sign in to Kitchen in the browser first.'}, status=403)
    token = AccessToken.objects.create(user=request.user, token=f'tda_{str(uuid.uuid4()).replace("-", "_")}',
                                       expires=timezone.now() + timedelta(days=3650), scope='read write')
    return Response({'token': token.token, 'user': request.user.get_full_name() or request.user.username,
                     'space': request.space.name, 'app_name': request.space.app_name or 'Kitchen'})


# ---- html -> markdown ---------------------------------------------------------------------------

def f_to_c(f):
    return round((float(f) - 32) * 5 / 9)


def c_to_f(c):
    return round(float(c) * 9 / 5 + 32)


def temps(text):
    """ChefSteps writes temperatures as [f 129] / [c 54]"""
    text = re.sub(r'\[f\s+(-?\d+(?:\.\d+)?)\]', lambda m: f'{m.group(1)} °F ({f_to_c(m.group(1))} °C)', text, flags=re.I)
    text = re.sub(r'\[c\s+(-?\d+(?:\.\d+)?)\]', lambda m: f'{m.group(1)} °C ({c_to_f(m.group(1))} °F)', text, flags=re.I)
    return text


def html_to_md(s):
    if not s:
        return ''
    s = re.sub(r'<br\s*/?>', '\n', s, flags=re.I)
    s = re.sub(r'<li[^>]*>', '\n- ', s, flags=re.I)
    s = re.sub(r'</(p|div|ul|ol|h\d)>', '\n\n', s, flags=re.I)
    s = re.sub(r'<(b|strong)[^>]*>(.*?)</\1>', r'**\2**', s, flags=re.I | re.S)
    s = re.sub(r'<(i|em)[^>]*>(.*?)</\1>', r'*\2*', s, flags=re.I | re.S)
    s = re.sub(r'<a [^>]*href="([^"]+)"[^>]*>(.*?)</a>', r'[\2](\1)', s, flags=re.I | re.S)
    s = re.sub(r'<[^>]+>', '', s)
    s = htmllib.unescape(s)
    s = temps(s)
    s = re.sub(r'[ \t]+\n', '\n', s)
    return re.sub(r'\n{3,}', '\n\n', s).strip()


def first_paragraph(md):
    for p in md.split('\n\n'):
        p = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', p).replace('**', '').strip()
        if p:
            return p
    return ''


# ---- ChefSteps --------------------------------------------------------------------------------

NO_UNIT = {'ea', 'each', 'whole', 'piece', 'pieces', 'pc', 'pcs', ''}
AS_NEEDED = {'a/n', 'as needed', 'to taste', 'n/a'}


def cs_ingredient(i):
    unit = str(i.get('metricUnit') or i.get('unit') or '').strip()
    note = str(i.get('tip') or i.get('preparation') or i.get('note') or '').strip()
    try:
        amount = float(i.get('metricAmount') or i.get('amount') or i.get('quantity') or 0)
    except ValueError:
        amount = 0
    if unit.lower() in AS_NEEDED or amount == 0:
        return {'food': {'name': i['name'][:128]}, 'unit': None, 'amount': 0, 'no_amount': True,
                'note': ', '.join(x for x in [note, 'as needed' if unit.lower() in AS_NEEDED else ''] if x)[:256]}
    return {'food': {'name': i['name'][:128]}, 'unit': None if unit.lower() in NO_UNIT else {'name': unit[:128]},
            'amount': amount, 'no_amount': False, 'note': note[:256]}


def from_chefsteps(page, url, signed_in=None):
    """ChefSteps page data -> (recipe json, hero image url, [step image url or None])"""
    d = page.get('data') or {}
    if not d.get('title'):
        raise ValueError('This ChefSteps page has no recipe on it.')
    steps_in = d.get('steps') or []
    if not steps_in:
        if page.get('isContentLimited') or d.get('studio') or d.get('premium'):
            if signed_in:
                raise ValueError('You’re signed in to ChefSteps, but it didn’t hand over this recipe. Check your Studio Pass is active, reload the page, and try again.')
            raise ValueError('ChefSteps only shows this recipe to signed-in Studio Pass members. Sign in to ChefSteps in this browser, reload the page and try again.')
        raise ValueError('This ChefSteps page has no steps to import.')

    intro = html_to_md(d.get('subTitle') or '')
    authors = ', '.join(a.get('name', '') for a in (d.get('authors') or [d.get('author') or {}]) if a.get('name') and a.get('name').lower() != 'chefsteps')
    desc = f'ChefSteps{f" ({authors})" if authors else ""}. {first_paragraph(intro)}'
    if len(desc) > 512:
        desc = desc[:509].rsplit(' ', 1)[0] + '…'

    steps, images, used = [], [], set()

    equipment = d.get('equipment') or []
    if equipment:
        lines = [f"- {e['name']}{' (optional)' if e.get('optional') else ''}" for e in equipment if e.get('name')]
        steps.append({'name': 'Equipment', 'instruction': '\n'.join(lines), 'ingredients': []})
        images.append(None)

    for s in steps_in:
        ings = [cs_ingredient(i) for i in (s.get('ingredients') or []) if i.get('name')]
        used.update(i.get('id') for i in (s.get('ingredients') or []))
        name = temps(htmllib.unescape(s.get('title') or '')).strip()
        if s.get('isTip'):
            name = f'Tip: {name}' if name else 'Tip'
        text = html_to_md(s.get('description') or '')
        if s.get('tip'):
            text += f"\n\n*Tip:* {html_to_md(s['tip'])}"
        steps.append({'name': name[:128], 'instruction': text, 'ingredients': ings})
        img = s.get('ImageUrl') or s.get('imageUrl') or s.get('image')
        if isinstance(img, dict):
            img = img.get('url') or img.get('imageUrl')
        images.append(img if isinstance(img, str) and img.startswith('http') else None)

    # anything in the ingredient list that no step uses goes up front
    left = [cs_ingredient(i) for i in (d.get('ingredients') or []) if i.get('name') and i.get('id') not in used]
    if left:
        at = 1 if equipment else 0
        steps.insert(at, {'name': 'Ingredients', 'instruction': '', 'ingredients': left})
        images.insert(at, None)

    video = (d.get('video') or {}).get('url')
    if video:
        steps.append({'name': 'Video', 'instruction': f'[Watch the ChefSteps video]({video})', 'ingredients': []})
        images.append(None)

    for n, s in enumerate(steps):
        s['order'] = n

    active, total = int(d.get('activeTime') or 0), int(d.get('totalTime') or 0)
    recipe = {
        'name': d['title'][:128], 'description': desc, 'source_url': url, 'internal': True,
        'servings': int(d.get('makesAmount') or 1) or 1, 'servings_text': (d.get('makesText') or '')[:32],
        'working_time': active, 'waiting_time': max(0, total - active),
        'keywords': [{'name': 'ChefSteps'}], 'steps': steps,
    }
    hero = d.get('heroImage')
    if isinstance(hero, list):
        hero = hero[0] if hero else None
    if isinstance(hero, dict):
        hero = hero.get('url') or hero.get('imageUrl')
    return recipe, hero if isinstance(hero, str) else None, images


# ---- any other site ---------------------------------------------------------------------------

def from_html(request, html, url):
    from recipe_scrapers import scrape_html
    from cookbook.helper import recipe_url_import as helper
    try:
        scrape = scrape_html(org_url=url, html=html, supported_only=False)
    except Exception as e:
        log.info(f'clip: no recipe found on {url}: {e}')
        raise ValueError('Couldn’t find a recipe on this page.')
    recipe = helper.get_from_scraper(scrape, request)
    if not recipe.get('name') or not recipe.get('steps'):
        raise ValueError('Couldn’t find a recipe on this page.')
    recipe['source_url'] = url
    recipe['keywords'] = [k for k in recipe.get('keywords', []) if k.get('import_keyword', k.get('importKeyword', True))]
    for n, s in enumerate(recipe['steps']):
        s.setdefault('order', n)
    return recipe, recipe.pop('image_url', None) or recipe.pop('image', None), [None] * len(recipe['steps'])


# ---- saving -----------------------------------------------------------------------------------

def fetch_image(url):
    if not url:
        return None, None
    try:
        r = safe_request('GET', url, headers=UA, timeout=20)
        if r.ok and r.content and len(r.content) > 1000:
            ext = {'image/png': '.png', 'image/webp': '.webp', 'image/gif': '.gif'}.get(r.headers.get('content-type', '').split(';')[0], '.jpg')
            return r.content, ext
    except Exception as e:
        log.warning(f'clip: image {url} failed: {e!r}')
    return None, None


def processed(request, content, ext):
    """resize like Tandoor's own uploads; None if it isn't a usable image"""
    out = handle_image(request, File(io.BytesIO(content)), ext)
    if out is None:
        return None
    if hasattr(out, 'seek'):
        out.seek(0)
    return out if isinstance(out, File) else File(out)


def preview(recipe, hero, images, duplicates):
    return {
        'name': recipe['name'], 'description': recipe.get('description', ''), 'image': hero,
        'servings': recipe.get('servings'), 'servings_text': recipe.get('servings_text', ''),
        'working_time': recipe.get('working_time', 0), 'waiting_time': recipe.get('waiting_time', 0),
        'ingredients': sum(len(s.get('ingredients', [])) for s in recipe['steps']),
        'steps': len(recipe['steps']), 'step_images': sum(1 for i in images if i),
        'source_url': recipe.get('source_url'), 'duplicates': duplicates,
    }


@api_view(['POST'])
@permission_classes([CustomIsUser & CustomTokenHasReadWriteScope])
def clip(request):
    from cookbook.serializer import RecipeSerializer
    d = request.data
    url = (d.get('url') or '').strip()
    if not url.startswith('http'):
        return Response({'error': 'Open a recipe page first.'}, status=400)
    try:
        if d.get('chefsteps'):
            try:
                recipe, hero, images = from_chefsteps(d['chefsteps'], url.split('?')[0].split('#')[0], d.get('chefstepsSignedIn'))
            except ValueError as e:
                # no steps in the page data: try what the page shows, else explain
                if not d.get('html'):
                    raise
                try:
                    recipe, hero, images = from_html(request, d['html'], url.split('?')[0].split('#')[0])
                except ValueError:
                    raise e
        elif d.get('html'):
            recipe, hero, images = from_html(request, d['html'], url)
        else:
            return Response({'error': 'Nothing to import from this page.'}, status=400)
    except ValueError as e:
        return Response({'error': str(e)}, status=422)

    duplicates = [{'id': r.id, 'name': r.name, 'url': f'/recipe/{r.id}'} for r in Recipe.objects.filter(space=request.space, source_url=recipe['source_url'])[:3]]
    if d.get('dry_run'):
        return Response({'preview': preview(recipe, hero, images, duplicates)})
    if duplicates and not d.get('force'):
        return Response({'error': 'Already in Kitchen.', 'duplicates': duplicates}, status=409)

    with transaction.atomic():
        s = RecipeSerializer(data=recipe, context={'request': request})
        if not s.is_valid():
            log.warning(f'clip: recipe rejected: {s.errors}')
            return Response({'error': 'Kitchen couldn’t save this recipe.', 'details': s.errors}, status=400)
        obj = s.save()

    # photos after the recipe exists, so a slow image host can't lose the recipe
    content, ext = fetch_image(hero)
    img = processed(request, content, ext) if content else None
    if img is not None:  # (a nameless Django File is falsy)
        obj.image.save(f'{uuid.uuid4()}_{obj.pk}{ext}', img)
        obj.save()
    saved_step_images = 0
    if any(images) and request.space.max_file_storage_mb != -1:
        steps = list(obj.steps.order_by('order', 'id'))
        for step, img in zip(steps, images):
            content, ext = fetch_image(img)
            pic = processed(request, content, ext) if content else None
            if pic is None:
                continue
            uf = UserFile(name=f'{obj.name[:90]} – {step.name[:30] or "step"}', space=request.space, created_by=request.user)
            uf.file.save(f'{uuid.uuid4()}{ext}', pic, save=False)
            uf.file_size_kb = round(uf.file.size / 1000)
            uf.save()
            step.file = uf
            step.save(update_fields=['file'])
            saved_step_images += 1

    return Response({'id': obj.id, 'name': obj.name, 'url': f'/recipe/{obj.id}', 'image': bool(obj.image),
                     'step_images': saved_step_images, 'steps': obj.steps.count()}, status=201)
