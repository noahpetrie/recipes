<template>
    <!-- home fork: the equipment a recipe needs and whether the kitchen has it (cookbook/views/home_equipment.py) -->
    <v-card v-if="state && (state.items.length || editing || state.suggestions.length)" class="mt-1 equipment-card">
        <v-card-text>
            <div class="d-flex align-center mb-2">
                <h3 class="text-subtitle-1 font-weight-bold flex-grow-1"><v-icon icon="fa-solid fa-blender" size="small" class="me-2" />Equipment</h3>
                <span v-if="!editing && missingCount" class="text-caption text-warning me-2">{{ missingCount }} you don’t have</span>
                <v-btn v-if="!editing && canEdit" variant="text" size="small" class="d-print-none" @click="startEdit">Edit</v-btn>
            </div>

            <template v-if="!editing">
                <div class="d-flex flex-wrap ga-2">
                    <v-menu v-for="e in state.items" :key="e.id" :disabled="e.have">
                        <template #activator="{props}">
                            <v-chip v-bind="props" :variant="e.have ? 'tonal' : 'outlined'" :color="e.have ? undefined : 'warning'" :title="e.via ? `Using your ${e.via}` : (e.have ? 'You have this' : 'You don’t have this')">
                                <template #prepend>
                                    <img v-if="e.image" :src="e.image" alt="" class="chip-img">
                                    <v-icon v-else :icon="e.have ? 'fa-solid fa-check' : 'fa-solid fa-circle-exclamation'" size="x-small" class="me-1" :color="e.have ? 'success' : 'warning'" />
                                </template>
                                <span v-if="e.note" class="me-1">{{ e.note }}</span>{{ e.note ? e.name.toLowerCase() : e.name }}
                                <span v-if="e.optional" class="text-medium-emphasis ms-1">(optional)</span>
                            </v-chip>
                        </template>
                        <v-list density="compact">
                            <v-list-item prepend-icon="fa-solid fa-check" title="I have this" subtitle="Mark it as owned" @click="ownIt(e)" />
                            <v-list-item prepend-icon="fa-solid fa-blender" title="All equipment" :to="{name: 'EquipmentPage'}" />
                        </v-list>
                    </v-menu>
                </div>
                <div v-if="state.items.length == 0" class="text-body-2 text-medium-emphasis">None listed.</div>
                <div v-if="state.suggestions.length && canEdit" class="d-flex flex-wrap align-center ga-1 mt-3 d-print-none">
                    <span class="text-caption text-medium-emphasis me-1">The steps also mention</span>
                    <v-chip v-for="s in state.suggestions" :key="s" size="small" variant="text" prepend-icon="fa-solid fa-plus" @click="addSuggestion(s)">{{ s }}</v-chip>
                </div>
            </template>

            <template v-else>
                <div v-for="(l, i) in draft" :key="l.key" class="edit-row">
                    <span class="flex-grow-1 min-w-0 text-truncate">{{ l.name }}</span>
                    <v-text-field v-model="l.note" placeholder="Size" hide-details density="compact" class="note-field" :aria-label="`Size of ${l.name}`" />
                    <v-checkbox-btn v-model="l.optional" density="compact" class="flex-grow-0" :aria-label="`${l.name} is optional`" />
                    <span class="text-caption text-medium-emphasis">optional</span>
                    <v-btn icon="fa-solid fa-xmark" variant="text" size="small" :aria-label="`Remove ${l.name}`" @click="draft.splice(i, 1)" />
                </div>
                <v-combobox v-model="adding" :items="choices" label="Add equipment" placeholder="Stand mixer, 9-inch springform pan…" hide-details density="compact" class="mt-3"
                            @update:model-value="addPicked" />
                <div v-if="draftSuggestions.length" class="d-flex flex-wrap align-center ga-1 mt-2">
                    <span class="text-caption text-medium-emphasis me-1">Mentioned in the steps</span>
                    <v-chip v-for="s in draftSuggestions" :key="s" size="small" variant="outlined" prepend-icon="fa-solid fa-plus" @click="pushDraft(s)">{{ s }}</v-chip>
                </div>
                <v-alert v-if="error" type="error" variant="tonal" density="compact" class="mt-3">{{ error }}</v-alert>
                <div class="d-flex justify-end ga-2 mt-3">
                    <v-btn variant="text" @click="editing = false">Cancel</v-btn>
                    <v-btn color="primary" variant="flat" :loading="saving" @click="save">Save</v-btn>
                </div>
            </template>
        </v-card-text>
    </v-card>
