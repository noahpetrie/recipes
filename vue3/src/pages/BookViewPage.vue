<template>
    <v-container>
        <v-row>
            <v-col>
                <v-card>
                    <v-card-title>{{ book.name }}
                        <v-btn class="float-right" variant="flat" :to="{name: 'BooksPage'}" prepend-icon="$books" v-if="mdAndUp">{{ $t('Books') }}</v-btn>
                    </v-card-title>
                    <v-card-text v-if="book.shared && book.shared.length > 0">
                        <v-chip-group>
                            <v-label class="me-2">{{ $t('shared_with') }}</v-label>
                            <v-chip v-for="u in book.shared">{{ u.displayName }}</v-chip>
                        </v-chip-group>
                    </v-card-text>
                    <v-card-text class="text-disabled">
                        {{ book.description }}
                    </v-card-text>
                </v-card>
            </v-col>
        </v-row>

        <!-- home: a book opens as a grid of recipe cards; ingredients and steps stay on the recipe page -->
        <v-row>
            <v-col cols="6" md="4" lg="3" v-for="r in recipes" :key="r.id" class="pa-0 mb-4">
                <recipe-card :recipe="r" height="20vh"></recipe-card>
            </v-col>
        </v-row>
        <v-row v-if="!loading && !loadingEntries && recipes.length == 0">
            <v-col class="text-center text-disabled">{{ $t('No_Results') }}</v-col>
        </v-row>
    </v-container>
</template>

<script setup lang="ts">


import {onMounted, ref} from "vue";
import {ApiApi, RecipeBook, RecipeBookEntry, RecipeOverview} from "@/openapi";
import {ErrorMessageType, useMessageStore} from "@/stores/MessageStore";
import {useRouter} from "vue-router";
import {useDisplay} from "vuetify";
import RecipeCard from "@/components/display/RecipeCard.vue";

const props = defineProps({
    bookId: {type: String, required: true},
})

const {mdAndUp} = useDisplay()
const router = useRouter()

const loading = ref(false)
const loadingEntries = ref(false)

const manualItems = ref(0)
const filterItems = ref(0)

const book = ref({} as RecipeBook)
const entries = ref([] as RecipeBookEntry[])
const recipes = ref([] as RecipeOverview[])

onMounted(() => {
    loadBook()
})

/**
 * load the given book and trigger loading its entries
 */
function loadBook() {
    const api = new ApiApi()
    loading.value = true

    api.apiRecipeBookRetrieve({id: props.bookId}).then(r => {
        book.value = r

        entries.value = []
        recLoadEntries(1)
    }).catch(err => {
        useMessageStore().addError(ErrorMessageType.FETCH_ERROR, err)
    }).finally(() => {
        loading.value = false
    })
}

/**
 * recursively load the book entries and trigger loading all entries from a saved custom filter
 * @param page
 */
function recLoadEntries(page: number) {
    const api = new ApiApi()
    loadingEntries.value = true

    api.apiRecipeBookEntryList({book: props.bookId, page: page, pageSize: 50}).then(r => {
        r.results.forEach(rBE => {
            recipes.value.push(rBE.recipeContent)
        })
        manualItems.value = r.count
        if (r.next) {
            recLoadEntries(page + 1)
        } else {
            if (book.value.filter) {
                recLoadFilter(book.value.filter.id, 1)
            } else {
                loadingEntries.value = false
            }
        }
    }).catch(err => {
        useMessageStore().addError(ErrorMessageType.FETCH_ERROR, err)
        loadingEntries.value = false
    })
}

/**
 * recursively load the recipes matched by the custom filter configured in the book
 * @param filterId filter id to look for
 * @param page page to load
 */
function recLoadFilter(filterId: number, page: number) {
    let api = new ApiApi()

    api.apiRecipeList({filter: filterId, page: page, pageSize: 50}).then(r => {
        const existingIds = new Set(recipes.value.map(rec => rec.id))
        const newRecipes = r.results.filter(rec => !existingIds.has(rec.id))
        recipes.value = recipes.value.concat(newRecipes)
        filterItems.value = recipes.value.length - manualItems.value
        if (r.next) {
            recLoadFilter(filterId, page + 1)
        } else {
            loadingEntries.value = false
        }
    }).catch(err => {
        useMessageStore().addError(ErrorMessageType.FETCH_ERROR, err)
        loadingEntries.value = false
    })
}

</script>

<style scoped></style>
