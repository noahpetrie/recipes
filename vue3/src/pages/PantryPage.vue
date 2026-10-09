<template>


    <v-container>
        <v-row dense>
            <v-col>
                <v-card prepend-icon="$pantry" :title="$t('Pantry')" class="page-header">
                    <template #subtitle>
                        <div class="text-wrap">
                            {{ $t('PantryHelp') }}
                        </div>
                    </template>
                    <template #append>
                        <!-- home fork: scanning looks things up; Restock adds; Stock count reconciles -->
                        <div class="d-flex flex-wrap ga-2 justify-end">
                            <v-btn variant="outlined" prepend-icon="fa-solid fa-barcode" @click="openScanPanel({mode: 'lookup'})">{{ $t('HomeScan', 'Scan') }}</v-btn>
                            <v-btn variant="outlined" prepend-icon="fa-solid fa-list-check" @click="openScanPanel({mode: 'count'})">{{ $t('HomeStockCount', 'Stock count') }}</v-btn>
                            <v-btn color="create" prepend-icon="$create" @click="openScanPanel({mode: 'restock'})">{{ $t('HomeRestock', 'Restock') }}</v-btn>
                        </div>

                    </template>
                </v-card>
            </v-col>
        </v-row>
        <v-row>
            <v-col cols="12">
                <v-card>
                    <v-card-text>
                        <v-row>
                            <v-col cols="12" md="6">
                                <v-model-select model="Food" v-model="food" hide-details></v-model-select>
                            </v-col>

                            <v-col cols="12" md="6">
                                <v-model-select model="InventoryLocation" v-model="inventoryLocation" hide-details></v-model-select>
                            </v-col>
                        </v-row>


                        <v-data-table-server
                            return-object
                            @update:options="loadItems"
                            :items="items"
                            :items-length="itemCount"
                            :loading="tableLoading"
                            :headers="tableHeaders"
                            :page="page"
                            :items-per-page="pageSize"
                            disable-sort
                        >
                            <template #item.code="{item}">
                                <v-chip size="small" label color="warning" class="me-2" prepend-icon="fa-solid fa-barcode">{{ item.code }}</v-chip>
                            </template>
                            <template #item.food="{item}">
                                {{ ingredientToString({food: item.food, unit: item.unit, amount: item.amount} as Ingredient) }}
                            </template>
                            <template #item.expires="{item}">
                                <template v-if="item.expires ">
                                    <v-chip size="small" label :color="(item.expires < DateTime.now() ? 'error' : 'success')">
                                        {{ DateTime.fromJSDate(item.expires).toLocaleString(DateTime.DATE_MED) }}
                                    </v-chip>
                                </template>
                            </template>
                            <template #item.inventoryLocation="{ item }">
                                {{ item.inventoryLocation.name }} <i class="fa-solid fa-snowflake" v-if="item.inventoryLocation.isFreezer"></i>
                                <span class="text-body-2 text-disabled">
                                    <br/>
                                {{ item.subLocation }}
                                </span>
                            </template>
                            <template #item.action="{item}">
                                <!-- home fork: the same actions as after a scan -->
                                <v-btn-group divided border density="comfortable">
                                    <v-btn icon="fa-solid fa-minus" :title="$t('HomeUseRemove', 'Use')" @click="openScanPanel({foodId: item.food.id, entryId: item.id, tab: 'use'})"></v-btn>
                                    <v-btn icon="fa-solid fa-arrow-right" :title="$t('Move')" @click="openScanPanel({foodId: item.food.id, entryId: item.id, tab: 'move'})"></v-btn>
                                    <v-btn icon="fa-solid fa-ellipsis" :title="$t('HomeDetails', 'Details')" @click="openScanPanel({foodId: item.food.id, entryId: item.id, tab: 'details'})"></v-btn>
                                </v-btn-group>

                            </template>
                        </v-data-table-server>

                        <inventory-entry-log-dialog v-model="entryLogDialog" :inventory-entry="entryLogEntry"></inventory-entry-log-dialog>

                        <pantry-booking-dialog v-model="bookingDialog" :bookingMode="bookingMode" :inventoryEntryId="bookingEntry?.id"
                                               @update="loadItems({page: page, itemsPerPage: pageSize})"></pantry-booking-dialog>
                    </v-card-text>
                </v-card>
            </v-col>
        </v-row>

        <!-- home fork: counts in progress and recent stock changes -->
        <v-row v-if="openCounts.length">
            <v-col cols="12">
                <div class="pantry-section">{{ $t('HomeOpenCounts', 'Counts in progress') }}</div>
                <div class="d-flex flex-wrap ga-2">
                    <v-btn v-for="c in openCounts" :key="c.id" variant="outlined" size="small" :to="{name: 'StockCountPage', params: {id: c.id}}">
                        {{ c.location.name }} · {{ c.counted }} {{ $t('HomeCountedLower', 'counted') }}
                    </v-btn>
                </div>
            </v-col>
        </v-row>
        <v-row>
            <v-col cols="12">
                <div class="pantry-section">{{ $t('HomeRecentActivity', 'Recent activity') }}</div>
                <div class="pantry-activity">
                    <div v-if="!activity.length" class="text-body-2 text-medium-emphasis pa-3">{{ $t('HomeNoActivity', 'Nothing yet.') }}</div>
                    <div v-for="h in activity" :key="h.id" class="pantry-activity-row">
                        <span class="pantry-kind" :class="'k-' + h.type">{{ kindLabel(h.type, h.note) }}</span>
                        <span class="flex-grow-1 min-w-0">
                            <a href="#" class="font-weight-medium" @click.prevent="openScanPanel({foodId: h.food.id, entryId: h.entry_id, tab: 'details'})">{{ h.food.name }}</a>
                            <span class="text-medium-emphasis"> · {{ activityText(h) }}</span>
                        </span>
                        <span class="text-medium-emphasis text-no-wrap">{{ fmtDate(h.created_at) }}</span>
                    </div>
                </div>
            </v-col>
        </v-row>
    </v-container>

