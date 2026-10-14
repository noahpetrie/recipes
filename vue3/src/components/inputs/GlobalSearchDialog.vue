<template>
    <slot name="activator">
        <v-btn @click="dialog = true" variant="plain" icon="fa-solid fa-search" class="mr-1 fa-fw d-print-none" v-if="mobile"></v-btn>
        <v-btn @click="dialog = true" variant="plain" class="d-print-none" v-else>
            <v-icon icon="fa-solid fa-search" class="mr-1 fa-fw"></v-icon>
            <span class="d-none d-sm-block">{{ $t('Search') }}</span>
            <v-chip size="x-small" variant="tonal" class="d-none d-md-flex ml-1" label>{{ isMac ? '⌘K' : $t('Ctrl+K') }}</v-chip>
        </v-btn>
    </slot>

    <!-- home fork: a command menu — pages, recipes, foods in the pantry or database, and books -->
    <v-dialog v-model="dialog" :max-width="mobile ? '100vw' : '640px'" :fullscreen="mobile" location="top" class="cmdk-dialog">
        <v-card class="global-search cmdk">
            <div class="cmdk-input">
                <v-icon icon="fa-solid fa-magnifying-glass" size="small" />
                <input id="id_global_search_input" v-model="searchQuery" autocomplete="off" spellcheck="false"
                       placeholder="Go to a page, recipe, food or book…" @keydown="onInputKey" />
                <v-btn v-if="mobile" variant="text" size="small" @click="dialog = false">{{ $t('Close') }}</v-btn>
                <kbd v-else>esc</kbd>
            </div>

            <div class="cmdk-list" ref="listEl">
                <template v-for="g in groups" :key="g.title">
                    <div class="cmdk-group">{{ g.title }}</div>
                    <button v-for="item in g.items" :key="item.key" type="button" class="cmdk-item" :class="{active: item.index == selected}"
                            :data-index="item.index" @mousemove="selected = item.index!" @click="open(item)">
                        <span class="cmdk-icon">
                            <img v-if="item.image && !broken.has(item.key)" :src="item.image" alt="" @error="broken.add(item.key)" />
                            <v-icon v-else :icon="item.icon" size="small" />
                        </span>
                        <span class="cmdk-name">{{ item.name }}</span>
                        <span v-if="item.hint" class="cmdk-hint">{{ item.hint }}</span>
                    </button>
                </template>
                <div v-if="query && results.length == 1 && !loading" class="cmdk-empty">Nothing else matches “{{ searchQuery }}”.</div>
            </div>

            <div class="cmdk-footer d-none d-sm-flex">
                <span><kbd>↑</kbd><kbd>↓</kbd> to move</span>
                <span><kbd>↵</kbd> to open</span>
                <span><kbd>esc</kbd> to close</span>
            </div>
        </v-card>
    </v-dialog>
</template>

<script setup lang="ts">
import {computed, nextTick, onMounted, onUnmounted, reactive, ref, watch} from 'vue'
import {ApiApi, Food, RecipeBook, RecipeFlat} from "@/openapi";
import {RouteLocationRaw, useRouter} from "vue-router";
import {useDisplay} from "vuetify";
import {ErrorMessageType, useMessageStore} from "@/stores/MessageStore";
import {useDebouncedSearch} from "@/composables/useDebouncedSearch";
import {useDjangoUrls} from "@/composables/useDjangoUrls";

type Item = { key: string, name: string, icon?: string, image?: string | null, hint?: string, to: RouteLocationRaw, index?: number }

const router = useRouter()
const {mobile} = useDisplay()
const isMac = /Mac|iPhone|iPad/.test(navigator.platform || navigator.userAgent)

const dialog = ref(false)
const flatRecipes = ref([] as RecipeFlat[])
const {inputValue: searchQuery, debouncedValue: debouncedSearchQuery, signal, reset: resetSearch} = useDebouncedSearch()
const selected = ref(0)
const foods = ref([] as Food[])
const books = ref([] as RecipeBook[])
const loading = ref(false)
const inStock = ref(new Set<number>())
const listEl = ref<HTMLElement | null>(null)
// pictures that fail to load show the icon instead
const broken = reactive(new Set<string>())

