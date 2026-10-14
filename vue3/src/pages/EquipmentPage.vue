<template>
    <!-- home fork: kitchen equipment (cookbook/views/home_equipment.py) -->
    <v-container class="equipment-page">
        <header class="eq-header">
            <div class="d-flex align-center ga-4">
                <v-avatar rounded color="primary" variant="tonal" size="48"><v-icon icon="fa-solid fa-blender" /></v-avatar>
                <div>
                    <h1 class="text-h4 font-weight-bold">Equipment</h1>
                    <p class="text-body-2 text-medium-emphasis mt-1">What your kitchen has. Recipes that need something you don’t have aren’t counted as ready to cook.</p>
                </div>
            </div>
            <v-btn color="primary" variant="flat" prepend-icon="fa-solid fa-plus" @click="addOpen = true">Add equipment</v-btn>
        </header>

        <v-alert v-if="error" type="error" variant="tonal" class="mb-4">{{ error }} <v-btn variant="text" size="small" @click="load">Retry</v-btn></v-alert>

        <div class="d-flex flex-wrap align-center ga-3 mb-4">
            <v-btn-toggle v-model="view" mandatory density="comfortable" variant="outlined" divided>
                <v-btn value="needed">Recipes need <span class="count">{{ needed.length }}</span></v-btn>
                <v-btn value="have">You have <span class="count">{{ haveCount }}</span></v-btn>
                <v-btn value="all">All <span class="count">{{ visible.length }}</span></v-btn>
            </v-btn-toggle>
            <v-text-field v-model="search" prepend-inner-icon="$search" label="Search equipment" hide-details clearable density="compact" class="eq-search" />
        </div>

        <v-progress-linear v-if="loading && !items" indeterminate color="primary" />

        <v-sheet v-else-if="items && view == 'needed' && needed.length == 0 && !search" rounded="lg" border class="pa-8 text-center text-medium-emphasis">
            You have everything your recipes call for.
        </v-sheet>

        <v-card v-else-if="items">
            <div v-if="view == 'needed'" class="px-4 pt-4 text-body-2 text-medium-emphasis">Equipment your recipes call for that Kitchen doesn’t know you have. Tick what you own.</div>
            <div class="eq-list">
                <template v-for="g in groups" :key="g.top.id">
                    <div class="eq-row" :class="{'is-top': true}">
                        <equipment-row-content :e="g.top" :busy="busy.has(g.top.id)" @owned="v => setOwned(g.top, v)" />
                        <v-menu>
                            <template #activator="{props}"><v-btn v-bind="props" icon="fa-solid fa-ellipsis-vertical" variant="text" size="small" :aria-label="`More for ${g.top.name}`" /></template>
                            <v-list density="compact">
                                <v-list-item v-if="!g.top.kind && !g.children.length" prepend-icon="fa-solid fa-folder-tree" title="Put under a kind…" @click="openKind(g.top)" />
                                <v-list-item prepend-icon="fa-solid fa-pen" title="Rename" @click="openRename(g.top)" />
                                <v-list-item :prepend-icon="g.top.hidden ? 'fa-solid fa-eye' : 'fa-solid fa-eye-slash'" :title="g.top.hidden ? 'Show' : 'Hide: not kitchen gear'" @click="patch(g.top, {hidden: !g.top.hidden})" />
                                <v-list-item prepend-icon="fa-solid fa-trash" title="Remove" base-color="error" @click="remove(g.top)" />
                            </v-list>
                        </v-menu>
                    </div>
                    <div v-for="c in g.children" :key="c.id" class="eq-row is-child">
                        <equipment-row-content :e="c" :busy="busy.has(c.id)" child @owned="v => setOwned(c, v)" />
                        <v-menu>
                            <template #activator="{props}"><v-btn v-bind="props" icon="fa-solid fa-ellipsis-vertical" variant="text" size="small" :aria-label="`More for ${c.name}`" /></template>
                            <v-list density="compact">
                                <v-list-item prepend-icon="fa-solid fa-folder-tree" title="Put under another kind…" @click="openKind(c)" />
                                <v-list-item prepend-icon="fa-solid fa-pen" title="Rename" @click="openRename(c)" />
                                <v-list-item :prepend-icon="c.hidden ? 'fa-solid fa-eye' : 'fa-solid fa-eye-slash'" :title="c.hidden ? 'Show' : 'Hide: not kitchen gear'" @click="patch(c, {hidden: !c.hidden})" />
                                <v-list-item prepend-icon="fa-solid fa-trash" title="Remove" base-color="error" @click="remove(c)" />
                            </v-list>
                        </v-menu>
                    </div>
                </template>
                <p v-if="groups.length == 0" class="py-8 text-center text-medium-emphasis">Nothing matches.</p>
            </div>
            <div v-if="hidden.length && view == 'all'" class="px-4 pb-4">
                <v-btn variant="text" size="small" :prepend-icon="showHidden ? 'fa-solid fa-chevron-up' : 'fa-solid fa-chevron-down'" @click="showHidden = !showHidden">
                    {{ hidden.length }} hidden (not kitchen gear)
                </v-btn>
                <div v-if="showHidden" class="eq-list">
                    <div v-for="h in hidden" :key="h.id" class="eq-row">
                        <equipment-row-content :e="h" :busy="false" />
                        <v-btn variant="text" size="small" @click="patch(h, {hidden: false})">Show</v-btn>
                    </div>
                </div>
            </div>
        </v-card>

        <v-dialog v-model="addOpen" max-width="440">
            <v-card title="Add equipment">
                <v-card-text>
                    <v-text-field v-model="newName" label="Name" placeholder="Pasta machine, 9-inch tart pan…" autofocus hide-details @keydown.enter="add" />
                    <v-checkbox v-model="newOwned" label="I have this" hide-details density="compact" class="mt-2" />
                </v-card-text>
                <v-card-actions><v-spacer /><v-btn @click="addOpen = false">Cancel</v-btn><v-btn color="primary" variant="flat" :disabled="!newName.trim()" @click="add">Add</v-btn></v-card-actions>
            </v-card>
        </v-dialog>

        <v-dialog v-model="kindOpen" max-width="440">
            <v-card :title="`Kind of equipment`" :subtitle="editing?.name">
                <v-card-text>
                    <p class="text-body-2 text-medium-emphasis mb-3">A recipe that asks for the kind (a stand mixer) is happy with anything of that kind you own.</p>
                    <v-autocomplete v-model="kindPick" :items="kinds" item-title="name" item-value="id" label="Kind" clearable hide-details />
                </v-card-text>
                <v-card-actions><v-spacer /><v-btn @click="kindOpen = false">Cancel</v-btn><v-btn color="primary" variant="flat" @click="saveKind">Save</v-btn></v-card-actions>
            </v-card>
        </v-dialog>

        <v-dialog v-model="renameOpen" max-width="440">
            <v-card title="Rename">
                <v-card-text><v-text-field v-model="renameText" label="Name" autofocus hide-details @keydown.enter="saveRename" /></v-card-text>
                <v-card-actions><v-spacer /><v-btn @click="renameOpen = false">Cancel</v-btn><v-btn color="primary" variant="flat" :disabled="!renameText.trim()" @click="saveRename">Save</v-btn></v-card-actions>
            </v-card>
        </v-dialog>
    </v-container>
