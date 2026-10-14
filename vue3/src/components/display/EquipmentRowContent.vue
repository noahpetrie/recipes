<template>
    <!-- home fork: one line of the Equipment page -->
    <v-checkbox-btn v-if="!e.homebox" :model-value="e.owned" :disabled="busy" :aria-label="`I have ${e.name}`" class="flex-grow-0"
                    @update:model-value="(v: any) => emit('owned', !!v)" />
    <v-tooltip v-else text="In your Homebox kitchen" location="top">
        <template #activator="{props}"><span v-bind="props" class="hb-check"><v-icon icon="fa-solid fa-house-circle-check" size="small" color="success" /></span></template>
    </v-tooltip>
    <span v-if="e.image || child" class="eq-photo" aria-hidden="true">
        <img v-if="e.image" :src="e.image" alt="" loading="lazy">
        <v-icon v-else icon="fa-solid fa-blender" size="small" class="text-medium-emphasis" />
    </span>
    <div class="flex-grow-1 min-w-0">
        <div class="eq-name" :class="{'font-weight-medium': !child}">{{ e.name }}</div>
        <div class="text-caption text-medium-emphasis eq-meta">
            <span v-if="e.owned">You have this</span>
            <span v-else-if="e.via" class="text-success">Covered by your {{ e.via }}</span>
            <span v-else-if="e.recipes">You don’t have this</span>
            <span v-if="e.basic && e.owned"> · basic kit</span>
            <span v-if="e.homebox"> · from Homebox</span>
        </div>
    </div>
    <span v-if="e.recipes" class="text-caption text-medium-emphasis text-no-wrap">{{ e.recipes }} {{ e.recipes == 1 ? 'recipe' : 'recipes' }}</span>
</template>

<script setup lang="ts">
import {Equipment} from '@/composables/useEquipment'

defineProps<{ e: Equipment, busy: boolean, child?: boolean }>()
const emit = defineEmits<{ owned: [value: boolean] }>()
</script>

<style scoped>
.eq-name { line-height: 1.3; overflow: hidden; text-overflow: ellipsis; }
.eq-meta { line-height: 1.3; }
.hb-check { width: 40px; display: inline-flex; justify-content: center; flex: none; }
.min-w-0 { min-width: 0; }
.eq-photo { width: 36px; height: 40px; flex: none; display: inline-flex; align-items: center; justify-content: center; border-radius: 8px; background: rgb(var(--v-theme-surface)); overflow: hidden; }
.eq-photo img { width: 100%; height: 100%; object-fit: contain; padding: 2px; }
</style>