// other words people use for each page
const PAGES: (Item & { words: string })[] = [
    {key: 'p-home', name: 'Home', icon: 'fa-solid fa-house', to: {name: 'StartPage'}, words: 'start'},
    {key: 'p-plan', name: 'Meal Plan', icon: '$mealplan', to: {name: 'MealPlanPage'}, words: 'planner calendar week dinner schedule'},
    {key: 'p-cook', name: 'Ready to Cook', icon: 'fa-solid fa-fire-burner', to: {name: 'CookNowPage'}, words: 'cook now what can i make staples'},
    {key: 'p-map', name: 'Food map', icon: 'fa-solid fa-earth-americas', to: {name: 'FoodMapPage'}, words: 'map world countries origin cuisine where from'},
    {key: 'p-shop', name: 'Shopping list', icon: '$shopping', to: {name: 'ShoppingListPage'}, words: 'shopping buy groceries list'},
    {key: 'p-pantry', name: 'Pantry', icon: '$pantry', to: {name: 'PantryPage'}, words: 'inventory stock fridge freezer'},
    {key: 'p-groceries', name: 'Add groceries', icon: 'fa-solid fa-basket-shopping', to: {name: 'GroceriesPage'}, words: 'bought receipt order restock'},
    {key: 'p-activity', name: 'Pantry activity', icon: 'fa-solid fa-clock-rotate-left', to: {name: 'PantryActivityPage'}, words: 'history log undo'},
    {key: 'p-books', name: 'Books', icon: '$books', to: {name: 'BooksPage'}, words: 'cookbooks library'},
    {key: 'p-search', name: 'All recipes', icon: '$recipes', to: {name: 'SearchPage'}, words: 'recipes search browse filter'},
    {key: 'p-new', name: 'New recipe', icon: 'fa-solid fa-plus', to: {name: 'ModelEditPage', params: {model: 'Recipe'}}, words: 'create add write'},
    {key: 'p-import', name: 'Import recipe', icon: '$import', to: {name: 'RecipeImportPage'}, words: 'url link website add'},
    {key: 'p-foods', name: 'Foods', icon: 'fa-solid fa-carrot', to: {name: 'ModelListPage', params: {model: 'Food'}}, words: 'ingredients database'},
    {key: 'p-database', name: 'Database', icon: 'fa-solid fa-database', to: {name: 'DatabasePage'}, words: 'units keywords supermarkets aisles'},
    {key: 'p-settings', name: 'Settings', icon: '$settings', to: {name: 'SettingsPage'}, words: 'preferences account options'},
    {key: 'p-shop-settings', name: 'Shopping settings', icon: '$settings', to: {name: 'ShoppingSettings'}, words: 'shopping options'},
    {key: 'p-plan-settings', name: 'Meal plan settings', icon: '$settings', to: {name: 'MealPlanSettings'}, words: 'meal types planner options'},
    {key: 'p-household', name: 'Household', icon: 'fa-solid fa-people-roof', to: {name: 'HouseholdPage'}, words: 'family members users invite'},
]

const query = computed(() => (searchQuery.value || '').trim().toLowerCase())

/** every word typed appears at the start of a word in the text */
function matches(text: string, q: string) {
    const words = text.toLowerCase().split(/[^a-z0-9]+/)
    return q.split(/\s+/).every(w => words.some(x => x.startsWith(w)) || text.toLowerCase().includes(w))
}

const groups = computed(() => {
    const q = query.value
    const out: { title: string, items: Item[] }[] = []
    const pages = q ? PAGES.filter(p => matches(p.name + ' ' + p.words, q)) : PAGES.slice(0, 7)
    if (pages.length) out.push({title: 'Pages', items: pages.slice(0, q ? 5 : 7)})

    const recipes = (q ? flatRecipes.value.filter(r => matches(r.name, q)) : flatRecipes.value).slice(0, q ? 8 : 5)
    if (recipes.length) out.push({title: 'Recipes', items: recipes.map(r => ({key: 'r' + r.id, name: r.name, image: r.image, icon: '$recipes', to: {name: 'RecipeViewPage', params: {id: r.id}}}))})

    if (q) {
        const fs = foods.value.slice(0, 6)
        if (fs.length) out.push({
            title: 'Foods', items: fs.map(f => inStock.value.has(f.id!)
                ? {key: 'f' + f.id, name: f.name, image: f.productImage, icon: '$pantry', hint: 'In the pantry', to: {name: 'PantryPage', query: {food: f.id}}}
                : {key: 'f' + f.id, name: f.name, image: f.productImage, icon: 'fa-solid fa-carrot', hint: 'Food', to: {name: 'ModelEditPage', params: {model: 'Food', id: f.id}}})
        })
        if (books.value.length) out.push({title: 'Books', items: books.value.slice(0, 4).map(b => ({key: 'b' + b.id, name: b.name, icon: '$books', to: {name: 'BookViewPage', params: {bookId: b.id}}}))})
        out.push({title: 'Search', items: [{key: 'search', name: `Search recipes for “${searchQuery.value.trim()}”`, icon: 'fa-solid fa-magnifying-glass', to: {name: 'SearchPage', query: {query: searchQuery.value.trim()}}}]})
    }
    let i = 0
    out.forEach(g => g.items = g.items.map(it => ({...it, index: i++})))
    return out
})
const results = computed(() => groups.value.flatMap(g => g.items))

watch(results, () => { selected.value = 0 })
watch(selected, async i => {
    await nextTick()
    listEl.value?.querySelector(`[data-index="${i}"]`)?.scrollIntoView({block: 'nearest'})
})