</template>

<script setup lang="ts">
import {computed, onMounted, reactive, ref, watch} from 'vue'
import EquipmentRowContent from '@/components/display/EquipmentRowContent.vue'
import {Equipment, equipmentApi, equipmentVersion} from '@/composables/useEquipment'

const items = ref<Equipment[] | null>(null)
const loading = ref(false)
const error = ref('')
const view = ref<'needed' | 'have' | 'all'>('all')
const search = ref('')
const showHidden = ref(false)
const busy = reactive(new Set<number>())

async function load() {
    loading.value = true
    error.value = ''
    try {
        items.value = (await equipmentApi('')).equipment
    } catch (e: any) {
        error.value = 'Couldn’t load equipment.'
    } finally {
        loading.value = false
    }
}

const visible = computed(() => (items.value ?? []).filter(e => !e.hidden))
const hidden = computed(() => (items.value ?? []).filter(e => e.hidden))
const needed = computed(() => visible.value.filter(e => !e.have && (e.recipes ?? 0) > 0))
const haveCount = computed(() => visible.value.filter(e => e.owned).length)
const kinds = computed(() => visible.value.filter(e => !e.general).map(e => ({id: e.id, name: e.name})))

function matches(e: Equipment) {
    const q = (search.value || '').trim().toLowerCase()
    if (q && !e.name.toLowerCase().includes(q) && !(e.general?.name.toLowerCase().includes(q))) return false
    if (view.value == 'needed') return !e.have && (e.recipes ?? 0) > 0
    if (view.value == 'have') return e.owned
    return true
}

