<template>
    <!-- home fork: where the dish comes from; opens the food map on that country -->
    <v-chip v-if="recipe.originCountry" :size="size" variant="tonal" label :to="{name: 'FoodMapPage', query: {country: recipe.originCountry}}"
            :title="`From ${label} — see it on the food map`">
        <span class="me-1">{{ flag(recipe.originCountry) }}</span>{{ label }}
    </v-chip>
</template>

<script setup lang="ts">
import {computed, PropType} from 'vue'
import {Recipe, RecipeOverview} from '@/openapi'
import {countryName, flag} from '@/utils/countries'

const props = defineProps({
    recipe: {type: Object as PropType<Recipe | RecipeOverview>, required: true},
    size: {type: String, default: 'small'},
})

const label = computed(() => [props.recipe.originRegion, countryName(props.recipe.originCountry)].filter(Boolean).join(', '))
</script>
