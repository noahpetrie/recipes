<template>
    <v-container>
        <v-row dense>
            <v-col>
                <v-card prepend-icon="$books" :title="$t('Books')" class="page-header">
                    <template #append>
                        <v-text-field v-if="books.length > 6 && !xs" v-model="filter" :placeholder="$t('Search')" prepend-inner-icon="$search" clearable hide-details
                                      density="compact" class="books-search me-3"></v-text-field>
                        <v-btn color="create" prepend-icon="$create" append-icon="fa-solid fa-caret-down">
                            {{ $t('Create') }}
                            <v-menu activator="parent">
                                <v-list density="compact">
                                    <v-list-item prepend-icon="$books" link>
                                        {{ $t('HomeCookbook', 'Cookbook') }}
                                        <v-list-item-subtitle>{{ $t('HomeCookbookHelp', 'A printed cookbook on your shelf') }}</v-list-item-subtitle>
                                        <model-edit-dialog model="RecipeBook" :item-defaults="{kind: 'cookbook'}" @create="(arg: RecipeBook) => {books.push(arg); loadContents(arg)}"></model-edit-dialog>
                                    </v-list-item>
                                    <v-list-item prepend-icon="fa-solid fa-layer-group" link>
                                        {{ $t('HomeCollection', 'Collection') }}
                                        <v-list-item-subtitle>{{ $t('HomeCollectionHelp', 'A group of your own recipes') }}</v-list-item-subtitle>
                                        <model-edit-dialog model="RecipeBook" :item-defaults="{kind: 'collection'}" @create="(arg: RecipeBook) => {books.push(arg); loadContents(arg)}"></model-edit-dialog>
                                    </v-list-item>
                                </v-list>
                            </v-menu>
                        </v-btn>
                    </template>
                </v-card>
            </v-col>
        </v-row>

        <v-row dense v-if="books.length > 6 && xs">
            <v-col cols="12">
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
                        <model-edit-dialog model="RecipeBook" @create="(arg: RecipeBook) => {books.push(arg); loadContents(arg)}"></model-edit-dialog>
                    </v-btn>
                </div>
            </v-col>
        </v-row>

        <!-- home: printed cookbooks as covers on a shelf -->
        <template v-if="cookbooks.length">
            <div class="books-section-title mt-2 mb-3">
                <v-icon icon="$books" size="small"></v-icon> {{ $t('HomeCookbooks', 'Cookbooks') }}
                <span class="text-medium-emphasis">{{ cookbooks.length }}</span>
            </div>
            <div class="cookbook-shelf mb-8">
                <router-link v-for="b in cookbooks" :key="b.id" :to="{name: 'BookViewPage', params: {bookId: b.id}}" class="cookbook">
                    <div class="cookbook-cover">
                        <img v-if="b.cover" :src="b.cover" alt="" loading="lazy">
                        <div v-else class="cookbook-blank"><span>{{ b.name }}</span></div>
                        <v-btn icon="$menu" variant="flat" size="x-small" class="cookbook-menu" @click.prevent.stop>
                            <v-icon icon="$menu"></v-icon>
                            <v-menu activator="parent">
                                <v-list density="compact">
                                    <v-list-item prepend-icon="$edit" link>
                                        {{ $t('Edit') }}
                                        <model-edit-dialog model="RecipeBook" :item="b" @closed="refreshBook(b)"
                                                           @delete="(arg: RecipeBook) => { books.splice(books.findIndex((value: RecipeBook) => value.id == arg.id!),1)}"></model-edit-dialog>
                                    </v-list-item>
                                </v-list>
                            </v-menu>
                        </v-btn>
                    </div>
                    <div class="cookbook-title two-lines" :title="b.name">{{ b.name }}</div>
                    <div v-if="b.author" class="cookbook-meta text-truncate" :title="b.author">{{ b.author }}</div>
                    <div v-if="contents[b.id!]?.total" class="cookbook-meta">{{ recipeCount(b) }}</div>
                </router-link>
            </div>
        </template>

        <!-- home: collections of your own recipes, as albums with a collage of their photos -->
        <template v-if="collections.length">
            <div v-if="cookbooks.length" class="books-section-title mb-3">
                <v-icon icon="fa-solid fa-layer-group" size="small"></v-icon> {{ $t('HomeCollections', 'Collections') }}
                <span class="text-medium-emphasis">{{ collections.length }}</span>
            </div>
            <div class="cookbook-shelf mb-8">
                <router-link v-for="b in collections" :key="b.id" :to="{name: 'BookViewPage', params: {bookId: b.id}}" class="cookbook">
                    <div class="cookbook-cover album-cover" :class="`album-${Math.min(collage(b).length, 4)}`">
                        <template v-if="collage(b).length">
                            <div v-for="r in collage(b)" :key="r.id" class="album-cell">
                                <img v-if="r.image" :src="r.image" alt="" loading="lazy">
                                <v-icon v-else icon="fa-solid fa-pizza-slice" class="opacity-50"></v-icon>
                            </div>
                        </template>
                        <div v-else-if="contents[b.id!]" class="album-empty">
                            <v-icon icon="fa-solid fa-layer-group" size="large" class="opacity-40 mb-2"></v-icon>
                            <v-btn size="small" variant="tonal" color="primary" prepend-icon="$create" @click.prevent.stop>
                                {{ $t('HomeAddRecipes', 'Add recipes') }}
                                <model-edit-dialog model="RecipeBook" :item="b" @closed="refreshBook(b)"
                                                   @delete="(arg: RecipeBook) => { books.splice(books.findIndex((value: RecipeBook) => value.id == arg.id!),1)}"></model-edit-dialog>
                            </v-btn>
                        </div>
                        <v-btn icon="$menu" variant="flat" size="x-small" class="cookbook-menu" @click.prevent.stop>
                            <v-icon icon="$menu"></v-icon>
                            <v-menu activator="parent">
                                <v-list density="compact">
                                    <v-list-item prepend-icon="$edit" link>
                                        {{ $t('Edit') }}
                                        <model-edit-dialog model="RecipeBook" :item="b" @closed="refreshBook(b)"
                                                           @delete="(arg: RecipeBook) => { books.splice(books.findIndex((value: RecipeBook) => value.id == arg.id!),1)}"></model-edit-dialog>
                                    </v-list-item>
                                </v-list>
                            </v-menu>
                        </v-btn>
                    </div>
                    <div class="cookbook-title" :title="b.name">{{ b.name }}</div>
                    <div class="cookbook-meta">
                        <template v-if="contents[b.id!]?.total">{{ recipeCount(b) }}</template>
                        <template v-if="b.filter"><template v-if="contents[b.id!]?.total"> · </template>{{ $t('HomeSavedSearch', 'Saved search') }}</template>
                    </div>
                    <div v-if="b.description" class="cookbook-meta books-description">{{ b.description }}</div>
                </router-link>
            </div>
        </template>
    </v-container>
