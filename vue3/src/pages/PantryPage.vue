<template>
    <v-container fluid max-width="none" class="pantry-page">
        <header class="pantry-header">
            <div class="d-flex align-center ga-4">
                <v-avatar rounded color="primary" variant="tonal" size="48"><v-icon icon="$pantry" /></v-avatar>
                <div><h1 class="text-h4 font-weight-bold">{{ $t('Pantry') }}</h1><p class="text-body-2 text-medium-emphasis mt-1">Your food, across every shelf and storage space.</p></div>
            </div>
            <div class="header-actions d-flex flex-wrap align-center ga-2">
                <span class="scanner-status" :class="'s-' + scannerState.kind" role="status" :title="scannerState.help"><span class="dot"></span>{{ scannerState.text }}</span>
                <v-btn variant="text" prepend-icon="fa-solid fa-clock-rotate-left" :to="{name: 'PantryActivityPage'}">Activity</v-btn>
                <v-btn variant="outlined" prepend-icon="fa-solid fa-barcode" @click="openScanPanel({mode: 'lookup'})">Scan item</v-btn>
                <v-btn variant="outlined" prepend-icon="fa-solid fa-list-check" @click="openScanPanel({mode: 'count'})">Stock count</v-btn>
                <v-btn variant="outlined" prepend-icon="fa-solid fa-barcode" @click="openScanPanel({mode: 'restock'})">Restock by scanning</v-btn>
                <v-btn color="create" prepend-icon="fa-solid fa-basket-shopping" :to="{name: 'GroceriesPage'}">Add groceries</v-btn>
            </div>
        </header>

        <v-alert v-if="countError" type="warning" variant="tonal" class="mb-4">Couldn’t load stock counts. <v-btn variant="text" size="small" @click="loadCounts">Retry</v-btn></v-alert>
        <v-sheet v-if="openCounts.length" rounded="lg" color="surface" border class="mb-5 pa-4">
            <h2 class="text-subtitle-1 font-weight-bold"><v-icon icon="fa-solid fa-list-check" size="small" class="me-2" />Stock count in progress</h2>
            <div v-for="count in openCounts" :key="count.id" class="d-flex align-center justify-space-between flex-wrap ga-3 mt-2">
                <div>{{ count.location?.name || 'Unassigned' }}<span v-if="count.sub_location"> · {{ count.sub_location }}</span><span class="text-medium-emphasis"> · {{ count.counted }} {{ count.counted === 1 ? 'line' : 'lines' }} counted · Draft</span></div>
                <v-btn variant="outlined" size="small" :to="{name: 'StockCountPage', params: {id: count.id}}" :aria-label="`Resume stock count in ${count.location?.name || 'Unassigned'}`">Resume</v-btn>
            </div>
        </v-sheet>

        <v-card>
            <v-card-text>
                <div class="pantry-tools">
                    <v-text-field v-model="search" label="Search products or retail barcodes" prepend-inner-icon="$search" clearable hide-details />
                    <v-btn variant="outlined" prepend-icon="fa-solid fa-filter" :aria-expanded="showFilters" aria-controls="pantry-filters" @click="showFilters = !showFilters">Filters</v-btn>
                    <v-select v-model="sort" label="Sort by" :items="sortItems" hide-details class="pantry-sort" />
                </div>
                <v-row v-show="showFilters" id="pantry-filters" class="mt-1">
                    <v-col cols="12" sm="6"><v-model-select model="Food" v-model="food" clearable hide-details /></v-col>
                    <v-col cols="12" sm="6"><v-model-select model="InventoryLocation" v-model="location" clearable hide-details /></v-col>
                </v-row>
                <!-- home fork: products on file with none in stock (home_pantry.catalog) -->
                <v-btn-toggle v-model="view" mandatory density="comfortable" variant="outlined" divided class="mt-4 view-toggle">
                    <v-btn value="stock">On hand<span class="count">{{ allProducts.length }}</span></v-btn>
                    <v-btn value="missing">Not on hand<span class="count">{{ catalog.length }}</span></v-btn>
                </v-btn-toggle>
                <div v-if="hasFilters" class="d-flex flex-wrap align-center ga-2 mt-3">
                    <v-chip v-if="search" size="small">Search: {{ search }}</v-chip>
                    <v-chip v-if="food" size="small">{{ food.name }}</v-chip>
                    <v-chip v-if="location" size="small">{{ location.name }}</v-chip>
                    <v-btn size="small" variant="text" @click="resetFilters">Reset filters</v-btn>
                </div>
                <template v-if="view == 'missing'">
                    <div class="mt-4 mb-1 text-body-2 text-medium-emphasis" role="status">{{ catalogLoading ? 'Loading…' : `${missing.length} ${missing.length === 1 ? 'product' : 'products'} you’ve had before and have none of now` }}</div>
                    <v-alert v-if="catalogError" type="error" variant="tonal" class="my-4">{{ catalogError }} <v-btn variant="text" @click="loadCatalog">Retry</v-btn></v-alert>
                    <v-progress-linear v-if="catalogLoading && !catalog.length" indeterminate color="primary" />
                    <p v-else-if="!missing.length" class="py-8 text-center text-medium-emphasis">{{ search ? 'No products match.' : 'Everything you’ve bought before is in stock.' }}</p>
                    <v-table v-else class="product-table">
                        <thead><tr><th scope="col">Product</th><th scope="col">Last bought</th><th scope="col">Aisle</th><th scope="col"><span class="sr-only">Actions</span></th></tr></thead>
                        <tbody><tr v-for="line in visibleMissing" :key="line.food.id" class="product-row missing-row" @click="missingId = line.food.id">
                            <td data-label="Product"><div class="d-flex align-center ga-3"><pantry-product-image small :src="line.food.image" /><div class="min-w-0"><button class="product-name" @click.stop="missingId = line.food.id">{{ line.food.name }}</button><span v-if="line.products.length > 1" class="text-caption text-medium-emphasis ms-2">{{ line.products.length }} products</span><div class="mobile-meta text-caption text-medium-emphasis">{{ boughtText(line) }}</div></div></div></td>
                            <td data-label="Last bought"><span v-if="line.last_bought">{{ boughtText(line) }}</span><span v-else class="text-medium-emphasis">—</span></td>
                            <td data-label="Aisle"><span :class="{'text-medium-emphasis': !line.food.aisle}">{{ line.food.aisle || '—' }}</span></td>
                            <td class="text-end"><v-chip v-if="line.on_list" size="small" color="success" variant="tonal" prepend-icon="fa-solid fa-check">On list</v-chip><v-btn v-else size="small" variant="outlined" prepend-icon="fa-solid fa-cart-plus" :loading="listing == line.food.id" @click.stop="addToList(line)">Add to list</v-btn></td>
                        </tr></tbody>
                    </v-table>
                    <div v-if="visibleMissing.length < missing.length" ref="moreSentinel" class="py-4 text-center text-body-2 text-medium-emphasis" role="status">Loading more…</div>
                </template>
                <template v-else>
                <div class="d-flex justify-space-between flex-wrap ga-2 mt-4 mb-1 text-body-2 text-medium-emphasis" role="status">
                    <span>{{ loading ? 'Loading inventory…' : error ? 'Inventory unavailable' : `${products.length} ${products.length === 1 ? 'product' : 'products'}${location ? ' in ' + location.name : ''}` }}</span>
                </div>
                <v-alert v-if="error" type="error" variant="tonal" class="my-4">{{ error }} <v-btn variant="text" @click="loadItems">Retry</v-btn></v-alert>
                <v-progress-linear v-if="loading" indeterminate color="primary" aria-label="Loading inventory" />
                <template v-else-if="!error">
                    <p v-if="!products.length" class="py-8 text-center text-medium-emphasis">{{ hasFilters ? 'No products match these filters.' : 'Your pantry is empty. Scan an item to look it up and add stock.' }}</p>
                    <v-table v-else class="product-table">
                        <thead><tr><th scope="col">Product</th><th scope="col">On hand</th><th scope="col">Location</th><th scope="col">Expiry</th><th scope="col"><span class="sr-only">Actions</span></th></tr></thead>
                        <tbody><tr v-for="product in visibleProducts" :key="product.key" class="product-row" @click="selectedKey = product.key">
                            <td data-label="Product"><div class="d-flex align-center ga-3"><pantry-product-image small :src="product.food?.productImage" /><div class="min-w-0"><button class="product-name" @click.stop="selectedKey = product.key">{{ product.food?.name || 'Unassigned product' }}</button><span v-if="product.batches.length > 1" class="text-caption text-medium-emphasis ms-2">{{ product.batches.length }} entries</span><div class="mobile-meta text-caption text-medium-emphasis">{{ product.locations.map(l => l.name).join(', ') }}<span v-if="product.earliestExpiry" :class="{'text-error': daysUntil(product.earliestExpiry)! < 0, 'text-warning': daysUntil(product.earliestExpiry)! >= 0 && daysUntil(product.earliestExpiry)! <= EXPIRY_WINDOW_DAYS}"> · {{ fmtDate(product.earliestExpiry) }}</span></div></div></div></td>
                            <td data-label="On hand"><strong>{{ totalText(product.totals) }}</strong></td>
                            <td data-label="Locations"><div>{{ product.locations.length === 1 ? product.locations[0].name : '' }}<template v-if="product.locations.length > 1"><span v-for="(place, i) in product.locations" :key="place.id ?? 'none'">{{ i ? ', ' : '' }}{{ place.name }} <span class="text-medium-emphasis">{{ totalText(place.totals) }}</span></span></template></div></td>
                            <td data-label="Earliest known expiry"><div><template v-if="product.earliestExpiry"><v-chip size="small" label :color="expiryColor(product.earliestExpiry)">{{ fmtDate(product.earliestExpiry) }}</v-chip><span v-if="daysUntil(product.earliestExpiry)! < 0" class="text-caption text-error ms-2">Past expiry</span><span v-else-if="daysUntil(product.earliestExpiry)! <= EXPIRY_WINDOW_DAYS" class="text-caption ms-2">Due soon</span></template><span v-else class="text-medium-emphasis" aria-label="Not recorded">—</span></div></td>
                            <td class="text-end"><v-btn icon="fa-solid fa-chevron-right" variant="text" size="x-small" :aria-label="`View ${product.food?.name || 'product'} batches`" @click.stop="selectedKey = product.key" /></td>
                        </tr></tbody>
                    </v-table>
                    <!-- more rows load as the end of the list scrolls into view -->
                    <div v-if="visibleProducts.length < products.length" ref="moreSentinel" class="py-4 text-center text-body-2 text-medium-emphasis" role="status">Loading more…</div>
                </template>
                </template>
            </v-card-text>
        </v-card>

        <v-dialog :model-value="selectedKey !== null" max-width="900" aria-labelledby="pantry-product-title" scrollable @update:model-value="v => { if (!v) selectedKey = null }">
            <v-card>
                <v-card-title class="d-flex align-center justify-space-between ga-2"><h2 id="pantry-product-title" class="text-h6 text-wrap">{{ selectedProduct?.food?.name || 'Product details' }}</h2><v-btn icon="$close" variant="text" aria-label="Close product details" @click="selectedKey = null" /></v-card-title>
                <v-card-text>
                    <p v-if="loading" role="status">Refreshing inventory…</p>
                    <v-alert v-else-if="error" type="error">{{ error }} <v-btn variant="text" @click="loadItems">Retry</v-btn></v-alert>
                    <template v-else-if="selectedProduct">
                        <div class="d-flex align-center ga-4"><pantry-product-image :src="selectedProduct.food?.productImage" /><p class="text-h5 font-weight-bold">{{ totalText(selectedProduct.totals) }} <span class="text-body-2 font-weight-regular">on hand</span></p></div>
                        <div class="d-flex flex-wrap ga-2 my-3"><v-chip v-for="place in selectedProduct.locations" :key="place.id ?? 'none'" size="small">{{ place.name }}: {{ totalText(place.totals) }}</v-chip></div>
                        <p v-if="lineBarcodes" class="text-body-2 mb-3">Retail barcodes: {{ lineBarcodes }}</p>
                        <p class="text-body-2 text-medium-emphasis">{{ selectedProduct.batches.length }} separate inventory entries · Quantities are shown by unit.</p>
                        <article v-for="batch in selectedProduct.batches" :key="batch.id" class="batch-card mt-4 pa-4">
                            <div class="d-flex justify-space-between flex-wrap ga-2"><h3 class="text-subtitle-1 font-weight-bold">{{ quantity(batch.amount ?? 0, batch.unit) }}<span v-if="entryGroup(batch)?.amount != null && entryGroup(batch)?.unit?.id != batch.unit?.id" class="font-weight-regular text-medium-emphasis"> ({{ quantity(entryGroup(batch)!.amount!, {name: entryGroup(batch)!.unit!.name, pluralName: entryGroup(batch)!.unit!.plural_name} as any) }})</span><span v-if="batch.food && batch.food.id != selectedProduct.food?.id" class="font-weight-regular"> · {{ batch.food.name }}</span></h3><span class="text-body-2">Item label #{{ batch.code || 'Not assigned' }}</span></div>
                            <p>{{ batch.inventoryLocation?.name || 'Unassigned' }}<span v-if="batch.subLocation"> · {{ batch.subLocation }}</span></p>
                            <p class="text-body-2 text-medium-emphasis mt-1">Expiry: {{ fmtDate(expiryDay(batch)) || 'Not recorded' }}</p>
                            <p v-if="batch.note" class="text-body-2 mt-1">{{ batch.note }}</p>
                            <div v-if="batch.food?.id" class="d-flex flex-wrap ga-2 mt-3">
                                <v-btn v-for="action in batchActions" :key="action.tab" variant="outlined" size="small" @click="batchAction(batch, action.tab)">{{ action.label }}</v-btn>
                            </div>
                        </article>
                        <!-- home fork: products under a general food (cookbook/helper/home_products.py) -->
                        <div class="group-box mt-5 pa-4">
                            <template v-if="!groupOpen">
                                <p class="text-body-2 text-medium-emphasis mb-2">
                                    <template v-if="lineProducts.length">Products counted as {{ selectedProduct.food?.name }}: {{ lineProducts.map(f => f.name).join(', ') }}.</template>
                                    <template v-else>Is this one kind of a more general food, like a brand of eggs? Group it so the pantry counts them together.</template>
                                </p>
                                <div class="d-flex flex-wrap ga-2">
                                    <v-btn v-if="!selectedProduct.grouped" size="small" variant="outlined" prepend-icon="fa-solid fa-layer-group" @click="startGroup">Group under a general food</v-btn>
                                    <v-btn v-for="f in lineProducts" :key="f.id" size="small" variant="text" @click="ungroup(f)">Count {{ f.name }} separately</v-btn>
                                </div>
                            </template>
                            <template v-else>
                                <p class="text-subtitle-2 mb-3">Group {{ selectedProduct.food?.name }} under</p>
                                <v-model-select model="Food" v-model="groupParent" hide-details density="compact" class="mb-3" />
                                <v-text-field v-if="groupCheck?.needs_size" v-model="groupPer" type="number" min="0" density="compact" hide-details class="mb-3"
                                              :label="`${groupCheck.to_unit.plural_name} in one ${groupCheck.from_unit.name}`" />
                                <v-alert v-if="groupError" type="error" density="compact" class="mb-3">{{ groupError }}</v-alert>
                                <div class="d-flex ga-2">
                                    <v-btn color="primary" variant="flat" size="small" :disabled="!groupParent || (groupCheck?.needs_size && !groupPer)" :loading="groupSaving" @click="saveGroup">Group</v-btn>
                                    <v-btn variant="text" size="small" @click="groupOpen = false">Cancel</v-btn>
                                </div>
                            </template>
                        </div>
                    </template>
                    <p v-else>No remaining stock for this product.</p>
                </v-card-text>
            </v-card>
        </v-dialog>
        <v-dialog :model-value="missingLine != null" max-width="720" scrollable aria-labelledby="pantry-missing-title" @update:model-value="v => { if (!v) missingId = null }">
            <v-card v-if="missingLine">
                <v-card-title class="d-flex align-center justify-space-between ga-2"><h2 id="pantry-missing-title" class="text-h6 text-wrap">{{ missingLine.food.name }}</h2><v-btn icon="$close" variant="text" aria-label="Close" @click="missingId = null" /></v-card-title>
                <v-card-text>
                    <div class="d-flex align-center ga-4 flex-wrap">
                        <pantry-product-image :src="missingLine.food.image" />
                        <div class="flex-grow-1"><p class="text-h6 font-weight-bold">None on hand</p><p class="text-body-2 text-medium-emphasis">{{ missingLine.last_bought ? boughtText(missingLine) : 'Not bought through a store order on file' }}</p></div>
                        <v-chip v-if="missingLine.on_list" color="success" variant="tonal" prepend-icon="fa-solid fa-check">On the shopping list</v-chip>
                        <v-btn v-else color="primary" variant="flat" prepend-icon="fa-solid fa-cart-plus" :loading="listing == missingLine.food.id" @click="addToList(missingLine)">Add to shopping list</v-btn>
                    </div>
                    <h3 class="text-subtitle-2 mt-6 mb-2">{{ missingLine.products.length > 1 ? 'Products' : 'Product' }}</h3>
                    <div v-for="p in missingLine.products" :key="p.id" class="missing-product d-flex align-center ga-3 pa-3">
                        <pantry-product-image small :src="p.image || missingLine.food.image" />
                        <div class="flex-grow-1 min-w-0"><div class="font-weight-medium">{{ p.name }}</div><div class="text-caption text-medium-emphasis">{{ p.last_bought ? `Last bought ${fmtDate(p.last_bought)}${p.times > 1 ? ` · ${p.times} times` : ''}` : 'No store orders on file' }}</div></div>
                        <v-btn size="small" variant="outlined" prepend-icon="fa-solid fa-plus" @click="addStock(p.id)">Add stock</v-btn>
                    </div>
                </v-card-text>
            </v-card>
        </v-dialog>
    </v-container>
