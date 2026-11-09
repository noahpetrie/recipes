<template>
    <v-container>
        <!-- home: a book header with its cover, author and a way back on every screen size -->
        <v-btn variant="text" size="small" prepend-icon="fa-solid fa-arrow-left" :to="{name: 'BooksPage'}" class="mb-2 ms-n2">{{ $t('Books') }}</v-btn>
        <div class="book-header mb-6">
            <img v-if="(book as any).cover" :src="(book as any).cover" alt="" class="book-header__cover">
            <div class="book-header__text">
                <h1 class="book-header__title">{{ book.name }}</h1>
                <div class="home-muted text-body-2" v-if="book.author">{{ book.author }}</div>
                <p class="home-muted text-body-2 mt-2" v-if="book.description">{{ book.description }}</p>
                <div class="d-flex flex-wrap align-center ga-1 mt-2" v-if="book.shared && book.shared.length > 0">
                    <span class="text-body-2 home-muted me-1">{{ $t('shared_with') }}</span>
                    <v-chip v-for="u in book.shared" :key="u.id" size="small">{{ u.displayName }}</v-chip>
                </div>
                <div class="text-body-2 home-muted mt-2" v-if="!loading && !loadingEntries">{{ recipes.length }} {{ recipes.length == 1 ? 'recipe' : 'recipes' }}</div>
            </div>
        </div>

        <!-- home: a book opens as a grid of recipe cards; ingredients and steps stay on the recipe page -->
        <v-row>
            <v-col cols="6" md="4" lg="3" v-for="r in recipes" :key="r.id" class="pa-0 mb-4">
                <recipe-card :recipe="r" height="20vh"></recipe-card>
            </v-col>
        </v-row>
        <v-row v-if="!loading && !loadingEntries && recipes.length == 0">
            <v-col class="text-center home-muted">{{ $t('No_Results') }}</v-col>
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

<style scoped>
.book-header {
    display: flex;
    gap: 20px;
    align-items: flex-start;
}

.book-header__cover {
    width: 96px;
    aspect-ratio: 2 / 3;
    object-fit: cover;
    border-radius: 6px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.18);
    flex: 0 0 auto;
}

.book-header__title {
    font-family: var(--home-display-font);
    font-size: 1.75rem;
    font-weight: 700;
    letter-spacing: -0.02em;
    line-height: 1.2;
}

.book-header__text p {
    max-width: 72ch;
}

@media (max-width: 599.98px) {
    .book-header__cover {
        width: 72px;
    }

    .book-header__title {
        font-size: 1.375rem;
    }
}
</style>
