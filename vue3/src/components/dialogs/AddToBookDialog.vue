<template>
    <!-- home: tick the books a recipe belongs to; each tick adds or removes it straight away -->
    <v-dialog activator="parent" max-width="440px" v-model="dialog">
        <v-card :loading="loading">
            <v-closable-card-title :title="$t('HomeAddToBook', 'Add to book')" :sub-title="props.recipe.name" v-model="dialog"></v-closable-card-title>
            <v-list v-if="books.length" density="comfortable" class="pt-0">
                <v-list-item v-for="b in books" :key="b.id" @click="toggle(b)" :disabled="busy.has(b.id!)">
                    <template #prepend>
                        <v-checkbox-btn :model-value="!!entryFor(b)" color="primary" density="compact" class="me-2"></v-checkbox-btn>
                    </template>
                    <v-list-item-title>{{ b.name }}</v-list-item-title>
                    <v-list-item-subtitle v-if="b.description">{{ b.description }}</v-list-item-subtitle>
                </v-list-item>
            </v-list>
            <v-card-text v-else-if="!loading" class="text-medium-emphasis">
                {{ $t('HomeBooksEmpty', 'No recipe books yet') }}
            </v-card-text>
            <v-card-actions>
                <v-btn :to="{name: 'BooksPage'}" variant="text" prepend-icon="$books">{{ $t('Books') }}</v-btn>
                <v-spacer></v-spacer>
                <v-btn color="primary" variant="flat" @click="dialog = false">{{ $t('Done', 'Done') }}</v-btn>
            </v-card-actions>
        </v-card>
    </v-dialog>
</template>

<script setup lang="ts">
import {PropType, ref, watch} from "vue";
import VClosableCardTitle from "@/components/dialogs/VClosableCardTitle.vue";
import {ApiApi, Recipe, RecipeBook, RecipeBookEntry, RecipeFlat, RecipeOverview} from "@/openapi";
import {ErrorMessageType, useMessageStore} from "@/stores/MessageStore";

const props = defineProps({
    recipe: {type: Object as PropType<Recipe | RecipeFlat | RecipeOverview>, required: true},
})

const dialog = ref(false)
const loading = ref(false)
const books = ref([] as RecipeBook[])
const entries = ref([] as RecipeBookEntry[])
const busy = ref(new Set<number>())

const entryFor = (b: RecipeBook) => entries.value.find(e => e.book == b.id)

watch(dialog, open => {
    if (!open) return
    const api = new ApiApi()
    loading.value = true
    Promise.all([
        api.apiRecipeBookList({pageSize: 100}),
        api.apiRecipeBookEntryList({recipe: props.recipe.id!, pageSize: 100}),
    ]).then(([b, e]) => {
        books.value = b.results
        entries.value = e.results
    }).catch(err => {
        useMessageStore().addError(ErrorMessageType.FETCH_ERROR, err)
    }).finally(() => {
        loading.value = false
    })
})

function toggle(b: RecipeBook) {
    const api = new ApiApi()
    const existing = entryFor(b)
    busy.value.add(b.id!)
    const done = () => busy.value.delete(b.id!)
    if (existing) {
        api.apiRecipeBookEntryDestroy({id: existing.id!}).then(() => {
            entries.value = entries.value.filter(e => e.id != existing.id)
        }).catch(err => useMessageStore().addError(ErrorMessageType.DELETE_ERROR, err)).finally(done)
    } else {
        api.apiRecipeBookEntryCreate({recipeBookEntry: {book: b.id!, recipe: props.recipe.id!} as RecipeBookEntry}).then(r => {
            entries.value.push(r)
        }).catch(err => useMessageStore().addError(ErrorMessageType.CREATE_ERROR, err)).finally(done)
    }
}
</script>
