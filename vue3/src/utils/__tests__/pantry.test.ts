import {strict as assert} from 'node:assert'
import {test} from 'node:test'
import {decimalSum, expiryDay, groupProducts, loadInventory, totalText} from '../pantry.ts'
import type {InventoryEntry} from '../../openapi'
const packages = {id: 1, name: 'package', pluralName: 'packages'}
const entry = (id: number, amount: number, extra = {}) => ({id, amount, food: {id: 1, name: 'Kraft Dinner Original'}, unit: packages, inventoryLocation: {id: 1, name: 'Pantry'}, code: id.toString(16).toUpperCase(), ...extra} as InventoryEntry)
const fixture = [entry(20, 2, {expires: new Date('2026-11-30')}), entry(22, 1, {expires: new Date('2027-01-14')}), entry(24, 2), entry(21, 4, {inventoryLocation: {id: 2, name: 'Basement'}}), entry(26, 1), entry(1, 1, {food: {id: 2, name: 'Nutella'}, unit: null})]

test('screenshot: two products, ten packages, all five labels and reconciled locations', () => {
    const products = groupProducts(fixture)
    assert.equal(products.length, 2)
    const kraft = products[0]!
    assert.equal(totalText(kraft.totals), '10 packages')
    assert.deepEqual(kraft.locations.map(l => [l.name, totalText(l.totals)]), [['Pantry', '6 packages'], ['Basement', '4 packages']])
    assert.deepEqual(kraft.batches.map(b => b.code), ['14', '16', '18', '15', '1A'])
    assert.equal(kraft.earliestExpiry, '2026-11-30')
    assert.equal(kraft.unknownExpiry, 3)
    assert.equal(totalText(products[1]!.totals), '1')
    assert.equal(products[1]!.earliestExpiry, null)
    assert.equal(fixture.length, 6)
})
test('units and identities stay separate, even with identical names', () => {
    const products = groupProducts([entry(1, 1), entry(2, 0.125, {unit: {id: 2, name: 'gram'}}), entry(3, 2, {unit: null}), entry(4, 3, {food: {id: 99, name: 'Kraft Dinner Original'}})])
    assert.equal(products.length, 2)
    assert.equal(totalText(products[0]!.totals), '1 package · 0.125 gram · 2')
})
test('unknown product identity does not merge records; missing locations reconcile', () => {
    const products = groupProducts([entry(1, 1, {food: null, inventoryLocation: null}), entry(2, 2, {food: null})])
    assert.equal(products.length, 2)
    assert.equal(products[0]!.locations[0]!.name, 'Unassigned')
})
test('decimal totals keep fractions without accumulation artifacts or two-place rounding', () => {
    assert.equal(decimalSum([0.1, 0.2, 0.0001]), '0.3001')
    assert.equal(decimalSum([1e-7, 2e-7]), '0.0000003')
    assert.equal(decimalSum(['0.1234567890123456', '0.0000000000000001']), '0.1234567890123457')
    assert.equal(decimalSum([-1, 0.25]), '-0.75')
    assert.equal(decimalSum([1, -1]), '0')
})
test('empty stock and old zero-quantity expiries do not affect on-hand expiry', () => {
    assert.deepEqual(groupProducts([]), [])
    const p = groupProducts([entry(1, 0, {expires: new Date('2000-01-01')}), entry(2, -1), entry(3, 0.5)])[0]!
    assert.equal(p.earliestExpiry, null)
    assert.equal(p.batches.length, 1)
    assert.equal(expiryDay(entry(1, 1, {expires: new Date('2026-11-30')})), '2026-11-30')
})
test('refresh projections reflect quantity edits and transfers without losing labels', () => {
    const updated = fixture.map(e => e.id === 20 ? {...e, amount: 0.5, inventoryLocation: {id: 2, name: 'Basement'}} as InventoryEntry : e)
    const p = groupProducts(updated)[0]!
    assert.equal(totalText(p.totals), '8.5 packages')
    assert.equal(p.batches.find(e => e.id === 20)!.code, '14')
    assert.equal(totalText(p.locations.find(l => l.id === 1)!.totals), '4 packages')
})
test('all pages are loaded before grouping; incomplete pages fail instead of showing partial stock', async () => {
    const loaded = await loadInventory(async page => ({results: fixture.slice((page - 1) * 2, page * 2), next: page < 3 ? 'next' : null, count: 6}))
    assert.equal(totalText(groupProducts(loaded)[0]!.totals), '10 packages')
    await assert.rejects(loadInventory(async () => ({results: fixture.slice(0, 2), next: null, count: 6})), /changed while loading/)
})
