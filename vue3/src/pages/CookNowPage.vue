<template>
    <v-container class="cook-page">
        <header class="cook-header">
            <div class="d-flex align-center ga-4">
                <v-avatar rounded color="primary" variant="tonal" size="48"><v-icon icon="fa-solid fa-fire-burner" /></v-avatar>
                <div>
                    <h1 class="text-h4 font-weight-bold">Ready to Cook</h1>
                    <p class="text-body-2 text-medium-emphasis mt-1">Your recipes, matched against the pantry and the staples you always keep.</p>
                </div>
            </div>
            <div class="d-flex flex-wrap ga-2">
                <v-btn variant="outlined" prepend-icon="fa-solid fa-jar" @click="openStaples">Staples<span v-if="data" class="text-medium-emphasis ms-1">· {{ data.staples }}</span></v-btn>
                <v-btn color="primary" variant="flat" prepend-icon="fa-solid fa-basket-shopping" :to="{name: 'GroceriesPage'}">Add groceries</v-btn>
            </div>
        </header>

        <v-alert v-if="error" type="error" variant="tonal" class="mb-4">Couldn’t load recipes. <v-btn variant="text" size="small" @click="load">Retry</v-btn></v-alert>

        <v-sheet v-if="data && data.staples == 0" rounded="lg" border class="pa-5 mb-5 quick-staples">
            <div class="d-flex align-start ga-3">
                <v-icon icon="fa-solid fa-jar" color="primary" class="mt-1" />
                <div class="flex-grow-1">
                    <div class="font-weight-bold">First, the things you always keep</div>
                    <div class="text-body-2 text-medium-emphasis">Salt, oil, spices and baking basics aren’t tracked in the pantry, so without staples every recipe looks like it’s missing them. These are the ones your recipes use. Untick anything you don’t keep.</div>
                </div>
            </div>
            <v-progress-linear v-if="!foods" indeterminate class="my-4" />
            <div v-else class="d-flex flex-wrap ga-2 my-4">
                <v-chip v-for="f in suggestedFoods" :key="f.id" filter :model-value="quick.has(f.id)" :variant="quick.has(f.id) ? 'tonal' : 'outlined'"
                        :color="quick.has(f.id) ? 'primary' : undefined" @click="quick.has(f.id) ? quick.delete(f.id) : quick.add(f.id)">{{ f.name }}</v-chip>
            </div>
            <div class="d-flex flex-wrap ga-2">
                <v-btn color="primary" variant="flat" :disabled="quick.size == 0" :loading="savingQuick" @click="saveQuick">Save {{ quick.size }} {{ quick.size == 1 ? 'staple' : 'staples' }}</v-btn>
                <v-btn variant="text" @click="openStaples">Choose from everything</v-btn>
            </div>
        </v-sheet>

        <div v-if="data" class="d-flex flex-wrap align-center ga-3 mb-5">
            <v-btn-toggle v-model="filter" mandatory density="comfortable" variant="outlined" divided>
                <v-btn value="ready">Have everything <span class="count">{{ counts.ready }}</span></v-btn>
                <v-btn value="close">Missing 1–2 <span class="count">{{ counts.close }}</span></v-btn>
                <v-btn value="all">All <span class="count">{{ counts.all }}</span></v-btn>
            </v-btn-toggle>
            <span class="text-body-2 text-medium-emphasis">{{ data.in_stock }} {{ data.in_stock == 1 ? 'item' : 'items' }} in the pantry</span>
        </div>

        <v-row v-if="loading && !data">
            <v-col v-for="n in 6" :key="n" cols="12" sm="6" md="4"><v-skeleton-loader type="image, article" /></v-col>
        </v-row>

        <v-sheet v-else-if="data && shown.length == 0" rounded="lg" border class="pa-8 text-center text-medium-emphasis">
            <template v-if="filter == 'ready'">Nothing is fully ready yet. Try <a href="#" @click.prevent="filter = 'close'">missing 1–2</a>, or mark the staples you keep.</template>
            <template v-else>No recipes here.</template>
        </v-sheet>

        <v-row v-else>
            <v-col v-for="r in shown" :key="r.id" cols="12" sm="6" md="4">
                <v-card class="cook-card h-100" :to="{name: 'RecipeViewPage', params: {id: r.id}}">
                    <v-img v-if="r.image" :src="r.image" aspect-ratio="1.6" cover />
                    <div v-else class="no-image"><v-icon icon="$recipes" size="32" /></div>
                    <v-card-text>
                        <div class="text-subtitle-1 font-weight-bold mb-2 name">{{ r.name }}</div>
                        <div class="d-flex align-center justify-space-between text-body-2 mb-1">
                            <span><b>{{ r.have }}</b> of {{ r.total }} ingredients</span>
                            <span v-if="r.missing.length == 0" class="ready"><v-icon icon="fa-solid fa-check" size="x-small" class="me-1" />Ready</span>
                        </div>
                        <v-progress-linear :model-value="r.total ? 100 * r.have / r.total : 0" rounded height="6" :color="r.missing.length == 0 ? 'success' : 'primary'" bg-opacity=".12" />

                        <div v-if="r.expiring.length" class="mt-3 d-flex flex-wrap ga-1">
                            <v-chip v-for="e in r.expiring" :key="e.id" size="small" color="warning" variant="tonal" prepend-icon="fa-solid fa-hourglass-half">
                                {{ e.name }} · {{ expiresText(e.expires) }}
                            </v-chip>
                        </div>

                        <div v-if="r.missing.length" class="mt-3">
                            <div class="text-caption text-medium-emphasis mb-1">Need</div>
                            <div class="d-flex flex-wrap ga-1">
                                <v-menu v-for="m in r.missing.slice(0, expanded.has(r.id) ? 99 : 6)" :key="m.id">
                                    <template #activator="{props}">
                                        <v-chip v-bind="props" size="small" variant="outlined" @click.prevent.stop>{{ m.name }}</v-chip>
                                    </template>
                                    <v-list density="compact">
                                        <v-list-item prepend-icon="fa-solid fa-box-open" title="I have some now" subtitle="Add it to the pantry" @click="haveIt(m.id)" />
                                        <v-list-item prepend-icon="fa-solid fa-jar" title="I always have this" subtitle="Mark as a staple" @click="setStaple(m.id, true)" />
                                    </v-list>
                                </v-menu>
                                <v-chip v-if="r.missing.length > 6 && !expanded.has(r.id)" size="small" variant="text" @click.prevent.stop="expanded.add(r.id)">+{{ r.missing.length - 6 }} more</v-chip>
                            </div>
                        </div>
                    </v-card-text>
                </v-card>
            </v-col>
        </v-row>

        <v-dialog v-model="staplesOpen" max-width="560" scrollable>
            <v-card>
                <v-card-title class="pt-5 px-6">Staples</v-card-title>
                <v-card-subtitle class="px-6 text-wrap">Things you always keep in the kitchen. They count as in stock for every recipe, without tracking amounts.</v-card-subtitle>
                <div class="px-6 pt-4"><v-text-field v-model="stapleSearch" prepend-inner-icon="$search" label="Search ingredients" hide-details clearable density="compact" /></div>
                <v-card-text class="px-6" style="max-height: 60vh">
                    <v-progress-linear v-if="!foods" indeterminate />
                    <template v-else>
                        <template v-for="group in stapleGroups" :key="group.title">
                            <div v-if="group.items.length" class="staple-group">
                                <div class="d-flex align-center justify-space-between">
                                    <h3 class="text-subtitle-2 font-weight-bold">{{ group.title }}</h3>
                                    <v-btn v-if="group.all" variant="text" size="small" @click="markAll(group.items)">Mark all</v-btn>
                                </div>
                                <div v-for="f in group.items" :key="f.id" class="staple-row">
                                    <v-checkbox-btn :model-value="f.on_hand" :disabled="busy.has(f.id)" @update:model-value="(v: any) => setStaple(f.id, !!v)" :aria-label="f.name" />
                                    <span class="flex-grow-1 staple-name">{{ f.name }}</span>
                                    <span v-if="f.in_stock" class="badge">In pantry</span>
                                    <span class="text-caption text-medium-emphasis">{{ f.recipes }} {{ f.recipes == 1 ? 'recipe' : 'recipes' }}</span>
                                </div>
                            </div>
                        </template>
                    </template>
                </v-card-text>
                <v-card-actions class="px-6 pb-4"><v-spacer /><v-btn color="primary" variant="flat" @click="staplesOpen = false">Done</v-btn></v-card-actions>
            </v-card>
        </v-dialog>
    </v-container>
