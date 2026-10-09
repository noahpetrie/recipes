<template>
    <!-- home: menu for a planned meal; opens from the ⋮ button or at the pointer on right-click (see openAt) -->
    <v-btn icon variant="plain" class="d-print-none" @click.stop="point = undefined">
        <v-icon icon="$menu"></v-icon>
        <v-menu activator="parent" v-model="menu" :target="point" :location="point ? 'bottom start' : undefined" close-on-content-click>
            <v-list density="compact">
                <div class="home-menu-label">{{ planName }} · {{ shortDate }}</div>
                <v-list-item v-if="plan.recipe" prepend-icon="fa-regular fa-file-lines" :to="recipeRoute">
                    {{ $t('HomeOpenRecipe', 'Open recipe') }}
                </v-list-item>
                <v-list-item prepend-icon="fa-regular fa-pen-to-square" link>
                    {{ $t('Edit') }}
                    <model-edit-dialog model="MealPlan" :item="plan"></model-edit-dialog>
                </v-list-item>
                <template v-if="plan.recipe">
                    <v-divider class="my-1"></v-divider>
                    <v-list-item prepend-icon="fa-solid fa-cart-shopping" link>
                        {{ $t('HomeAddToShopping', 'Add to shopping list') }}
                        <add-to-shopping-dialog :recipe="plan.recipe" :meal-plan="plan"></add-to-shopping-dialog>
                    </v-list-item>
                    <v-list-item prepend-icon="fa-regular fa-bookmark" link>
                        {{ $t('HomeAddToBook', 'Add to book') }}
                        <add-to-book-dialog :recipe="plan.recipe"></add-to-book-dialog>
                    </v-list-item>
                </template>
                <v-divider class="my-1"></v-divider>
                <v-list-item prepend-icon="fa-regular fa-trash-can" base-color="delete" @click="confirmDelete = true">
                    {{ $t('HomeRemoveFromPlan', 'Remove from plan') }}
                </v-list-item>
            </v-list>
        </v-menu>
    </v-btn>

    <v-dialog v-model="confirmDelete" max-width="420">
        <v-card class="pa-2">
            <v-card-title class="text-h6 pb-1">{{ $t('HomeRemoveMealQ', 'Remove this meal?') }}</v-card-title>
            <v-card-text class="pb-2">
                <div class="d-flex align-center ga-3 mpc-meal">
                    <v-avatar v-if="plan.recipe?.image" rounded="lg" size="56" :image="plan.recipe.image" class="mpc-thumb"></v-avatar>
                    <v-avatar v-else rounded="lg" size="56" class="mpc-thumb"><v-icon icon="fa-solid fa-pizza-slice" class="opacity-50"></v-icon></v-avatar>
                    <div class="min-w-0">
                        <div class="font-weight-medium">{{ planName }}</div>
                        <div class="text-body-2 text-medium-emphasis">{{ dateLabel }} · {{ plan.mealType.name }}</div>
                    </div>
                </div>
                <p class="text-body-2 text-medium-emphasis mt-3 mb-0">{{ $t('HomeRemoveMealHelp', 'The recipe itself stays in Tandoor.') }}</p>
            </v-card-text>
            <v-card-actions>
                <v-spacer></v-spacer>
                <v-btn variant="text" @click="confirmDelete = false">{{ $t('HomeKeep', 'Keep') }}</v-btn>
                <v-btn color="delete" variant="flat" prepend-icon="$delete" :loading="deleting" @click="remove()">{{ $t('HomeRemove', 'Remove') }}</v-btn>
            </v-card-actions>
        </v-card>
    </v-dialog>
</template>

<script setup lang="ts">
import {computed, PropType, ref} from 'vue'
import {DateTime} from "luxon";
import {MealPlan} from "@/openapi";
import ModelEditDialog from "@/components/dialogs/ModelEditDialog.vue";
import AddToShoppingDialog from "@/components/dialogs/AddToShoppingDialog.vue";
import AddToBookDialog from "@/components/dialogs/AddToBookDialog.vue";
import {useMealPlanStore} from "@/stores/MealPlanStore";
import {useI18n} from "vue-i18n";

const {t} = useI18n()

const props = defineProps({
    plan: {type: Object as PropType<MealPlan>, required: true},
})

const menu = ref(false)
const point = ref<[number, number] | undefined>(undefined)
const confirmDelete = ref(false)
const deleting = ref(false)

const recipeRoute = computed(() => ({
    name: 'RecipeViewPage',
    params: {id: String(props.plan.recipe?.id)},
    query: {servings: String(props.plan.servings ?? '')},
}))
const planName = computed(() => props.plan.recipe?.name ?? props.plan.title)
const shortDate = computed(() => {
    const d = DateTime.fromJSDate(props.plan.fromDate).startOf('day')
    const days = d.diff(DateTime.now().startOf('day'), 'days').days
    return days == 0 ? t('Today') : days == 1 ? t('Tomorrow', 'Tomorrow') : d.toLocaleString({weekday: 'short', month: 'short', day: 'numeric'})
})
const dateLabel = computed(() => DateTime.fromJSDate(props.plan.fromDate).toLocaleString({weekday: 'long', month: 'short', day: 'numeric'}))

function openAt(e: MouseEvent) {
    point.value = [e.clientX, e.clientY]
    menu.value = true
}

function remove() {
    deleting.value = true
    useMealPlanStore().deleteObject(props.plan).finally(() => {
        deleting.value = false
        confirmDelete.value = false
    })
}

defineExpose({openAt})
</script>

<style scoped>
.mpc-meal {
    padding: 10px;
    border-radius: 12px;
    background: rgba(var(--v-theme-on-surface), 0.04);
}

.mpc-thumb {
    background: rgba(var(--v-theme-on-surface), 0.06);
}
</style>
