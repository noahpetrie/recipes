"""
home fork: the pantry stock layer behind barcode scanning.

Scanning *finds* things (lookup); stock only changes through an explicit adjustment:

  add     amount is added (to a matching batch, or as a new batch)
  remove  amount is taken from one batch, never below zero
  set     a physical count: the location's recorded amount becomes the counted amount
  move    amount moves to another location (the batch is split if only part of it moves)
  edit    expiry / shelf / label / note of one batch; the amount is untouched
  undo    reverses one earlier booking if nothing has changed since

Every write takes a client request id (repeated ids return the first answer, so a scanner
double-fire or a retried click can't book twice) and, where a total is replaced, the amount the
client saw (a stale screen gets a 409 instead of overwriting someone else's change). Every stock
change is written to InventoryLog with who did it and an optional reason.

Stock counts are drafts: lines record what was on file when first counted and what was counted,
and nothing changes until the reviewed lines are applied.
"""
import datetime
import re
from collections import OrderedDict
from decimal import Decimal, InvalidOperation

from django.core.cache import caches
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from cookbook.helper.permission_helper import CustomIsUser, CustomTokenHasReadWriteScope
from cookbook.models import Food, InventoryEntry, InventoryLocation, InventoryLog, StockCount, StockCountLine, Unit

PERMS = [CustomIsUser & CustomTokenHasReadWriteScope]
IDEMPOTENCY_SECONDS = 15 * 60
REASONS = {'consumed', 'discarded', 'spoiled', 'donated', 'other'}


# ---- serialising ------------------------------------------------------------------------------

def num(d):
    """Decimal -> float without the 16 decimal places"""
    return float(round(Decimal(d or 0), 4))


def unit_json(u):
    return {'id': u.id, 'name': u.name, 'plural_name': u.plural_name or u.name} if u else None


def location_json(loc):
    return {'id': loc.id, 'name': loc.name, 'is_freezer': loc.is_freezer} if loc else None


def entry_json(e):
    return {
        'id': e.id, 'code': e.code, 'amount': num(e.amount), 'unit': unit_json(e.unit),
        'location': location_json(e.inventory_location), 'sub_location': e.sub_location or '',
        'expires': e.expires.isoformat() if e.expires else None, 'note': e.note or '',
        'counted_at': e.counted_at.isoformat() if e.counted_at else None,
        'updated_at': e.updated_at.isoformat(), 'food': {'id': e.food_id, 'name': e.food.name},
    }


def food_json(f):
    return {'id': f.id, 'name': f.name, 'plural_name': f.plural_name or '', 'barcodes': [b for b in (f.barcodes or '').split() if b],
            'preferred_unit': unit_json(f.preferred_unit), 'product': f.product_info or None}


def stock_json(space, food):
    """
    What's on hand for a food: totals per unit (never adding packages to grams), the same per
    location, and every batch. Batches are sorted soonest expiry first.
    """
    entries = list(InventoryEntry.objects.filter(space=space, food=food, amount__gt=0)
                   .select_related('inventory_location', 'unit', 'food')
                   .order_by('inventory_location__name', 'expires', 'id'))
    totals = OrderedDict()
    by_location = OrderedDict()
    for e in entries:
        key = e.unit_id or 0
        totals.setdefault(key, {'unit': unit_json(e.unit), 'amount': Decimal(0)})['amount'] += e.amount
        loc = by_location.setdefault(e.inventory_location_id, {'location': location_json(e.inventory_location), 'totals': OrderedDict()})
        loc['totals'].setdefault(key, {'unit': unit_json(e.unit), 'amount': Decimal(0)})['amount'] += e.amount
    expiries = sorted(e.expires for e in entries if e.expires)
    today = timezone.localdate()
    return {
        'totals': [{'unit': t['unit'], 'amount': num(t['amount'])} for t in totals.values()],
        'locations': [{'location': l['location'], 'totals': [{'unit': t['unit'], 'amount': num(t['amount'])} for t in l['totals'].values()]}
                      for l in by_location.values()],
        'batches': sorted([entry_json(e) for e in entries], key=lambda b: (b['expires'] or '9999', b['id'])),
        'earliest_expiry': expiries[0].isoformat() if expiries else None,
        'expired': sum(1 for d in expiries if d < today),
        'mixed_units': len(totals) > 1,
    }


