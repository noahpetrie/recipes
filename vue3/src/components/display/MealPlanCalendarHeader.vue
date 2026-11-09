<template>
    <!-- home: shadcn-style toolbar — range title, then Today, ‹ › and a date picker button -->
    <div class="mpc-header">
        <!-- home: the range shows on phones too (short form); the calendar's last date is exclusive -->
        <div class="mpc-range">
            <template v-if="mdAndUp">
                {{ DateTime.fromJSDate(props.headerProps?.displayFirstDate).toLocaleString(DateTime.DATE_MED) }} –
                {{ lastShownDate.toLocaleString(DateTime.DATE_MED) }}
            </template>
            <template v-else>
                {{ DateTime.fromJSDate(props.headerProps?.displayFirstDate).toLocaleString({month: 'short', day: 'numeric'}) }} –
                {{ lastShownDate.toLocaleString({month: 'short', day: 'numeric'}) }}
            </template>
        </div>
        <div class="mpc-tools">
            <shop-week-button />
            <!-- home fork: the auto planner and view options used to sit in the sidebar -->
            <v-btn variant="outlined" size="small" prepend-icon="fa-solid fa-calendar-plus" v-if="smAndUp">
                {{ $t('Auto_Planner') }}
                <auto-plan-dialog></auto-plan-dialog>
            </v-btn>
            <v-btn variant="outlined" size="small" icon :aria-label="$t('Auto_Planner')" :title="$t('Auto_Planner')" v-else>
                <v-icon icon="fa-solid fa-calendar-plus" size="small"></v-icon>
                <auto-plan-dialog></auto-plan-dialog>
            </v-btn>
            <v-btn variant="outlined" size="small" @click="date = new Date()">{{ $t('Today') }}</v-btn>
            <div class="mpc-group">
                <v-btn variant="outlined" size="small" icon="fa-solid fa-chevron-left" :aria-label="$t('Previous', 'Previous')"
                       @click="date = props.headerProps.previousFullPeriod"></v-btn>
                <v-btn variant="outlined" size="small" icon="fa-solid fa-chevron-right" :aria-label="$t('Next')"
                       @click="date = props.headerProps.nextFullPeriod"></v-btn>
            </div>
            <v-btn variant="outlined" size="small" prepend-icon="fa-regular fa-calendar" class="mpc-date" v-if="smAndUp">
                {{ DateTime.fromJSDate(date).toLocaleString({month: 'short', day: 'numeric', year: 'numeric'}) }}
                <v-menu activator="parent" v-model="pickerOpen" :close-on-content-click="false" location="bottom end">
                    <v-date-picker v-model="date" hide-header color="primary" @update:model-value="pickerOpen = false"
                                   :first-day-of-week="useUserPreferenceStore().deviceSettings.mealplan_startingDayOfWeek"></v-date-picker>
                </v-menu>
            </v-btn>
            <v-btn variant="outlined" size="small" icon :aria-label="$t('Settings')" :title="$t('Settings')">
                <v-icon icon="fa-solid fa-sliders" size="small"></v-icon>
                <v-menu activator="parent" :close-on-content-click="false" location="bottom end">
                    <v-card width="320" class="mpc-options">
                        <v-card-text class="pb-2">
                            <meal-plan-device-settings compact></meal-plan-device-settings>
                        </v-card-text>
                        <v-divider></v-divider>
                        <v-list density="compact" class="py-1">
                            <meal-plan-ical-dialog></meal-plan-ical-dialog>
                        </v-list>
                    </v-card>
                </v-menu>
            </v-btn>
        </div>
    </div>
</template>

<script setup lang="ts">

import {IHeaderProps} from "vue-simple-calendar/dist/src/IHeaderProps";
import {computed, ref, watch} from "vue";
import {useDisplay} from "vuetify";
import {DateTime} from "luxon";
import {useUserPreferenceStore} from "@/stores/UserPreferenceStore";
import ShopWeekButton from "@/components/buttons/ShopWeekButton.vue";
import AutoPlanDialog from "@/components/dialogs/AutoPlanDialog.vue";
import MealPlanIcalDialog from "@/components/dialogs/MealPlanIcalDialog.vue";
import MealPlanDeviceSettings from "@/components/settings/MealPlanDeviceSettings.vue";

const emit = defineEmits(['input'])

const props = defineProps({
    headerProps: {
        type: Object as () => IHeaderProps,
        required: true,
    },
})

const date = ref(new Date())
const {mdAndUp, smAndUp} = useDisplay()
const lastShownDate = computed(() => DateTime.fromJSDate(props.headerProps?.displayLastDate).minus({day: 1}))
const pickerOpen = ref(false)

watch(() => date.value, (newValue, oldValue) => {
    emit('input', newValue)
})

</script>

<style scoped>
.mpc-header {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px 16px;
}

.mpc-range {
    white-space: nowrap;
    font-size: 1.125rem;
    font-weight: 600;
    letter-spacing: -0.01em;
}

.mpc-tools {
    margin-left: auto;
    display: flex;
    flex-wrap: wrap;
    justify-content: flex-end;
    min-width: 0;
    align-items: center;
    gap: 8px;
}

/* phones and unfolded phones: range on its own line, tools below it from the left */
@media (max-width: 759.98px) {
    .mpc-header {
        flex-wrap: wrap;
        row-gap: 10px;
    }

    .mpc-tools {
        margin-left: 0;
        width: 100%;
        justify-content: flex-start;
    }
}

/* the two arrows as one joined control */
.mpc-group {
    display: inline-flex;
}

.mpc-group .v-btn {
    width: 32px !important;
    height: 32px !important;
    border-radius: 0 !important;
}

.mpc-group .v-btn:first-child {
    border-radius: 8px 0 0 8px !important;
}

.mpc-group .v-btn:last-child {
    border-radius: 0 8px 8px 0 !important;
    margin-left: -1px;
}

.mpc-group .v-btn :deep(.v-icon) {
    font-size: 12px;
    opacity: 0.7;
}

.mpc-date {
    min-width: 140px;
    justify-content: flex-start;
}
</style>