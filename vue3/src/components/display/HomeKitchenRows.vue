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
            <v-row dense>
                <v-col v-for="r in row.recipes" :key="r.id" cols="6" sm="4" md="3">
                    <v-card class="h-100 kitchen-card" variant="flat" :to="{name: 'RecipeViewPage', params: {id: r.id}}">
                        <v-img v-if="r.image" :src="r.image" aspect-ratio="1.6" cover rounded="lg" />
                        <div v-else class="no-image rounded-lg"><v-icon icon="$recipes" size="28" /></div>
                        <div class="pt-2">
                            <div class="font-weight-bold name">{{ r.name }}</div>
                            <div class="text-caption mt-1">
                                <span v-if="row.key == 'use' && r.expiring.length" class="text-warning">
                                    <v-icon icon="fa-solid fa-hourglass-half" size="x-small" class="me-1" />{{ r.expiring.map(e => e.name).join(', ') }}
                                </span>
                                <span v-else-if="r.missing.length == 0" class="text-success"><v-icon icon="fa-solid fa-check" size="x-small" class="me-1" />You have everything</span>
                                <span v-else class="text-medium-emphasis">Need {{ r.missing.map(m => m.name).join(', ') }}</span>
                            </div>
                        </div>
                    </v-card>
                </v-col>
            </v-row>
        </section>
    </div>
</template>

<script setup lang="ts">
import {computed, onMounted, ref, watch, watchEffect} from 'vue'
import {useDjangoUrls} from '@/composables/useDjangoUrls'
import {pantryVersion} from '@/composables/useScan'
import {useHomeShown} from '@/composables/useHomeShown'

type Cookable = { id: number, name: string, image: string | null, total: number, have: number, missing: { id: number, name: string }[], expiring: { id: number, name: string, expires: string }[] }

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
    if (use.length) out.push({key: 'use', title: 'Use it up', icon: 'fa-solid fa-hourglass-half', recipes: use.slice(0, 4)})
    const ready = rs.filter(r => r.missing.length == 0 && !r.expiring.length)
    if (ready.length) out.push({key: 'ready', title: 'Ready to cook', icon: 'fa-solid fa-check', recipes: ready.slice(0, 4)})
    else if (data.value?.staples || data.value?.in_stock) {
        const close = rs.filter(r => r.missing.length > 0 && r.missing.length <= 2)
        if (close.length) out.push({key: 'close', title: 'Almost ready', icon: 'fa-solid fa-cart-shopping', recipes: close.slice(0, 4)})
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
.kitchen-card { background: transparent; }
.row-title { color: inherit; text-decoration: none; display: block; margin-bottom: 8px; }
.kitchen-card .name { line-height: 1.3; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.no-image { aspect-ratio: 1.6; display: flex; align-items: center; justify-content: center; background: rgba(var(--v-theme-on-surface), .05); color: rgba(var(--v-theme-on-surface), .35); }
</style>