// kinds with the products under them; a kind shows when it or one of its products matches
const groups = computed(() => {
    const children = new Map<number, Equipment[]>()
    visible.value.forEach(e => { if (e.general) children.set(e.general.id, [...(children.get(e.general.id) ?? []), e]) })
    return visible.value.filter(e => !e.general).map(top => {
        const kids = children.get(top.id) ?? []
        const shownKids = matches(top) && view.value == 'all' ? kids : kids.filter(matches)
        return {top, children: shownKids, show: matches(top) || shownKids.length > 0}
    }).filter(g => g.show && (view.value != 'needed' || matches(g.top) || g.children.length))
        // what you have first, except in "Recipes need", which is a plain A–Z to-do list
        .sort((a, b) => (view.value == 'needed' ? 0 : Number(b.top.have) - Number(a.top.have)) || a.top.name.localeCompare(b.top.name))
})

async function patch(e: Equipment, body: any) {
    busy.add(e.id)
    try {
        await equipmentApi(`${e.id}/`, 'PATCH', body)
        await load()
    } catch (err: any) {
        error.value = err.message
    } finally {
        busy.delete(e.id)
    }
}

const setOwned = (e: Equipment, v: boolean) => patch(e, {owned: v})

async function remove(e: Equipment) {
    const what = e.recipes ? ` It’s listed in ${e.recipes} ${e.recipes == 1 ? 'recipe' : 'recipes'}.` : ''
    if (!confirm(`Remove ${e.name}?${what}`)) return
    try {
        await equipmentApi(`${e.id}/`, 'DELETE')
        await load()
    } catch (err: any) {
        error.value = err.message
    }
}

const addOpen = ref(false)
const newName = ref('')
const newOwned = ref(true)

async function add() {
    if (!newName.value.trim()) return
    try {
        const e = await equipmentApi('', 'POST', {name: newName.value})
        if (newOwned.value && !e.owned) await equipmentApi(`${e.id}/`, 'PATCH', {owned: true})
        addOpen.value = false
        newName.value = ''
        await load()
    } catch (err: any) {
        error.value = err.message
    }
}

const editing = ref<Equipment | null>(null)
const kindOpen = ref(false)
const kindPick = ref<number | null>(null)

function openKind(e: Equipment) {
    editing.value = e
    kindPick.value = e.general?.id ?? null
    kindOpen.value = true
}

async function saveKind() {
    if (editing.value) await patch(editing.value, {general: kindPick.value})
    kindOpen.value = false
}

const renameOpen = ref(false)
const renameText = ref('')

function openRename(e: Equipment) {
    editing.value = e
    renameText.value = e.name
    renameOpen.value = true
}

async function saveRename() {
    if (editing.value && renameText.value.trim()) await patch(editing.value, {name: renameText.value.trim()})
    renameOpen.value = false
}

watch(equipmentVersion, () => { if (!loading.value) load() })
onMounted(async () => {
    await load()
    if (needed.value.length) view.value = 'needed'
})
</script>

<style scoped>
.eq-header { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 24px; margin: 16px 0 28px; }
.count { margin-left: 6px; font-size: .75rem; opacity: .65; }
.eq-search { max-width: 320px; min-width: 200px; }
.eq-list { padding: 4px 0; }
.eq-row { display: flex; align-items: center; gap: 8px; padding: 4px 8px 4px 16px; min-height: 52px; border-top: 1px solid rgba(var(--v-border-color), var(--v-border-opacity)); }
.eq-list .eq-row:first-child { border-top: 0; }
.eq-row.is-child { padding-left: 48px; border-top-style: dashed; }
@media (max-width: 600px) {
    .eq-header { margin-top: 8px; gap: 16px; }
    .eq-header h1 { font-size: 1.75rem !important; }
    .eq-row.is-child { padding-left: 32px; }
}
</style>
