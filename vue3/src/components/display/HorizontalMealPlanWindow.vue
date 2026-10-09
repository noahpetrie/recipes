<template>
    <!--    <v-row justify="space-between">-->
    <!--        <v-col>-->
    <!--            <h2><i class="fas fa-calendar-week fa-fw"></i> Meal Plans</h2>-->
    <!--        </v-col>-->
    <!--    </v-row>-->

    <v-row class="mt-0" v-if="mealPlanWindows.length > 0">
        <v-col>
            <v-window v-model="currentWindowIndex">
                <v-window-item v-for="(w, i) in mealPlanWindows" :value="i" class="pt-1 pb-1">
                    <v-row>
                        <v-col v-for="mealPlanGridItem in w">

                            <v-list density="compact" class="pt-0 pb-0 mp-day">
                                <v-list-item class="text-center">
                                    <div class="d-flex ">
                                        <div class="flex-col align-self-start">
                                            <v-btn @click="currentWindowIndex--" v-if="currentWindowIndex != 0" icon="fa-solid fa-chevron-left" size="small"></v-btn>
                                        </div>
                                        <div class="flex-col flex-grow-1 mt-auto mb-auto">
                                            {{ mealPlanGridItem.date_label }}
                                        </div>
                                        <div class="flex-col align-self-end">
                                            <v-btn @click="currentWindowIndex++" v-if="currentWindowIndex + 1 < mealPlanWindows.length" icon="fa-solid fa-chevron-right"
                                                   size="small"></v-btn>
                                        </div>
                                    </div>
                                </v-list-item>
                                <v-progress-linear v-if="loading" height="1" indeterminate></v-progress-linear>
                                <v-divider v-if="mealPlanGridItem.plan_entries.length > 0"></v-divider>
                                <v-list-item v-for="p in mealPlanGridItem.plan_entries" :key="p.id" @click="clickMealPlan(p)" link @contextmenu="openMenu(p, $event)">
                                    <template #prepend>
                                        <!-- home: square photo thumbnails, like the rest of the app -->
                                        <v-avatar :image="p.recipe.image" v-if="p.recipe?.image" rounded="lg" size="44" class="mp-thumb"></v-avatar>
                                        <v-avatar v-else rounded="lg" size="44" class="mp-thumb"><v-icon icon="fa-solid fa-pizza-slice" size="small" class="opacity-60"></v-icon></v-avatar>
                                    </template>
                                    <v-list-item-title class="mp-title">
                                        <span v-if="p.recipe">{{ p.recipe.name }}</span>
                                        <span v-else>{{ p.title }}</span>
                                    </v-list-item-title>
                                    <v-list-item-subtitle>
                                        {{ p.mealType.name }}
                                    </v-list-item-subtitle>
                                    <model-edit-dialog model="MealPlan" :item="p" v-if="!p.recipe"></model-edit-dialog>
                                    <template #append>
                                        <meal-plan-context-menu :ref="el => setMenuRef(p.id!, el)" :plan="p"></meal-plan-context-menu>
                                    </template>
                                </v-list-item>
                                <v-list-item class="text-center cursor-pointer mp-add" :class="{'mp-add-empty': mealPlanGridItem.plan_entries.length == 0}" variant="tonal">
                                    <model-edit-dialog model="MealPlan" :item-defaults="{fromDate: mealPlanGridItem.date.toJSDate()}"></model-edit-dialog>
                                    <!-- home: an empty day says so instead of showing a bare + -->
                                    <span v-if="mealPlanGridItem.plan_entries.length == 0" class="text-body-2 text-medium-emphasis">{{ $t('HomeNothingPlanned', 'Nothing planned') }} · </span>
                                    <v-icon icon="$create" size="x-small"></v-icon>
                                    <span v-if="mealPlanGridItem.plan_entries.length == 0" class="text-body-2 text-primary ms-1">{{ $t('Add') }}</span>
                                </v-list-item>
                            </v-list>
                        </v-col>
                    </v-row>
                </v-window-item>
            </v-window>
        </v-col>
    </v-row>

