<template>
    <v-container class="groceries-page">
        <header class="page-header">
            <div class="d-flex align-center ga-4">
                <v-avatar rounded color="primary" variant="tonal" size="48"><v-icon icon="fa-solid fa-basket-shopping" /></v-avatar>
                <div>
                    <h1 class="text-h4 font-weight-bold">Add groceries</h1>
                    <p class="text-body-2 text-medium-emphasis mt-1">Put a whole shop away at once. Where things go and when they expire are filled in for you.</p>
                </div>
            </div>
        </header>

        <v-alert v-if="error" type="error" variant="tonal" class="mb-4" closable @click:close="error = ''">{{ error }}</v-alert>
        <v-alert v-if="done" type="success" variant="tonal" class="mb-4" closable @click:close="done = 0">
            Added {{ done }} {{ done == 1 ? 'item' : 'items' }} to the pantry.
            <template #append>
                <div class="d-flex ga-2 flex-wrap">
                    <v-btn variant="text" size="small" :to="{name: 'PantryPage'}">See pantry</v-btn>
                    <v-btn variant="text" size="small" :to="{name: 'CookNowPage'}">Ready to Cook</v-btn>
                </div>
            </template>
        </v-alert>

        <v-row>
            <v-col cols="12" md="7">
                <v-btn-toggle v-model="mode" mandatory density="comfortable" variant="outlined" divided class="mb-4">
                    <v-btn value="pick" prepend-icon="fa-solid fa-list-check">Pick items</v-btn>
                    <v-btn value="paste" prepend-icon="fa-solid fa-receipt">Paste a receipt</v-btn>
                </v-btn-toggle>

                <template v-if="mode == 'pick'">
                    <v-text-field v-model="search" prepend-inner-icon="$search" label="Search, or type something new" hide-details clearable density="compact" class="mb-3"
                                  @keydown.enter="addNewFromSearch" />
                    <v-progress-linear v-if="!data" indeterminate />
                    <div v-else>
                        <div v-if="q && !exact" class="pick-row new-row" role="button" tabindex="0" @click="addNewFromSearch" @keydown.enter="addNewFromSearch">
                            <v-icon icon="$create" size="small" color="primary" />
                            <span class="flex-grow-1">Add “{{ search.trim() }}” as a new item</span>
                        </div>
                        <template v-for="group in groups" :key="group.aisle">
                            <h3 class="aisle">{{ group.aisle }}</h3>
                            <div v-for="f in group.foods" :key="f.id" class="pick-row" :class="{picked: inCart(f.id)}" role="checkbox" :aria-checked="inCart(f.id)" tabindex="0"
                                 @click="toggle(f)" @keydown.enter.prevent="toggle(f)" @keydown.space.prevent="toggle(f)">
                                <v-checkbox-btn :model-value="inCart(f.id)" tabindex="-1" density="compact" class="flex-none" :aria-label="f.name" @click.stop="toggle(f)" />
                                <span class="flex-grow-1 name">{{ f.name }}</span>
                                <span v-if="f.in_stock" class="badge good">In pantry</span>
                                <span v-else-if="f.staple" class="badge">Staple</span>
                                <span v-if="f.recipes" class="text-caption text-medium-emphasis">{{ f.recipes }} {{ f.recipes == 1 ? 'recipe' : 'recipes' }}</span>
                            </div>
                        </template>
                        <p v-if="groups.length == 0 && !q" class="text-medium-emphasis">Nothing to pick yet. Import a recipe first.</p>
                    </div>
                </template>

                <template v-else>
                    <v-textarea v-model="receipt" label="Receipt or online order" rows="8" auto-grow
                                placeholder="Paste the lines from a receipt or an order email, one item per line" hide-details class="mb-3" />
                    <v-btn color="primary" variant="flat" prepend-icon="fa-solid fa-wand-magic-sparkles" :loading="matching" :disabled="!receipt.trim()" @click="matchReceipt">Match items</v-btn>
                    <div v-if="matched" class="mt-4">
                        <p class="text-body-2 text-medium-emphasis mb-2">{{ matched.filter(m => m.food).length }} of {{ matched.length }} lines matched. Tick the ones to add.</p>
                        <div v-for="(m, i) in matched" :key="i" class="match-row">
                            <v-checkbox-btn v-model="m.on" density="compact" class="flex-none" :aria-label="m.line" />
                            <div class="flex-grow-1 min-w-0">
                                <div class="text-caption text-medium-emphasis line">{{ m.line }}</div>
                                <div v-if="m.food" class="font-weight-medium">{{ m.food.name }} <span class="text-medium-emphasis">× {{ m.amount }}</span></div>
                                <v-text-field v-else v-model="m.name" density="compact" hide-details label="New item name" class="mt-1" />
                            </div>
                        </div>
                        <v-btn class="mt-3" variant="outlined" prepend-icon="fa-solid fa-arrow-right" :disabled="!matched.some(m => m.on)" @click="addMatched">Add ticked lines to your shop</v-btn>
                    </div>
                </template>
            </v-col>

            <v-col cols="12" md="5">
                <v-card border flat class="cart">
                    <v-card-title class="d-flex align-center justify-space-between pt-4">
                        <span>Your shop</span>
                        <span class="text-body-2 text-medium-emphasis">{{ cart.length }} {{ cart.length == 1 ? 'item' : 'items' }}</span>
                    </v-card-title>
                    <v-card-text>
                        <p v-if="cart.length == 0" class="text-medium-emphasis">Pick what you bought, or paste a receipt.</p>
                        <div v-for="(c, i) in cart" :key="c.key" class="cart-item">
                            <div class="d-flex align-center ga-2">
                                <span class="font-weight-medium flex-grow-1">{{ c.name }}<span v-if="!c.food_id" class="badge ms-2">New</span></span>
                                <v-btn icon="$close" size="x-small" variant="text" :aria-label="`Remove ${c.name}`" @click="cart.splice(i, 1)" />
                            </div>
                            <div class="cart-fields">
                                <v-text-field v-model.number="c.amount" type="number" min="0" step="any" label="Amount" density="compact" hide-details />
                                <v-select v-model="c.unit_id" :items="data?.units ?? []" item-title="name" item-value="id" label="Unit" density="compact" hide-details />
                                <v-select v-model="c.location_id" :items="data?.locations ?? []" item-title="name" item-value="id" label="Goes in" density="compact" hide-details />
                                <v-text-field v-model="c.expires" type="date" label="Expires" density="compact" hide-details clearable />
                            </div>
                            <div v-if="c.days" class="text-caption text-medium-emphasis mt-1">Usually keeps about {{ keeps(c.days) }}</div>
                        </div>
                    </v-card-text>
                    <v-card-actions class="px-4 pb-4">
                        <v-btn v-if="cart.length" variant="text" @click="cart = []">Clear</v-btn>
                        <v-spacer />
                        <v-btn color="primary" variant="flat" :disabled="cart.length == 0" :loading="saving" @click="save">
                            Add {{ cart.length || '' }} {{ cart.length == 1 ? 'item' : 'items' }} to pantry
                        </v-btn>
                    </v-card-actions>
                </v-card>
            </v-col>
        </v-row>
    </v-container>
