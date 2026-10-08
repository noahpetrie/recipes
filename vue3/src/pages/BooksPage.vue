<template>
    <v-container>
        <v-row dense>
            <v-col>
                <v-card prepend-icon="$books" :title="$t('Books')" class="page-header">
                    <template #append>
                        <v-btn color="create" prepend-icon="$create">
                            {{ $t('Create') }}
                            <model-edit-dialog model="RecipeBook" @create="(arg: RecipeBook) => {books.push(arg)}"></model-edit-dialog>
                        </v-btn>
                    </template>
                </v-card>
            </v-col>
        </v-row>

        <v-row dense v-if="books.length > 6">
            <v-col cols="12" md="6">
                <v-text-field v-model="filter" :placeholder="$t('Search')" prepend-inner-icon="$search" clearable hide-details density="comfortable"></v-text-field>
            </v-col>
        </v-row>

        <v-row v-if="loading && books.length == 0">
            <v-col cols="12" sm="6" lg="4" v-for="i in 3" :key="i">
                <v-skeleton-loader type="list-item-avatar-two-line" class="rounded-lg"></v-skeleton-loader>
            </v-col>
        </v-row>

        <!-- empty state -->
        <v-row v-if="!loading && books.length == 0">
            <v-col>
                <div class="books-empty text-center">
                    <div class="books-empty-icon mx-auto mb-4"><v-icon icon="$books" size="28"></v-icon></div>
                    <div class="text-h6 mb-1">{{ $t('HomeBooksEmpty', 'No recipe books yet') }}</div>
                    <p class="text-body-2 text-medium-emphasis mb-4">{{ $t('HomeBooksEmptyHelp', 'Group recipes into books, like a weeknight rotation or holiday baking.') }}</p>
                    <v-btn color="create" prepend-icon="$create">
                        {{ $t('Create') }}
                        <model-edit-dialog model="RecipeBook" @create="(arg: RecipeBook) => {books.push(arg)}"></model-edit-dialog>
                    </v-btn>
                </div>
            </v-col>
        </v-row>

        <v-row>
            <v-col cols="12" sm="6" lg="4" v-for="b in filteredBooks" :key="b.id">
                <v-card class="home-tile h-100" :to="{name: 'BookViewPage', params: {bookId: b.id}}">
                    <v-card-item>
                        <template #prepend>
                            <v-icon icon="$books"></v-icon>
                        </template>
                        <v-card-title>{{ b.name }}</v-card-title>
                        <v-card-subtitle>{{ b.createdBy.displayName }}</v-card-subtitle>
                        <template #append>
                            <v-btn icon="$menu" variant="text" size="small" @click.prevent.stop>
                                <v-icon icon="$menu"></v-icon>
                                <v-menu activator="parent">
                                    <v-list density="compact">
                                        <v-list-item prepend-icon="$edit" link>
                                            {{ $t('Edit') }}
                                            <model-edit-dialog model="RecipeBook" :item="b"
                                                               @delete="(arg: RecipeBook) => { books.splice(books.findIndex((value: RecipeBook) => value.id == arg.id!),1)}"></model-edit-dialog>
                                        </v-list-item>
                                    </v-list>
                                </v-menu>
                            </v-btn>
                        </template>
                    </v-card-item>
                    <v-card-text v-if="b.description" class="pt-0 text-medium-emphasis books-description">{{ b.description }}</v-card-text>
                </v-card>
            </v-col>
        </v-row>
    </v-container>
</template>

<script setup lang="ts">


import {computed, onMounted, ref} from "vue";
import {ApiApi, RecipeBook, RecipeBookEntry} from "@/openapi";
import {ErrorMessageType, useMessageStore} from "@/stores/MessageStore";
import ModelEditDialog from "@/components/dialogs/ModelEditDialog.vue";

const loading = ref(false)

const viewingBook = ref<null | RecipeBook>(null)
const viewingBookEntries = ref([] as RecipeBookEntry[])

const books = ref([] as RecipeBook[])
const filter = ref('')
const filteredBooks = computed(() => {
    const f = (filter.value ?? '').trim().toLowerCase()
    return f ? books.value.filter(b => b.name.toLowerCase().includes(f) || (b.description ?? '').toLowerCase().includes(f)) : books.value
})

onMounted(() => {
    loadBooks()
})

function loadBooks() {
    const api = new ApiApi()
    loading.value = true
    api.apiRecipeBookList().then(r => {
        books.value = r.results
    }).catch(err => {
        useMessageStore().addError(ErrorMessageType.FETCH_ERROR)
    }).finally(() => {
        loading.value = false
    })
}

function loadBookEntries(recipeBook : RecipeBook){
    const api = new ApiApi()
    loading.value = true
    api.apiRecipeBookEntryList({})
}

</script>

<style scoped>
.books-description {
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
}
</style>