</template>


<script lang="ts" setup>
import {useI18n} from "vue-i18n";
const {t} = useI18n()

import {computed, onMounted, ref} from 'vue'
import {useDisplay} from "vuetify";
import {MealPlan} from "@/openapi";
import {useMealPlanStore} from "@/stores/MealPlanStore";
import {DateTime} from "luxon";
import {homePageCols} from "@/utils/breakpoint_utils";
import ModelEditDialog from "@/components/dialogs/ModelEditDialog.vue";
import {useRouter} from "vue-router";
import MealPlanContextMenu from "@/components/inputs/MealPlanContextMenu.vue";

const router = useRouter()
const {name} = useDisplay()

const loading = ref(false)
const currentWindowIndex = ref(0)

let numberOfCols = computed(() => {
    return homePageCols(name.value)
})

type MealPlanGridItem = {
    date: DateTime,
    create_default_date: String,
    date_label: String,
    plan_entries: Array<MealPlan>,
}

const meal_plan_grid = computed(() => {
    let grid = [] as MealPlanGridItem[]

    for (const x of Array(4).keys()) {
        let grid_day_date = DateTime.now().plus({days: x})
        grid.push({
            date: grid_day_date,
            create_default_date: grid_day_date.toISODate(), // improve meal plan edit modal to do formatting itself and accept dates
            // home: "Today" / "Tomorrow" / "Sat, Oct 10" instead of "Sat, 10/10/26"
            date_label: x == 0 ? t('Today') : (x == 1 ? t('Tomorrow', 'Tomorrow') : grid_day_date.toLocaleString({weekday: 'short', month: 'short', day: 'numeric'})),
            plan_entries: useMealPlanStore().planList.filter((m: MealPlan) => ((DateTime.fromJSDate(m.fromDate).startOf('day') <= grid_day_date.startOf('day')) && (DateTime.fromJSDate((m.toDate != undefined) ? m.toDate : m.fromDate).startOf('day') >= grid_day_date.startOf('day')))),
        } as MealPlanGridItem)
    }

    return grid
})

let mealPlanWindows = computed(() => {
    let windows = [] as Array<Array<MealPlanGridItem>>
    let current_window = [] as Array<MealPlanGridItem>
    for (const [i, mealPlanGridItem] of meal_plan_grid.value.entries()) {
        current_window.push(mealPlanGridItem)

        if (i % numberOfCols.value == numberOfCols.value - 1) {
            if (current_window.length > 0) {
                windows.push(current_window)
            }
            current_window = []
        }
    }
    if (current_window.length > 0) {
        windows.push(current_window)
    }
    return windows
})

onMounted(() => {
    loading.value = true
    useMealPlanStore().refreshFromAPI(DateTime.now().toJSDate(), DateTime.now().plus({days: 7}).toJSDate()).finally(() => {
        loading.value = false
    })
})

// home: right-click a planned meal for its menu (Shift+right-click keeps the browser's)
const menuRefs: Record<number, InstanceType<typeof MealPlanContextMenu> | null> = {}

function setMenuRef(id: number, el: unknown) {
    menuRefs[id] = (el as InstanceType<typeof MealPlanContextMenu> | null) ?? null
}

function openMenu(plan: MealPlan, e: MouseEvent) {
    const m = menuRefs[plan.id!]
    if (e.shiftKey || !m) return
    e.preventDefault()
    m.openAt(e)
}

function clickMealPlan(plan: MealPlan) {
    if (plan.recipe) {
        router.push({
            name: 'RecipeViewPage',
            params: {id: String(plan.recipe.id)},          // keep id in params
            query: {servings: String(plan.servings ?? '')} // pass servings as query
        })
    }
}

</script>


<style scoped>
.mp-thumb {
    background: rgba(var(--v-theme-on-surface), 0.06);
}

/* two lines for long recipe names instead of "Butter Chicken (…" */
.mp-title {
    white-space: normal;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    line-height: 1.3;
}
</style>