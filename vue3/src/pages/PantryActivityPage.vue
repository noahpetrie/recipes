<template>
    <v-container>
        <v-btn variant="text" prepend-icon="fa-solid fa-arrow-left" :to="{name: 'PantryPage'}" class="mb-4">Pantry</v-btn>
        <h1 class="text-h4 font-weight-bold mb-2">Inventory activity</h1>
        <p class="text-medium-emphasis mb-6">All recorded changes, including corrections and reversals.</p>
        <v-card><v-card-text>
            <v-model-select model="Food" v-model="food" clearable hide-details class="mb-4" />
            <v-alert v-if="error" type="error" variant="tonal" class="mb-4">Couldn’t load activity. <v-btn variant="text" @click="load">Retry</v-btn></v-alert>
            <v-data-table-server :headers="headers" :items="items" :items-length="count" :loading="loading" v-model:page="page" v-model:items-per-page="pageSize" :items-per-page-options="[10, 25, 50]" disable-sort @update:options="load">
                <template #item.bookingType="{item}">{{ eventLabel(item.bookingType || '', item.note || '') }}</template>
                <template #item.createdAt="{item}">{{ item.createdAt.toLocaleString() }}</template>
                <template #item.product="{item}">{{ item.entry.food?.name || 'Unassigned product' }}<div class="text-caption">Item label #{{ item.entry.code }}</div></template>
                <template #item.change="{item}">{{ change(item) }}</template>
                <template #item.location="{item}">{{ item.oldInventoryLocation?.id !== item.newInventoryLocation?.id ? `${item.oldInventoryLocation?.name || 'Unassigned'} → ` : '' }}{{ item.newInventoryLocation?.name || 'Unassigned' }}</template>
                <template #item.note="{item}">{{ String(item.bookingType) === 'undo' ? item.note?.replace(/^undid #/, 'Reverses activity #') : item.note }}</template>
            </v-data-table-server>
        </v-card-text></v-card>
    </v-container>
</template>
<script setup lang="ts">
import {onUnmounted, ref, watch} from 'vue'
import {ApiApi, type Food, type InventoryLog} from '@/openapi'
import VModelSelect from '@/components/inputs/VModelSelect.vue'
import {eventLabel} from '@/utils/pantryActivity'
import {decimalSum, quantity} from '@/utils/pantry'
import {pantryVersion} from '@/composables/useScan'
const food = ref<Food | null>(null)
const items = ref<InventoryLog[]>([])
const count = ref(0)
const page = ref(1)
const pageSize = ref(25)
const loading = ref(false)
const error = ref(false)
const headers = [{title: 'Event', key: 'id'}, {title: 'Action', key: 'bookingType'}, {title: 'Date and time', key: 'createdAt'}, {title: 'Product / label', key: 'product'}, {title: 'Quantity change', key: 'change'}, {title: 'Location', key: 'location'}, {title: 'Note', key: 'note'}]
function change(item: InventoryLog) {
    const delta = decimalSum([item.newAmount ?? 0, -(item.oldAmount ?? 0)])
    return `${Number(delta) > 0 ? '+' : ''}${quantity(delta, item.entry.unit)}`
}
let sequence = 0
async function load() {
    const current = ++sequence
    loading.value = true
    error.value = false
    try {
        const result = await new ApiApi().apiInventoryLogList({foodId: food.value?.id, page: page.value, pageSize: pageSize.value})
        if (current === sequence) { items.value = result.results; count.value = result.count }
    } catch { if (current === sequence) { items.value = []; count.value = 0; error.value = true } }
    finally { if (current === sequence) loading.value = false }
}
watch(food, () => { page.value = 1; load() })
watch(pantryVersion, load)
onUnmounted(() => sequence++)
</script>
