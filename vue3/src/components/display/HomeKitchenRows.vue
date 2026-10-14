<template>
    <!-- home fork: the start page's kitchen rows, from "Ready to Cook" (cookbook/views/home_cook.py) -->
    <div v-if="data" class="kitchen-rows mt-4">
        <v-sheet v-if="data.staples == 0 || data.in_stock == 0" rounded="lg" border class="pa-4 mb-6 d-flex align-center flex-wrap ga-3">
            <v-icon icon="fa-solid fa-fire-burner" color="primary" />
            <div class="flex-grow-1" style="min-width: 220px">
                <div class="font-weight-medium">See what you can cook tonight</div>
                <div class="text-body-2 text-medium-emphasis">
                    <template v-if="data.staples == 0">Mark the staples you always keep, then </template>add what you bought, and Kitchen shows which recipes you can make.
                </div>
            </div>
            <v-btn v-if="data.staples == 0" variant="outlined" :to="{name: 'CookNowPage'}">Choose staples</v-btn>
            <v-btn color="primary" variant="flat" prepend-icon="fa-solid fa-basket-shopping" :to="{name: 'GroceriesPage'}">Add groceries</v-btn>
        </v-sheet>

        <section v-for="row in rows" :key="row.key" class="mb-6">
            <!-- same heading as the recipe rows below (HorizontalRecipeWindow) -->
            <router-link :to="{name: 'CookNowPage'}" class="row-title">
                <h4><i :class="row.icon + ' fa-fw'"></i> {{ row.title }} <span class="ms-2 text-body-2">More <i class="fa-solid fa-chevron-right"></i></span></h4>
            </router-link>
            <div class="home-grid" :style="{gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))`}">
                <home-recipe-tile v-for="r in row.recipes" :key="r.id" :recipe="r">
                    <template #status>
                        <span v-if="row.key == 'use' && r.expiring.length" class="text-warning" :title="r.expiring.map(e => e.name).join(', ')">
                            <v-icon icon="fa-solid fa-hourglass-half" size="x-small" class="me-1" />{{ r.expiring.map(e => e.name).join(', ') }}
                        </span>
                        <span v-else-if="r.missing.length == 0" class="text-success"><v-icon icon="fa-solid fa-check" size="x-small" class="me-1" />You have everything</span>
                        <span v-else class="text-medium-emphasis" :title="`Need ${r.missing.map(m => m.name).join(', ')}`">
                            <v-icon icon="fa-solid fa-cart-shopping" size="x-small" class="me-1" />Need {{ r.missing.map(m => m.name).join(', ') }}
                        </span>
                    </template>
                </home-recipe-tile>
            </div>
        </section>
    </div>
</template>

<script setup lang="ts">
import HomeRecipeTile from '@/components/display/HomeRecipeTile.vue'
import {useHomeCols} from '@/composables/useHomeCols'
import {computed, onMounted, ref, watch, watchEffect} from 'vue'
import {useDjangoUrls} from '@/composables/useDjangoUrls'
import {pantryVersion} from '@/composables/useScan'
import {useHomeShown} from '@/composables/useHomeShown'

type Cookable = { id: number, name: string, image: string | null, total: number, have: number, missing: { id: number, name: string }[], expiring: { id: number, name: string, expires: string }[] }

const cols = useHomeCols()
const data = ref<{ recipes: Cookable[], staples: number, in_stock: number } | null>(null)

async function load() {
    try {
        const r = await fetch(useDjangoUrls().getDjangoUrl('api/home/cookable/'), {credentials: 'same-origin'})
        if (r.ok) data.value = await r.json()
    } catch {
        // the rest of the start page works without these rows
    }
}

const rows = computed(() => {
    const rs = data.value?.recipes ?? []
    const out = []
    const use = rs.filter(r => r.expiring.length)
    if (use.length) out.push({key: 'use', title: 'Use it up', icon: 'fa-solid fa-hourglass-half', recipes: use.slice(0, cols.value)})
    const ready = rs.filter(r => r.missing.length == 0 && !r.expiring.length)
    if (ready.length) out.push({key: 'ready', title: 'Ready to cook', icon: 'fa-solid fa-check', recipes: ready.slice(0, cols.value)})
    else if (data.value?.staples || data.value?.in_stock) {
        const close = rs.filter(r => r.missing.length > 0 && r.missing.length <= 2)
        if (close.length) out.push({key: 'close', title: 'Almost ready', icon: 'fa-solid fa-cart-shopping', recipes: close.slice(0, cols.value)})
    }
    return out
})

// the recipe rows below skip these
const homeShown = useHomeShown(0)
watchEffect(() => homeShown.claim(rows.value.flatMap(row => row.recipes.map(r => r.id))))

watch(pantryVersion, load)
onMounted(load)
</script>

<style scoped>
.home-grid { display: grid; gap: 16px; padding: 0 2px; }
.row-title { color: inherit; text-decoration: none; display: block; margin-bottom: 8px; }
</style>
