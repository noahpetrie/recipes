<template>
    <!-- home fork: the start page's compact recipe card: photo, name on up to two lines, one status line -->
    <div class="home-tile" @contextmenu="onContextMenu">
        <router-link :to="{name: 'RecipeViewPage', params: {id: recipe.id}}" class="tile-link">
            <recipe-thumb :src="recipe.image" :aspect="3 / 2" />
            <div class="d-flex align-start mt-2">
                <div class="tile-name clamp-2 flex-grow-1" :title="recipe.name">{{ recipe.name }}</div>
            </div>
        </router-link>
        <div class="d-flex align-center tile-status">
            <div class="flex-grow-1 min-w-0 text-truncate">
                <slot name="status">
                    <span v-if="full?.lastCooked" class="text-success"><v-icon icon="fa-solid fa-check" size="x-small" class="me-1" /><span class="label">Made</span></span>
                    <span v-else class="text-medium-emphasis"><v-icon icon="fa-regular fa-bookmark" size="x-small" class="me-1" /><span class="label">To try</span></span>
                    <span v-if="full?.originCountry" class="ms-2" :title="countryName(full.originCountry)">{{ flag(full.originCountry) }}</span>
                    <span v-if="minutes" class="ms-2 text-medium-emphasis"><v-icon icon="fa-regular fa-clock" size="x-small" class="me-1" />{{ formatMinutes(minutes) }}</span>
                </slot>
            </div>
            <recipe-context-menu v-if="full" ref="contextMenu" :recipe="full" size="x-small" class="tile-menu" />
        </div>
    </div>
</template>

<script setup lang="ts">
import {computed, PropType, ref} from 'vue'
import {Recipe, RecipeOverview} from '@/openapi'
import RecipeThumb from '@/components/display/RecipeThumb.vue'
import RecipeContextMenu from '@/components/inputs/RecipeContextMenu.vue'
import {countryName, flag} from '@/utils/countries'
import {formatMinutes} from '@/utils/home_format'

const props = defineProps({
    // a full recipe from the API (menu, made, flag and time), or just {id, name, image} with a status slot
    recipe: {type: Object as PropType<{id?: number, name: string, image?: string | null} | RecipeOverview | Recipe>, required: true},
})

const full = computed(() => 'keywords' in props.recipe ? props.recipe as RecipeOverview : undefined)
const minutes = computed(() => (full.value?.workingTime ?? 0) + (full.value?.waitingTime ?? 0))

const contextMenu = ref<InstanceType<typeof RecipeContextMenu> | null>(null)
function onContextMenu(e: MouseEvent) {
    if (e.shiftKey || !contextMenu.value) return
    e.preventDefault()
    contextMenu.value.openAt(e)
}
</script>

<style scoped>
.home-tile { min-width: 0; container-type: inline-size; }
.tile-link { color: inherit; text-decoration: none; display: block; }
.tile-link:hover .tile-name { color: rgb(var(--v-theme-primary)); }
.tile-name { font-weight: 600; font-size: .95rem; min-height: 2.6em; }
.tile-status { font-size: .78rem; min-height: 26px; }
/* narrow cards (phones): the made / to-try icon alone, so the time fits */
@container (max-width: 200px) { .label { display: none; } }
.tile-menu { margin-right: -8px; }
.min-w-0 { min-width: 0; }
</style>