def log_json(l):
    e = l.entry
    return {
        'id': l.id, 'type': l.booking_type, 'created_at': l.created_at.isoformat(),
        'by': (l.created_by.get_full_name() or l.created_by.username) if l.created_by else None,
        'food': {'id': e.food_id, 'name': e.food.name}, 'entry_id': e.id, 'code': e.code, 'unit': unit_json(e.unit),
        'old_amount': num(l.old_amount), 'new_amount': num(l.new_amount), 'delta': num(l.new_amount - l.old_amount),
        'old_location': location_json(l.old_inventory_location), 'new_location': location_json(l.new_inventory_location),
        'note': l.note or '',
    }


# ---- helpers ----------------------------------------------------------------------------------

def dec(value, field, allow_zero=False):
    try:
        d = Decimal(str(value))
    except (InvalidOperation, TypeError):
        raise ValueError(f'{field} must be a number')
    if d < 0 or (d == 0 and not allow_zero):
        raise ValueError(f'{field} must be {"zero or more" if allow_zero else "more than zero"}')
    return d


def date_or_none(value):
    if value in (None, '', 'null'):
        return None
    try:
        return datetime.date.fromisoformat(str(value)[:10])
    except ValueError:
        raise ValueError('Expiry must be a date.')


def get_obj(model, space, pk, what):
    if pk in (None, '', 'null'):
        return None
    obj = model.objects.filter(space=space, pk=pk).first()
    if obj is None:
        raise ValueError(f'{what} not found')
    return obj


def book(request, entry, kind, old_amount, old_location, note=''):
    return InventoryLog.objects.create(
        space=request.space, entry=entry, booking_type=kind, old_amount=old_amount, new_amount=entry.amount,
        old_inventory_location=old_location, new_inventory_location=entry.inventory_location,
        note=(note or '')[:256], created_by=request.user)


def new_entry(request, food, unit, amount, location, sub_location='', expires=None, code=None, note=''):
    e = InventoryEntry.objects.create(
        space=request.space, created_by=request.user, food=food, unit=unit, amount=amount,
        inventory_location=location, sub_location=sub_location or '', expires=expires or None,
        code=(code or None), note=note or None)
    if not e.code:
        e.code = hex(e.id)[2:].upper()
        e.save(update_fields=['code'])
    return e


def label_taken(space, code, exclude_id=None):
    qs = InventoryEntry.objects.filter(space=space, code__iexact=code)
    if exclude_id:
        qs = qs.exclude(pk=exclude_id)
    return qs.exists()


def qty(amount, unit):
    a = num(amount)
    a = int(a) if a == int(a) else a
    if unit is None:
        return f'{a}'
    return f'{a} {unit.name if a == 1 else (unit.plural_name or unit.name)}'


# ---- lookup -----------------------------------------------------------------------------------

@api_view(['GET'])
@permission_classes(PERMS)
def lookup(request):
    """what a scanned code is: a pantry label, a known product, or an unknown barcode (looked up online)"""
    from cookbook.views.api import _lookup_product
    raw = request.query_params.get('code', '')
    code = re.sub(r'[^0-9A-Za-z]', '', raw)[:32]
    if not code:
        return Response({'error': 'Scan or type a barcode.'}, status=400)

    label = InventoryEntry.objects.filter(space=request.space, code__iexact=code).select_related('food', 'unit', 'inventory_location').first() \
        if len(code) <= 16 else None
    food = Food.objects.filter(space=request.space, barcodes__regex=rf'(^|\s){code}(\s|$)').first() if code.isdigit() else None

    if label and food and label.food_id != food.id:
        # the same characters are both a label and a retail barcode: let the person choose
        return Response({'code': code, 'kind': 'ambiguous', 'label_entry': entry_json(label), 'food': food_json(food),
                         'stock': stock_json(request.space, food)})
    if label:
        return Response({'code': code, 'kind': 'label', 'label_entry': entry_json(label), 'food': food_json(label.food),
                         'stock': stock_json(request.space, label.food)})

    product = None
    if code.isdigit() and len(code) >= 8 and not (food and food.product_info):
        product = _lookup_product(code)
        if food and product:
            food.product_info = product
            food.save(update_fields=['product_info'])
    if food:
        return Response({'code': code, 'kind': 'product', 'food': food_json(food), 'stock': stock_json(request.space, food)})
    if not (code.isdigit() and len(code) >= 6):
        return Response({'code': code, 'kind': 'invalid', 'error': f'"{raw}" isn\'t a product barcode or a pantry label.'})
    return Response({'code': code, 'kind': 'unknown', 'product': product})