</template>

<script setup lang="ts">
import {computed, onMounted, onUnmounted, ref, watch} from 'vue'
import {useRoute, useRouter} from 'vue-router'
import {ApiApi, type Food, type InventoryEntry, type InventoryLocation} from '@/openapi'
import PantryProductImage from '@/components/display/PantryProductImage.vue'
import VModelSelect from '@/components/inputs/VModelSelect.vue'
import {daysUntil, fmtDate, inputPaused, openScanPanel, pantryApi, pantryVersion, scanPanel, scanStatus} from '@/composables/useScan'
import {entryGroup, EXPIRY_WINDOW_DAYS, expiryDay, groupProducts, loadInventory, quantity, totalText} from '@/utils/pantry'

const items = ref<InventoryEntry[]>([])
const loading = ref(true)
const error = ref('')
const search = ref('')
const food = ref<Food | null>(null)
const location = ref<InventoryLocation | null>(null)
const showFilters = ref(false)
const sort = ref('name')
const selectedKey = ref<string | null>(null)
const allProducts = computed(() => groupProducts(items.value))
const view = ref<'stock' | 'missing'>('stock')
// A location filter scopes displayed totals; the drill-down always includes all product batches.
const products = computed(() => {
    const query = (search.value || '').trim().toLocaleLowerCase()
    const result = groupProducts(items.value.filter(e => (!food.value || e.food?.id === food.value.id || entryGroup(e)?.food.id === food.value.id) && (!location.value || e.inventoryLocation?.id === location.value.id)))
        .filter(p => !query || [p.food, ...p.batches.map(b => b.food)].some(f => f?.name.toLocaleLowerCase().includes(query) || f?.barcodes?.includes(query)))
    return sort.value === 'expiry' ? result.sort((a, b) => (a.earliestExpiry || '9999').localeCompare(b.earliestExpiry || '9999')) : result
})
// the list grows as you scroll instead of paging
const CHUNK = 40
const shown = ref(CHUNK)
const visibleProducts = computed(() => products.value.slice(0, shown.value))
watch([search, food, location, sort, view], () => { shown.value = CHUNK })

