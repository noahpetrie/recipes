<template>
    <v-container class="pantry-page">
        <header class="pantry-header">
            <div class="d-flex align-center ga-4">
                <v-avatar rounded color="primary" variant="tonal" size="48"><v-icon icon="$pantry" /></v-avatar>
                <div><h1 class="text-h4 font-weight-bold">{{ $t('Pantry') }}</h1><p class="text-body-2 text-medium-emphasis mt-1">Your food, across every shelf and storage space.</p></div>
            </div>
            <div class="header-actions d-flex flex-wrap ga-2">
                <v-btn variant="text" prepend-icon="fa-solid fa-clock-rotate-left" :to="{name: 'PantryActivityPage'}">Activity</v-btn>
                <v-btn variant="outlined" prepend-icon="fa-solid fa-barcode" @click="openScanPanel({mode: 'lookup'})">Scan item</v-btn>
                <v-btn variant="outlined" prepend-icon="fa-solid fa-list-check" @click="openScanPanel({mode: 'count'})">Stock count</v-btn>
                <v-btn color="create" prepend-icon="$create" @click="openScanPanel({mode: 'restock'})">Restock</v-btn>
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
                    <v-select v-model="sort" label="Sort by" :items="[{title: 'Product name', value: 'name'}, {title: 'Earliest known expiry', value: 'expiry'}]" hide-details class="pantry-sort" />
                </div>
                <v-row v-show="showFilters" id="pantry-filters" class="mt-1">
                    <v-col cols="12" sm="6"><v-model-select model="Food" v-model="food" clearable hide-details /></v-col>
                    <v-col cols="12" sm="6"><v-model-select model="InventoryLocation" v-model="location" clearable hide-details /></v-col>
                </v-row>
                <div v-if="hasFilters" class="d-flex flex-wrap align-center ga-2 mt-3">
                    <v-chip v-if="search" size="small">Search: {{ search }}</v-chip>
                    <v-chip v-if="food" size="small">{{ food.name }}</v-chip>
                    <v-chip v-if="location" size="small">{{ location.name }}</v-chip>
                    <v-btn size="small" variant="text" @click="resetFilters">Reset filters</v-btn>
                </div>
                <div class="d-flex justify-space-between flex-wrap ga-2 mt-5 mb-2 text-body-2 text-medium-emphasis" role="status">
                    <span>{{ loading ? 'Loading inventory…' : error ? 'Inventory unavailable' : `${products.length} ${products.length === 1 ? 'product' : 'products'}${location ? ' in ' + location.name : ''}` }}</span>
                    <span>Expiry warnings: within {{ EXPIRY_WINDOW_DAYS }} days</span>
                </div>
                <v-alert v-if="error" type="error" variant="tonal" class="my-4">{{ error }} <v-btn variant="text" @click="loadItems">Retry</v-btn></v-alert>
                <v-progress-linear v-if="loading" indeterminate color="primary" aria-label="Loading inventory" />
                <template v-else-if="!error">
                    <p v-if="!products.length" class="py-8 text-center text-medium-emphasis">{{ hasFilters ? 'No products match these filters.' : 'Your pantry is empty. Scan an item to look it up and add stock.' }}</p>
                    <v-table v-else class="product-table">
                        <thead><tr><th scope="col">Product</th><th scope="col">On hand</th><th scope="col">Locations</th><th scope="col">Earliest known expiry</th><th scope="col"><span class="sr-only">Actions</span></th></tr></thead>
                        <tbody><tr v-for="product in visibleProducts" :key="product.key">
                            <td data-label="Product"><div class="d-flex align-center ga-3 py-3"><pantry-product-image :src="product.food?.productImage" /><div><button class="product-name" @click="selectedKey = product.key">{{ product.food?.name || 'Unassigned product' }}</button><div class="text-caption text-medium-emphasis">{{ product.batches.length }} inventory {{ product.batches.length === 1 ? 'entry' : 'entries' }}</div></div></div></td>
                            <td data-label="On hand"><strong>{{ totalText(product.totals) }}</strong></td>
                            <td data-label="Locations"><div><div v-for="place in product.locations" :key="place.id ?? 'none'" class="py-1">{{ place.name }} <span class="text-medium-emphasis">{{ totalText(place.totals) }}</span></div></div></td>
                            <td data-label="Earliest known expiry"><div><div v-if="product.earliestExpiry"><v-chip size="small" label :color="expiryColor(product.earliestExpiry)">{{ fmtDate(product.earliestExpiry) }}</v-chip><div v-if="daysUntil(product.earliestExpiry)! < 0" class="text-caption text-error">Past expiry</div><div v-else-if="daysUntil(product.earliestExpiry)! <= EXPIRY_WINDOW_DAYS" class="text-caption">Due within {{ EXPIRY_WINDOW_DAYS }} days</div></div><span v-else class="text-medium-emphasis">Not recorded</span><div v-if="product.earliestExpiry && product.unknownExpiry" class="text-caption text-medium-emphasis">{{ product.unknownExpiry }} entries without a date</div></div></td>
                            <td><v-btn variant="text" size="small" :aria-label="`View ${product.food?.name || 'product'} batches`" @click="selectedKey = product.key">View batches</v-btn></td>
                        </tr></tbody>
                    </v-table>
                    <div v-if="products.length" class="d-flex align-center justify-space-between flex-wrap ga-3 mt-4">
                        <span class="text-body-2 text-medium-emphasis" role="status">{{ (productPage - 1) * pageSize + 1 }}–{{ Math.min(productPage * pageSize, products.length) }} of {{ products.length }} products</span>
                        <v-select v-model="pageSize" label="Products per page" :items="[10, 25, 50]" hide-details style="max-width: 170px" />
                        <v-pagination v-if="pageCount > 1" v-model="productPage" :length="pageCount" :total-visible="5" density="comfortable" aria-label="Product pages" />
                    </div>
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
                        <p v-if="selectedProduct.food?.barcodes" class="text-body-2 mb-3">Retail barcodes: {{ selectedProduct.food.barcodes }}</p>
                        <p class="text-body-2 text-medium-emphasis">{{ selectedProduct.batches.length }} separate inventory entries · Quantities are shown by unit.</p>
                        <article v-for="batch in selectedProduct.batches" :key="batch.id" class="batch-card mt-4 pa-4">
                            <div class="d-flex justify-space-between flex-wrap ga-2"><h3 class="text-subtitle-1 font-weight-bold">{{ quantity(batch.amount ?? 0, batch.unit) }}</h3><span class="text-body-2">Item label #{{ batch.code || 'Not assigned' }}</span></div>
                            <p>{{ batch.inventoryLocation?.name || 'Unassigned' }}<span v-if="batch.subLocation"> · {{ batch.subLocation }}</span></p>
                            <p class="text-body-2 text-medium-emphasis mt-1">Expiry: {{ fmtDate(expiryDay(batch)) || 'Not recorded' }}</p>
                            <p v-if="batch.note" class="text-body-2 mt-1">{{ batch.note }}</p>
                            <div v-if="batch.food?.id" class="d-flex flex-wrap ga-2 mt-3">
                                <v-btn v-for="action in batchActions" :key="action.tab" variant="outlined" size="small" @click="batchAction(batch, action.tab)">{{ action.label }}</v-btn>
                            </div>
                        </article>
                    </template>
                    <p v-else>No remaining stock for this product.</p>
                </v-card-text>
            </v-card>
        </v-dialog>
    </v-container>