@api_view(['GET'])
@permission_classes(PERMS)
def stock(request):
    try:
        food = get_obj(Food, request.space, request.query_params.get('food_id'), 'Food')
    except ValueError as e:
        return Response({'error': str(e)}, status=404)
    if food is None:
        return Response({'error': 'food_id required'}, status=400)
    return Response({'food': food_json(food), 'stock': stock_json(request.space, food)})


@api_view(['POST'])
@permission_classes(PERMS)
def link_barcode(request):
    """remember a retail barcode on an existing food, or on a new food"""
    code = re.sub(r'[^0-9]', '', str(request.data.get('code', '')))
    product = request.data.get('product') or None
    if not code:
        return Response({'error': 'code required'}, status=400)
    with transaction.atomic():
        other = Food.objects.filter(space=request.space, barcodes__regex=rf'(^|\s){code}(\s|$)').first()
        if request.data.get('food_id'):
            food = Food.objects.filter(space=request.space, pk=request.data['food_id']).first()
            if food is None:
                return Response({'error': 'Food not found'}, status=404)
        else:
            name = (request.data.get('name') or '').strip()[:128]
            if not name:
                return Response({'error': 'Give the new food a name.'}, status=400)
            food = Food.objects.filter(space=request.space, name__iexact=name).first() or Food.objects.create(space=request.space, name=name)
        if other and other.id != food.id:
            # a barcode means one product: move it from the food it was on
            other.barcodes = ' '.join(b for b in other.barcodes.split() if b != code)
            other.save(update_fields=['barcodes'])
        codes = [b for b in (food.barcodes or '').split() if b]
        if code not in codes:
            codes.append(code)
        food.barcodes = ' '.join(codes)
        if product and not food.product_info:
            food.product_info = {k: product.get(k, '') for k in ('name', 'brand', 'quantity', 'image', 'source')}
        food.save()
    return Response({'food': food_json(food), 'stock': stock_json(request.space, food)})


# ---- adjustments ------------------------------------------------------------------------------

@api_view(['POST'])
@permission_classes(PERMS)
def adjust(request):
    d = request.data
    rid = str(d.get('request_id') or '')[:64]
    cache = caches['default']
    key = f'home_pantry_req_{request.space.id}_{request.user.id}_{rid}'
    if rid and (hit := cache.get(key)):
        return Response(hit['body'], status=hit['status'])
    try:
        with transaction.atomic():
            body, status = _adjust(request, d)
    except ValueError as e:
        body, status = {'error': str(e)}, 400
    if rid and status < 500:
        cache.set(key, {'body': body, 'status': status}, IDEMPOTENCY_SECONDS)
    return Response(body, status=status)


