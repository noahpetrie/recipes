// Isolated fixture preview: all API reads are local and writes are rejected. Never points at production.
import {createApp} from 'vue'
import {VApp, VMain} from 'vuetify/components'
import {createPinia} from 'pinia'
import {createI18n} from 'vue-i18n'
import {createRouter, createWebHashHistory} from 'vue-router'
import vuetify from '../src/vuetify'
import PantryScanPanel from '../src/components/dialogs/PantryScanPanel.vue'
import PantryPage from '../src/pages/PantryPage.vue'
import PantryActivityPage from '../src/pages/PantryActivityPage.vue'
import {ApiApi} from '../src/openapi'
import '../src/home-theme.css'
// Fixture pack photography from the official Kraft Heinz and Nutella product pages.
// These preview images do not assign sizes or images to production records.
const food = {id: 1, name: 'Kraft Dinner Original', barcodes: '068100000001', productImage: 'https://cdn.allotta.io/image/upload/v1761977451/dxp-images/brands/products/00068100904826-original-macaroni-and-cheese-dinner/marketing-view-color-front_content-hub-12290187_1dafa94080b194870d2a9ee809113393.png'}
const unit = {id: 1, name: 'package', pluralName: 'packages'}
const pantry = {id: 1, name: 'Pantry'}
const basement = {id: 2, name: 'Basement'}
const entry = (id, amount, location = pantry, expires = null) => ({id, amount, food, unit, inventoryLocation: location, code: id.toString(16).toUpperCase(), expires: expires ? new Date(expires) : null})
const scenario = new URLSearchParams(location.search).get('scenario')
const entries = [entry(20, 2, pantry, '2026-11-30'), entry(22, 1, pantry, '2027-01-14'), entry(24, 2), entry(21, 4, basement), entry(26, 1), {...entry(1, 1), food: {id: 2, name: 'Nutella', productImage: 'https://www.nutella.com/ca/sites/nutella20_ca/files/2021-02/375-gr-pet2x_v2_1502.jpg'}, unit: null}]
entries[0].subLocation = 'Top shelf'
// A deliberately synthetic household assortment for checking larger inventories.
if (scenario === 'large') {
    const names = ['Arborio rice', 'Baking powder', 'Baking soda', 'Balsamic vinegar', 'Black beans', 'Black pepper', 'Brown rice', 'Canned chickpeas', 'Canned corn', 'Canned salmon', 'Canned tomatoes', 'Canned tuna', 'Coconut milk', 'Couscous', 'Dijon mustard', 'Dried apricots', 'Dried lentils', 'Egg noodles', 'Flour', 'Granola', 'Green tea', 'Honey', 'Hot sauce', 'Instant coffee', 'Jasmine rice', 'Maple syrup', 'Oats', 'Olive oil', 'Pancake mix', 'Peanut butter', 'Penne pasta', 'Pinto beans', 'Popcorn kernels', 'Quinoa', 'Raisins', 'Red wine vinegar', 'Rolled oats', 'Sea salt', 'Sesame oil', 'Soy sauce', 'Spaghetti', 'Sugar', 'Sunflower seeds', 'Tomato paste', 'Vanilla extract', 'Vegetable broth', 'White beans', 'Whole wheat flour']
    names.forEach((name, i) => entries.push({...entry(100 + i, 1 + i % 5, i % 4 === 0 ? basement : pantry), food: {id: 100 + i, name}, unit: null}))
}

ApiApi.prototype.apiInventoryEntryList = async () => {
    if (scenario === 'error') throw new Error('Fixture inventory failure')
    return {results: scenario === 'empty' ? [] : entries, count: scenario === 'empty' ? 0 : entries.length, next: null}
}
ApiApi.prototype.apiFoodList = async () => ({results: [food, entries[5].food], count: 2})
ApiApi.prototype.apiInventoryLocationList = async () => ({results: [pantry, basement], count: 2})
ApiApi.prototype.apiUnitList = async () => ({results: [unit], count: 1})
ApiApi.prototype.apiInventoryLogList = async ({foodId} = {}) => ({results: foodId === 2 ? [] : events.map(event => ({id: event.id, bookingType: event.type, createdAt: new Date(event.created_at), entry: entries[0], oldAmount: 2, newAmount: 2 + event.delta, oldInventoryLocation: pantry, newInventoryLocation: pantry, note: event.note})), count: foodId === 2 ? 0 : events.length})
const events = ['undo', 'add', 'remove', 'count', 'undo'].map((type, i) => ({id: 50-i, type, food, entry_id: 20, delta: type === 'undo' || type === 'remove' ? -1 : 1, unit: {id: 1, name: 'package', plural_name: 'packages'}, old_location: pantry, new_location: pantry, note: type === 'undo' ? 'undid #44' : '', created_at: `2026-10-09T${15-i}:00:00Z`}))
window.fetch = async (input, init) => {
    if (init?.method && init.method !== 'GET') return new Response(JSON.stringify({error: 'Writes disabled in fixture preview'}), {status: 403})
    if (scenario === 'error') return new Response('{}', {status: 500})
    if (scenario === 'empty') return new Response(JSON.stringify({results: []}))
    const url = String(input)
    if (url.includes('stock/')) {
        const batches = entries.filter(e => e.food.id === 1).map(e => ({id: e.id, code: e.code, amount: e.amount, unit: {id: 1, name: 'package', plural_name: 'packages'}, location: e.inventoryLocation, expires: e.expires?.toISOString().slice(0, 10), sub_location: e.subLocation || ''}))
        return new Response(JSON.stringify({food: {...food, barcodes: [food.barcodes], preferred_unit: {id: 1, name: 'package', plural_name: 'packages'}}, stock: {batches, totals: [{amount: 10, unit: {id: 1, name: 'package', plural_name: 'packages'}}], locations: [{location: pantry, totals: [{amount: 6, unit: {id: 1, name: 'package', plural_name: 'packages'}}]}, {location: basement, totals: [{amount: 4, unit: {id: 1, name: 'package', plural_name: 'packages'}}]}], mixed_units: false, expired: 0}}))
    }
    if (url.includes('counts/') && scenario === 'large') return new Response(JSON.stringify({results: []}))
    if (url.includes('counts/')) return new Response(JSON.stringify({results: [{id: 1, location: pantry, counted: 1, status: 'open'}]}))
    if (url.includes('activity/')) return new Response(JSON.stringify({results: events}))
    return new Response('{}', {status: 404})
}
const router = createRouter({history: createWebHashHistory(), routes: [{path: '/', name: 'PantryPage', component: PantryPage}, {path: '/activity', name: 'PantryActivityPage', component: PantryActivityPage}, {path: '/count/:id', name: 'StockCountPage', component: {template: '<p>Fixture count route</p>'}}]})
const app = createApp({components: {PantryScanPanel, VApp, VMain}, template: '<v-app><v-main><router-view /></v-main><PantryScanPanel /></v-app>'})
app.use(createPinia()).use(vuetify).use(createI18n({legacy: false, locale: 'en', missingWarn: false, fallbackWarn: false, messages: {en: {Pantry: 'Pantry', Food: 'Food', InventoryLocation: 'Inventory location'}}})).use(router).mount('#app')