</template>

<script setup lang="ts">


import {computed, onMounted, ref} from "vue";
import {ApiApi, RecipeBook, RecipeBookEntry, RecipeOverview} from "@/openapi";
import {ErrorMessageType, useMessageStore} from "@/stores/MessageStore";
import ModelEditDialog from "@/components/dialogs/ModelEditDialog.vue";
import {useDisplay} from "vuetify";
import {useI18n} from "vue-i18n";

const {t} = useI18n()

const {xs} = useDisplay()

const loading = ref(false)

const viewingBook = ref<null | RecipeBook>(null)
const viewingBookEntries = ref([] as RecipeBookEntry[])

const books = ref([] as RecipeBook[])
const filter = ref('')
const filteredBooks = computed(() => {
    const f = (filter.value ?? '').trim().toLowerCase()
    return f ? books.value.filter(b => [b.name, b.description, b.author].some(v => (v ?? '').toLowerCase().includes(f))) : books.value
})
const recipeCount = (b: RecipeBook) => {
    const n = contents.value[b.id!]?.total ?? 0
    return `${n} ${(n == 1 ? t('Recipe') : t('Recipes')).toLowerCase()}`
}
// up to four photos for a collection's collage, preferring recipes that have one
const collage = (b: RecipeBook) => {
    const r = contents.value[b.id!]?.recipes ?? []
    return [...r.filter(x => x.image), ...r.filter(x => !x.image)].slice(0, 4)
}
const cookbooks = computed(() => filteredBooks.value.filter(b => b.kind == 'cookbook'))
const collections = computed(() => filteredBooks.value.filter(b => b.kind != 'cookbook'))

/**
 * home: after editing, pick up a new cover/author/kind as well as the recipe count
 */
function refreshBook(b: RecipeBook) {
    new ApiApi().apiRecipeBookRetrieve({id: b.id!}).then(fresh => {
        const i = books.value.findIndex(x => x.id == fresh.id)
        if (i >= 0) books.value[i] = fresh
        loadContents(fresh)
    }).catch(() => {})
}

