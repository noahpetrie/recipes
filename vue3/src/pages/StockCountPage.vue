<template>
    <!-- home fork: review a stock count and apply the differences (nothing changes before Apply) -->
    <v-container class="scp">
        <v-btn variant="text" size="small" prepend-icon="fa-solid fa-arrow-left" :to="{name: 'PantryPage'}" class="px-1 mb-2">{{ $t('Pantry') }}</v-btn>
        <div v-if="count" class="d-flex align-center flex-wrap ga-3 mb-1">
            <h1 class="scp-title">{{ $t('HomeStockCountOf', {place: count.location.name}, 'Stock count: {place}') }}</h1>
            <span class="scp-status" :class="count.status">{{ statusLabel(count.status) }}</span>
            <v-spacer></v-spacer>
            <template v-if="count.status == 'open'">
                <v-btn variant="outlined" prepend-icon="fa-solid fa-barcode" @click="openScanPanel({mode: 'count'})">{{ $t('HomeKeepScanning', 'Keep scanning') }}</v-btn>
                <v-btn variant="text" color="delete" @click="discardOpen = true">{{ $t('HomeDiscard', 'Discard') }}</v-btn>
            </template>
        </div>
        <p v-if="count" class="text-body-2 text-medium-emphasis mb-5">
            {{ $t('HomeStartedOn', {date: fmtDate(count.created_at)}, 'Started {date}') }} · {{ count.counted }} {{ $t('HomeCountedLower', 'counted') }} ·
            {{ count.discrepancies }} {{ $t('HomeDifferent', 'different') }} · {{ count.not_counted?.length ?? 0 }} {{ $t('HomeNotCountedLower', 'not counted') }}
        </p>

        <v-alert v-if="error" type="error" variant="tonal" density="compact" class="mb-4" role="alert">{{ error }}</v-alert>

        <template v-if="count">
            <div class="scp-card">
                <table class="scp-table">
                    <thead>
                    <tr>
                        <th v-if="count.status == 'open'" class="w-0"><span class="d-sr-only">{{ $t('HomeApply', 'Apply') }}</span></th>
                        <th>{{ $t('Food') }}</th>
                        <th class="num">{{ $t('HomeOnFile', 'On file') }}</th>
                        <th class="num">{{ $t('HomeCounted', 'Counted') }}</th>
                        <th class="num">{{ $t('HomeDifference', 'Difference') }}</th>
                        <th>{{ $t('HomeStatus', 'Status') }}</th>
                    </tr>
                    </thead>
                    <tbody>
                    <tr v-if="!count.lines.length">
                        <td :colspan="6" class="text-medium-emphasis py-6 text-center">{{ $t('HomeNothingCounted', 'Nothing counted yet. Scan products in Stock count mode.') }}</td>
                    </tr>
                    <tr v-for="l in count.lines" :key="l.id" :class="{'scp-done': l.applied}">
                        <td v-if="count.status == 'open'">
                            <v-checkbox-btn v-if="!l.applied" v-model="selected" :value="l.id" :disabled="l.status == 'changed'" density="compact"
                                            :aria-label="$t('HomeApplyLine', {food: l.food.name}, 'Apply {food}')"></v-checkbox-btn>
                        </td>
                        <td>
                            <div class="font-weight-medium">{{ l.food.name }}</div>
                            <div v-if="l.status == 'needs_batch' && !l.applied" class="mt-1">
                                <v-select v-model="batches[l.id]" :items="batchItems(l)" item-title="title" item-value="value" density="compact" hide-details
                                          :label="$t('HomeWhichBatchChanged', 'Which batch changed?')" class="scp-batch"></v-select>
                            </div>
                            <div v-if="l.result" class="text-body-2 text-medium-emphasis">{{ l.result }}</div>
                            <div v-if="lineErrors[l.id]" class="text-body-2 text-error">{{ lineErrors[l.id] }}</div>
                        </td>
                        <td class="num">
                            {{ qty(l.recorded, l.unit) }}
                            <div v-if="l.status == 'changed'" class="text-body-2 text-error">{{ $t('HomeNowN', {q: qty(l.recorded_now, l.unit)}, 'now {q}') }}</div>
                        </td>
                        <td class="num">{{ qty(l.counted, l.unit) }}</td>
                        <td class="num" :class="l.delta > 0 ? 'text-success' : l.delta < 0 ? 'text-error' : ''">{{ l.delta == 0 ? '—' : (l.delta > 0 ? '+' : '−') + fmtAmount(Math.abs(l.delta)) }}</td>
                        <td>
                            <span class="scp-pill" :class="l.status">{{ lineStatus(l) }}</span>
                            <div v-if="l.status == 'changed' && !l.applied" class="mt-1 d-flex ga-1 flex-wrap">
                                <v-btn size="x-small" variant="outlined" @click="keepCount(l)">{{ $t('HomeKeepMyCount', 'Keep my count') }}</v-btn>
                                <v-btn size="x-small" variant="text" @click="removeLine(l)">{{ $t('HomeRecount', 'Re-count') }}</v-btn>
                            </div>
                        </td>
                    </tr>
                    </tbody>
                </table>
            </div>

            <div v-if="count.status == 'open'" class="d-flex align-center flex-wrap ga-3 mt-4">
                <span class="text-body-2 text-medium-emphasis">{{ applySummary }}</span>
                <v-spacer></v-spacer>
                <v-btn color="primary" variant="flat" :disabled="!selected.length" :loading="busy" @click="confirmOpen = true">
                    {{ $t('HomeApplyN', {n: selected.length}, 'Apply {n} line(s)') }}
                </v-btn>
                <v-btn variant="outlined" :disabled="busy" @click="finish">{{ $t('HomeFinishCount', 'Finish count') }}</v-btn>
            </div>

            <div v-if="count.not_counted?.length" class="mt-8">
                <div class="scp-section">{{ $t('HomeNotCounted', 'Not counted') }} ({{ count.not_counted.length }})</div>
                <p class="text-body-2 text-medium-emphasis">{{ $t('HomeNotCountedHelp', {place: count.location.name}, 'On file in {place} but not scanned in this count. They’re left exactly as they are — not set to zero.') }}</p>
                <div class="scp-uncounted">
                    <span v-for="u in count.not_counted" :key="u.food.id + '-' + (u.unit?.id ?? 0)" class="scp-chip">{{ u.food.name }} · {{ qty(u.recorded, u.unit) }}</span>
                </div>
            </div>
        </template>

        <!-- confirm apply -->
        <v-dialog v-model="confirmOpen" max-width="480">
            <v-card>
                <v-card-title>{{ $t('HomeApplyCountQ', 'Apply this count?') }}</v-card-title>
                <v-card-text>
                    <p class="mb-2">{{ $t('HomeApplyCountHelp', 'Each line is checked against what’s on file right now; a line that changed since you counted is skipped.') }}</p>
                    <ul class="scp-confirm">
                        <li v-for="l in count?.lines.filter((x: any) => selected.includes(x.id))" :key="l.id">
                            {{ l.food.name }}: {{ qty(l.recorded, l.unit) }} → {{ qty(l.counted, l.unit) }}
                            <span v-if="l.delta == 0" class="text-medium-emphasis"> ({{ $t('HomeMarkedCounted', 'marked as counted') }})</span>
                        </li>
                    </ul>
                </v-card-text>
                <v-card-actions>
                    <v-spacer></v-spacer>
                    <v-btn variant="text" @click="confirmOpen = false">{{ $t('Cancel') }}</v-btn>
                    <v-btn color="primary" variant="flat" :loading="busy" @click="apply">{{ $t('HomeApply', 'Apply') }}</v-btn>
                </v-card-actions>
            </v-card>
        </v-dialog>

        <v-dialog v-model="discardOpen" max-width="420">
            <v-card>
                <v-card-title>{{ $t('HomeDiscardCountQ', 'Discard this count?') }}</v-card-title>
                <v-card-text>{{ $t('HomeDiscardCountHelp', 'Counts not yet applied are thrown away. The pantry stays as it is.') }}</v-card-text>
                <v-card-actions>
                    <v-spacer></v-spacer>
                    <v-btn variant="text" @click="discardOpen = false">{{ $t('Cancel') }}</v-btn>
                    <v-btn color="delete" variant="flat" @click="discard">{{ $t('HomeDiscard', 'Discard') }}</v-btn>
                </v-card-actions>
            </v-card>
        </v-dialog>
    </v-container>