// products on file with none in stock
type CatalogProduct = { id: number, name: string, image: string, last_bought: string, times: number }
type CatalogLine = { food: { id: number, name: string, image: string, aisle: string | null }, products: CatalogProduct[], last_bought: string, times: number, on_list: boolean }
const catalog = ref<CatalogLine[]>([])
const catalogLoading = ref(false)
const catalogError = ref('')
const sortItems = computed(() => view.value == 'missing'
    ? [{title: 'Product name', value: 'name'}, {title: 'Last bought', value: 'bought'}, {title: 'Most bought', value: 'times'}]
    : [{title: 'Product name', value: 'name'}, {title: 'Earliest known expiry', value: 'expiry'}])
watch(view, () => { if (!sortItems.value.some(i => i.value == sort.value)) sort.value = 'name' })
const missing = computed(() => {
    const query = (search.value || '').trim().toLocaleLowerCase()
    const lines = catalog.value.filter(l => (!food.value || l.food.id === food.value.id || l.products.some(p => p.id === food.value!.id))
        && (!query || [l.food.name, ...l.products.map(p => p.name)].some(n => n.toLocaleLowerCase().includes(query))))
    if (sort.value == 'bought') return [...lines].sort((a, b) => (b.last_bought || '').localeCompare(a.last_bought || ''))
    if (sort.value == 'times') return [...lines].sort((a, b) => b.times - a.times)
    return lines
})
const visibleMissing = computed(() => missing.value.slice(0, shown.value))
const missingId = ref<number | null>(null)
const missingLine = computed(() => catalog.value.find(l => l.food.id === missingId.value) ?? null)
function boughtText(l: CatalogLine) {
    return l.last_bought ? `${fmtDate(l.last_bought)}${l.times > 1 ? ` · ${l.times}×` : ''}` : ''
}
async function loadCatalog() {
    catalogLoading.value = true; catalogError.value = ''
    try { catalog.value = (await pantryApi('catalog/')).lines } catch { catalogError.value = 'Couldn’t load the products you’ve had before.' } finally { catalogLoading.value = false }
}
const listing = ref<number | null>(null)
async function addToList(l: CatalogLine) {
    listing.value = l.food.id
    try { await pantryApi('catalog/', {food_id: l.food.id}); l.on_list = true } catch { catalogError.value = `Couldn’t add ${l.food.name} to the shopping list.` } finally { listing.value = null }
}
function addStock(foodId: number) {
    missingId.value = null
    openScanPanel({mode: 'lookup', foodId, tab: 'add'})
}
const moreSentinel = ref<HTMLElement | null>(null)
let observer: IntersectionObserver | null = null
watch(moreSentinel, el => {
    observer?.disconnect()
    if (!el) return
    observer = new IntersectionObserver(entries => { if (entries.some(e => e.isIntersecting)) shown.value += CHUNK }, {rootMargin: '600px'})
    observer.observe(el)
})
const selectedProduct = computed(() => allProducts.value.find(p => p.key === selectedKey.value))
// /pantry?food=12 (from the search menu) opens that food once the stock has loaded
const route = useRoute()
const router = useRouter()
watch([() => route.query.food, allProducts], ([id]) => {
    const line = id ? allProducts.value.find(p => p.key === `food:${id}` || p.batches.some(b => String(b.food?.id) === String(id))) : null
    if (line) {
        selectedKey.value = line.key
        router.replace({query: {...route.query, food: undefined}})
    }
}, {immediate: true})
// handheld scanner state: a text box with focus takes the scanner's typing, so scans pause
const scannerState = computed(() => {
    if (inputPaused.value || scanStatus.value == 'paused') return {kind: 'paused', text: 'Scanning paused', help: inputPaused.value ? 'A text box has focus. Click elsewhere on the page to scan again.' : 'Finish or discard the open edit to scan the next item.'}
    if (scanPanel.open && (scanStatus.value == 'found' || scanStatus.value == 'new')) return {kind: 'found', text: scanStatus.value == 'new' ? 'New barcode' : 'Product found', help: ''}
    if (scanStatus.value == 'looking') return {kind: 'looking', text: 'Looking up…', help: ''}
    return {kind: 'ready', text: 'Scanner ready', help: 'Scan a barcode or item label any time.'}
})
const hasFilters = computed(() => !!(search.value || food.value || location.value))
function resetFilters() { search.value = ''; food.value = null; location.value = null }
function expiryColor(day: string) { const days = daysUntil(day)!; return days < 0 ? 'error' : days <= EXPIRY_WINDOW_DAYS ? 'warning' : undefined }
const batchActions = [{tab: 'add', label: 'Add stock'}, {tab: 'use', label: 'Use / remove'}, {tab: 'count', label: 'Set quantity / correct'}, {tab: 'move', label: 'Move'}, {tab: 'details', label: 'Edit expiry / details'}, {tab: 'duplicate', label: 'Duplicate'}]
function batchAction(batch: InventoryEntry, tab: string) {
    selectedKey.value = null
    openScanPanel({mode: 'lookup', foodId: batch.food.id, entryId: batch.id, tab})
}
// grouping a product under a general food
const lineBarcodes = computed(() => [...new Set([selectedProduct.value?.food, ...(selectedProduct.value?.batches ?? []).map(b => b.food)]
    .flatMap(f => (f?.barcodes || '').split(/\s+/)).filter(Boolean))].join(' '))
