<template>
    <model-editor-base
        :loading="loading"
        :dialog="dialog"
        @save="saveObject"
        @delete="deleteObject"
        @close="emit('close'); editingObjChanged = false"
        :is-update="isUpdate()"
        :is-changed="editingObjChanged"
        :model-class="modelClass"
        :object-name="editingObjName()"
        :editing-object="editingObj">

        <v-card-text class="pa-0">
            <v-tabs v-model="tab" :disabled="loading" grow>
                <v-tab value="book">{{ $t('Book') }}</v-tab>
                <v-tab value="recipes" :disabled="!isUpdate()">{{ $t('Recipes') }}</v-tab>
            </v-tabs>
        </v-card-text>

        <v-card-text>
            <v-tabs-window v-model="tab">

                <v-tabs-window-item value="book">

                    <v-form :disabled="loading">
                        <!-- home fork: printed cookbook or a collection of your own recipes -->
                        <v-btn-toggle v-model="editingObj.kind" mandatory color="primary" variant="outlined" density="comfortable" class="mb-4">
                            <v-btn value="collection" prepend-icon="fa-solid fa-layer-group">{{ $t('HomeCollection', 'Collection') }}</v-btn>
                            <v-btn value="cookbook" prepend-icon="$books">{{ $t('HomeCookbook', 'Cookbook') }}</v-btn>
                        </v-btn-toggle>
                        <v-text-field :label="$t('Name')" v-model="editingObj.name"></v-text-field>
                        <v-text-field v-if="editingObj.kind == 'cookbook'" :label="$t('HomeAuthor', 'Author')" v-model="editingObj.author"></v-text-field>
                        <div v-if="isUpdate() && editingObj.kind == 'cookbook'" class="d-flex align-center ga-3 mb-5">
                            <div class="book-cover-preview">
                                <img v-if="editingObj.cover" :src="editingObj.cover" alt="">
                                <v-icon v-else icon="$books" class="opacity-50"></v-icon>
                            </div>
                            <v-file-input :label="$t('HomeCover', 'Cover')" accept="image/*" prepend-icon="" prepend-inner-icon="fa-solid fa-image" hide-details
                                          :loading="fileApiLoading" @update:model-value="uploadCover"></v-file-input>
                            <v-btn v-if="editingObj.cover" variant="text" color="delete" @click="uploadCover(null)">{{ $t('Remove', 'Remove') }}</v-btn>
                        </div>
                        <v-textarea :label="$t('Description')" v-model="editingObj.description" rows="3"></v-textarea>
                        <v-model-select model="User" v-model="editingObj.shared" chips multiple></v-model-select>
                        <v-model-select model="CustomFilter" v-model="editingObj.filter"></v-model-select>
                        <v-number-input :label="$t('Order')" :hint="$t('OrderInformation')" v-model="editingObj.order"></v-number-input>
                    </v-form>
                </v-tabs-window-item>

                <v-tabs-window-item value="recipes">
                    <v-model-select model="Recipe" v-model="selectedRecipes" multiple chips>
                        <template #append>
                            <v-btn icon color="create" @click="addRecipesToBook()">
                                <v-icon icon="$create"></v-icon>
                            </v-btn>
                        </template>
                    </v-model-select>
                    <v-data-table-server
                        @update:options="loadRecipeBookEntries"
                        :items="recipeBookEntries"
                        :headers="tableHeaders"
                        :items-length="itemCount"
                    >
                        <template #item.action="{item}">
                            <v-btn icon="$delete" color="delete" @click="removeRecipeFromBook(item)"></v-btn>
                        </template>

                    </v-data-table-server>
                </v-tabs-window-item>
            </v-tabs-window>
        </v-card-text>
    </model-editor-base>
</template>

<script setup lang="ts">
import {useFileApi} from "@/composables/useFileApi";

import {onMounted, PropType, ref, watch} from "vue";
import {ApiApi, Recipe, RecipeBook, RecipeBookEntry, User} from "@/openapi";
import {VDataTableUpdateOptions} from "@/vuetify";

import {useModelEditorFunctions} from "@/composables/useModelEditorFunctions";
import ModelEditorBase from "@/components/model_editors/ModelEditorBase.vue";
import ModelSelect from "@/components/inputs/ModelSelect.vue";
import {ErrorMessageType, MessageType, PreparedMessage, useMessageStore} from "@/stores/MessageStore";
import {useUserPreferenceStore} from "@/stores/UserPreferenceStore";
import {useI18n} from "vue-i18n";
import VModelSelect from "@/components/inputs/VModelSelect.vue";

const props = defineProps({
    item: {type: {} as PropType<RecipeBook>, required: false, default: null},
    itemId: {type: [Number, String], required: false, default: undefined},
    itemDefaults: {type: {} as PropType<RecipeBook>, required: false, default: {} as RecipeBook},
    dialog: {type: Boolean, default: false}
})