</template>

<script setup lang="ts">
import {computed, onMounted, ref, watch} from "vue";
import {useI18n} from "vue-i18n";
import {useRouter} from "vue-router";
import {fmtAmount, fmtDate, openScanPanel, pantryApi, pantryVersion, qty, store} from "@/composables/useScan";

const props = defineProps<{ id: string }>()
const {t} = useI18n()
const router = useRouter()

const count = ref<any>(null)
const error = ref('')
const busy = ref(false)
const selected = ref<number[]>([])
const batches = ref<Record<number, number | string>>({})
const lineErrors = ref<Record<number, string>>({})
const confirmOpen = ref(false)
const discardOpen = ref(false)

async function load() {
    try {
        count.value = await pantryApi(`counts/${props.id}/`)
        // pre-select what can be applied: differences and matches, not lines that changed underneath
        selected.value = count.value.lines.filter((l: any) => !l.applied && l.status != 'changed').map((l: any) => l.id)
        error.value = ''
    } catch (err: any) {
        error.value = err.message
    }
}

onMounted(load)
watch(pantryVersion, load)

const applySummary = computed(() => {
    const lines = count.value?.lines.filter((l: any) => selected.value.includes(l.id)) ?? []
    const changes = lines.filter((l: any) => l.delta != 0).length
    return t('HomeApplySummary', {c: changes, m: lines.length - changes}, '{c} change(s), {m} confirmed as counted')
})

