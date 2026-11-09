<template>
    <v-dialog :fullscreen="mobile" v-model="showDialog" max-width="500px">
        <v-card>
            <v-closable-card-title :title="shoppingListFood.food.name" v-model="showDialog"></v-closable-card-title>

            <v-card-text class="pt-0 pr-4 pl-4">
                <!-- home fork: "I have it" and the store product usually bought (cookbook/views/home_restock.py) -->
                <div class="d-flex flex-wrap ga-2 mb-4">
                    <v-btn color="primary" variant="flat" prepend-icon="fa-solid fa-box-open" :loading="having" @click="haveIt">I have it</v-btn>
                    <v-btn v-if="storeLink" variant="outlined" prepend-icon="fa-solid fa-store" :href="storeLink.url" target="_blank" rel="noopener">Open at {{ storeLink.store || 'the store' }}</v-btn>
                </div>
                <p v-if="storeLink" class="text-caption text-medium-emphasis mt-n2 mb-4">Usually: {{ storeLink.name }}</p>

                <div class="home-form mb-4">
                    <v-model-select model="SupermarketCategory" @update:modelValue="category => useShoppingStore().updateCategories([shoppingListFood], category)" create hide-details></v-model-select>
                    <v-model-select model="ShoppingList" @update:modelValue="shoppingListUpdate" multiple chips create hide-details></v-model-select>
                </div>

                <!-- home: secondary actions as one quiet row instead of four coloured tiles -->
                <div class="d-flex flex-wrap ga-2 mb-5">
                    <v-btn variant="outlined" size="small" prepend-icon="fa-solid fa-clock-rotate-left"
                           @click="useShoppingStore().delayEntries(entriesList, !isShoppingLineDelayed, true); showDialog=false">
                        <span v-if="!isShoppingLineDelayed">{{ $t('ShopLater') }}</span>
                        <span v-else>{{ $t('ShopNow') }}</span>
                    </v-btn>
                    <v-btn variant="outlined" size="small" prepend-icon="fa-solid fa-eye-slash"
                           @click="useShoppingStore().setFoodIgnoredState(entriesList,true, true);  showDialog = false">
                        {{ $t('Ignore_Shopping') }}
                    </v-btn>
                    <v-btn variant="outlined" size="small" prepend-icon="$edit"
                           :to="{name: 'ModelEditPage', params: {model: 'Food', id: shoppingListFood?.food.id!}}" target="_blank">
                        {{ $t('Edit') }}
                    </v-btn>
                    <v-btn variant="text" size="small" color="delete" prepend-icon="$delete" @click="deleteAllEntries()">
                        {{ $t('Delete_All') }}
                    </v-btn>
                </div>

                <div class="d-flex align-center mb-1">
                    <span class="text-body-2 font-weight-medium flex-grow-1">{{ $t('Entries') }}</span>
                    <v-btn variant="outlined" size="small" prepend-icon="$create" @click="addEntryForFood()">{{ $t('Add') }}</v-btn>
                </div>
                <v-list density="compact">
                    <template v-for="[i, e] in shoppingListFood.entries" :key="e.id">
                        <v-list-item border rounded="lg" class="mt-2 py-2">
                            <v-list-item-title>
                                <b>
                                    <span v-if="e.amount != 0">{{ $n(e.amount) }}&nbsp;</span>
                                    <span v-if="e.unit">{{ e.unit.name }}&nbsp;</span>
                                </b>
                                <span v-if="e.food">
                                    {{ e.food.name }}
                                </span>
                            </v-list-item-title>
                            <v-list-item-subtitle v-if="e.completedAt">
                                <v-icon icon="fa-solid fa-check" size="small" color="success"></v-icon>
                                {{ $t('Completed') }} {{ DateTime.fromJSDate(e.completedAt).toLocaleString(DateTime.DATETIME_SHORT) }}
                            </v-list-item-subtitle>
                            <v-list-item-subtitle v-if="e.listRecipe && e.listRecipeData.recipe">
                                {{ e.listRecipeData.servings }} x {{ e.listRecipeData.recipeData.name }}
                            </v-list-item-subtitle>
                            <v-list-item-subtitle v-if="e.listRecipe && e.listRecipeData.mealplan">
                                {{ e.listRecipeData.mealPlanData.mealType.name }} {{ DateTime.fromJSDate(e.listRecipeData.mealPlanData.fromDate).toLocaleString(DateTime.DATE_SHORT) }}
                            </v-list-item-subtitle>
                            <v-list-item-subtitle>
                                {{ e.createdBy.displayName }} - {{ DateTime.fromJSDate(e.createdAt).toLocaleString(DateTime.DATETIME_SHORT) }}
                            </v-list-item-subtitle>
                            <v-list-item-subtitle v-if="isDelayed(e)" class="text-info font-weight-bold">
                                {{ $t('PostponedUntil') }} {{ DateTime.fromJSDate(e.delayUntil!).toLocaleString(DateTime.DATETIME_SHORT) }}
                            </v-list-item-subtitle>
                            <v-list-item-subtitle v-if="e.shoppingLists.length > 0" class="text-info font-weight-bold">
                                <shopping-lists-bar :shopping-lists="e.shoppingLists"></shopping-lists-bar>
                            </v-list-item-subtitle>

                            <v-btn-group divided border density="compact" class="entry-actions mt-2">
                                <v-btn icon="" @click="e.amount = e.amount / 2; updateEntryAmount(e)" v-if="!e.ingredient">
                                    <v-icon icon="fa-solid fa-divide"></v-icon>
                                </v-btn>
                                <v-btn icon="" @click="e.amount--; updateEntryAmount(e)" v-if="!e.ingredient">
                                    <v-icon icon="fa-solid fa-minus"></v-icon>
                                </v-btn>
                                <v-btn icon="" @click="e.amount++; updateEntryAmount(e)" v-if="!e.ingredient">
                                    <v-icon icon="fa-solid fa-plus"></v-icon>
                                </v-btn>

                                <v-btn icon="" @click="e.amount = e.amount * 2; updateEntryAmount(e)" v-if="!e.ingredient">
                                    <v-icon icon="fa-solid fa-times"></v-icon>
                                </v-btn>
                                <v-btn icon="" v-if="!e.ingredient" :aria-label="$t('Edit')">
                                    <v-icon icon="$edit"></v-icon>
                                    <model-edit-dialog model="ShoppingListEntry" :item="e"
                                                       @delete="useShoppingStore().entries.delete(e.id!); shoppingListFood.entries.delete(e.id!)"
                                                       @save="(args: ShoppingListEntry) => { useShoppingStore().entries.set(e.id!, args); shoppingListFood.entries.set(e.id!, args) }"></model-edit-dialog>
                                </v-btn>
                                <v-btn icon="" v-if="e.listRecipe && e.listRecipeData.recipe && e.ingredient"
                                       :to="{name: 'RecipeViewPage', params: {id: e.listRecipeData.recipe}}">
                                    <v-icon icon="$recipes"></v-icon>
                                </v-btn>
                                <v-btn icon="" @click="useShoppingStore().deleteObject(e, true); shoppingListFood.entries.delete(e.id!)" class="text-delete" :aria-label="$t('Delete')">
                                    <v-icon icon="$delete"></v-icon>
                                </v-btn>
                            </v-btn-group>
                        </v-list-item>
                    </template>


                </v-list>


            </v-card-text>
            <v-card-actions v-if="mobile">
                <v-btn variant="text" @click="showDialog = false">{{ $t('Close') }}</v-btn>
            </v-card-actions>
        </v-card>
    </v-dialog>
