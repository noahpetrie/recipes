<template>
    <!-- home fork: a recipe picture anywhere in a list or card; an icon when there's no picture or it fails to load -->
    <div class="recipe-thumb" :class="[`rounded-${rounded}`]" :style="box">
        <img v-if="src && !failed" :src="src" alt="" loading="lazy" @error="failed = true">
        <v-icon v-else icon="$recipes" :size="iconSize" />
    </div>
</template>

<script setup lang="ts">
import {computed, ref, watch} from 'vue'

const props = defineProps({
    src: {type: String as () => string | null | undefined, default: undefined},
    // a number makes a square of that many px; otherwise it fills the width at this aspect ratio
    size: {type: Number, default: 0},
    aspect: {type: Number, default: 1.6},
    rounded: {type: String, default: 'lg'},
})

const failed = ref(false)
watch(() => props.src, () => failed.value = false)
const box = computed(() => props.size ? {width: `${props.size}px`, height: `${props.size}px`, flex: `0 0 ${props.size}px`} : {width: '100%', aspectRatio: String(props.aspect)})
const iconSize = computed(() => props.size ? Math.max(14, Math.round(props.size * .4)) : 32)
</script>

<style scoped>
.recipe-thumb { display: flex; align-items: center; justify-content: center; overflow: hidden; background: rgba(var(--v-theme-on-surface), .05); color: rgba(var(--v-theme-on-surface), .35); }
.recipe-thumb img { width: 100%; height: 100%; object-fit: cover; display: block; }
</style>