function batchItems(l: any) {
    return [...l.batches.map((b: any) => ({title: `#${b.code} · ${qty(b.amount, b.unit)}${b.expires ? ' · ' + fmtDate(b.expires) : ''}`, value: b.id})),
        ...(l.delta > 0 ? [{title: t('HomeAsNewBatch', 'A new batch'), value: 'new'}] : [])]
}

function statusLabel(s: string) {
    return ({open: t('HomeInProgress', 'In progress'), applied: t('HomeFinished', 'Finished'), discarded: t('HomeDiscarded2', 'Discarded')} as any)[s] ?? s
}

function lineStatus(l: any) {
    if (l.applied) return t('HomeApplied', 'Applied')
    return ({matches: t('HomeMatches', 'Matches'), discrepancy: t('HomeDifferentCap', 'Different'), needs_batch: t('HomeChooseBatchShort', 'Choose batch'),
        changed: t('HomeChangedSince', 'Changed since counted')} as any)[l.status] ?? l.status
}

async function apply() {
    const missing = count.value.lines.filter((l: any) => selected.value.includes(l.id) && l.status == 'needs_batch' && !batches.value[l.id])
    if (missing.length) {
        confirmOpen.value = false
        error.value = t('HomeChooseBatchesFirst', {foods: missing.map((l: any) => l.food.name).join(', ')}, 'Choose which batch changed for: {foods}')
        return
    }
    busy.value = true
    try {
        const r = await pantryApi(`counts/${props.id}/apply/`, {line_ids: selected.value, batches: batches.value})
        lineErrors.value = Object.fromEntries(r.results.filter((x: any) => !x.ok).map((x: any) => [x.line_id, x.error]))
        count.value = r.count
        selected.value = count.value.lines.filter((l: any) => !l.applied && l.status != 'changed' && !lineErrors.value[l.id]).map((l: any) => l.id)
        pantryVersion.value++
        const ok = r.results.filter((x: any) => x.ok).length
        error.value = Object.keys(lineErrors.value).length ? t('HomeSomeNotApplied', {ok, n: Object.keys(lineErrors.value).length}, '{ok} applied, {n} not applied — see the lines below.') : ''
    } catch (err: any) {
        error.value = err.message
    } finally {
        busy.value = false
        confirmOpen.value = false
    }
}

async function keepCount(l: any) {
    // take the current on-file amount as the new baseline and keep what was counted
    await pantryApi(`counts/${props.id}/line/`, {line_id: l.id}, 'DELETE')
    await pantryApi(`counts/${props.id}/line/`, {food_id: l.food.id, unit_id: l.unit?.id ?? null, counted: l.counted})
    await load()
}

async function removeLine(l: any) {
    await pantryApi(`counts/${props.id}/line/`, {line_id: l.id}, 'DELETE')
    await load()
}

async function finish() {
    await pantryApi(`counts/${props.id}/finish/`, {})
    store('kitchen:openCount', null)
    await load()
}

async function discard() {
    await pantryApi(`counts/${props.id}/finish/`, {discard: true})
    store('kitchen:openCount', null)
    discardOpen.value = false
    router.push({name: 'PantryPage'})
}
</script>

<style scoped>
.scp-title {
    font-size: 1.5rem;
    font-weight: 650;
    letter-spacing: -0.015em;
}

.scp-status, .scp-pill {
    font-size: 0.75rem;
    font-weight: 500;
    padding: 2px 8px;
    border-radius: 6px;
    background: rgba(var(--v-theme-on-surface), 0.06);
    white-space: nowrap;
}

.scp-status.open, .scp-pill.needs_batch {
    background: rgba(var(--v-theme-warning), 0.16);
}

.scp-pill.discrepancy {
    background: rgba(var(--v-theme-primary), 0.12);
    color: rgb(var(--v-theme-primary));
}

.scp-pill.changed {
    background: rgba(var(--v-theme-error), 0.12);
    color: rgb(var(--v-theme-error));
}

.scp-card {
    border-radius: 12px;
    box-shadow: 0 0 0 1px rgba(var(--v-theme-on-surface), 0.1);
    background: rgb(var(--v-theme-surface));
    overflow-x: auto;
}

.scp-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.875rem;
}

.scp-table th {
    text-align: left;
    font-weight: 500;
    font-size: 0.8125rem;
    color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
    padding: 10px 12px;
    border-bottom: 1px solid rgba(var(--v-theme-on-surface), 0.08);
}

.scp-table td {
    padding: 10px 12px;
    vertical-align: top;
    border-bottom: 1px solid rgba(var(--v-theme-on-surface), 0.06);
}

.scp-table .num {
    text-align: right;
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
}

.scp-done {
    opacity: 0.6;
}

.scp-batch {
    max-width: 280px;
}

.scp-section {
    font-weight: 600;
    margin-bottom: 4px;
}

.scp-uncounted {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
}

.scp-chip {
    font-size: 0.8125rem;
    padding: 2px 8px;
    border-radius: 6px;
    background: rgba(var(--v-theme-on-surface), 0.05);
}

.scp-confirm {
    padding-left: 18px;
    font-size: 0.875rem;
}
</style>
