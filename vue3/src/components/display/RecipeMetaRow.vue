<template>
    <!-- home fork: under the recipe title. Status and facts on one line in one style, keywords quieter below -->
    <div class="recipe-meta">
        <div class="d-flex flex-wrap align-center ga-2">
            <made-it-badge class="d-print-none" long :recipe="recipe" :servings="servings" v-if="useUserPreferenceStore().isAuthenticated" />
            <origin-chip :recipe="recipe" />
            <v-chip v-if="recipe.rating" size="small" label variant="tonal" :title="`Rated ${recipe.rating} of 5`">
                <v-icon icon="fa-solid fa-star" size="x-small" class="me-1" color="amber-darken-2" />{{ recipe.rating }}
            </v-chip>
            <v-chip v-if="recipe._private" size="small" label variant="tonal" prepend-icon="fa-solid fa-lock"
                    :title="recipe.shared?.length ? `Shared with ${recipe.shared.map(u => u.displayName).join(', ')}` : 'Only you can see this'">
                Private<template v-if="recipe.shared?.length"> · {{ recipe.shared.length }}</template>
            </v-chip>
        </div>
        <keywords-component v-if="recipe.keywords?.length" class="mt-2 quiet-keywords" variant="text" size="x-small" :keywords="recipe.keywords" />
    </div>
</template>

<script setup lang="ts">
import {PropType} from 'vue'
import {Recipe} from '@/openapi'
import {useUserPreferenceStore} from '@/stores/UserPreferenceStore'
import MadeItBadge from '@/components/display/MadeItBadge.vue'
import OriginChip from '@/components/display/OriginChip.vue'
import KeywordsComponent from '@/components/display/KeywordsBar.vue'

defineProps({
    recipe: {type: Object as PropType<Recipe>, required: true},
    servings: {type: Number, default: undefined},
})
</script>

<style scoped>
.quiet-keywords :deep(.v-chip) { color: rgba(var(--v-theme-on-surface), .6); padding: 0 6px; background: rgba(var(--v-theme-on-surface), .05); }
.quiet-keywords :deep(.v-chip:hover) { color: rgb(var(--v-theme-primary)); }
</style>
