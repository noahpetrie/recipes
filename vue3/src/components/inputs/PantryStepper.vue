<template>
    <!-- home fork: the big − [ 1 package ] + amount control used by the pantry scan panel -->
    <div class="pst">
        <v-btn icon="fa-solid fa-minus" variant="outlined" class="pst-btn" :disabled="!(num > min)" :aria-label="$t('HomeLess', 'Less')"
               @click="emit('update:modelValue', Math.max(min, num - 1))"></v-btn>
        <label class="pst-box">
            <input :value="modelValue" type="number" :min="min" :max="max ?? undefined" step="any" inputmode="decimal" :aria-label="label"
                   @input="onInput" @keydown.enter.prevent="emit('enter')">
            <span v-if="unit" class="pst-unit">{{ unit }}</span>
        </label>
        <v-btn icon="fa-solid fa-plus" variant="outlined" class="pst-btn" :disabled="max != null && num >= max" :aria-label="$t('HomeMore', 'More')"
               @click="emit('update:modelValue', max != null ? Math.min(max, num + 1) : num + 1)"></v-btn>
    </div>
</template>

<script setup lang="ts">
import {computed} from "vue";

const props = withDefaults(defineProps<{ modelValue: any, unit?: string, label?: string, min?: number, max?: number | null }>(), {min: 0, max: null})
const emit = defineEmits<{ (e: 'update:modelValue', v: any): void, (e: 'enter'): void }>()

const num = computed(() => Number(props.modelValue) || 0)

function onInput(e: Event) {
    const v = (e.target as HTMLInputElement).value
    emit('update:modelValue', v === '' ? '' : Number(v))
}
</script>

<style scoped>
.pst {
    display: flex;
    align-items: center;
    gap: 12px;
}

.pst-btn {
    border-color: rgba(var(--v-theme-on-surface), 0.14) !important;
    flex-shrink: 0;
}

.pst-box {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 10px 8px 8px;
    border-radius: 12px;
    box-shadow: inset 0 0 0 1px rgba(var(--v-theme-on-surface), 0.14);
    cursor: text;
}

.pst-box:focus-within {
    box-shadow: inset 0 0 0 1px rgb(var(--v-theme-on-surface)), 0 0 0 3px rgba(var(--v-theme-on-surface), 0.08);
}

.pst-box input {
    width: 100%;
    text-align: center;
    font-size: 1.75rem;
    font-weight: 600;
    line-height: 1.2;
    font-variant-numeric: tabular-nums;
    outline: none;
    background: transparent;
    color: inherit;
    -moz-appearance: textfield;
}

.pst-box input::-webkit-outer-spin-button, .pst-box input::-webkit-inner-spin-button {
    -webkit-appearance: none;
}

.pst-unit {
    font-size: 0.8125rem;
    color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
</style>