onMounted(() => {
    loadBooks()
})

// recipes in each book (manual entries plus a saved search, if any), for the count and thumbnails
const THUMBS = 12  // enough for the counts and collages
const contents = ref({} as Record<number, { total: number, recipes: RecipeOverview[] }>)

async function loadContents(b: RecipeBook) {
    const api = new ApiApi()
    try {
        const entries = await api.apiRecipeBookEntryList({book: b.id!, pageSize: THUMBS})
        const recipes = entries.results.map(e => e.recipeContent)
        let total = entries.count
        if (b.filter) {
            const found = await api.apiRecipeList({filter: b.filter.id!, pageSize: THUMBS})
            const seen = new Set(recipes.map(r => r.id))
            recipes.push(...found.results.filter(r => !seen.has(r.id)))
            total += found.count
        }
        contents.value[b.id!] = {total, recipes}
    } catch (err) {
        contents.value[b.id!] = {total: 0, recipes: []}
    }
}

function loadBooks() {
    const api = new ApiApi()
    loading.value = true
    api.apiRecipeBookList().then(r => {
        books.value = r.results
        books.value.forEach(b => loadContents(b))
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
.books-section-title {
    display: flex;
    align-items: center;
    gap: 8px;
    font-weight: 600;
    font-size: 0.95rem;
}

.cookbook-shelf {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
    gap: 24px 20px;
}

@media (max-width: 600px) {
    .cookbook-shelf {
        grid-template-columns: repeat(2, 1fr);
        gap: 20px 16px;
    }
}

.cookbook {
    color: inherit;
    text-decoration: none;
    min-width: 0;
}

.cookbook-cover {
    position: relative;
    aspect-ratio: 3 / 4;
    border-radius: 4px 8px 8px 4px;
    overflow: hidden;
    background: rgba(var(--v-theme-on-surface), 0.06);
    box-shadow: 0 1px 2px rgba(0, 0, 0, .12), 0 6px 16px rgba(0, 0, 0, .10), inset 3px 0 0 rgba(0, 0, 0, .08);
    transition: transform .15s ease, box-shadow .15s ease;
}

.cookbook:hover .cookbook-cover {
    transform: translateY(-3px);
    box-shadow: 0 2px 4px rgba(0, 0, 0, .14), 0 12px 24px rgba(0, 0, 0, .14), inset 3px 0 0 rgba(0, 0, 0, .08);
}

.cookbook-cover img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
}

.books-search {
    width: 240px;
}

/* collection collage: 1 photo fills; 2 stack; 3 = one wide on top + two; 4 = 2x2 */
.album-cover {
    display: grid;
    gap: 2px;
    border-radius: 8px;
    box-shadow: 0 1px 2px rgba(0, 0, 0, .10), 0 4px 12px rgba(0, 0, 0, .08);
}

.album-1 { grid-template: 1fr / 1fr; }
.album-2 { grid-template: 1fr 1fr / 1fr; }
.album-3 { grid-template: 3fr 2fr / 1fr 1fr; }
.album-3 .album-cell:first-child { grid-column: 1 / 3; }
.album-4 { grid-template: 1fr 1fr / 1fr 1fr; }

.album-cell {
    min-height: 0;
    overflow: hidden;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(var(--v-theme-on-surface), 0.06);
}

.album-cell img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
}

.album-empty {
    height: 100%;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    border: 1.5px dashed rgba(var(--v-theme-on-surface), 0.18);
    border-radius: 8px;
}

.album-cover:has(.album-empty) {
    box-shadow: none;
    background: transparent;
}

.cookbook-blank {
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 12px;
    text-align: center;
    font-weight: 600;
    background: rgb(var(--v-theme-primary));
    color: rgb(var(--v-theme-on-primary));
}

.cookbook-menu {
    position: absolute;
    top: 6px;
    right: 6px;
    opacity: 0;
    transition: opacity .15s;
}

.cookbook:hover .cookbook-menu, .cookbook-menu[aria-expanded="true"] {
    opacity: 1;
}

@media (hover: none) {
    .cookbook-menu {
        opacity: .9;
    }
}

.cookbook-title {
    margin-top: 10px;
    font-weight: 600;
    line-height: 1.3;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
}

/* cookbooks always take two lines for the title, so the authors underneath line up */
.cookbook-title.two-lines {
    min-height: 2.6em;
}

.cookbook-meta {
    font-size: 0.8125rem;
    color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}

.books-description {
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
}
</style>
