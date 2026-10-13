<template>
    <!-- home fork: foods due again by how often they're bought (cookbook/views/home_restock.py) -->
    <v-sheet v-if="due.length || held.length" rounded="lg" border class="restock pa-4 mb-4">
        <div class="d-flex align-center justify-space-between flex-wrap ga-2">
            <div>
                <h2 class="text-subtitle-1 font-weight-bold"><v-icon icon="fa-solid fa-arrows-rotate" size="small" class="me-2" />Due to restock</h2>
                <p class="text-body-2 text-medium-emphasis">Things you buy regularly that aren’t in the pantry or on the list.</p>
            </div>
            <v-btn v-if="due.length > 1" size="small" variant="outlined" prepend-icon="fa-solid fa-cart-plus" :loading="busy == 'all'" @click="addAll">Add all {{ due.length }}</v-btn>
        </div>
        <v-alert v-if="away && held.length" type="info" variant="tonal" density="compact" class="mt-3" icon="fa-solid fa-suitcase-rolling">
            {{ away.title }} from {{ fmtDate(away.from) }}: fresh things are held back so they don’t spoil while you’re away.
        </v-alert>

        <div class="restock-grid mt-3">
            <div v-for="i in shown" :key="i.food.id" class="restock-item">
                <pantry-product-image small :src="i.food.image || i.product.image" />
                <div class="min-w-0 flex-grow-1">
                    <div class="font-weight-medium text-truncate">{{ i.food.name }}</div>
                    <div class="text-caption text-medium-emphasis">Every {{ span(i.every_days) }} · last {{ ago(i.since_days) }}</div>
                    <a v-if="i.product.url" :href="i.product.url" target="_blank" rel="noopener" class="store-link text-truncate d-block">
                        <v-icon icon="fa-solid fa-store" size="x-small" class="me-1" />{{ i.product.name }}
                    </a>
                </div>
                <div class="d-flex align-center">
                    <v-btn icon="fa-solid fa-cart-plus" size="small" variant="text" color="primary" :loading="busy == i.food.id" :aria-label="`Add ${i.food.name} to the list`" title="Add to the list" @click="add(i)" />
                    <v-menu>
                        <template #activator="{props}"><v-btn v-bind="props" icon="fa-solid fa-ellipsis-vertical" size="small" variant="text" :aria-label="`More for ${i.food.name}`" /></template>
                        <v-list density="compact">
                            <v-list-item prepend-icon="fa-solid fa-box-open" title="I have it" subtitle="Add it to the pantry" @click="have(i)" />
                            <v-list-item prepend-icon="fa-solid fa-clock" title="Not now" subtitle="Hide for 2 weeks" @click="snooze(i)" />
                        </v-list>
                    </v-menu>
                </div>
            </div>
        </div>
        <v-btn v-if="due.length > LIMIT && !showAll" variant="text" size="small" class="mt-2" @click="showAll = true">Show all {{ due.length }}</v-btn>

        <details v-if="held.length" class="mt-3 held">
            <summary class="text-body-2">Held until you’re back ({{ held.length }}): {{ held.map(i => i.food.name).join(', ') }}</summary>
            <div class="restock-grid mt-2">
                <div v-for="i in held" :key="i.food.id" class="restock-item">
                    <pantry-product-image small :src="i.food.image || i.product.image" />
                    <div class="min-w-0 flex-grow-1">
                        <div class="font-weight-medium text-truncate">{{ i.food.name }}</div>
                        <div class="text-caption text-medium-emphasis">Every {{ span(i.every_days) }} · last {{ ago(i.since_days) }}</div>
                    </div>
                    <v-btn icon="fa-solid fa-cart-plus" size="small" variant="text" :loading="busy == i.food.id" :aria-label="`Add ${i.food.name} anyway`" title="Add anyway" @click="add(i)" />
                </div>
            </div>
        </details>
    </v-sheet>
</template>

<script setup lang="ts">
import {computed, onMounted, ref} from 'vue'
import {useDisplay} from 'vuetify'
import PantryProductImage from '@/components/display/PantryProductImage.vue'
import {haveFood, homeApi, loadStoreLinks} from '@/composables/useHomeShop'
import {fmtDate, pantryApi} from '@/composables/useScan'
import {useShoppingStore} from '@/stores/ShoppingStore'
import {MessageType, useMessageStore} from '@/stores/MessageStore'

