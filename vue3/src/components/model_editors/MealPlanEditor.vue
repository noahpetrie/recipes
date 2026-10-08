<template>
    <model-editor-base
        :loading="loading"
        :dialog="dialog"
        @save="saveObject().then((obj:MealPlan) => { useMealPlanStore().plans.set(obj.id, obj);})"
        @delete="useMealPlanStore().plans.delete(editingObj.id); deleteObject()"
        @close="emit('close'); editingObjChanged = false"
        :is-update="isUpdate()"
        :is-changed="editingObjChanged"
        :model-class="modelClass"
        :object-name="editingObjName()"
        :editing-object="editingObj">

        <!-- tabs only matter once the plan exists (the shopping tab is unavailable for new plans) -->
        <v-tabs v-model="tab" :disabled="loading" grow density="compact" v-if="isUpdate()">
            <v-tab prepend-icon="$mealplan" value="plan">{{ $t('Meal_Plan') }}</v-tab>
            <v-tab prepend-icon="$shopping" value="shopping">{{ $t('Shopping_list') }}</v-tab>
        </v-tabs>

        <v-card-text class="meal-plan-editor">
            <v-tabs-window v-model="tab">
                <v-tabs-window-item value="plan">
                    <v-form :disabled="loading">

                        <!-- what -->
                        <v-model-select model="Recipe" v-model="editingObj.recipe" hide-details
                                        @update:modelValue="editingObj.servings = editingObj.recipe ? editingObj.recipe.servings : 1"></v-model-select>

                        <v-list-item v-if="editingObj && editingObj.recipe" class="mpe-recipe mt-2" rounded="lg"
                                     :to="{name: 'RecipeViewPage', params: {id: editingObj.recipe.id}}" target="_blank">
                            <template #prepend>
                                <v-avatar rounded="lg" size="48" :image="editingObj.recipe.image" class="me-1" v-if="editingObj.recipe.image"></v-avatar>
                                <v-avatar rounded="lg" size="48" color="tandoor" class="me-1" v-else>{{ editingObj.recipe.name.charAt(0) }}</v-avatar>
                            </template>
                            <v-list-item-title class="font-weight-medium">{{ editingObj.recipe.name }}</v-list-item-title>
                            <v-list-item-subtitle v-if="editingObj.recipe.workingTime || editingObj.recipe.waitingTime">
                                <v-icon icon="fa-regular fa-clock" size="x-small" class="me-1"></v-icon>
                                {{ (editingObj.recipe.workingTime ?? 0) + (editingObj.recipe.waitingTime ?? 0) }} min
                            </v-list-item-subtitle>
                            <template #append>
                                <v-icon icon="fa-solid fa-arrow-up-right-from-square" size="x-small" class="text-medium-emphasis"></v-icon>
                            </template>
                        </v-list-item>

                        <v-text-field v-model="editingObj.title" hide-details class="mt-3"
                                      :label="editingObj.recipe ? $t('Title') : $t('or') + ' ' + $t('Title').toLowerCase()"
                                      :placeholder="editingObj.recipe ? editingObj.recipe.name : ''"></v-text-field>

                        <!-- when -->
                        <div class="mpe-section-label">{{ $t('Date') }}</div>
                        <div class="d-flex align-center ga-2 flex-wrap">
                            <div class="d-flex align-center flex-grow-1 mpe-date">
                                <v-btn icon="fa-solid fa-chevron-left" variant="text" size="small" density="comfortable" :title="$t('Previous_Day')"
                                       @click="dateRangeValue = shiftDateRange(dateRangeValue, -1); updateDate()"></v-btn>
                                <v-text-field :model-value="dateLabel" readonly prepend-inner-icon="$calendar" density="compact" hide-details
                                              :aria-label="$t('Date')" :active="datePickerMenu" :focused="datePickerMenu">
                                    <v-menu v-model="datePickerMenu" :close-on-content-click="false" activator="parent" transition="scale-transition">
                                        <v-date-picker v-model="pickerValue" multiple="range" @update:modelValue="onPickerChange" hide-header color="primary"
                                                       :first-day-of-week="useUserPreferenceStore().deviceSettings.mealplan_startingDayOfWeek"
                                                       :show-week="useUserPreferenceStore().deviceSettings.mealplan_displayWeekNumbers"></v-date-picker>
                                    </v-menu>
                                </v-text-field>
                                <v-btn icon="fa-solid fa-chevron-right" variant="text" size="small" density="comfortable" :title="$t('Next_Day')"
                                       @click="dateRangeValue = shiftDateRange(dateRangeValue, +1); updateDate()"></v-btn>
                            </div>

                            <v-text-field v-model="mealPlanTime" class="mpe-time"
                                          :active="timePickerMenu" :focus="timePickerMenu"
                                          :aria-label="$t('Time')" prepend-inner-icon="fa-regular fa-clock" readonly density="compact" hide-details>
                                <v-menu v-model="timePickerMenu" :close-on-content-click="false"
                                        activator="parent" transition="scale-transition">
                                    <v-time-picker v-if="timePickerMenu" format="24hr"
                                                   v-model="mealPlanTime"
                                                   @update:modelValue="applyTimeToEditingDates"></v-time-picker>
                                </v-menu>
                            </v-text-field>

                            <div class="mpe-stepper" :title="$t('Days')">
                                <v-btn icon="fa-solid fa-minus" variant="text" size="x-small" :disabled="dayCount <= 1"
                                       @click="adjustDateRangeLength(dateRangeValue,-1); updateDate()"></v-btn>
                                <span class="mpe-stepper-value">{{ dayCount }} {{ (dayCount == 1 ? $t('Day') : $t('Days')).toLowerCase() }}</span>
                                <v-btn icon="fa-solid fa-plus" variant="text" size="x-small"
                                       @click="adjustDateRangeLength(dateRangeValue,+1); updateDate()"></v-btn>
                            </div>
                        </div>

                        <!-- details -->
                        <div class="d-flex align-center ga-2 mt-4 flex-wrap">
                            <div class="flex-grow-1 mpe-mealtype">
                                <v-model-select model="MealType" create v-model="editingObj.mealType" density="compact" hide-details></v-model-select>
                            </div>
                            <div class="mpe-stepper" :title="$t('Servings')">
                                <v-btn icon="fa-solid fa-minus" variant="text" size="x-small" :disabled="editingObj.servings <= 1"
                                       @click="editingObj.servings = Math.max(1, Math.round((editingObj.servings ?? 1) - 1))"></v-btn>
                                <span class="mpe-stepper-value">{{ Number(editingObj.servings ?? 1).toLocaleString() }} {{ (editingObj.servings == 1 ? $t('Serving') : $t('Servings')).toLowerCase() }}</span>
                                <v-btn icon="fa-solid fa-plus" variant="text" size="x-small"
                                       @click="editingObj.servings = Math.floor((editingObj.servings ?? 0) + 1)"></v-btn>
                            </div>
                        </div>

                        <v-switch :label="$t('AddToShopping')" v-model="editingObj.addshopping" hide-details density="compact" class="mt-2"
                                  v-if="editingObj.recipe && !isUpdate()"></v-switch>
                        <v-btn prepend-icon="$shopping" color="create" variant="tonal" class="mt-3" v-if="!editingObj.shopping && editingObj.recipe && isUpdate()">
                            {{ $t('AddToShopping') }}
                            <add-to-shopping-dialog :recipe="editingObj.recipe" :meal-plan="editingObj"
                                                    @created="editingObj.shopping = true;"></add-to-shopping-dialog>
                        </v-btn>

                        <v-textarea :label="$t('Note')" v-model="editingObj.note" rows="2" auto-grow hide-details class="mt-3"
                                    v-if="showNote || editingObj.note" :autofocus="showNote && !editingObj.note"></v-textarea>
                        <v-btn variant="text" size="small" prepend-icon="fa-regular fa-note-sticky" class="mt-2 px-1 text-medium-emphasis" v-else
                               @click="showNote = true">{{ $t('Add') }} {{ $t('Note').toLowerCase() }}</v-btn>

                    </v-form>
                </v-tabs-window-item>

                <v-tabs-window-item value="shopping">
                    <closable-help-alert class="mb-2" :text="$t('MealPlanShoppingHelp')"></closable-help-alert>

                    <shopping-list-view :meal-plan-id="editingObj.id"></shopping-list-view>

                </v-tabs-window-item>
            </v-tabs-window>
        </v-card-text>
    </model-editor-base>