</template>

<script setup lang="ts">

import {DateTime} from "luxon";
import {ingredientToString} from "@/utils/model_utils.ts";
import {ApiApi, ApiInventoryEntryListRequest, Food, Ingredient, InventoryEntry, InventoryLocation} from "@/openapi";
import {onMounted, PropType, ref, watch} from "vue";
import {useI18n} from "vue-i18n";
import InventoryEntryLogDialog from "@/components/dialogs/InventoryEntryLogDialog.vue";
import {VDataTableUpdateOptions} from "@/vuetify.ts";
import {ErrorMessageType, useMessageStore} from "@/stores/MessageStore.ts";
import {useUserPreferenceStore} from "@/stores/UserPreferenceStore.ts";
import PantryBookingDialog from "@/components/dialogs/PantryBookingDialog.vue";
import ModelSelect from "@/components/inputs/ModelSelect.vue";
import VModelSelect from "@/components/inputs/VModelSelect.vue";
import {fmtDate, noteText, openScanPanel, pantryApi, pantryVersion, qty} from "@/composables/useScan";

const {t} = useI18n()

// table
const tableLoading = ref(false)

const items = ref([] as InventoryEntry[])
const itemCount = ref(0)
const page = ref(1)
const pageSize = ref(useUserPreferenceStore().deviceSettings.general_tableItemsPerPage)

const tableHeaders = ref([
    {title: t('Code'), key: 'code'},
    {title: t('Food'), key: 'food'},
    {title: t('Expires'), key: 'expires',},
    {title: t('InventoryLocation'), key: 'inventoryLocation',},
    {title: 'Actions', key: 'action', align: 'end'},
])

const entryLogDialog = ref(false)
const entryLogEntry = ref<InventoryEntry | null>(null)

const bookingDialog = ref(false)
const bookingMode = ref('move')
const bookingEntry = ref<InventoryEntry | null>(null)

