<template>
    <!-- home fork: put the next week's planned recipes on the shopping list (POST /api/home/shop-plan/) -->
    <v-btn variant="flat" color="primary" size="small" prepend-icon="$shopping" :loading="loading" @click="shop">
        Shop for the week
        <v-dialog v-model="open" max-width="460">
            <v-card>
                <v-card-title class="pt-5 px-6 text-wrap">{{ title }}</v-card-title>
                <v-card-text class="px-6">
                    <p v-if="error" class="text-error">{{ error }}</p>
                    <template v-else-if="result">
                        <p v-if="result.added.length">Added {{ result.added.join(', ') }}.</p>
                        <p v-if="result.already.length" class="text-medium-emphasis mt-2">Already on the list: {{ result.already.join(', ') }}.</p>
                        <p v-if="!result.added.length && !result.already.length" class="text-medium-emphasis">Nothing with a recipe is planned for {{ rangeText }}. Plan a few meals first.</p>
                        <p v-if="result.skipped.length" class="text-medium-emphasis mt-2">Left off because you have them: {{ result.skipped.join(', ') }}.</p>
                    </template>
                </v-card-text>
                <v-card-actions class="px-6 pb-4">
                    <v-spacer />
                    <v-btn variant="text" @click="open = false">Close</v-btn>
                    <v-btn v-if="result?.items" color="primary" variant="flat" :to="{name: 'ShoppingListPage'}">Open shopping list</v-btn>
                </v-card-actions>
            </v-card>
        </v-dialog>
    </v-btn>
</template>

<script setup lang="ts">
import {computed, ref} from 'vue'
import {DateTime} from 'luxon'
import {useDjangoUrls} from '@/composables/useDjangoUrls'
import {getCookie} from '@/utils/cookie'

const open = ref(false)
const loading = ref(false)
const error = ref('')
const result = ref<{ added: string[], already: string[], items: number, skipped: string[] } | null>(null)

const start = () => DateTime.now().startOf('day')
const rangeText = computed(() => `${start().toLocaleString({weekday: 'short', month: 'short', day: 'numeric'})} – ${start().plus({days: 6}).toLocaleString({weekday: 'short', month: 'short', day: 'numeric'})}`)
const title = computed(() => error.value ? 'Couldn’t update the shopping list' : result.value?.added.length ? `${result.value.items} items on your list` : 'Shop for the week')

async function shop() {
    loading.value = true
    error.value = ''
    result.value = null
    try {
        const r = await fetch(useDjangoUrls().getDjangoUrl('api/home/shop-plan/'), {
            method: 'POST', credentials: 'same-origin',
            headers: {'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') ?? ''},
            body: JSON.stringify({from: start().toISODate(), to: start().plus({days: 6}).toISODate()}),
        })
        const d = await r.json().catch(() => ({}))
        if (!r.ok) throw new Error(d.error || `Error ${r.status}`)
        result.value = d
    } catch (e: any) {
        error.value = e.message
    } finally {
        loading.value = false
        open.value = true
    }
}
</script>