</template>

<script setup lang="ts">

import {computed, nextTick, onMounted, onUnmounted, PropType, ref, toRaw, watch} from "vue";
import {ApiApi, MealPlan, MealType, ShoppingListRecipe} from "@/openapi";
import ModelEditorBase from "@/components/model_editors/ModelEditorBase.vue";
import {useModelEditorFunctions} from "@/composables/useModelEditorFunctions";
import {DateTime} from "luxon";
import {adjustDateRangeLength, shiftDateRange} from "@/utils/date_utils";
import ModelSelect from "@/components/inputs/ModelSelect.vue";
import {useUserPreferenceStore} from "@/stores/UserPreferenceStore";
import {ErrorMessageType, MessageType, useMessageStore} from "@/stores/MessageStore";
import ShoppingLineItem from "@/components/display/ShoppingLineItem.vue";
import {useShoppingStore} from "@/stores/ShoppingStore";
import ShoppingListEntryInput from "@/components/inputs/ShoppingListEntryInput.vue";
import ClosableHelpAlert from "@/components/display/ClosableHelpAlert.vue";
import {useMealPlanStore} from "@/stores/MealPlanStore";
import AddToShoppingDialog from "@/components/dialogs/AddToShoppingDialog.vue";
import ShoppingListView from "@/components/display/ShoppingListView.vue";
import VModelSelect from "@/components/inputs/VModelSelect.vue";

