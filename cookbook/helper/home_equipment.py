"""
home fork: kitchen equipment ("tools" in Mealie) — what a recipe needs and whether the kitchen has it.

General kinds of equipment (Stand mixer, Springform pan) come from CATALOG; specific products
(Breville the Bakery Chef Stand Mixer, from Homebox or a ChefSteps clip) sit under the kind they
are. A recipe's need is met when
  - that piece, or anything under it, is owned (needs "Digital scale", you own an OXO scale), or
  - it's a specific product and something else of the same kind is owned (ChefSteps asks for the
    Breville Smart Oven Air Fryer Pro, you have the Smart Oven Air), or
  - a kind that does the job is owned (a stand mixer covers "hand mixer").
Basic cookware (skillets, sheet pans, mixing bowls) and supplies (parchment) are assumed owned
when first created; untick them on the Equipment page if not.

Recipes get their equipment once (`ensure`): a ChefSteps/website "Equipment" step is turned into
equipment lines and removed, otherwise the step text is read for the equipment it mentions.
"""
import re

from cookbook.models import Equipment, Recipe, RecipeEquipment, Step

# (name, basic, words that name it in a recipe or product name, kinds that also do the job)
# Order matters: more specific kinds first (immersion blender before blender).
CATALOG = [
    ('Immersion blender', False, [r'immersion blender', r'stick blender', r'hand blender'], ['Blender']),
    ('Ice cream maker', False, [r'ice[- ]cream (maker|machine|freezer)', r'smart scoop', r'gelato maker', r'\bchurn', r'\bcreami\b', r'pacojet'], []),
    ('Whipping siphon', False, [r'siphon', r'cream whipper', r'\bisi\b'], []),
    ('Rice cooker', False, [r'rice cooker'], []),
    ('Pressure cooker', False, [r'pressure cooker', r'instant pot', r'multi-?cooker'], []),
    ('Slow cooker', False, [r'slow cooker', r'crock-?pot'], []),
    ('Vacuum sealer', False, [r'vacuum seal(er|ing machine)', r'chamber vacuum'], []),
    ('Sous vide circulator', False, [r'sous vide (circulator|cooker|machine|device|stick|bath)', r'cook sous vide', r'immersion circulator', r'\bjoule\b(?!.*oven)', r'anova precision cooker'], []),
    ('Countertop oven', False, [r'countertop oven', r'toaster oven', r'smart oven', r'joule.*oven'], []),
    ('Air fryer', False, [r'air fryer'], ['Countertop oven']),
    ('Induction burner', False, [r'induction (burner|cooktop|hob|cooking system)', r'control ?°?freak'], []),
    ('Waffle maker', False, [r'waffle (iron|maker)', r'smart waffle'], []),
    ('Espresso machine', False, [r'espresso machine', r'barista (touch|express|pro)'], []),
    ('Pasta machine', False, [r'pasta (machine|roller|maker)'], []),
    ('Stand mixer', False, [r'stand mixer', r'bakery chef', r'kitchenaid (artisan|stand|professional|pro)', r'mixer fitted with', r'bowl of (an electric|a stand|the) mixer',
                            r'paddle attachment', r'dough hook', r'whisk attachment'], []),
    ('Hand mixer', False, [r'hand(-?held)? mixer', r'electric (hand )?mixer', r'electric beaters'], ['Stand mixer']),
    ('Food processor', False, [r'food processor', r'mini[- ]chopper'], []),
    ('Blender', False, [r'(?<!immersion )(?<!stick )(?<!hand )blender', r'vitamix', r'blendtec'], []),
    ('Spice grinder', False, [r'spice grinder', r'coffee grinder'], []),
    ('Mortar and pestle', False, [r'mortar and pestle', r'\bmortar\b'], []),
    ('Mandoline', False, [r'mandoline'], []),
    ('Kitchen torch', False, [r'(kitchen|blow|culinary) ?torch', r'\btorch\b'], []),
    ('Oven thermometer', False, [r'oven thermometer'], []),
    ('Candy thermometer', False, [r'(candy|deep[- ]fry|sugar) thermometer'], ['Instant-read thermometer']),
    ('Instant-read thermometer', False, [r'instant[- ]read', r'probe thermometer', r'meat thermometer', r'thermopop', r'thermapen',
                                        r'digital thermometer', r'\bthermometer'], []),
    ('Digital scale', False, [r'(kitchen|digital|food|drip|pocket|gram) scale', r'\bscale\b(?! (the|it|up|down|back))'], []),
    ('Piping bag', False, [r'piping bag', r'pastry bag', r'decorating bags?'], []),
    ('Piping tips', False, [r'piping tips?', r'pastry tips?', r'decorating (set|tips?)'], []),
    ('Portion scoop', False, [r'portion scoop', r'cookie scoop', r'disher'], []),
    ('Springform pan', False, [r'spring-?form'], []),
    ('Bundt pan', False, [r'bundt'], []),
    ('Tart pan', False, [r'tart (pan|tin)'], []),
    ('Ramekins', False, [r'ramekin'], []),
    ('Dutch oven', False, [r'dutch oven', r'cocotte'], []),
    ('Wok', False, [r'\bwok\b'], []),
    ('Cast-iron skillet', False, [r'cast[- ]iron (skillet|pan)'], ['Skillet']),
    ('Grill pan', False, [r'grill pan', r'griddle pan'], []),
    ('Pizza stone', False, [r'pizza (stone|steel)', r'baking steel'], []),
    ('Spider strainer', False, [r'spider'], []),
    ('Fine-mesh sieve', False, [r'fine[- ]mesh (sieve|strainer)', r'chinois'], []),
    ('Steamer basket', False, [r'steamer (basket|insert)', r'bamboo steamer'], []),
    ('Muffin tin', True, [r'muffin (tin|pan)', r'cupcake (tin|pan)'], []),
    ('Loaf pan', True, [r'loaf (pan|tin)'], []),
    ('Cake pan', True, [r'cake pans?\b', r'round pans?\b'], []),
    ('Pie plate', True, [r'pie (plate|dish|pan)'], []),
    ('Baking dish', True, [r'baking dish', r'casserole dish', r'gratin dish', r'roasting pan', r'(9|8|13)[- ]by[- ](9|13|8)'], []),
    ('Sheet pan', True, [r'sheet pans?', r'baking sheets?', r'sheet tray', r'jelly[- ]roll pan', r'half sheet', r'quarter sheet'], []),
    ('Wire rack', True, [r'(wire|cooling|baking/cooling|baking) racks?', r'roasting rack'], []),
    ('Skillet', True, [r'skillet', r'fry(ing)? pan', r'saut[eé] pan', r'sauteuse', r'nonstick pan'], []),
    ('Saucepan', True, [r'sauce ?pan', r'saucier', r'\bpot\b(?! roast)'], []),
    ('Stockpot', True, [r'stock ?pot', r'soup pot', r'large pot'], ['Dutch oven']),
    ('Mixing bowl', True, [r'mixing bowl'], []),
    ('Spatula', True, [r'spatula', r'spoon scraper'], []),
    ('Whisk', True, [r'\b(a|the|balloon|wire) whisk\b'], []),
    ('Box grater', True, [r'box grater', r'microplane', r'\bzester\b'], []),
    ('Rolling pin', True, [r'rolling pin'], []),
    ('Ruler', True, [r'\bruler'], []),
    ('Parchment paper', True, [r'parchment'], []),
    ('Zip-top bag', True, [r'zip-?(top|lock)', r'ziploc', r'freezer bag'], []),
    ('Storage container', True, [r'storage container', r'airtight container'], []),
]
BY_NAME = {c[0].lower(): c for c in CATALOG}
COMPILED = [(c[0], [re.compile(p, re.I) for p in c[2]]) for c in CATALOG]
SIZE = re.compile(r'\(?\b(\d+(?:[./]\d+)?(?:\s*(?:x|by)\s*\d+)?)\s*[- ]?\s*(inch|in\.|"|quart|qt|cup|gallon|liter|litre|l|cm)\b\.?\)?', re.I)


