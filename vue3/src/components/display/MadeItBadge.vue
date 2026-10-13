<template>
    <!-- home fork: made before (from the cook log) or still on the "to try" pile -->
    <span class="d-inline-flex align-center flex-wrap ga-1">
        <v-chip v-if="made" :size="size" label color="success" variant="tonal" prepend-icon="fa-solid fa-check" :title="`Last made ${date}`">
            {{ long ? `Made · ${date}` : 'Made' }}
        </v-chip>
        <v-chip v-else :size="size" label variant="outlined" prepend-icon="fa-regular fa-bookmark" title="You haven’t logged making this yet">
            To try
        </v-chip>
        <v-btn v-if="long" size="small" variant="text" color="primary" :prepend-icon="made ? 'fa-solid fa-rotate-right' : 'fa-solid fa-check'"
               :loading="saving" @click="mark">
            {{ made ? 'Made it again' : 'I made this' }}
        </v-btn>
    </span>
</template>

<script setup lang="ts">
import {computed, PropType, ref} from 'vue'
import {DateTime} from "luxon";
import {Recipe, RecipeOverview} from "@/openapi";
import {markMade} from "@/composables/useMade";

const props = defineProps({
    recipe: {type: Object as PropType<Recipe | RecipeOverview>, required: true},
    servings: {type: Number, default: undefined},
    size: {type: String, default: 'x-small'},
    // recipe page: show the date and an "I made this" button
    long: {type: Boolean, default: false},
})

const saving = ref(false)
const made = computed(() => props.recipe.lastCooked != null)
const date = computed(() => props.recipe.lastCooked ? DateTime.fromJSDate(new Date(props.recipe.lastCooked)).toLocaleString(DateTime.DATE_MED) : '')

async function mark() {
    saving.value = true
    await markMade(props.recipe, props.servings)
    saving.value = false
}
</script>