const props = defineProps({
    item: {type: {} as PropType<MealPlan>, required: false, default: null},
    itemDefaults: {type: {} as PropType<MealPlan>, required: false, default: {} as MealPlan},
    itemId: {type: [Number, String], required: false, default: undefined},
    dialog: {type: Boolean, default: false}
})

const emit = defineEmits(['create', 'save', 'delete', 'close', 'changedState'])
const {
    setupState,
    deleteObject,
    saveObject,
    isUpdate,
    editingObjName,
    applyItemDefaults,
    loading,
    editingObj,
    editingObjChanged,
    modelClass
} = useModelEditorFunctions<MealPlan>('MealPlan', emit)

/**
 * watch prop changes and re-initialize editor
 * required to embed editor directly into pages and be able to change item from the outside
 */
watch([() => props.item, () => props.itemId], () => {
    initializeEditor()
})

// object specific data (for selects/display)
const tab = ref('plan')

const dateRangeValue = ref([] as Date[])
const timePickerMenu = ref(false)
const mealPlanTime = ref('12:00')
const showNote = ref(false)

/** number of days covered by the selected range (a plan can span several days) */
const dayCount = computed(() => {
    if (!dateRangeValue.value || dateRangeValue.value.length == 0) return 1
    const sorted = [...dateRangeValue.value].sort((a, b) => a.getTime() - b.getTime())
    return Math.round(DateTime.fromJSDate(sorted[sorted.length - 1]!).startOf('day')
        .diff(DateTime.fromJSDate(sorted[0]!).startOf('day'), 'days').days) + 1
})

/** "Fri, Oct 9" for a single day, "Fri, Oct 9 – Sun, Oct 11" for a range */
const datePickerMenu = ref(false)
// the calendar starts a fresh selection each time it opens: first click = that day, second click = range end
const pickerValue = ref([] as Date[])
watch(datePickerMenu, (open) => {
    if (open) pickerValue.value = []
})

function onPickerChange(value: Date[]) {
    if (value && value.length > 0) {
        dateRangeValue.value = [...value]
        updateDate()
    }
}
const dateLabel = computed(() => {
    const dates = (dateRangeValue.value ?? []).filter(d => d instanceof Date)
    if (dates.length == 0) return ''
    const fmt = (d: Date) => DateTime.fromJSDate(d).toLocaleString({weekday: 'short', month: 'short', day: 'numeric'})
    const sorted = [...dates].sort((a, b) => a.getTime() - b.getTime())
    const first = sorted[0]!, last = sorted[sorted.length - 1]!
    return DateTime.fromJSDate(first).hasSame(DateTime.fromJSDate(last), 'day') ? fmt(first) : `${fmt(first)} – ${fmt(last)}`
})

watch(() => editingObj.value.mealType, (newType, oldType) => {
    if (newType?.time && newType?.time !== oldType?.time) {
        mealPlanTime.value = newType.time.substring(0, 5)
        applyTimeToEditingDates()
    }
})

function applyTimeToEditingDates() {
    if (!mealPlanTime.value) return
    let changed = editingObjChanged.value
    const [hours, minutes] = mealPlanTime.value.split(':').map(Number)
    if (editingObj.value.fromDate) {
        editingObj.value.fromDate = DateTime.fromJSDate(editingObj.value.fromDate)
            .set({hour: hours, minute: minutes, second: 0, millisecond: 0}).toJSDate()
    }
    if (editingObj.value.toDate) {
        editingObj.value.toDate = DateTime.fromJSDate(editingObj.value.toDate)
            .set({hour: hours, minute: minutes, second: 0, millisecond: 0}).toJSDate()
    }
    nextTick(() => {
        editingObjChanged.value = changed
    })
}

/**
 * update shopping list when switching to shopping tab
 */
watch(() => tab.value, (newVal, oldVal) => {
    if (newVal == 'shopping') {
        useShoppingStore().selectedMealPlan = editingObj.value.id
        useShoppingStore().updateEntriesStructure()
    }
})

onMounted(() => {
    initializeEditor()
})