const lineProducts = computed(() => {
    const p = selectedProduct.value
    if (!p?.grouped) return []
    const seen = new Map<number, Food>()
    p.batches.forEach(b => { if (b.food?.id && b.food.id != p.food?.id) seen.set(b.food.id, b.food) })
    return [...seen.values()]
})
const groupOpen = ref(false)
const groupParent = ref<Food | null>(null)
const groupPer = ref<string | number>('')
const groupCheck = ref<any>(null)
const groupError = ref('')
const groupSaving = ref(false)
watch(selectedKey, () => { groupOpen.value = false })
function startGroup() {
    groupOpen.value = true; groupParent.value = null; groupPer.value = ''; groupCheck.value = null; groupError.value = ''
}
watch(groupParent, async parent => {
    groupCheck.value = null; groupError.value = ''
    const food = selectedProduct.value?.food
    if (!parent || !food) return
    try {
        groupCheck.value = await pantryApi('group/', {food_id: food.id, parent_id: parent.id, check: true})
        if (groupCheck.value.per != null) groupPer.value = groupCheck.value.per
    } catch (e: any) { groupError.value = e?.message || 'Couldn’t check the units.' }
})
async function saveGroup() {
    const food = selectedProduct.value?.food
    if (!food || !groupParent.value) return
    groupSaving.value = true; groupError.value = ''
    try {
        await pantryApi('group/', {food_id: food.id, parent_id: groupParent.value.id, per: groupPer.value || undefined})
        const parentId = groupParent.value.id
        groupOpen.value = false
        await loadItems()
        selectedKey.value = `food:${parentId}`
    } catch (e: any) { groupError.value = e?.message || 'Couldn’t group it.' } finally { groupSaving.value = false }
}
async function ungroup(f: Food) {
    try {
        await pantryApi('group/', {food_id: f.id, parent_id: null})
        await loadItems()
    } catch (e: any) { groupError.value = e?.message || 'Couldn’t separate it.' }
}