</template>

<script setup lang="ts">
// home fork: put a whole shop into the pantry at once (cookbook/views/home_groceries.py)
import {computed, onMounted, ref} from 'vue'
import {useDjangoUrls} from '@/composables/useDjangoUrls'
import {getCookie} from '@/utils/cookie'
import {pantryVersion} from '@/composables/useScan'

type Unit = { id: number, name: string, plural_name: string }
type GroceryFood = { id: number, name: string, aisle: string | null, recipes: number, bought: number, staple: boolean, in_stock: boolean, location_id: number | null, days: number | null, unit: Unit | null }
type CartItem = { key: string, food_id: number | null, name: string, amount: number, unit_id: number | null, location_id: number | null, expires: string | null, days: number | null }
type Match = { line: string, amount: number, name: string, food?: GroceryFood, on: boolean }

const data = ref<{ foods: GroceryFood[], locations: { id: number, name: string }[], units: Unit[], today: string } | null>(null)
const mode = ref<'pick' | 'paste'>('pick')
const search = ref('')
const cart = ref<CartItem[]>([])
const receipt = ref('')
const matched = ref<Match[] | null>(null)
const matching = ref(false)
const saving = ref(false)
const error = ref('')
const done = ref(0)

async function api(path: string, body?: any) {
    const {getDjangoUrl} = useDjangoUrls()
    const r = await fetch(getDjangoUrl(`api/home/${path}`), {
        method: body === undefined ? 'GET' : 'POST', credentials: 'same-origin',
        headers: {'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') ?? ''},
        body: body === undefined ? undefined : JSON.stringify(body),
    })
    const json = await r.json().catch(() => ({}))
    if (!r.ok) throw new Error(json.error || `Something went wrong (${r.status}).`)
    return json
}

async function load() {
    try {
        data.value = await api('groceries/')
    } catch (e: any) {
        error.value = `Couldn’t load your foods. ${e.message}`
    }
}

const q = computed(() => (search.value || '').trim().toLowerCase())
const exact = computed(() => (data.value?.foods ?? []).some(f => f.name.toLowerCase() == q.value))

const groups = computed(() => {
    const out: { aisle: string, foods: GroceryFood[] }[] = []
    for (const f of data.value?.foods ?? []) {
        if (q.value && !f.name.toLowerCase().includes(q.value)) continue
        // staples you always keep and what's already in stock go last in their aisle
        const aisle = f.aisle || 'Other'
        let g = out.find(x => x.aisle == aisle)
        if (!g) out.push(g = {aisle, foods: []})
        g.foods.push(f)
    }
    out.forEach(g => g.foods.sort((a, b) => Number(a.staple || a.in_stock) - Number(b.staple || b.in_stock) || b.recipes - a.recipes || a.name.localeCompare(b.name)))
    return out
})

