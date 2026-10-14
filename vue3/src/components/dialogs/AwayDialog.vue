<template>
    <!-- home fork: mark days away; the meal plan shows them and restock holds back fresh food (composables/useAway.ts) -->
    <v-dialog v-model="open" max-width="420">
        <v-card>
            <v-card-title class="d-flex align-center ga-2 pt-4"><v-icon icon="fa-solid fa-suitcase-rolling" size="small" />I’m away</v-card-title>
            <v-card-text>
                <v-row dense>
                    <v-col cols="6"><v-text-field v-model="from" type="date" label="From" density="comfortable" /></v-col>
                    <v-col cols="6"><v-text-field v-model="to" type="date" label="Back" :min="from" density="comfortable" /></v-col>
                    <v-col cols="12"><v-text-field v-model="place" label="Where (optional)" placeholder="e.g. Montreal" density="comfortable" clearable @keydown.enter="save" /></v-col>
                </v-row>
                <p class="text-body-2 text-medium-emphasis">Fresh food won’t be suggested for restocking just before you go.</p>
            </v-card-text>
            <v-card-actions>
                <v-spacer />
                <v-btn variant="text" @click="open = false">Cancel</v-btn>
                <v-btn color="primary" variant="flat" :loading="saving" :disabled="!from || !to || to < from" @click="save">Save</v-btn>
            </v-card-actions>
        </v-card>
    </v-dialog>
</template>

<script setup lang="ts">
import {ref, watch} from 'vue'
import {DateTime} from 'luxon'
import {markAway} from '@/composables/useAway'

const open = defineModel<boolean>({default: false})
const props = defineProps({start: {type: Object as () => Date, default: () => new Date()}})

const from = ref(''), to = ref(''), place = ref('')
const saving = ref(false)

watch(open, o => {
    if (!o) return
    from.value = DateTime.fromJSDate(props.start).toISODate()!
    to.value = DateTime.fromJSDate(props.start).plus({days: 2}).toISODate()!
    place.value = ''
})
watch(from, f => { if (to.value && f > to.value) to.value = f })

async function save() {
    if (!from.value || !to.value || to.value < from.value) return
    saving.value = true
    try {
        // noon, so the day doesn't shift with the time zone
        await markAway(DateTime.fromISO(from.value).set({hour: 12}).toJSDate(), DateTime.fromISO(to.value).set({hour: 12}).toJSDate(), place.value ?? '')
        open.value = false
    } finally {
        saving.value = false
    }
}
</script>