type Item = { food: { id: number, name: string, image: string, aisle: string | null }, product: { name: string, url: string, image: string },
    every_days: number, since_days: number, last_bought: string, times: number, fresh: boolean, hold: boolean }

const {smAndDown} = useDisplay()
// a few on a phone so the list itself stays in view
const LIMIT = computed(() => smAndDown.value ? 3 : 8)
const SNOOZE_KEY = 'home_restock_snooze'
const items = ref<Item[]>([])
const away = ref<{ title: string, from: string, to: string } | null>(null)
const busy = ref<number | 'all' | null>(null)
const showAll = ref(false)
const snoozed = ref<Record<number, number>>(readSnoozed())

function readSnoozed(): Record<number, number> {
    try {
        const all = JSON.parse(localStorage.getItem(SNOOZE_KEY) || '{}')
        return Object.fromEntries(Object.entries(all).filter(([, until]) => (until as number) > Date.now())) as any
    } catch { return {} }
}

const visible = computed(() => items.value.filter(i => !snoozed.value[i.food.id]))
const due = computed(() => visible.value.filter(i => !i.hold))
const held = computed(() => visible.value.filter(i => i.hold))
const shown = computed(() => showAll.value ? due.value : due.value.slice(0, LIMIT.value))

function span(days: number) {
    if (days < 14) return `${days} days`
    if (days < 60) return `${Math.round(days / 7)} weeks`
    return `${Math.round(days / 30)} months`
}
function ago(days: number) {
    return days == 0 ? 'today' : days == 1 ? 'yesterday' : `${span(days)} ago`
}

async function load() {
    try {
        const r = await homeApi('restock/')
        items.value = r.items
        away.value = r.away
    } catch {
        items.value = []
    }
}

async function refreshList() {
    await useShoppingStore().refreshFromAPI()
    loadStoreLinks()
}

async function add(i: Item) {
    busy.value = i.food.id
    try {
        await pantryApi('catalog/', {food_id: i.food.id})
        items.value = items.value.filter(x => x.food.id != i.food.id)
        await refreshList()
    } catch (e: any) {
        useMessageStore().addMessage(MessageType.ERROR, e?.message || `Couldn’t add ${i.food.name}.`, 5000)
    } finally { busy.value = null }
}

async function addAll() {
    busy.value = 'all'
    try {
        for (const i of [...due.value]) {
            await pantryApi('catalog/', {food_id: i.food.id})
            items.value = items.value.filter(x => x.food.id != i.food.id)
        }
        await refreshList()
    } catch (e: any) {
        useMessageStore().addMessage(MessageType.ERROR, e?.message || 'Couldn’t add them all.', 5000)
    } finally { busy.value = null }
}

async function have(i: Item) {
    busy.value = i.food.id
    try {
        useMessageStore().addMessage(MessageType.SUCCESS, await haveFood(i.food.id), 4000)
        items.value = items.value.filter(x => x.food.id != i.food.id)
    } catch (e: any) {
        useMessageStore().addMessage(MessageType.ERROR, e?.message || 'Couldn’t add it to the pantry.', 5000)
    } finally { busy.value = null }
}

function snooze(i: Item) {
    snoozed.value = {...snoozed.value, [i.food.id]: Date.now() + 14 * 86400000}
    try { localStorage.setItem(SNOOZE_KEY, JSON.stringify(snoozed.value)) } catch { /* only this visit */ }
}

defineExpose({load})
onMounted(load)
</script>

<style scoped>
.restock-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 8px; }
.restock-item { display: flex; align-items: center; gap: 12px; padding: 8px 4px 8px 8px; border: 1px solid rgba(var(--v-theme-on-surface), .1); border-radius: 12px; min-width: 0; overflow: hidden; }
.store-link { display: block; max-width: 100%; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; font-size: .75rem; color: rgba(var(--v-theme-on-surface), .6); text-decoration: none; }
.store-link:hover { color: rgb(var(--v-theme-primary)); text-decoration: underline; }
.held summary { cursor: pointer; color: rgba(var(--v-theme-on-surface), .7); }
.min-w-0 { min-width: 0; }
</style>