function addDays(days: number | null) {
    if (!days || !data.value) return null
    const d = new Date(data.value.today + 'T12:00:00')
    d.setDate(d.getDate() + days)
    return d.toISOString().slice(0, 10)
}

function keeps(days: number) {
    if (days >= 60) return `${Math.round(days / 30)} months`
    if (days >= 14) return `${Math.round(days / 7)} weeks`
    return `${days} ${days == 1 ? 'day' : 'days'}`
}

function inCart(id: number) {
    return cart.value.some(c => c.food_id == id)
}

function itemFor(f: GroceryFood, amount = 1): CartItem {
    return {key: `f${f.id}`, food_id: f.id, name: f.name, amount, unit_id: f.unit?.id ?? null, location_id: f.location_id, expires: addDays(f.days), days: f.days}
}

function newItem(name: string, amount = 1): CartItem {
    const units = data.value?.units ?? []
    return {key: `n${name.toLowerCase()}`, food_id: null, name: name.charAt(0).toUpperCase() + name.slice(1), amount,
        unit_id: units.find(u => u.name == 'package')?.id ?? null, location_id: data.value?.locations[0]?.id ?? null, expires: null, days: null}
}

function toggle(f: GroceryFood) {
    const i = cart.value.findIndex(c => c.food_id == f.id)
    if (i >= 0) cart.value.splice(i, 1)
    else cart.value.push(itemFor(f))
}

function addNewFromSearch() {
    const name = search.value.trim()
    if (!name || exact.value) return
    if (!cart.value.some(c => c.name.toLowerCase() == name.toLowerCase())) cart.value.push(newItem(name))
    search.value = ''
}

async function matchReceipt() {
    matching.value = true
    error.value = ''
    try {
        const r = await api('groceries/match/', {text: receipt.value})
        matched.value = r.lines.map((l: any) => ({...l, on: !!l.food}))
    } catch (e: any) {
        error.value = e.message
    } finally {
        matching.value = false
    }
}

function addMatched() {
    for (const m of matched.value ?? []) {
        if (!m.on) continue
        if (m.food) {
            const existing = cart.value.find(c => c.food_id == m.food!.id)
            if (existing) existing.amount += m.amount
            else cart.value.push(itemFor(m.food, m.amount))
        } else if (m.name.trim()) {
            cart.value.push(newItem(m.name.trim(), m.amount))
        }
    }
    matched.value = null
    receipt.value = ''
    mode.value = 'pick'
}

async function save() {
    saving.value = true
    error.value = ''
    try {
        const r = await api('groceries/', {
            request_id: crypto.randomUUID?.() ?? String(Date.now()),
            items: cart.value.map(c => ({food_id: c.food_id, food_name: c.food_id ? undefined : c.name, amount: c.amount || 1,
                unit_id: c.unit_id, location_id: c.location_id, expires: c.expires || null})),
        })
        done.value = r.added
        cart.value = []
        pantryVersion.value++
        await load()
        window.scrollTo({top: 0, behavior: 'smooth'})
    } catch (e: any) {
        error.value = e.message
    } finally {
        saving.value = false
    }
}

onMounted(load)
</script>

<style scoped>
.page-header { margin: 16px 0 28px; }
.aisle { font-size: .75rem; font-weight: 700; text-transform: uppercase; letter-spacing: .06em; color: rgba(var(--v-theme-on-surface), .6); margin: 18px 0 4px; }
.pick-row { display: flex; align-items: center; gap: 8px; min-height: 42px; padding: 0 8px; border-radius: 8px; cursor: pointer; text-align: start; }
.pick-row:hover { background: rgba(var(--v-theme-on-surface), .04); }
.pick-row:focus-visible { outline: 2px solid rgb(var(--v-theme-primary)); outline-offset: -2px; }
.pick-row.picked { background: rgba(var(--v-theme-primary), .08); }
.new-row { color: rgb(var(--v-theme-primary)); font-weight: 500; }
.flex-none { flex: none; }
.min-w-0 { min-width: 0; }
.badge { font-size: .72rem; padding: 1px 8px; border-radius: 6px; background: rgba(var(--v-theme-on-surface), .07); color: rgba(var(--v-theme-on-surface), .7); white-space: nowrap; }
.badge.good { background: rgba(var(--v-theme-success), .12); color: rgb(var(--v-theme-success)); }
.match-row { display: flex; align-items: flex-start; gap: 8px; padding: 8px 0; border-top: 1px solid rgba(var(--v-theme-on-surface), .08); }
.match-row .line { overflow-wrap: anywhere; font-family: ui-monospace, Menlo, monospace; }
.cart { position: sticky; top: 80px; }
.cart-item { padding: 12px 0; border-top: 1px solid rgba(var(--v-theme-on-surface), .08); }
.cart-item:first-of-type { border-top: 0; }
.cart-fields { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 8px; }
@media (max-width: 600px) {
    .page-header { margin-top: 8px; }
    .page-header h1 { font-size: 1.75rem !important; }
    .cart { position: static; }
}
</style>