onUnmounted(() => {
    if (useShoppingStore().selectedMealPlan == editingObj.value.id) {
        useShoppingStore().selectedMealPlan = undefined
    }
})

/**
 * component specific state setup logic
 */
function initializeEditor() {
    const api = new ApiApi()

    // load meal types and create new object based on default type when initially loading
    // TODO remove this once moved to user preference from MealType property
    loading.value = true

    setupState(props.item, props.itemId, {
        newItemFunction: () => {
            const noonToday = DateTime.now().set({hour: 12, minute: 0, second: 0, millisecond: 0})
            editingObj.value.fromDate = noonToday.toJSDate()
            editingObj.value.toDate = noonToday.toJSDate()
            mealPlanTime.value = '12:00'

            editingObj.value.servings = 1

            if (useUserPreferenceStore().userSettings.defaultMealType){
                editingObj.value.mealType = useUserPreferenceStore().userSettings.defaultMealType
            }

            // home: without a default the API rejects the plan ("meal_type: required"); preselect the first meal type
            if (!editingObj.value.mealType && !(props.itemDefaults as MealPlan)?.mealType) {
                api.apiMealTypeList({pageSize: 1}).then(r => {
                    if (!editingObj.value.mealType && r.results.length > 0) {
                        const changed = editingObjChanged.value
                        editingObj.value.mealType = r.results[0]!
                        nextTick(() => { editingObjChanged.value = changed })
                    }
                })
            }

            editingObj.value.addshopping = useUserPreferenceStore().userSettings.mealplanAutoaddShopping

            applyItemDefaults(props.itemDefaults)

            if (editingObj.value.mealType?.time) {
                mealPlanTime.value = editingObj.value.mealType.time.substring(0, 5)
            }
            applyTimeToEditingDates()

            if (editingObj.value.toDate < editingObj.value.fromDate) {
                editingObj.value.toDate = editingObj.value.fromDate
            }

            initializeDateRange()

            nextTick(() => {
                editingObjChanged.value = false
            })
        }, existingItemFunction: () => {
            editingObj.value = structuredClone(toRaw(editingObj.value))
            if (editingObj.value.fromDate) {
                mealPlanTime.value = DateTime.fromJSDate(editingObj.value.fromDate).toFormat('HH:mm')
            }
            initializeDateRange()
        }
    },)

}

/**
 * update the editing object with data from the date range selector whenever its changed (could probably be a watcher)
 */
// TODO properly hook into beforeSave hook if i ever implement one for model editors
function updateDate() {
    if (dateRangeValue.value != null) {
        editingObj.value.fromDate = dateRangeValue.value[0]
        if (dateRangeValue.value[dateRangeValue.value.length - 1] > editingObj.value.fromDate) {
            editingObj.value.toDate = dateRangeValue.value[dateRangeValue.value.length - 1]
        } else {
            editingObj.value.toDate = editingObj.value.fromDate
        }
        applyTimeToEditingDates()
    } else {
        useMessageStore().addMessage(MessageType.WARNING, 'Missing Date', 7000)
    }
}

/**
 * initialize the dateRange selector when the editingObject is initialized
 */
function initializeDateRange() {
    if (editingObj.value.toDate && DateTime.fromJSDate(editingObj.value.toDate).diff(DateTime.fromJSDate(editingObj.value.fromDate), 'days').toObject().days! >= 1) {
        dateRangeValue.value = [editingObj.value.fromDate]
        let currentDate = DateTime.fromJSDate(editingObj.value.fromDate).plus({day: 1}).toJSDate()
        while (currentDate <= editingObj.value.toDate) {
            dateRangeValue.value.push(currentDate)
            currentDate = DateTime.fromJSDate(currentDate).plus({day: 1}).toJSDate()
        }
    } else {
        dateRangeValue.value = [editingObj.value.fromDate]
    }
}

</script>

<style scoped>
.mpe-section-label {
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.02em;
    text-transform: uppercase;
    color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
    margin: 20px 0 6px;
}

.mpe-date {
    min-width: 260px;
}

.mpe-date :deep(.v-input) {
    flex: 1 1 auto;
}

.mpe-time {
    flex: 0 0 120px;
}

.mpe-mealtype {
    min-width: 200px;
}

.mpe-stepper {
    display: inline-flex;
    align-items: center;
    gap: 2px;
    height: 40px;
    padding: 0 4px;
    border-radius: 10px;
    background: rgba(var(--v-theme-on-surface), 0.04);
    white-space: nowrap;
}

.mpe-stepper-value {
    min-width: 76px;
    text-align: center;
    font-size: 0.875rem;
    font-variant-numeric: tabular-nums;
}

.mpe-recipe {
    background: rgba(var(--v-theme-on-surface), 0.035);
}
</style>
