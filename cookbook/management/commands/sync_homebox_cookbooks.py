"""
home fork: bring cookbooks from Homebox (the household inventory) onto Kitchen's Books shelf.

A Homebox item of type "Book" with the tag "Cookbook" becomes a cookbook here, with its cover,
author and a description (publisher, year, pages, ISBN, where it's kept). New Homebox books are
checked once against Open Library's subjects and tagged "Cookbook" automatically when they're
about cooking; removing the tag in Homebox afterwards sticks.

Name, author and description are written when the cookbook is first brought over (so edits in
Kitchen are kept); the cover is filled in whenever Kitchen has none. Nothing is deleted here when
a book leaves Homebox, since a cookbook may have recipes attached by then.

Runs every few minutes from launchd on the host:
    docker exec home-apps-tandoor-1 /opt/recipes/venv/bin/python manage.py sync_homebox_cookbooks
Settings (environment): HOMEBOX_URL (e.g. http://host.docker.internal:8383), HOMEBOX_API_KEY,
HOMEBOX_SYNC_USER (the Kitchen username that owns the books).
"""
import json
import os
import re
from io import BytesIO
from pathlib import Path

import requests
from django.conf import settings
from django.contrib.auth.models import User
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django_scopes import scopes_disabled

from cookbook.models import RecipeBook, UserSpace

TAG = 'Cookbook'
COOKING_SUBJECT = re.compile(r'cook|cookery|cookbook|recipe|baking|culinary', re.I)
STATE_FILE = Path(settings.MEDIA_ROOT) / 'homebox_sync_state.json'


