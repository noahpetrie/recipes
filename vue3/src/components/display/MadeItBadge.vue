<template>
    <!-- home fork: made before (from the cook log) or still on the "to try" pile -->
    <!-- recipe page (long): one control. "To try" marks it made when tapped; "Made · date" has "Made it again" in its menu -->
    <span v-if="long" class="d-inline-flex align-center">
        <v-chip v-if="!made" size="small" label variant="outlined" prepend-icon="fa-regular fa-bookmark" :disabled="saving" title="Tap when you’ve made it" @click="mark">
            To try
            <span class="mark-hint ms-2"><v-icon icon="fa-solid fa-check" size="x-small" class="me-1" />Mark made</span>
        </v-chip>
        <v-menu v-else>
            <template #activator="{props: p}">
                <v-chip v-bind="p" size="small" label color="success" variant="tonal" prepend-icon="fa-solid fa-check" :title="`Last made ${date}`">
                    Made · {{ date }}<v-icon icon="fa-solid fa-chevron-down" size="x-small" class="ms-2" />
                </v-chip>
            </template>
            <v-list density="compact">
                <v-list-item prepend-icon="fa-solid fa-rotate-right" title="Made it again" subtitle="Log today’s cook" @click="mark" />
            </v-list>
        </v-menu>
    </span>
    <template v-else>
        <v-chip v-if="made" :size="size" label color="success" variant="tonal" prepend-icon="fa-solid fa-check" :title="`Last made ${date}`">Made</v-chip>
        <v-chip v-else :size="size" label variant="outlined" prepend-icon="fa-regular fa-bookmark" title="You haven’t logged making this yet">To try</v-chip>
    </template>
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

<style scoped>
.mark-hint { display: inline-flex; align-items: center; padding-left: 8px; border-left: 1px solid rgba(var(--v-theme-on-surface), .2); color: rgb(var(--v-theme-primary)); font-weight: 500; }
</style>