</template>

<script setup lang="ts">

import {computed, ref} from "vue";
import {ApiApi, PatchedShoppingListEntry, ShoppingList, ShoppingListEntry, SupermarketCategory} from "@/openapi";
import ModelSelect from "@/components/inputs/ModelSelect.vue";
import {IShoppingListFood} from "@/types/Shopping";
import VClosableCardTitle from "@/components/dialogs/VClosableCardTitle.vue";
import {DateTime} from "luxon";
import {useDisplay} from "vuetify";
import ModelEditDialog from "@/components/dialogs/ModelEditDialog.vue";
import {useShoppingStore} from "@/stores/ShoppingStore";
import {isDelayed, isShoppingListFoodDelayed} from "@/utils/logic_utils";
import {ErrorMessageType, PreparedMessage, useMessageStore} from "@/stores/MessageStore";
import ShoppingListsBar from "@/components/display/ShoppingListsBar.vue";
import {useUserPreferenceStore} from "@/stores/UserPreferenceStore.ts";
import VModelSelect from "@/components/inputs/VModelSelect.vue";
import {MessageType} from "@/stores/MessageStore";
import {haveFood, loadStoreLinks, storeLinks} from "@/composables/useHomeShop";

const {mobile} = useDisplay()

const showDialog = defineModel<Boolean>()
const shoppingListFood = defineModel<IShoppingListFood>('shoppingListFood', {required: true})