const food = ref<Food | undefined>(undefined)
const inventoryLocation = ref<InventoryLocation | undefined>(undefined)

watch(food, () => {
    loadItems({page: 1, itemsPerPage: pageSize.value})
})

watch(inventoryLocation, () => {
    loadItems({page: 1, itemsPerPage: pageSize.value})
})

/**
 * load inventory data based on current props
 */
// home fork: refresh after any change made from the scan panel
watch(pantryVersion, () => {
    loadItems({page: page.value, itemsPerPage: pageSize.value} as VDataTableUpdateOptions)
    loadActivity()
})

const activity = ref<any[]>([])
const openCounts = ref<any[]>([])

function loadActivity() {
    pantryApi('activity/?limit=15').then(r => activity.value = r.results).catch(() => {})
    pantryApi('counts/?status=open').then(r => openCounts.value = r.results).catch(() => {})
}

onMounted(loadActivity)

const REASON_KIND: Record<string, string> = {discarded: 'Thrown out', spoiled: 'Spoiled', donated: 'Given away', other: 'Removed'}

function kindLabel(k: string, note = '') {
    if (k == 'remove' && REASON_KIND[note.split(' ')[0]!]) return t('HomeReason_' + note.split(' ')[0], REASON_KIND[note.split(' ')[0]!]!)
    return ({add: t('HomeKAdd', 'Added'), remove: t('HomeKRemove', 'Used'), move: t('HomeKMove', 'Moved'), count: t('HomeKCount', 'Counted'),
        edit: t('HomeKEdit', 'Edited'), undo: t('HomeKUndo', 'Undone')} as any)[k] ?? k
}

function activityText(h: any) {
    const d = h.delta
    const change = d == 0 ? '' : `${d > 0 ? '+' : '−'}${qty(Math.abs(d), h.unit)} · `
    const place = h.type == 'move' && h.old_location?.id != h.new_location?.id ? `${h.old_location.name} → ${h.new_location.name}` : h.new_location?.name
    return `${change}${place}${noteText(h.type, h.note) ? ' · ' + noteText(h.type, h.note) : ''}${h.by ? ' · ' + h.by : ''}`
}

function loadItems(options: VDataTableUpdateOptions) {
    let api = new ApiApi()

    let parameters = {} as ApiInventoryEntryListRequest

    if (food.value) {
        parameters.foodId = food.value.id!
    }
    if (inventoryLocation.value) {
        parameters.inventoryLocationId = inventoryLocation.value.id!
    }

    tableLoading.value = true

    page.value = options.page
    pageSize.value = options.itemsPerPage

    parameters.page = options.page
    parameters.pageSize = options.itemsPerPage

    api.apiInventoryEntryList(parameters).then((r: any) => {
        items.value = r.results
        itemCount.value = r.count
    }).catch((err: any) => {
        useMessageStore().addError(ErrorMessageType.FETCH_ERROR, err)
    }).finally(() => {
        tableLoading.value = false
    })

}

</script>

<style scoped>
.pantry-section {
    font-weight: 600;
    margin: 4px 0 8px;
}

.pantry-activity {
    border-radius: 12px;
    background: rgb(var(--v-theme-surface));
    box-shadow: 0 0 0 1px rgba(var(--v-theme-on-surface), 0.1);
}

.pantry-activity-row {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 14px;
    font-size: 0.875rem;
    border-top: 1px solid rgba(var(--v-theme-on-surface), 0.06);
}

.pantry-activity-row:first-child {
    border-top: 0;
}

.pantry-activity-row a {
    color: inherit;
    text-decoration: none;
}

.pantry-activity-row a:hover {
    text-decoration: underline;
}

.pantry-kind {
    min-width: 64px;
    font-weight: 600;
}

.pantry-kind.k-add { color: rgb(var(--v-theme-success)); }
.pantry-kind.k-remove { color: rgb(var(--v-theme-error)); }


</style>