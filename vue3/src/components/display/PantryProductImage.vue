<template>
    <div class="product-photo" :class="{small}" aria-hidden="true">
        <img v-if="src && !failed" :src="src" alt="" loading="lazy" decoding="async" @error="failed = true">
        <v-icon v-else icon="$pantry" color="primary" />
    </div>
</template>
<script setup lang="ts">
import {ref, watch} from 'vue'
const props = defineProps<{src?: string | null, small?: boolean}>()
const failed = ref(false)
watch(() => props.src, () => { failed.value = false })
</script>
<style scoped>
.product-photo { width: 64px; height: 76px; flex: 0 0 64px; display: flex; align-items: center; justify-content: center; border-radius: 10px; background: rgb(var(--v-theme-surface)); overflow: hidden; }
.product-photo img { width: 100%; height: 100%; object-fit: contain; padding: 4px; }
.product-photo.small { width: 36px; height: 40px; flex-basis: 36px; border-radius: 8px; }
.product-photo.small img { padding: 2px; }
</style>
