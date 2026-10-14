<template>
    <!-- home fork: the coming days as a row of equal cards, as many across as fit (a week on a wide screen) -->
    <section class="mb-6">
        <div class="d-flex align-center mb-2">
            <router-link :to="{name: 'MealPlanPage'}" class="row-title">
                <h4><i class="fa-solid fa-calendar-days fa-fw"></i> {{ $t('Meal_Plan') }} <span class="ms-2 text-body-2">{{ $t('More') }} <i class="fa-solid fa-chevron-right"></i></span></h4>
            </router-link>
            <v-spacer />
            <v-progress-circular v-if="loading" indeterminate size="16" width="2" class="me-2" />
            <v-btn icon="fa-solid fa-chevron-left" size="small" variant="text" :disabled="page == 0" aria-label="Earlier days" @click="page--" />
            <v-btn icon="fa-solid fa-chevron-right" size="small" variant="text" :disabled="(page + 1) * numberOfCols >= DAYS" aria-label="Later days" @click="page++" />
        </div>
        <div class="mp-grid" :style="{gridTemplateColumns: `repeat(${numberOfCols}, minmax(0, 1fr))`}">
            <v-sheet v-for="d in shownDays" :key="d.create_default_date" rounded="lg" border class="mp-day" :class="{today: d.today}">
                <!-- click the date, or right-click anywhere on this bar, for the day's menu (plan a meal, I'm away) -->
                <div class="mp-head" @contextmenu="openDayMenu(d, $event)">
                    <button type="button" class="mp-date flex-grow-1 text-truncate" @click="openDayMenu(d, $event)">{{ d.date_label }}<v-icon icon="fa-solid fa-chevron-down" size="10" class="ms-1 mp-chev" /></button>
                    <v-btn icon size="x-small" variant="text" :aria-label="`Plan a meal for ${d.date_label}`" :title="`Plan a meal for ${d.date_label}`">
                        <v-icon icon="$create" size="x-small" />
                        <model-edit-dialog model="MealPlan" :item-defaults="{fromDate: d.date.toJSDate()}"></model-edit-dialog>
                    </v-btn>
                </div>
                <!-- days away: a banner instead of a "Dinner" line -->
                <div v-for="p in d.away" :key="p.id" class="mp-away" :class="{fill: d.meals.length == 0}" @contextmenu="openMenu(p, $event)">
                    <v-icon icon="fa-solid fa-suitcase-rolling" size="small" class="me-2" />
                    <span class="flex-grow-1 text-truncate">Away<template v-if="awayPlace(p)"> · {{ awayPlace(p) }}</template></span>
                    <model-edit-dialog model="MealPlan" :item="p"></model-edit-dialog>
                    <span class="mp-away-menu" @click.stop><meal-plan-context-menu :ref="el => setMenuRef(p.id!, el)" :plan="p"></meal-plan-context-menu></span>
                </div>
                <div v-if="d.plan_entries.length == 0" class="mp-empty text-body-2 text-medium-emphasis">{{ $t('HomeNothingPlanned', 'Nothing planned') }}</div>
                <v-list v-else-if="d.meals.length" density="compact" class="py-1 bg-transparent">
                    <v-list-item v-for="p in d.meals" :key="p.id" @click="clickMealPlan(p)" link @contextmenu="openMenu(p, $event)" class="px-2">
                        <template #prepend>
                            <recipe-thumb v-if="p.recipe" :src="p.recipe.image" :size="40" class="me-3" />
                            <div v-else class="mp-icon me-3"><v-icon icon="fa-regular fa-note-sticky" size="small" /></div>
                        </template>
                        <v-list-item-title class="mp-title">{{ p.recipe ? p.recipe.name : p.title }}</v-list-item-title>
                        <v-list-item-subtitle>{{ p.mealType.name }}</v-list-item-subtitle>
                        <model-edit-dialog model="MealPlan" :item="p" v-if="!p.recipe"></model-edit-dialog>
                        <template #append>
                            <meal-plan-context-menu :ref="el => setMenuRef(p.id!, el)" :plan="p"></meal-plan-context-menu>
                        </template>
                    </v-list-item>
                </v-list>
            </v-sheet>
        </div>

        <v-menu v-model="dayMenu" :target="dayPoint" location="bottom start" close-on-content-click>
            <v-list density="compact" v-if="menuDay">
                <div class="home-menu-label">{{ menuDay.date_label }}</div>
                <v-list-item prepend-icon="$create" @click="planDialog = true">Plan a meal</v-list-item>
                <v-list-item prepend-icon="fa-solid fa-suitcase-rolling" @click="awayDialog = true">I’m away…</v-list-item>
                <v-list-item prepend-icon="fa-solid fa-calendar-days" :to="{name: 'MealPlanPage'}">Open Meal Plan</v-list-item>
            </v-list>
        </v-menu>
        <model-edit-dialog v-if="menuDay" model="MealPlan" v-model="planDialog" :item-defaults="{fromDate: menuDay.date.toJSDate()}"></model-edit-dialog>
        <away-dialog v-model="awayDialog" :start="menuDay?.date.toJSDate()" />
    </section>
</template>


<script lang="ts" setup>
import RecipeThumb from '@/components/display/RecipeThumb.vue'
import {useI18n} from "vue-i18n";
const {t} = useI18n()

