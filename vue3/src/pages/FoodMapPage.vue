<template>
    <!-- home fork: where the recipes come from (Recipe.origin_country), and which of them you've made -->
    <v-container class="map-page">
        <header class="d-flex align-center ga-4 mb-4">
            <v-avatar rounded color="primary" variant="tonal" size="48"><v-icon icon="fa-solid fa-earth-americas" /></v-avatar>
            <div>
                <h1 class="text-h4 font-weight-bold">Food map</h1>
                <p class="text-body-2 text-medium-emphasis mt-1">Where the dishes you’ve made come from.</p>
            </div>
        </header>

        <v-alert v-if="error" type="error" variant="tonal" class="mb-4">Couldn’t load the map. <v-btn variant="text" size="small" @click="load">Retry</v-btn></v-alert>

        <div v-if="countries.length" class="d-flex flex-wrap align-center ga-4 mb-3">
            <div class="stat"><span class="stat-n">{{ madeCountries.length }}</span> {{ madeCountries.length == 1 ? 'country' : 'countries' }} cooked</div>
            <div class="stat"><span class="stat-n">{{ toTryCountries.length }}</span> more to try</div>
            <div class="legend ms-auto">
                <span><i class="swatch made" />Made</span>
                <span><i class="swatch try" />Recipes to try</span>
            </div>
        </div>

        <v-sheet rounded="lg" border class="map-wrap mb-5" ref="wrap">
            <v-progress-linear v-if="!shapes.length" indeterminate />
            <template v-else>
            <svg :viewBox="viewBox" class="map" role="img" aria-label="World map of recipe origins">
                <path v-for="s in shapes" :key="s.key" :d="s.d" class="land" :class="[stateOf(s.code), {selected: s.code && s.code == selected}]"
                      @click="select(s.code)">
                    <title>{{ tooltip(s.code, s.name) }}</title>
                </path>
            </svg>
            <v-btn-toggle v-model="area" mandatory density="compact" variant="outlined" divided class="zoom">
                <v-btn v-for="(_, name) in AREAS" :key="name" :value="name" size="small">{{ name }}</v-btn>
            </v-btn-toggle>
            </template>
        </v-sheet>

        <v-sheet v-if="!loading && !countries.length && !error" rounded="lg" border class="pa-8 text-center text-medium-emphasis">
            No recipes have a country yet. Edit a recipe and choose its <b>Country of origin</b>, like France for French Onion Soup.
        </v-sheet>

        <div class="country-grid">
            <v-card v-for="c in sorted" :key="c.code" :id="`country-${c.code}`" class="country" :class="{selected: c.code == selected}" variant="outlined" @click="select(c.code, false)">
                <div class="d-flex align-center ga-3 pa-3 pb-1">
                    <span class="country-flag">{{ flag(c.code) }}</span>
                    <div class="flex-grow-1 min-w-0">
                        <div class="font-weight-bold text-truncate">{{ countryName(c.code) }}</div>
                        <div class="text-caption text-medium-emphasis">{{ summary(c) }}</div>
                    </div>
                </div>
                <v-list density="compact" class="py-0">
                    <v-list-item v-for="r in c.recipes" :key="r.id" :to="{name: 'RecipeViewPage', params: {id: r.id}}" @click.stop>
                        <template #prepend>
                            <v-avatar size="32" rounded class="me-2">
                                <v-img v-if="r.image" :src="r.image" cover />
                                <v-icon v-else icon="$recipes" size="small" />
                            </v-avatar>
                        </template>
                        <v-list-item-title>{{ r.name }}</v-list-item-title>
                        <v-list-item-subtitle>{{ [r.region, made(r)].filter(Boolean).join(' · ') }}</v-list-item-subtitle>
                        <template #append>
                            <v-chip v-if="r.last_cooked" size="x-small" color="success" variant="tonal">Made</v-chip>
                            <v-chip v-else size="x-small" variant="outlined">To try</v-chip>
                        </template>
                    </v-list-item>
                </v-list>
            </v-card>
        </div>
    </v-container>
</template>

<script setup lang="ts">
import {computed, nextTick, onMounted, ref, shallowRef} from 'vue'
import {useRoute, useRouter} from 'vue-router'
import {geoEqualEarth, geoPath} from 'd3-geo'
import {feature} from 'topojson-client'
import {codeForShape, countryName, flag} from '@/utils/countries'
import {homeApi} from '@/composables/useHomeShop'

type OriginRecipe = {id: number, name: string, image: string | null, region: string, last_cooked: string | null, times: number}
type Country = {code: string, recipes: OriginRecipe[]}

const W = 960, H = 470
const route = useRoute()
const router = useRouter()
const countries = ref<Country[]>([])
const shapes = shallowRef<{key: string, code?: string, name: string, d: string}[]>([])
const area = ref('World')
let project: ((p: [number, number]) => [number, number] | null) | undefined
const loading = ref(true)
const error = ref(false)
const selected = ref<string | undefined>((route.query.country as string)?.toUpperCase() || undefined)

const byCode = computed(() => new Map(countries.value.map(c => [c.code, c])))
const isMade = (c: Country) => c.recipes.some(r => r.last_cooked)
const madeCountries = computed(() => countries.value.filter(isMade))
const toTryCountries = computed(() => countries.value.filter(c => !isMade(c)))
// the chosen country first, then the ones you've cooked, then the rest by name
const sorted = computed(() => [...countries.value].sort((a, b) =>
    Number(b.code == selected.value) - Number(a.code == selected.value) || Number(isMade(b)) - Number(isMade(a)) || countryName(a.code).localeCompare(countryName(b.code))))