def tidy(name):
    """'Springform pan (9-inch) (optional)' -> ('Springform pan', '9-inch', True)"""
    text = re.sub(r'[™®©]', '', name or '').replace('°', '')
    optional = bool(re.search(r'\(optional\)|\boptional\b', text, re.I))
    text = re.sub(r'\(optional\)|\boptional\b', '', text, flags=re.I)
    note = ''
    m = SIZE.search(text)
    if m:
        unit = {'in.': 'inch', '"': 'inch', 'qt': 'quart', 'litre': 'liter', 'l': 'liter'}.get(m.group(2).lower(), m.group(2).lower())
        note = f'{m.group(1).replace(" ", "")}-{unit}'
        text = text[:m.start()] + ' ' + text[m.end():]
    m = re.match(r'\s*(1/4|1/2|quarter|half)[- ](?=sheet)', text, re.I)
    if m:
        note = {'1/4': 'quarter', '1/2': 'half'}.get(m.group(1).lower(), m.group(1).lower()) + '-sheet'
        text = text[m.end():]
    text = re.sub(r'^\s*the\s+', '', text, flags=re.I)
    text = re.sub(r'\(s\)', '', text)
    text = re.sub(r'\s*\(\s*\)\s*', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip(' -,.')
    text = text[:1].upper() + text[1:]
    return text, note, optional


def key(name):
    """compare names: 'Breville the Bakery Chef™ Stand Mixer' == 'Breville Bakery Chef Stand Mixer'"""
    text = re.sub(r'[™®©°]', '', name or '').lower()
    text = re.sub(r'\(s\)|\bthe\b|[^a-z0-9 ]', ' ', text)
    ws = [w[:-1] if len(w) > 3 and w.endswith('s') and not w.endswith('ss') else w for w in text.split()]
    return ' '.join(ws)


def kind_of(name):
    """the CATALOG kind a name is, or None ('Vitamix A3500 Ascent Series Blender' -> 'Blender')"""
    for kind, pats in COMPILED:
        if any(p.search(name) for p in pats):
            return kind
    return None


def general(space, kind):
    """the Equipment row for a CATALOG kind, created on first use (basics start owned)"""
    eq = Equipment.objects.filter(space=space, name__iexact=kind, general__isnull=True).first()
    if eq is None:
        eq = Equipment.objects.create(space=space, name=kind, owned=BY_NAME[kind.lower()][1])
    return eq


def find_or_create(space, name):
    """the Equipment a recipe's 'Breville Bakery Chef™ Stand Mixer' means, creating it under its kind if new"""
    k = key(name)
    for eq in Equipment.objects.filter(space=space):
        if key(eq.name) == k:
            return eq
    kind = kind_of(name)
    if kind and key(kind) == k:
        return general(space, kind)
    if kind:
        # a product of a known kind has a brand or model in it ("Joule Turbo Sous Vide", "Vitamix A3500 …");
        # otherwise it's just the kind in other words ("Silicone spatula", "Baking/Cooling rack")
        generic = general(space, kind)
        kind_words = set(key(kind).split())
        branded = [w for w in name.split()[1:] if re.match(r'[A-Z]', w) and key(w) not in kind_words]
        if not branded:
            return generic
        return Equipment.objects.create(space=space, name=name[:128], general=generic)
    return Equipment.objects.create(space=space, name=name[:128])


ALT = re.compile(r'^\s*,?\s*or\s+(?:(?:an?|the|large|small|medium|big|heavy|\d+-inch|\d+-quart)\s+)*$', re.I)


def detect(text):
    """[(kind, optional)] for the CATALOG kinds a recipe's text mentions, in order of first mention;
    a kind only ever offered as an alternative ("a blender or food processor") is optional"""
    hits = []  # (start, end, kind)
    for kind, pats in COMPILED:
        for p in pats:
            for m in p.finditer(text):
                if any(a < m.end() and m.start() < b for a, b, _ in hits):
                    continue  # already part of a more specific mention ("immersion blender")
                hits.append((m.start(), m.end(), kind))
    hits.sort()
    alt = set()
    for (a1, b1, k1), (a2, b2, k2) in zip(hits, hits[1:]):
        if k1 != k2 and ALT.match(text[b1:a2]):
            alt.update({(a1, k1), (a2, k2)})
    first, required = {}, set()
    for a, b, k in hits:
        first.setdefault(k, a)
        if (a, k) not in alt:
            required.add(k)
    return [(k, k not in required) for k, _ in sorted(first.items(), key=lambda x: x[1])]


def equipment_step(recipe):
    """the generated "Equipment" step of a ChefSteps clip or website import, if any"""
    for s in recipe.steps.all():
        if (s.name or '').strip().lower() == 'equipment' and not s.ingredients.exists():
            lines = [l.strip() for l in (s.instruction or '').splitlines() if l.strip()]
            if lines and all(l.startswith(('-', '*', '•')) for l in lines):
                return s, [l.lstrip('-*• ').strip() for l in lines]
    return None, []


def set_lines(recipe, items):
    """replace a recipe's equipment: items = [(Equipment, optional, note)]"""
    RecipeEquipment.objects.filter(recipe=recipe).delete()
    seen = set()
    for n, (eq, optional, note) in enumerate(items):
        if eq.id in seen:
            continue
        seen.add(eq.id)
        RecipeEquipment.objects.create(recipe=recipe, equipment=eq, optional=optional, note=note[:64], order=n, space=recipe.space)


def ensure(recipe):
    """give a recipe its equipment the first time it's looked at; True if anything changed"""
    if recipe.equipment_checked:
        return False
    step, listed = equipment_step(recipe)
    items = []
    if listed:
        for line in listed:
            name, note, optional = tidy(line)
            if name:
                items.append((find_or_create(recipe.space, name), optional, note))
        step.delete()
    else:
        text = ' '.join(f'{s.name or ""} {s.instruction or ""}' for s in recipe.steps.all())
        for kind, optional in detect(text):
            m = re.search(r'(\d+(?:[./]\d+)?)[- ]?(inch|quart)[- ]+(?:\w+[- ]){0,2}?' + re.escape(kind.split()[0].lower()[:6]), text, re.I)
            items.append((general(recipe.space, kind), optional, f'{m.group(1)}-{m.group(2).lower()}' if m else ''))
    set_lines(recipe, items)
    Recipe.objects.filter(pk=recipe.pk).update(equipment_checked=True)
    recipe.equipment_checked = True
    return True


def ensure_all(space):
    for r in Recipe.objects.filter(space=space, equipment_checked=False).prefetch_related('steps'):
        ensure(r)


class Kitchen:
    """which equipment the household has, and through what"""

    def __init__(self, space):
        self.all = {e.id: e for e in Equipment.objects.filter(space=space)}
        self.children = {}
        for e in self.all.values():
            if e.general_id:
                self.children.setdefault(e.general_id, []).append(e)
        self.by_kind = {e.name.lower(): e for e in self.all.values() if e.general_id is None}

    def owned_under(self, eq):
        """eq itself or something under it that's owned"""
        if eq.owned and not eq.hidden:
            return eq
        return next((c for c in self.children.get(eq.id, []) if c.owned and not c.hidden), None)

    def have(self, eq):
        """the owned Equipment that does the job, or None"""
        hit = self.owned_under(eq)
        if hit:
            return hit
        top = self.all.get(eq.general_id) if eq.general_id else None
        if top:
            hit = self.owned_under(top)
            if hit:
                return hit
        kind = (top or eq).name.lower()
        for other in (BY_NAME.get(kind) or (None, None, None, []))[3]:
            o = self.by_kind.get(other.lower())
            hit = o and self.owned_under(o)
            if hit:
                return hit
        return None