</template>

<script setup lang="ts">
// home fork: "Ready to Cook" (cookbook/views/home_cook.py)
import {computed, onMounted, reactive, ref, watch} from 'vue'
import {useDjangoUrls} from '@/composables/useDjangoUrls'
import {getCookie} from '@/utils/cookie'
import {daysUntil, pantryVersion} from '@/composables/useScan'

type Missing = { id: number, name: string }
type Cookable = { id: number, name: string, image: string | null, total: number, have: number, missing: Missing[], expiring: { id: number, name: string, expires: string }[] }
type StapleFood = { id: number, name: string, recipes: number, on_hand: boolean, in_stock: boolean, suggested: boolean }

const data = ref<{ recipes: Cookable[], staples: number, in_stock: number } | null>(null)
const loading = ref(false)
const error = ref(false)
const filter = ref<'ready' | 'close' | 'all'>('all')
const expanded = reactive(new Set<number>())

const staplesOpen = ref(false)
const foods = ref<StapleFood[] | null>(null)
const stapleSearch = ref('')
const busy = reactive(new Set<number>())
let changed = false

async function api(path: string, body?: any) {
    const {getDjangoUrl} = useDjangoUrls()
    const r = await fetch(getDjangoUrl(`api/home/${path}`), {
        method: body === undefined ? 'GET' : 'POST', credentials: 'same-origin',
        headers: {'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') ?? ''},
        body: body === undefined ? undefined : JSON.stringify(body),
    })
    if (!r.ok) throw new Error(`${r.status}`)
    return r.json()
}

