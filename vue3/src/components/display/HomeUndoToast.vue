<template>
    <!-- home fork: "Moved Coq au Vin to Thu, Oct 15 · Undo" (composables/useMealPlanMove.ts) -->
    <v-snackbar :model-value="!!undoToast" @update:model-value="v => !v && (undoToast = null)" :timeout="6000" location="bottom">
        {{ undoToast?.text }}
        <template #actions>
            <v-btn variant="text" color="primary" :loading="busy" @click="undo">Undo</v-btn>
        </template>
    </v-snackbar>
</template>

<script setup lang="ts">
import {ref} from 'vue'
import {undoToast} from '@/composables/useMealPlanMove'

const busy = ref(false)
async function undo() {
    if (!undoToast.value) return
    busy.value = true
    try { await undoToast.value.undo() } finally { busy.value = false; undoToast.value = null }
}
</script>