class Command(BaseCommand):
    help = 'Bring cookbooks from Homebox onto the Books shelf (home fork)'

    def add_arguments(self, parser):
        parser.add_argument('--no-tag', action='store_true', help="don't add the Cookbook tag in Homebox (read only)")
        parser.add_argument('--verbose', action='store_true')

    def handle(self, *args, **opts):
        base = os.getenv('HOMEBOX_URL', '').rstrip('/')
        key = os.getenv('HOMEBOX_API_KEY', '')
        username = os.getenv('HOMEBOX_SYNC_USER', '')
        if not (base and key and username):
            raise CommandError('HOMEBOX_URL, HOMEBOX_API_KEY and HOMEBOX_SYNC_USER must be set')
        self.verbose = opts['verbose']
        s = requests.Session()
        s.headers['Authorization'] = f'Bearer {key}'
        api = f'{base}/api/v1'

        def get(path, **kw):
            r = s.get(api + path, timeout=20, **kw)
            r.raise_for_status()
            return r

        state = self.load_state()
        checked = set(state.get('checked', []))
        # with --no-tag nothing is written to Homebox, so remember detected cookbooks here instead
        detected = set(state.get('detected', []))

        # the Cookbook tag (created on first run)
        tags = get('/tags').json()
        tag = next((t for t in tags if t['name'].lower() == TAG.lower()), None)
        if tag is None and not opts['no_tag']:
            r = s.post(api + '/tags', json={'name': TAG, 'description': 'Shown on the Kitchen Books shelf', 'color': '#a05a38'}, timeout=20)
            r.raise_for_status()
            tag = r.json()
        tag_id = tag['id'] if tag else None

        items = get('/entities', params={'pageSize': 2000}).json().get('items', [])
        books = [i for i in items if (i.get('entityType') or {}).get('name') == 'Book' and not i.get('archived')]

        with scopes_disabled():
            user = User.objects.get(username=username)
            space = UserSpace.objects.filter(user=user, active=True).first().space
            synced = 0
            for summary in books:
                tagged = any(t['id'] == tag_id for t in summary.get('tags', [])) if tag_id else False
                if opts['no_tag'] and summary['id'] in detected:
                    tagged = True
                if not tagged and summary['id'] in checked:
                    continue
                detail = get(f"/entities/{summary['id']}").json()
                fields = {f['name']: (f.get('textValue') or '').strip() for f in detail.get('fields', [])}

                if not tagged:
                    # new to the sync: is it about cooking? Asked once per book.
                    checked.add(summary['id'])
                    if not self.looks_like_cookbook(fields.get('ISBN', '')):
                        continue
                    detected.add(summary['id'])
                    if not opts['no_tag']:
                        tag_ids = [t['id'] for t in detail.get('tags', [])] + [tag_id]
                        s.patch(f"{api}/entities/{summary['id']}", json={'id': summary['id'], 'tagIds': tag_ids}, timeout=20).raise_for_status()
                        self.log(f"tagged as {TAG} in Homebox: {summary['name']}")

                self.sync_book(s, api, space, user, detail, fields)
                synced += 1

        state['checked'] = sorted(checked)
        state['detected'] = sorted(detected)
        self.save_state(state)
        self.log(f'{synced} cookbook(s) in sync', always=self.verbose)

    def sync_book(self, s, api, space, user, item, fields):
        isbn = fields.get('ISBN', '')
        book = RecipeBook.objects.filter(space=space, homebox_id=item['id']).first()
        if book is None and isbn:
            # cookbooks brought over before the sync existed carry the ISBN in their description
            book = RecipeBook.objects.filter(space=space, homebox_id__isnull=True, description__contains=isbn).first()
        created = book is None
        if created:
            title = item['name']
            book = RecipeBook(space=space, created_by=user, kind=RecipeBook.KIND_COOKBOOK, name=title[:128],
                              author=fields.get('Author', '')[:256], description=self.describe(s, api, item, fields))
        book.homebox_id = item['id']
        book.kind = RecipeBook.KIND_COOKBOOK
        book.save()

        if not book.cover:
            content, ext = None, '.jpg'
            photo = self.primary_photo(item)
            if photo:
                r = s.get(f"{api}/entities/{item['id']}/attachments/{photo['id']}", timeout=30)
                if r.ok and r.content:
                    content, ext = r.content, ('.png' if 'png' in r.headers.get('content-type', '') else '.jpg')
            if content is None and isbn:
                content = self.online_cover(isbn)
            if content:
                book.cover.save(f'{book.pk}_homebox{ext}', File(BytesIO(content)), save=True)
        if created:
            self.log(f'added to Kitchen: {book.name}')

    def describe(self, s, api, item, fields):
        # same shape as the hand-made ones: "Subtitle. Publisher, 2011 · 287 pages · ISBN … · Kept in …"
        pub = ', '.join(b for b in [fields.get('Publisher') or item.get('manufacturer'), fields.get('Published')] if b)
        bits = [b for b in [pub, f"{fields['Pages']} pages" if fields.get('Pages') else '', f"ISBN {fields['ISBN']}" if fields.get('ISBN') else ''] if b]
        text = ' · '.join(bits)
        sub = fields.get('Subtitle', '').strip().rstrip('.')
        if sub:
            text = f'{sub[0].upper()}{sub[1:]}. {text}' if text else f'{sub}.'
        try:
            trail = s.get(f"{api}/entities/{item['id']}/path", timeout=20).json()
            where = ' › '.join(p['name'] for p in trail if p['id'] != item['id'])
            if where:
                text += f' · Kept in {where}.' if text else f'Kept in {where}.'
        except Exception:
            pass
        return text

    @staticmethod
    def primary_photo(item):
        photos = [a for a in item.get('attachments', []) if a.get('type') == 'photo']
        return next((a for a in photos if a.get('primary')), photos[0] if photos else None)

    @staticmethod
    def online_cover(isbn):
        """a cover photo when Homebox has none: Open Library, then Amazon's ISBN image"""
        try:
            r = requests.get(f'https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg', params={'default': 'false'}, timeout=15)
            if r.ok and len(r.content) > 2000:
                return r.content
        except Exception:
            pass
        isbn10 = Command.isbn10(isbn)
        if isbn10:
            try:
                r = requests.get(f'https://images-na.ssl-images-amazon.com/images/P/{isbn10}.01.LZZZZZZZ.jpg', timeout=15)
                if r.ok and len(r.content) > 2000:  # a missing image is a 43-byte gif
                    return r.content
            except Exception:
                pass
        return None

    @staticmethod
    def isbn10(isbn):
        d = re.sub(r'[^0-9X]', '', isbn.upper())
        if len(d) == 10:
            return d
        if len(d) == 13 and d.startswith('978'):
            core = d[3:12]
            check = (11 - sum((10 - i) * int(c) for i, c in enumerate(core)) % 11) % 11
            return core + ('X' if check == 10 else str(check))
        return None

    @staticmethod
    def looks_like_cookbook(isbn):
        if not isbn:
            return False
        try:
            r = requests.get('https://openlibrary.org/api/books', params={'bibkeys': f'ISBN:{isbn}', 'format': 'json', 'jscmd': 'data'}, timeout=15)
            subjects = [x.get('name', '') for x in r.json().get(f'ISBN:{isbn}', {}).get('subjects', [])]
            return any(COOKING_SUBJECT.search(x) for x in subjects)
        except Exception:
            return False

    def load_state(self):
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            return {}

    def save_state(self, state):
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(state))

    def log(self, msg, always=True):
        if always:
            self.stdout.write(msg)