const quick = reactive(new Set<number>())
const savingQuick = ref(false)
const suggestedFoods = computed(() => (foods.value ?? []).filter(f => f.suggested && !f.in_stock))

async function loadQuick() {
    try {
        foods.value = (await api('staples/')).foods
        quick.clear()
        suggestedFoods.value.forEach(f => quick.add(f.id))
    } catch {
        foods.value = []
    }
}

async function saveQuick() {
    savingQuick.value = true
    try {
        await api('staples/', {foods: [...quick], on_hand: true})
        await load()
    } catch {
        error.value = true
    } finally {
        savingQuick.value = false
    }
}

async function load() {
    loading.value = true
    error.value = false
    try {
        data.value = await api('cookable/')
        if (data.value?.staples == 0 && !staplesOpen.value) loadQuick()
    } catch {
        error.value = true
    } finally {
        loading.value = false
    }
}

const counts = computed(() => {
    const rs = data.value?.recipes ?? []
    return {ready: rs.filter(r => r.missing.length == 0).length, close: rs.filter(r => r.missing.length > 0 && r.missing.length <= 2).length, all: rs.length}
})

const shown = computed(() => {
    const rs = data.value?.recipes ?? []
    if (filter.value == 'ready') return rs.filter(r => r.missing.length == 0)
    if (filter.value == 'close') return rs.filter(r => r.missing.length > 0 && r.missing.length <= 2)
    return rs
})

function expiresText(iso: string) {
    const d = daysUntil(iso)
    if (d === null) return ''
    if (d < 0) return 'expired'
    if (d == 0) return 'expires today'
    if (d == 1) return 'expires tomorrow'
    return `expires in ${d} days`
}

async function openStaples() {
    staplesOpen.value = true
    stapleSearch.value = ''
    foods.value = null
    try {
        foods.value = (await api('staples/')).foods
    } catch {
        foods.value = []
    }
}

const stapleGroups = computed(() => {
    const q = (stapleSearch.value || '').trim().toLowerCase()
    const list = (foods.value ?? []).filter(f => !q || f.name.toLowerCase().includes(q))
    return [
        {title: 'Your staples', items: list.filter(f => f.on_hand), all: false},
        {title: 'Suggested', items: list.filter(f => !f.on_hand && f.suggested), all: true},
        {title: 'Everything else your recipes use', items: list.filter(f => !f.on_hand && !f.suggested), all: false},
    ]
})

// home fork: "I have it" books enough for any recipe into the pantry (home_restock.have)
async function haveIt(id: number) {
    busy.add(id)
    try {
        await api('have/', {food_id: id})
        await load()
    } catch {
        // the chip stays; nothing changed
    } finally {
        busy.delete(id)
    }
}

async function setStaple(id: number, on: boolean) {
    busy.add(id)
    try {
        await api('staples/', {food: id, on_hand: on})
        const f = foods.value?.find(x => x.id == id)
        if (f) f.on_hand = on
        changed = true
        if (!staplesOpen.value) await load()
    } catch {
        error.value = true
    } finally {
        busy.delete(id)
    }
}

async function markAll(items: StapleFood[]) {
    const ids = items.map(f => f.id)
    ids.forEach(id => busy.add(id))
    try {
        await api('staples/', {foods: ids, on_hand: true})
        items.forEach(f => f.on_hand = true)
        changed = true
    } catch {
        error.value = true
    } finally {
        ids.forEach(id => busy.delete(id))
    }
}

watch(staplesOpen, open => {
    if (!open && changed) {
        changed = false
        load()
    }
})
watch(pantryVersion, load)
onMounted(load)
</script>

<style scoped>
.cook-header { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 24px; margin: 16px 0 28px; }
.count { margin-left: 6px; font-size: .75rem; opacity: .65; }
.cook-card .name { line-height: 1.3; }
.no-image { aspect-ratio: 1.6; display: flex; align-items: center; justify-content: center; background: rgba(var(--v-theme-on-surface), .05); color: rgba(var(--v-theme-on-surface), .35); }
.ready { color: rgb(var(--v-theme-success)); font-weight: 600; font-size: .8125rem; }
.staple-group { margin-bottom: 16px; }
.staple-group h3 { margin: 8px 0 4px; }
.staple-row { display: flex; align-items: center; gap: 8px; min-height: 40px; text-align: start; }
.staple-row :deep(.v-selection-control) { flex: none; }
.badge { font-size: .75rem; padding: 1px 8px; border-radius: 6px; background: rgba(var(--v-theme-success), .12); color: rgb(var(--v-theme-success)); }
@media (max-width: 600px) {
    .cook-header { margin-top: 8px; gap: 16px; }
    .cook-header h1 { font-size: 1.75rem !important; }
}
</style>