const emit = defineEmits(['create', 'save', 'delete', 'close', 'changedState'])
const {setupState, deleteObject, saveObject, isUpdate, editingObjName, loading, editingObj, editingObjChanged, modelClass} = useModelEditorFunctions<RecipeBook>('RecipeBook', emit)

/**
 * watch prop changes and re-initialize editor
 * required to embed editor directly into pages and be able to change item from the outside
 */
watch([() => props.item, () => props.itemId], () => {
    initializeEditor()
})

const {t} = useI18n()
const tab = ref("book")
const recipeBookEntries = ref([] as RecipeBookEntry[])

const selectedRecipes = ref([] as Recipe[])

const tablePage = ref(1)
const itemCount = ref(0)

const tableHeaders = [
    {title: t('Name'), key: 'recipeContent.name',},
    {key: 'action', width: '1%', noBreak: true, align: 'end'},
]

onMounted(() => {
    initializeEditor()
})

/**
 * component specific state setup logic
 */
function initializeEditor() {
    setupState(props.item, props.itemId, {
        newItemFunction: () => {
            editingObj.value.shared = [] as User[]
            editingObj.value.kind = editingObj.value.kind ?? 'collection'
            recipeBookEntries.value = []
        },
        existingItemFunction: () => {
            recipeBookEntries.value = []
        },
        itemDefaults: props.itemDefaults
    })
}

/**
 * home fork: upload (or with null, remove) the cover straight away; it isn't part of the normal save
 */
const {fileApiLoading, updateBookCover} = useFileApi()

function uploadCover(file: File | File[] | null) {
    const f = Array.isArray(file) ? file[0] : file
    if (file != null && !f) return
    updateBookCover(editingObj.value.id!, f ?? null).then(b => {
        (editingObj.value as any).cover = b.cover
    }).catch(err => {
        useMessageStore().addError(ErrorMessageType.UPDATE_ERROR, err)
    })
}

/**
 * add selected recipes into the book and client list
 */
function addRecipesToBook() {
    let api = new ApiApi()

    if (selectedRecipes.value.length > 0) {
        selectedRecipes.value.forEach(selectedRecipe => {
            let duplicateFound = false

            recipeBookEntries.value.forEach(rBE => {
                if (rBE.recipe == selectedRecipe.id) {
                    duplicateFound = true
                }
            })

            if (!duplicateFound) {
                api.apiRecipeBookEntryCreate({recipeBookEntry: {book: editingObj.value.id!, recipe: selectedRecipe.id!}}).then(r => {
                    recipeBookEntries.value.push(r)
                }).catch(err => {
                    useMessageStore().addError(ErrorMessageType.CREATE_ERROR, err)
                })
            } else {
                useMessageStore().addMessage(MessageType.WARNING, t('WarningRecipeBookEntryDuplicate'), 5000)
            }
        })
        selectedRecipes.value = []
    }
}

/**
 * remove the given entry from the book both in the database and on the frontend
 * @param recipeBookEntry
 */
function removeRecipeFromBook(recipeBookEntry: RecipeBookEntry) {
    let api = new ApiApi()

    api.apiRecipeBookEntryDestroy({id: recipeBookEntry.id!}).then((r) => {
        recipeBookEntries.value.splice(recipeBookEntries.value.findIndex(rBE => rBE.id! == recipeBookEntry.id!), 1)
        useMessageStore().addPreparedMessage(PreparedMessage.DELETE_SUCCESS)
    }).catch(err => {
        useMessageStore().addError(ErrorMessageType.DELETE_ERROR, err)
    })
}


/**
 * load items from API whenever the table calls for it
 * parameters defined by vuetify
 * @param options
 */
function loadRecipeBookEntries(options: VDataTableUpdateOptions) {
    let api = new ApiApi()

    loading.value = true
    window.scrollTo({top: 0, behavior: 'smooth'})

    if (tablePage.value != options.page) {
        tablePage.value = options.page
    }

    useUserPreferenceStore().deviceSettings.general_tableItemsPerPage = options.itemsPerPage

    api.apiRecipeBookEntryList({page: options.page, pageSize: options.itemsPerPage, book: editingObj.value.id}).then((r: any) => {
        recipeBookEntries.value = r.results
        itemCount.value = r.count
    }).catch((err: any) => {
        useMessageStore().addError(ErrorMessageType.FETCH_ERROR, err)
    }).finally(() => {
        loading.value = false
    })
}

</script>

<style scoped>
.book-cover-preview {
    width: 48px;
    height: 64px;
    border-radius: 4px;
    overflow: hidden;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(var(--v-theme-on-surface), 0.06);
}

.book-cover-preview img {
    width: 100%;
    height: 100%;
    object-fit: cover;
}
</style>