const shoppingListUpdateLoading = ref(false)

/**
 * returns a flat list of entries for the given shopping list food
 */
const storeLink = computed(() => storeLinks.value[shoppingListFood.value.food.id!])
const having = ref(false)
async function haveIt() {
    having.value = true
    try {
        const msg = await haveFood(shoppingListFood.value.food.id!)
        useMessageStore().addMessage(MessageType.SUCCESS, msg, 4000)
        showDialog.value = false
        await useShoppingStore().refreshFromAPI()
        loadStoreLinks()
    } catch (e: any) {
        useMessageStore().addMessage(MessageType.ERROR, e?.message || 'Couldn’t add it to the pantry.', 5000)
    } finally {
        having.value = false
    }
}

const entriesList = computed(() => {
    let list = [] as ShoppingListEntry[]
    shoppingListFood.value.entries.forEach(e => {
        list.push(e)
    })
    return list
})

/**
 * checks all entries associated with shopping line, if any is delayed return true else false
 */
const isShoppingLineDelayed = computed(() => {
    return isShoppingListFoodDelayed(shoppingListFood.value)
})

/**
 * change the shopping list for all entries
 * @param shoppingLists
 */
function shoppingListUpdate(shoppingLists: ShoppingList[]) {
    const api = new ApiApi()
    const promises: Promise<any>[] = []
    shoppingListUpdateLoading.value = true

    shoppingListFood.value.entries.forEach(e => {
        e.shoppingLists = shoppingLists
        promises.push(api.apiShoppingListEntryUpdate({id: e.id, shoppingListEntry: e}).then(r => {

        }).catch(err => {
            useMessageStore().addError(ErrorMessageType.UPDATE_ERROR, err)
        }))
    })
    if (useUserPreferenceStore().userSettings.shoppingUpdateFoodLists){
        shoppingListFood.value.food.shoppingLists = shoppingLists
        promises.push(api.apiFoodUpdate({id: shoppingListFood.value.food.id!, food: shoppingListFood.value.food}).then(r => {

        }).catch(err => {
            useMessageStore().addError(ErrorMessageType.UPDATE_ERROR, err)
        }))
    }

    Promise.all(promises).finally(() => shoppingListUpdateLoading.value = false)
}

/**
 * add new entry for currently selected food type
 */
function addEntryForFood() {
    useShoppingStore().createObject({
        food: shoppingListFood.value?.food,
        unit: null,
        amount: 1,
    } as ShoppingListEntry, false).then((r: ShoppingListEntry | undefined) => {
        if (r != undefined) {
            shoppingListFood.value?.entries.set(r.id!, r)
        }
    })
}

/**
 * delete all shopping list entries for the given shopping list food
 */
function deleteAllEntries() {
    showDialog.value = false
    shoppingListFood.value.entries.forEach(e => {
        useShoppingStore().deleteObject(e, true)
    })
}

/**
 * update the amount for the given shopping list entry in the database
 * @param entry
 */
function updateEntryAmount(entry: ShoppingListEntry) {
    let api = new ApiApi()
    api.apiShoppingListEntryPartialUpdate({id: entry.id!, patchedShoppingListEntry: {amount: entry.amount} as PatchedShoppingListEntry}).then(r => {

    }).catch(err => {
        useMessageStore().addError(ErrorMessageType.UPDATE_ERROR, err)
    })
}

</script>

<style scoped>
.entry-actions {
    height: 32px !important;
}

.entry-actions .v-btn {
    width: 40px;
}

.entry-actions .v-btn :deep(.v-icon) {
    font-size: 13px;
}



</style>