</template>

<script setup lang="ts">
import {computed, onMounted, onUnmounted, ref, watch} from 'vue'
import {ApiApi, type Food, type InventoryEntry, type InventoryLocation} from '@/openapi'
import PantryProductImage from '@/components/display/PantryProductImage.vue'
import VModelSelect from '@/components/inputs/VModelSelect.vue'
import {daysUntil, fmtDate, openScanPanel, pantryApi, pantryVersion, scanPanel} from '@/composables/useScan'
import {EXPIRY_WINDOW_DAYS, expiryDay, groupProducts, loadInventory, quantity, totalText} from '@/utils/pantry'

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
// A location filter scopes displayed totals; the drill-down always includes all product batches.
const products = computed(() => {
    const query = (search.value || '').trim().toLocaleLowerCase()
    const result = groupProducts(items.value.filter(e => (!food.value || e.food?.id === food.value.id) && (!location.value || e.inventoryLocation?.id === location.value.id)))
        .filter(p => !query || p.food?.name.toLocaleLowerCase().includes(query) || p.food?.barcodes?.includes(query))
    return sort.value === 'expiry' ? result.sort((a, b) => (a.earliestExpiry || '9999').localeCompare(b.earliestExpiry || '9999')) : result
})
const productPage = ref(1)
const pageSize = ref(10)
const pageCount = computed(() => Math.max(1, Math.ceil(products.value.length / pageSize.value)))
const visibleProducts = computed(() => products.value.slice((productPage.value - 1) * pageSize.value, productPage.value * pageSize.value))
watch([search, food, location, sort, pageSize], () => { productPage.value = 1 })
watch(pageCount, pages => { productPage.value = Math.min(productPage.value, pages) })
const selectedProduct = computed(() => allProducts.value.find(p => p.key === selectedKey.value))
const hasFilters = computed(() => !!(search.value || food.value || location.value))
function resetFilters() { search.value = ''; food.value = null; location.value = null }
function expiryColor(day: string) { const days = daysUntil(day)!; return days < 0 ? 'error' : days <= EXPIRY_WINDOW_DAYS ? 'warning' : undefined }
const batchActions = [{tab: 'add', label: 'Add stock'}, {tab: 'use', label: 'Use / remove'}, {tab: 'count', label: 'Set quantity / correct'}, {tab: 'move', label: 'Move'}, {tab: 'details', label: 'Edit expiry / details'}, {tab: 'duplicate', label: 'Duplicate'}]
function batchAction(batch: InventoryEntry, tab: string) {
    selectedKey.value = null
    openScanPanel({mode: 'lookup', foodId: batch.food.id, entryId: batch.id, tab})
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
function refresh() { loadItems(); loadCounts() }
watch(pantryVersion, refresh)
watch(() => scanPanel.open, open => { if (!open) loadCounts() })
onMounted(() => { refresh(); window.addEventListener('focus', refresh) })
onUnmounted(() => { sequence++; countSequence++; window.removeEventListener('focus', refresh) })
</script>

<style scoped>
.pantry-header { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 24px; margin: 16px 0 32px; }
.pantry-tools { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.pantry-tools > :first-child { flex: 1 1 260px; }
.pantry-sort { flex: 0 1 220px; min-width: 180px; }
.product-name { text-align: start; font-weight: 600; color: inherit; overflow-wrap: anywhere; }
.product-name:hover { text-decoration: underline; }
.product-name:focus-visible { outline: 2px solid rgb(var(--v-theme-primary)); outline-offset: 4px; border-radius: 2px; }
.product-table td { padding-top: 12px !important; padding-bottom: 12px !important; }
.batch-card { border: 1px solid rgba(var(--v-theme-on-surface), .12); border-radius: 12px; }
.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%); }
@media (max-width: 700px) {
    .pantry-header { margin-top: 8px; gap: 20px; }
    .header-actions { width: 100%; }
    .pantry-header h1 { font-size: 1.75rem !important; }
    .product-table :deep(thead) { position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%); }
    .product-table :deep(table), .product-table :deep(tbody), .product-table :deep(tr) { display: block; width: 100%; }
    .product-table :deep(tr) { border-top: 1px solid rgba(var(--v-theme-on-surface), .12); padding: 12px 0; }
    .product-table :deep(td) { display: flex; align-items: baseline; justify-content: space-between; flex-wrap: wrap; gap: 8px; height: auto !important; border: 0 !important; padding: 6px 0 !important; }
    .product-table td[data-label]:not(:first-child) { display: grid; grid-template-columns: 125px minmax(0, 1fr); }
    .product-table td[data-label]:not(:first-child) > * { text-align: end; overflow-wrap: anywhere; }
    .product-table td[data-label]:not(:first-child)::before { content: attr(data-label); font-size: .8125rem; color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity)); }
}
</style>