import {computed, onMounted, ref} from 'vue'
import {MealPlan} from "@/openapi";
import {useMealPlanStore} from "@/stores/MealPlanStore";
import {DateTime} from "luxon";
import {useHomeCols} from "@/composables/useHomeCols";
import ModelEditDialog from "@/components/dialogs/ModelEditDialog.vue";
import {useRouter} from "vue-router";
import MealPlanContextMenu from "@/components/inputs/MealPlanContextMenu.vue";
import AwayDialog from "@/components/dialogs/AwayDialog.vue";
import {awayPlace, isAway} from "@/composables/useAway";

const router = useRouter()

const loading = ref(false)
const page = ref(0)
const numberOfCols = useHomeCols()
// two weeks ahead; a week fits across a wide screen
const DAYS = 14

type MealPlanGridItem = {
    date: DateTime,
    create_default_date: String,
    date_label: String,
    plan_entries: Array<MealPlan>,
    away: Array<MealPlan>,
    meals: Array<MealPlan>,
    today: boolean,
}

const meal_plan_grid = computed(() => {
    let grid = [] as MealPlanGridItem[]

    for (const x of Array(DAYS).keys()) {
        let grid_day_date = DateTime.now().plus({days: x})
        grid.push({
            date: grid_day_date,
            today: x == 0,
            create_default_date: grid_day_date.toISODate(), // improve meal plan edit modal to do formatting itself and accept dates
            // home: "Today" / "Tomorrow" / "Sat, Oct 10" instead of "Sat, 10/10/26"
            date_label: x == 0 ? t('Today') : (x == 1 ? t('Tomorrow', 'Tomorrow') : grid_day_date.toLocaleString({weekday: 'short', month: 'short', day: 'numeric'})),
            plan_entries: useMealPlanStore().planList.filter((m: MealPlan) => ((DateTime.fromJSDate(m.fromDate).startOf('day') <= grid_day_date.startOf('day')) && (DateTime.fromJSDate((m.toDate != undefined) ? m.toDate : m.fromDate).startOf('day') >= grid_day_date.startOf('day')))),
        } as MealPlanGridItem)
        const day = grid[grid.length - 1]!
        day.away = day.plan_entries.filter(isAway)
        day.meals = day.plan_entries.filter(p => !isAway(p))
    }

    return grid
})

const shownDays = computed(() => meal_plan_grid.value.slice(page.value * numberOfCols.value, (page.value + 1) * numberOfCols.value))

onMounted(() => {
    loading.value = true
    useMealPlanStore().refreshFromAPI(DateTime.now().toJSDate(), DateTime.now().plus({days: DAYS}).toJSDate()).finally(() => {
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

// the day menu: from the date (click) or anywhere on the date bar (right-click)
const dayMenu = ref(false)
const dayPoint = ref<[number, number]>([0, 0])
const menuDay = ref<MealPlanGridItem | null>(null)
const planDialog = ref(false)
const awayDialog = ref(false)

function openDayMenu(d: MealPlanGridItem, e: MouseEvent) {
    if (e.type == 'contextmenu' && e.shiftKey) return
    e.preventDefault()
    menuDay.value = d
    dayPoint.value = [e.clientX, e.clientY]
    dayMenu.value = true
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
.row-title { color: inherit; text-decoration: none; }
.mp-grid { display: grid; gap: 12px; padding: 0 2px; }
/* equal heights: every day stretches to the tallest in the row */
.mp-day { display: flex; flex-direction: column; min-width: 0; container-type: inline-size; }
/* phone-width days: the name gets the room instead of the picture */
@container (max-width: 200px) { .mp-day :deep(.v-list-item__prepend) { display: none; } }
.mp-day.today { border-color: rgba(var(--v-theme-primary), .5) !important; }
.mp-head { display: flex; align-items: center; gap: 4px; padding: 6px 4px 6px 12px; font-weight: 600; font-size: .875rem; border-bottom: 1px solid rgba(var(--v-theme-on-surface), .08); }
.mp-day.today .mp-head { color: rgb(var(--v-theme-primary)); }
.mp-date { all: unset; cursor: pointer; font: inherit; display: inline-flex; align-items: center; min-width: 0; }
.mp-date:hover, .mp-date:focus-visible { color: rgb(var(--v-theme-primary)); }
.mp-chev { opacity: 0; transition: opacity .15s; }
.mp-head:hover .mp-chev, .mp-date:focus-visible .mp-chev { opacity: .6; }
.mp-away { display: flex; align-items: center; margin: 8px 8px 0; padding: 6px 4px 6px 10px; border-radius: 8px; cursor: pointer; font-size: .875rem; font-weight: 500;
    background: rgba(var(--v-theme-on-surface), .06); color: rgba(var(--v-theme-on-surface), .75); min-width: 0; }
.mp-away.fill { flex: 1; margin-bottom: 8px; }
.mp-away-menu { margin: -6px 0; }
.mp-empty { flex: 1; display: flex; align-items: center; justify-content: center; padding: 14px 8px; }
.mp-icon { width: 40px; height: 40px; flex: 0 0 40px; border-radius: 8px; display: flex; align-items: center; justify-content: center; background: rgba(var(--v-theme-on-surface), .06); color: rgba(var(--v-theme-on-surface), .55); }

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