</template>

<script setup lang="ts">
import {computed, onMounted, ref, watch} from 'vue'
import {Equipment, equipmentApi, equipmentVersion, RecipeEquipmentLine} from '@/composables/useEquipment'

const props = defineProps<{ recipeId: number, canEdit?: boolean }>()
const emit = defineEmits<{ converted: [] }>()

const state = ref<{ items: RecipeEquipmentLine[], suggestions: string[] } | null>(null)
const editing = ref(false)
const saving = ref(false)
const error = ref('')
let ownWrite = false

async function load() {
    try {
        const r = await equipmentApi(`recipe/${props.recipeId}/`)
        state.value = r
        if (r.converted) emit('converted')
    } catch {
        state.value = null  // the recipe reads fine without it
    }
}

const missingCount = computed(() => (state.value?.items ?? []).filter(e => !e.have && !e.optional).length)

async function ownIt(e: Equipment) {
    try {
        ownWrite = true
        await equipmentApi(`${e.id}/`, 'PATCH', {owned: true})
        await load()
    } catch { /* stays as it was */ }
}

async function addSuggestion(name: string) {
    await put([...(state.value?.items ?? []).map(l => ({id: l.id, optional: l.optional, note: l.note})), {name}])
}

// editing
type Draft = { key: string, id?: number, name: string, optional: boolean, note: string }
const draft = ref<Draft[]>([])
const all = ref<Equipment[]>([])
const adding = ref<any>(null)

function startEdit() {
    draft.value = (state.value?.items ?? []).map(l => ({key: `e${l.id}`, id: l.id, name: l.name, optional: l.optional, note: l.note}))
    error.value = ''
    editing.value = true
    equipmentApi('').then(r => all.value = r.equipment.filter((e: Equipment) => !e.hidden)).catch(() => {})
}

const choices = computed(() => all.value.map(e => e.name).filter(n => !draft.value.some(d => d.name == n)))
const draftSuggestions = computed(() => (state.value?.suggestions ?? []).filter(s => !draft.value.some(d => d.name.toLowerCase() == s.toLowerCase())))

function pushDraft(name: string) {
    const e = all.value.find(x => x.name.toLowerCase() == name.toLowerCase())
    draft.value.push({key: `n${Date.now()}${name}`, id: e?.id, name: e?.name ?? name, optional: false, note: ''})
}

function addPicked(v: any) {
    const name = (typeof v == 'string' ? v : v?.title ?? '').trim()
    if (name) pushDraft(name)
    setTimeout(() => adding.value = null)
}

async function put(items: any[]) {
    ownWrite = true
    state.value = await equipmentApi(`recipe/${props.recipeId}/`, 'PUT', {items})
}

async function save() {
    saving.value = true
    error.value = ''
    try {
        await put(draft.value.map(d => d.id ? {id: d.id, optional: d.optional, note: d.note} : {name: d.name, optional: d.optional, note: d.note}))
        editing.value = false
    } catch (e: any) {
        error.value = e.message
    } finally {
        saving.value = false
    }
}

watch(() => props.recipeId, load)
watch(equipmentVersion, () => {
    if (ownWrite) { ownWrite = false; return }
    if (!editing.value) load()
})
onMounted(load)
</script>

<style scoped>
.chip-img { width: 20px; height: 20px; object-fit: contain; margin-inline-end: 6px; margin-inline-start: -4px; }
.edit-row { display: flex; align-items: center; gap: 6px; min-height: 44px; border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity)); }
.note-field { max-width: 110px; flex: 0 0 110px; }
.min-w-0 { min-width: 0; }
</style>