function stateOf(code?: string) {
    const c = code ? byCode.value.get(code) : undefined
    return !c ? '' : isMade(c) ? 'made' : 'try'
}

function summary(c: Country) {
    const m = c.recipes.filter(r => r.last_cooked).length, t = c.recipes.length - m
    return [m ? `${m} made` : '', t ? `${t} to try` : ''].filter(Boolean).join(' · ')
}

function tooltip(code: string | undefined, name: string) {
    const c = code ? byCode.value.get(code) : undefined
    return `${code ? countryName(code) : name}${c ? ` — ${summary(c)}` : ''}`
}

function made(r: OriginRecipe) {
    if (!r.last_cooked) return ''
    return `made ${r.times > 1 ? `${r.times}× · last ` : ''}${new Date(r.last_cooked).toLocaleDateString(undefined, {month: 'short', year: 'numeric'})}`
}

// zoom presets as [west, south, east, north]; Europe is too small to tap at world scale
const AREAS: Record<string, [number, number, number, number] | null> = {
    World: null, Americas: [-170, -56, -30, 72], Europe: [-25, 34, 45, 71], Africa: [-20, -36, 55, 38], Asia: [25, -11, 150, 56],
}
const viewBox = computed(() => {
    const b = AREAS[area.value]
    if (!b || !project || !shapes.value.length) return `0 0 ${W} ${H}`
    const pts: [number, number][] = []
    for (let i = 0; i <= 10; i++) for (const [lon, lat] of [[b[0] + (b[2] - b[0]) * i / 10, b[1]], [b[0] + (b[2] - b[0]) * i / 10, b[3]], [b[0], b[1] + (b[3] - b[1]) * i / 10], [b[2], b[1] + (b[3] - b[1]) * i / 10]])
        pts.push(project([lon!, lat!])!)
    const xs = pts.map(p => p[0]), ys = pts.map(p => p[1])
    const x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = Math.min(...ys), y1 = Math.max(...ys)
    return `${x0} ${y0} ${x1 - x0} ${y1 - y0}`
})

async function select(code?: string, scroll = true) {
    if (!code || !byCode.value.has(code)) return
    selected.value = code
    router.replace({query: {...route.query, country: code}})
    if (scroll) {
        await nextTick()
        document.getElementById(`country-${code}`)?.scrollIntoView({behavior: 'smooth', block: 'nearest'})
    }
}

async function drawMap() {
    // the 1:50m world shapes are big, so they load with this page only
    const topo: any = (await import('world-atlas/countries-50m.json')).default
    const world = feature(topo, topo.objects.countries) as any
    const land = world.features.filter((f: any) => f.properties?.name != 'Antarctica')
    const projection = geoEqualEarth().fitExtent([[4, 4], [W - 4, H - 4]], {type: 'FeatureCollection', features: land} as any)
    const path = geoPath(projection)
    project = projection as any
    shapes.value = land.map((f: any, i: number) => ({key: `${f.id ?? 'x'}-${i}`, code: codeForShape(f.id, f.properties?.name), name: f.properties?.name ?? '', d: path(f) ?? ''}))
}

async function load() {
    loading.value = true
    error.value = false
    try {
        countries.value = (await homeApi('origins/')).countries
    } catch {
        error.value = true
    } finally {
        loading.value = false
    }
}

onMounted(() => {
    load()
    drawMap()
})
</script>

<style scoped>
.map-page { max-width: 1200px; }
.map-wrap { position: relative; overflow: hidden; background: rgba(var(--v-theme-on-surface), .02); }
.map { display: block; width: 100%; aspect-ratio: 960 / 470; }
.zoom { position: absolute; left: 8px; bottom: 8px; background: rgb(var(--v-theme-surface)); }
@media (max-width: 600px) { .zoom { position: static; display: flex; margin: 0 8px 8px; } .zoom .v-btn { flex: 1; min-width: 0; padding: 0 4px; } }
.land { vector-effect: non-scaling-stroke; }
.land { fill: rgba(var(--v-theme-on-surface), .1); stroke: rgb(var(--v-theme-surface)); stroke-width: .6; transition: fill .15s; }
.land.try { fill: rgba(var(--v-theme-primary), .4); cursor: pointer; }
.land.made { fill: rgb(var(--v-theme-primary)); cursor: pointer; }
.land.try:hover, .land.made:hover { opacity: .8; }
.land.selected { stroke: rgb(var(--v-theme-on-surface)); stroke-width: 1.2; }
.stat { font-size: .95rem; color: rgba(var(--v-theme-on-surface), .7); }
.stat-n { font-size: 1.6rem; font-weight: 700; color: rgb(var(--v-theme-on-surface)); margin-right: 4px; }
.legend { display: flex; gap: 16px; font-size: .85rem; color: rgba(var(--v-theme-on-surface), .7); }
.legend span { display: inline-flex; align-items: center; gap: 6px; }
.swatch { display: inline-block; width: 14px; height: 14px; border-radius: 3px; }
.swatch.made { background: rgb(var(--v-theme-primary)); }
.swatch.try { background: rgba(var(--v-theme-primary), .4); }
.country-grid { display: grid; align-items: start; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 12px; }
.country { border-color: rgba(var(--v-theme-on-surface), .12); scroll-margin-top: 80px; }
.country.selected { border-color: rgb(var(--v-theme-primary)); box-shadow: 0 0 0 1px rgb(var(--v-theme-primary)); }
.country-flag { font-size: 1.8rem; line-height: 1; }
.min-w-0 { min-width: 0; }
</style>