def _adjust(request, d):
    action = d.get('action')
    space = request.space

    if action == 'add':
        food = get_obj(Food, space, d.get('food_id'), 'Food')
        if food is None:
            raise ValueError('Choose a food.')
        unit = get_obj(Unit, space, d.get('unit_id'), 'Unit')
        amount = dec(d.get('amount'), 'Amount')
        location = get_obj(InventoryLocation, space, d.get('location_id'), 'Location')
        if location is None:
            raise ValueError('Choose where it goes.')
        sub = (d.get('sub_location') or '').strip()[:64]
        expires = date_or_none(d.get('expires'))
        code = (d.get('code') or '').strip()[:16] or None
        if code and label_taken(space, code):
            raise ValueError(f'Label #{code} is already on another item.')
        if d.get('remember_unit') and food.preferred_unit_id != (unit.id if unit else None):
            food.preferred_unit = unit
            food.save(update_fields=['preferred_unit'])

        target = None
        if d.get('entry_id'):
            target = InventoryEntry.objects.select_for_update(of=('self',)).filter(space=space, food=food, pk=d['entry_id']).first()
            if target is None:
                raise ValueError('That batch no longer exists.')
            if target.unit_id != (unit.id if unit else None):
                raise ValueError('That batch is counted in a different unit.')
        elif not code and not d.get('new_batch'):
            # same food, unit, place and expiry: one batch (a custom label always means its own item)
            same_shelf = Q(sub_location=sub) | (Q(sub_location__isnull=True) if not sub else Q(pk__in=[]))
            target = InventoryEntry.objects.select_for_update(of=('self',)).filter(
                same_shelf, space=space, food=food, unit=unit, inventory_location=location, expires=expires, amount__gt=0
            ).order_by('id').first()
        if target:
            old, old_loc = target.amount, target.inventory_location
            target.amount += amount
            target.save()
            log = book(request, target, InventoryLog.B_ADD, old, old_loc)
            entry = target
        else:
            entry = new_entry(request, food, unit, amount, location, sub, expires, code, d.get('note'))
            log = book(request, entry, InventoryLog.B_ADD, Decimal(0), location)
        msg = f'Added {qty(amount, unit)} of {food.name} to {location.name}'

    elif action == 'remove':
        entry = InventoryEntry.objects.select_for_update(of=('self',)).filter(space=space, pk=d.get('entry_id')).select_related('food', 'unit').first()
        if entry is None:
            raise ValueError('Choose which batch to take from.')
        amount = dec(d.get('amount'), 'Amount')
        if amount > entry.amount:
            raise ValueError(f'Only {qty(entry.amount, entry.unit)} in that batch.')
        reason = (d.get('reason') or '').lower()
        reason = reason if reason in REASONS else ''
        old = entry.amount
        entry.amount -= amount
        entry.save()
        log = book(request, entry, InventoryLog.B_REMOVE, old, entry.inventory_location, ' '.join(x for x in [reason, d.get('note') or ''] if x))
        msg = f'Removed {qty(amount, entry.unit)} of {entry.food.name}'
        food = entry.food

    elif action == 'set':
        food = get_obj(Food, space, d.get('food_id'), 'Food')
        location = get_obj(InventoryLocation, space, d.get('location_id'), 'Location')
        if food is None or location is None:
            raise ValueError('Choose the food and the location you counted.')
        unit = get_obj(Unit, space, d.get('unit_id'), 'Unit')
        counted = dec(d.get('counted'), 'Count', allow_zero=True)
        result = apply_count(request, food, unit, location, counted, d.get('expected'), d.get('entry_id'), d.get('note') or 'count')
        if 'conflict' in result or 'needs_batch' in result:
            return {**result, 'stock': stock_json(space, food)}, 409
        log, entry, msg = result['log'], result['entry'], result['message']

    elif action == 'move':
        entry = InventoryEntry.objects.select_for_update(of=('self',)).filter(space=space, pk=d.get('entry_id')).select_related('food', 'unit').first()
        if entry is None:
            raise ValueError('Choose which batch to move.')
        to = get_obj(InventoryLocation, space, d.get('to_location_id'), 'Location')
        if to is None:
            raise ValueError('Choose where it goes.')
        amount = dec(d.get('amount', entry.amount), 'Amount')
        if amount > entry.amount:
            raise ValueError(f'Only {qty(entry.amount, entry.unit)} in that batch.')
        to_sub = (d.get('to_sub_location') or '').strip()[:64]
        old, old_loc = entry.amount, entry.inventory_location
        if amount == entry.amount:
            entry.inventory_location, entry.sub_location = to, to_sub
            entry.save()
            log = book(request, entry, InventoryLog.B_MOVE, old, old_loc)
        else:
            entry.amount -= amount
            entry.save()
            log = book(request, entry, InventoryLog.B_MOVE, old, old_loc, f'{qty(amount, entry.unit)} to {to.name}')
            moved = new_entry(request, entry.food, entry.unit, amount, to, to_sub, entry.expires, None, entry.note)
            book(request, moved, InventoryLog.B_MOVE, Decimal(0), old_loc, f'from #{entry.code}')
            entry = moved
        msg = f'Moved {qty(amount, entry.unit)} of {entry.food.name} from {old_loc.name} to {to.name}'
        food = entry.food

    elif action == 'edit':
        entry = InventoryEntry.objects.select_for_update(of=('self',)).filter(space=space, pk=d.get('entry_id')).select_related('food').first()
        if entry is None:
            raise ValueError('That batch no longer exists.')
        changed = []
        if 'expires' in d and date_or_none(d['expires']) != entry.expires:
            entry.expires = date_or_none(d['expires'])
            changed.append('expiry')
        if 'sub_location' in d and (d['sub_location'] or '') != (entry.sub_location or ''):
            entry.sub_location = (d['sub_location'] or '')[:64]
            changed.append('shelf')
        if 'note' in d and (d['note'] or '') != (entry.note or ''):
            entry.note = (d['note'] or '')[:256] or None
            changed.append('note')
        if 'code' in d and d['code'] and d['code'] != entry.code:
            code = str(d['code']).strip()[:16]
            if label_taken(space, code, exclude_id=entry.id):
                raise ValueError(f'Label #{code} is already on another item.')
            entry.code = code
            changed.append('label')
        if not changed:
            return {'message': 'Nothing changed', 'stock': stock_json(space, entry.food), 'entry': entry_json(entry), 'log_id': None}, 200
        entry.save()
        log = book(request, entry, InventoryLog.B_EDIT, entry.amount, entry.inventory_location, 'changed ' + ', '.join(changed))
        msg = f'Updated {", ".join(changed)} of {entry.food.name} #{entry.code}'
        food = entry.food

    elif action == 'undo':
        log0 = InventoryLog.objects.select_for_update(of=('self',)).filter(space=space, pk=d.get('log_id')).select_related('entry', 'entry__food', 'entry__unit').first()
        if log0 is None or log0.booking_type == InventoryLog.B_UNDO:
            raise ValueError('Nothing to undo.')
        entry = InventoryEntry.objects.select_for_update(of=('self',)).get(pk=log0.entry_id)
        if entry.amount != log0.new_amount or entry.inventory_location_id != log0.new_inventory_location_id:
            return {'error': f'{entry.food.name} has changed since, so it can\'t be undone automatically.', 'conflict': True,
                    'stock': stock_json(space, entry.food)}, 409
        old, old_loc = entry.amount, entry.inventory_location
        entry.amount, entry.inventory_location = log0.old_amount, log0.old_inventory_location
        entry.save()
        log = book(request, entry, InventoryLog.B_UNDO, old, old_loc, f'undid #{log0.id}')
        msg = f'Undone — {entry.food.name} batch #{entry.code} is back to {qty(entry.amount, entry.unit)} in {entry.inventory_location.name}'
        food = entry.food

    else:
        raise ValueError('Unknown action.')

    return {'message': msg, 'log_id': log.id if log else None, 'entry': entry_json(entry) if entry else None,
            'food': food_json(food), 'stock': stock_json(space, food)}, 200


