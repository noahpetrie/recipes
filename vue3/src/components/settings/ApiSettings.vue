<template>
    <v-form>
        <p class="text-h6">{{ $t('API') }}</p>
        <v-divider class="mb-3"></v-divider>

        <v-row>
            <database-link-col prepend-icon="fa-solid fa-terminal" :href="useDjangoUrls().getDjangoUrl('api')" :lg="6" :title="$t('API_Browser')"></database-link-col>
            <database-link-col prepend-icon="fa-solid fa-laptop-code" :href="useDjangoUrls().getDjangoUrl('/docs/api/')" :lg="6"
                               :title="$t('API_Documentation')"></database-link-col>
        </v-row>

        <v-alert color="error" variant="tonal" class="mt-4" icon="fa-solid fa-triangle-exclamation">
            The API is made for developers to interact with the application.
            It is possible to break things using the API, so be careful and create a backup first.
            The API definition can and will change; read the changelog to spot changes early.
        </v-alert>

        <div class="text-body-2 mt-5 api-help">
            <p>Authenticate by sending the word <code>Bearer</code> followed by an API token in the <code>Authorization</code> header:</p>
            <pre class="api-code">curl -X GET https://your.domain.com/api/recipe/ \
  -H 'Authorization: Bearer TOKEN'</pre>
            <p>You can have several tokens, each with its own scope: <code>read</code>, <code>write</code> or <code>bookmarklet</code>.
                The bookmarklet scope only lets the bookmarklet in.</p>
        </div>

        <v-alert color="warning" variant="tonal" class="mt-4">Save your token when you create it; it can’t be viewed again afterwards.</v-alert>

        <div class="d-flex align-center mt-6 mb-2">
            <span class="text-subtitle-1 font-weight-bold flex-grow-1">Tokens</span>
            <v-btn prepend-icon="$create" variant="outlined" size="small">{{ $t('New') }}
                <model-edit-dialog model="AccessToken" @create="loadAccessTokens()" :close-after-create="false"></model-edit-dialog>
            </v-btn>
        </div>

        <v-list class="api-tokens" border rounded="lg" density="compact" v-if="accessTokenList.length">
            <v-list-item v-for="at in accessTokenList" :key="at.id">
                <v-list-item-title class="api-token">{{ maskToken(at.token) }}</v-list-item-title>
                <v-list-item-subtitle>
                    Scope {{ at.scope }} · Expires {{ DateTime.fromJSDate(at.expires).toLocaleString(DateTime.DATE_MED) }}
                </v-list-item-subtitle>
                <template #append>
                    <v-chip color="error" size="small" variant="tonal" class="me-2" v-if="at.expires < DateTime.now().toJSDate()">Expired</v-chip>
                    <v-btn icon variant="text" size="small" :aria-label="$t('Edit')">
                        <v-icon icon="$edit" size="small"></v-icon>
                        <model-edit-dialog model="AccessToken" :item="at" @delete="loadAccessTokens()"></model-edit-dialog>
                    </v-btn>
                </template>
            </v-list-item>
        </v-list>


    </v-form>
</template>


<script setup lang="ts">

import {onMounted, ref} from "vue";
import {AccessToken, ApiApi} from "@/openapi";
import {ErrorMessageType, useMessageStore} from "@/stores/MessageStore";
import {DateTime} from "luxon";

// home: don't show full tokens on screen; the start and end are enough to tell them apart
function maskToken(token?: string) {
    if (!token) return ''
    return token.length > 12 ? `${token.slice(0, 6)}••••••••${token.slice(-4)}` : token
}
import ModelEditDialog from "@/components/dialogs/ModelEditDialog.vue";
import DatabaseLinkCol from "@/components/display/DatabaseLinkCol.vue";
import {useDjangoUrls} from "@/composables/useDjangoUrls.ts";

const accessTokenList = ref([] as AccessToken[])

onMounted(() => {
    loadAccessTokens()
})

function loadAccessTokens() {
    const api = new ApiApi()
    api.apiAccessTokenList().then(r => {
        accessTokenList.value = r
    }).catch(err => {
        useMessageStore().addError(ErrorMessageType.FETCH_ERROR, err)
    })
}

</script>

<style scoped>
.api-help p { margin-bottom: 8px; max-width: 72ch; }
.api-code { font-size: 0.8125rem; background: rgba(var(--v-theme-on-surface), 0.05); border-radius: 8px; padding: 10px 12px; overflow-x: auto; margin: 4px 0 12px; white-space: pre; }
.api-token { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 0.8125rem; }


</style>