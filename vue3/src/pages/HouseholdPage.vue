<template>
    <v-container>
        <v-card class="page-header" :prepend-icon="THousehold.icon" :title="$t('Households')"></v-card>
        <v-card class="mb-16">
            <v-card-text class="text-body-2">
                <p>{{ $t('HouseholdSetup1') }}</p>
                <p class="mt-2">{{ $t('HouseholdSetup2') }}</p>
                <p class="mt-2">{{ $t('HouseholdSetup3') }}</p>
                <p class="mt-2">{{ $t('HouseholdSetup4') }}</p>

                <!-- home: once you're in a household, say so instead of showing a disabled form -->
                <v-alert v-if="useUserPreferenceStore().activeUserSpace?.household != null" type="success" variant="tonal" class="mt-5" icon="fa-solid fa-check">
                    You’re in the household <b>{{ useUserPreferenceStore().activeUserSpace?.household?.name }}</b>.
                </v-alert>
                <div v-else class="d-flex flex-wrap ga-2 align-start mt-5">
                    <v-text-field v-model="householdName" :label="$t('Household')" hide-details class="household-name"></v-text-field>
                    <v-btn color="primary" variant="flat" height="40" @click="createAndJoinHousehold" :loading="loading">
                        {{ $t('CreateAndJoin') }}
                    </v-btn>
                </div>

                <v-row>
                    <database-model-col model="UserSpace" :disabled="useUserPreferenceStore().activeUserSpace?.household == null || loading"></database-model-col>
                </v-row>

            </v-card-text>
            <v-card-actions>
                <v-btn variant="text" @click=" skipHouseholdSetup()" :loading="loading">{{ $t('Skip') }}</v-btn>
            </v-card-actions>
        </v-card>


    </v-container>
</template>

<script setup lang="ts">


import {ApiApi} from "@/openapi";
import {onMounted, ref} from "vue";
import {ErrorMessageType, PreparedMessage, useMessageStore} from "@/stores/MessageStore.ts";
import {useUserPreferenceStore} from "@/stores/UserPreferenceStore.ts";
import {THousehold} from "@/types/Models.ts";
import {useRouter} from "vue-router";
import DatabaseModelCol from "@/components/display/DatabaseModelCol.vue";

const router = useRouter()

const loading = ref(false)
const householdName = ref("")


onMounted(() => {

})

function createAndJoinHousehold() {
    let api = new ApiApi()
    let userSpace = useUserPreferenceStore().activeUserSpace

    loading.value = true
    if (userSpace != null) {
        api.apiHouseholdCreate({household: {name: householdName.value}}).then(r => {
            userSpace.household = r

            api.apiUserSpaceUpdate({id: userSpace.id!, userSpace: userSpace}).then(r => {
                useUserPreferenceStore().activeSpace.householdSetupCompleted = true
                useMessageStore().addPreparedMessage(PreparedMessage.CREATE_SUCCESS)


                api.apiSpacePartialUpdate({id: useUserPreferenceStore().activeSpace.id!, patchedSpace: useUserPreferenceStore().activeSpace}).then(r => {
                    useUserPreferenceStore().activeSpace = r
                }).catch(err => {
                    useMessageStore().addError(ErrorMessageType.UPDATE_ERROR, err)
                }).finally(() => {
                    loading.value = false
                })

            }).catch(err => {
                useMessageStore().addError(ErrorMessageType.CREATE_ERROR, err)
                loading.value = false
            })

        }).catch(err => {
            useMessageStore().addError(ErrorMessageType.CREATE_ERROR, err)
            loading.value = false
        })
    }
}

function skipHouseholdSetup() {
    let api = new ApiApi()

    useUserPreferenceStore().activeSpace.householdSetupCompleted = true
    loading.value = true

    api.apiSpacePartialUpdate({id: useUserPreferenceStore().activeSpace.id!, patchedSpace: useUserPreferenceStore().activeSpace}).then(r => {
        useUserPreferenceStore().activeSpace = r
    }).catch(err => {
        useMessageStore().addError(ErrorMessageType.UPDATE_ERROR, err)
    }).finally(() => {
        loading.value = false
        router.push({name: 'StartPage'})
    })
}


</script>

<style scoped>
.household-name { flex: 1 1 240px; max-width: 420px; }



</style>