def apply_count(request, food, unit, location, counted, expected=None, entry_id=None, note='count', count_id=None):
    """
    Make what's recorded at a location equal what was counted. Returns {'log','entry','message'},
    {'conflict': ...} when the recorded amount isn't what the counter saw, or {'needs_batch': [...]}
    when several batches could absorb the difference and none was chosen.
    """
    space = request.space
    entries = list(InventoryEntry.objects.select_for_update(of=('self',)).filter(space=space, food=food, unit=unit, inventory_location=location, amount__gt=0)
                   .select_related('unit').order_by('expires', 'id'))
    recorded = sum((e.amount for e in entries), Decimal(0))
    if expected is not None and Decimal(str(expected)) != recorded:
        return {'conflict': True, 'recorded': num(recorded),
                'error': f'{food.name} in {location.name} changed from {qty(Decimal(str(expected)), unit)} to {qty(recorded, unit)} while you were counting.'}
    now = timezone.now()
    tag = f'{note} #{count_id}' if count_id else note
    if counted == recorded:
        for e in entries:
            e.counted_at = now
            e.save(update_fields=['counted_at'])
        return {'log': None, 'entry': entries[0] if entries else None, 'message': f'{food.name}: {qty(counted, unit)} in {location.name} — matches'}
    delta = counted - recorded
    target = None
    if entry_id not in (None, '', 'new'):
        target = next((e for e in entries if str(e.id) == str(entry_id)), None)
        if target is None:
            raise ValueError('That batch isn\'t in this location.')
    elif entry_id == 'new' and delta > 0:
        target = None
    elif len(entries) == 1:
        target = entries[0]
    elif len(entries) > 1:
        return {'needs_batch': [entry_json(e) for e in entries],
                'error': f'{food.name} has {len(entries)} batches in {location.name}. Choose which one changed.'}
    if target is None:
        if delta < 0:
            raise ValueError('Nothing recorded to reduce.')
        target = new_entry(request, food, unit, delta, location)
        target.counted_at = now
        target.save(update_fields=['counted_at'])
        log = book(request, target, InventoryLog.B_COUNT, Decimal(0), location, tag)
    else:
        if target.amount + delta < 0:
            return {'needs_batch': [entry_json(e) for e in entries],
                    'error': f'Batch #{target.code} only has {qty(target.amount, unit)}. Choose another batch, or count it batch by batch.'}
        old = target.amount
        target.amount += delta
        target.counted_at = now
        target.save()
        log = book(request, target, InventoryLog.B_COUNT, old, location, tag)
    sign = '+' if delta > 0 else '−'
    return {'log': log, 'entry': target,
            'message': f'Set {food.name} in {location.name} to {qty(counted, unit)} ({sign}{qty(abs(delta), unit)})'}