let sequence = 0
async function loadItems() {
    const current = ++sequence
    loading.value = true
    error.value = ''
    try {
        const api = new ApiApi()
        const result = await loadInventory(page => api.apiInventoryEntryList({page, pageSize: 100}))
        if (current === sequence) items.value = result
    } catch (err) {
        if (current === sequence) { items.value = []; error.value = 'Couldn’t load complete inventory totals. Please retry.' }
    } finally { if (current === sequence) loading.value = false }
}
const openCounts = ref<any[]>([])
const countError = ref(false)
let countSequence = 0
async function loadCounts() {
    const current = ++countSequence
    try { const r = await pantryApi('counts/?status=open'); if (current === countSequence) { openCounts.value = r.results; countError.value = false } }
    catch { if (current === countSequence) countError.value = true }
}
function refresh() { loadItems(); loadCounts(); loadCatalog() }
watch(pantryVersion, refresh)
watch(() => scanPanel.open, open => { if (!open) loadCounts() })
onMounted(() => { refresh(); window.addEventListener('focus', refresh) })
onUnmounted(() => { sequence++; countSequence++; observer?.disconnect(); window.removeEventListener('focus', refresh) })
</script>

<style scoped>
.pantry-page { padding: 12px 24px; }
.pantry-header { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 16px 24px; margin: 8px 0 20px; }
.scanner-status { display: inline-flex; align-items: center; gap: 6px; height: 28px; padding: 0 10px; margin-right: 4px; border-radius: 999px; font-size: .8125rem; font-weight: 500; background: rgba(var(--v-theme-on-surface), .05); color: rgba(var(--v-theme-on-surface), .75); }
.scanner-status .dot { width: 7px; height: 7px; border-radius: 50%; background: rgb(var(--v-theme-success)); }
.scanner-status.s-paused .dot { background: rgb(var(--v-theme-warning)); }
.scanner-status.s-looking .dot { background: rgb(var(--v-theme-info)); }
.pantry-tools { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.pantry-tools > :first-child { flex: 1 1 260px; }
.pantry-sort { flex: 0 1 220px; min-width: 180px; }
.product-name { text-align: start; font-weight: 600; color: inherit; overflow-wrap: anywhere; }
.product-name:hover { text-decoration: underline; }
.product-name:focus-visible { outline: 2px solid rgb(var(--v-theme-primary)); outline-offset: 4px; border-radius: 2px; }
.product-table :deep(td) { height: auto !important; padding-top: 4px !important; padding-bottom: 4px !important; }
.product-table :deep(th) { height: 36px !important; }
.product-row { cursor: pointer; }
.product-row:hover { background: rgba(var(--v-theme-on-surface), .03); }
.min-w-0 { min-width: 0; }
.mobile-meta { display: none; }
.batch-card { border: 1px solid rgba(var(--v-theme-on-surface), .12); border-radius: 12px; }
.group-box { background: rgba(var(--v-theme-on-surface), .03); border-radius: 12px; }
.view-toggle .count { margin-left: 8px; font-size: .75rem; opacity: .6; font-variant-numeric: tabular-nums; }
.missing-row :deep(.product-photo) { opacity: .75; }
.missing-product { border: 1px solid rgba(var(--v-theme-on-surface), .12); border-radius: 12px; }
.missing-product + .missing-product { margin-top: 8px; }
.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%); }
@media (max-width: 700px) {
    .pantry-page { padding: 8px 12px; }
    .pantry-header { margin-top: 8px; gap: 20px; }
    .header-actions { width: 100%; }
    .pantry-header h1 { font-size: 1.75rem !important; }
    .pantry-tools > :first-child { flex-basis: 100%; }
    .pantry-sort { flex: 1 1 160px; }
    /* phones: one line per product - photo, name with location and expiry under it, amount */
    .product-table :deep(thead) { position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%); }
    .product-table :deep(table), .product-table :deep(tbody) { display: block; width: 100%; }
    .product-table :deep(tr) { display: flex; align-items: center; gap: 12px; border-top: 1px solid rgba(var(--v-theme-on-surface), .12); padding: 6px 0; }
    .product-table :deep(td) { height: auto !important; border: 0 !important; padding: 0 !important; }
    .product-table td[data-label="Product"] { flex: 1 1 auto; min-width: 0; }
    .product-table td[data-label="On hand"] { flex: 0 0 auto; text-align: end; }
    .product-table td[data-label="Locations"], .product-table td[data-label="Earliest known expiry"], .product-table td[data-label="Last bought"], .product-table td[data-label="Aisle"] { display: none; }
    .product-table:not(:has(.missing-row)) td:last-child { display: none; }
    .mobile-meta { display: block !important; }
}
</style>