watch(dialog, open => {
    resetSearch()
    foods.value = []
    books.value = []
    selected.value = 0
    if (open) {
        setTimeout(() => document.getElementById('id_global_search_input')?.focus(), 20)
        loadStock()
    }
})

function onInputKey(e: KeyboardEvent) {
    if (e.key == 'ArrowDown') {
        e.preventDefault()
        selected.value = Math.min(results.value.length - 1, selected.value + 1)
    } else if (e.key == 'ArrowUp') {
        e.preventDefault()
        selected.value = Math.max(0, selected.value - 1)
    } else if (e.key == 'Enter') {
        e.preventDefault()
        const item = results.value[selected.value]
        if (item) open(item)
    }
}

function open(item: Item) {
    dialog.value = false
    router.push(item.to)
}

function handleKeydown(e: KeyboardEvent) {
    // Cmd+K on macOS, Ctrl+K elsewhere (accept either so external keyboards work too)
    if (e.key.toLowerCase() == 'k' && (e.ctrlKey || e.metaKey)) {
        e.preventDefault()
        dialog.value = !dialog.value
    }
}

async function loadStock() {
    try {
        const r = await fetch(useDjangoUrls().getDjangoUrl('api/home/kitchen/'), {credentials: 'same-origin'})
        if (r.ok) {
            const d = await r.json()
            inStock.value = new Set(d.stocked)
        }
    } catch {
        // foods then open in the database instead of the pantry
    }
}

onMounted(() => {
    window.addEventListener('keydown', handleKeydown)
    new ApiApi().apiRecipeFlatList().then(r => {
        flatRecipes.value = r
    }).catch(err => {
        useMessageStore().addError(ErrorMessageType.FETCH_ERROR, err)
    })
})

onUnmounted(() => {
    window.removeEventListener('keydown', handleKeydown)
})

/** foods and books come from the server once typing pauses */
watch(debouncedSearchQuery, val => {
    if (!val) return
    const api = new ApiApi()
    loading.value = true
    Promise.all([
        api.apiFoodList({query: val, pageSize: 10}, {signal: signal.value}).then(r => foods.value = r.results),
        api.apiRecipeBookList({query: val, pageSize: 4}, {signal: signal.value}).then(r => books.value = r.results),
    ]).catch(err => {
        if (err.name !== 'AbortError' && err.cause?.name !== 'AbortError') {
            useMessageStore().addError(ErrorMessageType.FETCH_ERROR, err)
        }
    }).finally(() => {
        loading.value = false
    })
})
</script>

<style>
.cmdk-dialog > .v-overlay__content { margin-top: 12vh !important; }
.cmdk { border-radius: 12px !important; overflow: hidden; display: flex; flex-direction: column; max-height: 70vh; }
.v-dialog--fullscreen .cmdk { max-height: none; border-radius: 0 !important; }
.cmdk-input { display: flex; align-items: center; gap: 10px; padding: 12px 16px; border-bottom: 1px solid var(--home-hairline, rgba(0, 0, 0, .08)); color: rgba(var(--v-theme-on-surface), .55); }
.cmdk-input input { flex: 1; min-width: 0; border: 0; outline: 0; background: transparent; font-size: 1rem; color: rgb(var(--v-theme-on-surface)); padding: 4px 0; }
.cmdk-list { overflow-y: auto; padding: 6px 8px 8px; flex: 1; }
.cmdk-group { font-size: .75rem; font-weight: 500; color: rgba(var(--v-theme-on-surface), .55); padding: 10px 8px 4px; }
.cmdk-item { display: flex; align-items: center; gap: 12px; width: 100%; text-align: left; padding: 7px 8px; border-radius: 8px; color: rgb(var(--v-theme-on-surface)); font-size: .9375rem; }
.cmdk-item.active { background: rgba(var(--v-theme-on-surface), .06); }
.cmdk-icon { width: 28px; height: 28px; flex: none; display: flex; align-items: center; justify-content: center; border-radius: 6px; overflow: hidden; color: rgba(var(--v-theme-on-surface), .6); }
.cmdk-icon img { width: 100%; height: 100%; object-fit: cover; }
.cmdk-name { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.cmdk-hint { font-size: .75rem; color: rgba(var(--v-theme-on-surface), .5); flex: none; }
.cmdk-empty { padding: 10px 8px; font-size: .875rem; color: rgba(var(--v-theme-on-surface), .55); }
.cmdk-footer { gap: 16px; padding: 8px 16px; border-top: 1px solid var(--home-hairline, rgba(0, 0, 0, .08)); font-size: .75rem; color: rgba(var(--v-theme-on-surface), .55); }
.cmdk kbd { font-family: inherit; font-size: .6875rem; border: 1px solid var(--home-hairline, rgba(0, 0, 0, .12)); border-radius: 4px; padding: 0 5px; margin-right: 3px; background: rgba(var(--v-theme-on-surface), .03); }
</style>