# ---- history ----------------------------------------------------------------------------------

@api_view(['GET'])
@permission_classes(PERMS)
def activity(request):
    qs = InventoryLog.objects.filter(space=request.space).select_related(
        'entry', 'entry__food', 'entry__unit', 'old_inventory_location', 'new_inventory_location', 'created_by').order_by('-created_at', '-id')
    if food_id := request.query_params.get('food_id'):
        qs = qs.filter(entry__food_id=food_id)
    if entry_id := request.query_params.get('entry_id'):
        qs = qs.filter(entry_id=entry_id)
    limit = min(int(request.query_params.get('limit', 50) or 50), 200)
    return Response({'results': [log_json(l) for l in qs[:limit]]})


# ---- stock counts -----------------------------------------------------------------------------

def recorded_at(space, food, unit, location):
    return sum((e.amount for e in InventoryEntry.objects.filter(space=space, food=food, unit=unit, inventory_location=location, amount__gt=0)), Decimal(0))


def count_json(space, c, full=False):
    lines = list(c.lines.select_related('food', 'unit').all())
    out = {
        'id': c.id, 'status': c.status, 'location': location_json(c.inventory_location), 'sub_location': c.sub_location,
        'created_at': c.created_at.isoformat(), 'finished_at': c.finished_at.isoformat() if c.finished_at else None,
        'counted': len(lines), 'discrepancies': sum(1 for l in lines if l.counted != l.recorded),
    }
    if not full:
        return out
    rows = []
    for l in lines:
        now = recorded_at(space, l.food, l.unit, c.inventory_location)
        batches = InventoryEntry.objects.filter(space=space, food=l.food, unit=l.unit, inventory_location=c.inventory_location, amount__gt=0).count()
        status = 'applied' if l.applied else ('matches' if l.counted == l.recorded else 'discrepancy')
        if not l.applied and now != l.recorded:
            status = 'changed'
        elif not l.applied and l.counted != l.recorded and batches > 1:
            status = 'needs_batch'
        rows.append({'id': l.id, 'food': {'id': l.food_id, 'name': l.food.name}, 'unit': unit_json(l.unit),
                     'recorded': num(l.recorded), 'recorded_now': num(now), 'counted': num(l.counted),
                     'delta': num(l.counted - l.recorded), 'status': status, 'applied': l.applied, 'result': l.result,
                     'batches': [entry_json(e) for e in InventoryEntry.objects.filter(
                         space=space, food=l.food, unit=l.unit, inventory_location=c.inventory_location, amount__gt=0).select_related('food', 'unit', 'inventory_location')]})
    counted_keys = {(l.food_id, l.unit_id) for l in lines}
    uncounted = OrderedDict()
    for e in InventoryEntry.objects.filter(space=space, inventory_location=c.inventory_location, amount__gt=0).select_related('food', 'unit').order_by('food__name'):
        if (e.food_id, e.unit_id) in counted_keys:
            continue
        u = uncounted.setdefault((e.food_id, e.unit_id), {'food': {'id': e.food_id, 'name': e.food.name}, 'unit': unit_json(e.unit), 'recorded': Decimal(0)})
        u['recorded'] += e.amount
    out['lines'] = rows
    out['not_counted'] = [{**u, 'recorded': num(u['recorded'])} for u in uncounted.values()]
    return out


@api_view(['GET', 'POST'])
@permission_classes(PERMS)
def counts(request):
    if request.method == 'POST':
        location = InventoryLocation.objects.filter(space=request.space, pk=request.data.get('location_id')).first()
        if location is None:
            return Response({'error': 'Choose the location you\'re counting.'}, status=400)
        existing = StockCount.objects.filter(space=request.space, inventory_location=location, status=StockCount.S_OPEN).first()
        c = existing or StockCount.objects.create(space=request.space, created_by=request.user, inventory_location=location,
                                                  sub_location=(request.data.get('sub_location') or '')[:64])
        return Response(count_json(request.space, c, full=True), status=200 if existing else 201)
    qs = StockCount.objects.filter(space=request.space).select_related('inventory_location')
    if request.query_params.get('status'):
        qs = qs.filter(status=request.query_params['status'])
    return Response({'results': [count_json(request.space, c) for c in qs[:20]]})


@api_view(['GET'])
@permission_classes(PERMS)
def count_detail(request, pk):
    c = StockCount.objects.filter(space=request.space, pk=pk).select_related('inventory_location').first()
    if c is None:
        return Response({'error': 'Count not found'}, status=404)
    return Response(count_json(request.space, c, full=True))


@api_view(['POST', 'DELETE'])
@permission_classes(PERMS)
def count_line(request, pk):
    """record (or change) what was counted for one product; nothing in the pantry changes yet"""
    c = StockCount.objects.filter(space=request.space, pk=pk, status=StockCount.S_OPEN).first()
    if c is None:
        return Response({'error': 'This count is finished.'}, status=400)
    d = request.data
    if request.method == 'DELETE':
        StockCountLine.objects.filter(space=request.space, count=c, pk=d.get('line_id'), applied=False).delete()
        return Response(count_json(request.space, c, full=True))
    try:
        food = get_obj(Food, request.space, d.get('food_id'), 'Food')
        unit = get_obj(Unit, request.space, d.get('unit_id'), 'Unit')
        if food is None:
            raise ValueError('Choose a food.')
        line = StockCountLine.objects.filter(space=request.space, count=c, food=food, unit=unit, applied=False).first()
        if d.get('increment'):
            step = dec(d.get('increment'), 'Increment')
            counted = (line.counted if line else Decimal(0)) + step
        else:
            counted = dec(d.get('counted'), 'Count', allow_zero=True)
    except ValueError as e:
        return Response({'error': str(e)}, status=400)
    if line is None:
        line = StockCountLine(space=request.space, count=c, food=food, unit=unit,
                              recorded=recorded_at(request.space, food, unit, c.inventory_location))
    line.counted = counted
    line.save()
    return Response({'line_id': line.id, 'recorded': num(line.recorded), 'counted': num(line.counted),
                     'message': f'Counted {qty(counted, unit)} of {food.name} (on file: {qty(line.recorded, unit)})',
                     'count': count_json(request.space, c, full=True)})


@api_view(['POST'])
@permission_classes(PERMS)
def count_apply(request, pk):
    """apply the chosen lines; each one is checked against what's on file now"""
    c = StockCount.objects.filter(space=request.space, pk=pk, status=StockCount.S_OPEN).select_related('inventory_location').first()
    if c is None:
        return Response({'error': 'This count is finished.'}, status=400)
    ids = {int(i) for i in request.data.get('line_ids', [])}
    batches = {str(k): v for k, v in (request.data.get('batches') or {}).items()}
    results = []
    for line in c.lines.select_related('food', 'unit').filter(applied=False):
        if line.id not in ids:
            continue
        try:
            with transaction.atomic():
                r = apply_count(request, line.food, line.unit, c.inventory_location, line.counted, line.recorded,
                                batches.get(str(line.id)), 'count', c.id)
                if 'conflict' in r or 'needs_batch' in r:
                    results.append({'line_id': line.id, 'ok': False, 'error': r['error']})
                    continue
                line.applied = True
                line.result = r['message']
                line.save()
                results.append({'line_id': line.id, 'ok': True, 'message': r['message']})
        except ValueError as e:
            results.append({'line_id': line.id, 'ok': False, 'error': str(e)})
    if request.data.get('finish') and not c.lines.filter(applied=False).exists():
        c.status = StockCount.S_APPLIED
        c.finished_at = timezone.now()
        c.save()
    return Response({'results': results, 'count': count_json(request.space, c, full=True)})


@api_view(['POST'])
@permission_classes(PERMS)
def count_finish(request, pk):
    """close a count: 'discard' throws the draft away, otherwise unapplied lines are left as they are"""
    c = StockCount.objects.filter(space=request.space, pk=pk, status=StockCount.S_OPEN).first()
    if c is None:
        return Response({'error': 'This count is finished.'}, status=400)
    c.status = StockCount.S_DISCARDED if request.data.get('discard') else StockCount.S_APPLIED
    c.finished_at = timezone.now()
    c.save()
    return Response(count_json(request.space, c))
