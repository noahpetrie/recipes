<template>
    <!-- home: compact account header — name, then space · household on one quiet line -->
    <v-list-item class="menu-user-info">
        <template #prepend>
            <v-avatar color="primary" size="32">{{ useUserPreferenceStore().userSettings.user.displayName.charAt(0) }}</v-avatar>
        </template>
        <v-list-item-title class="font-weight-medium">{{ useUserPreferenceStore().userSettings.user.displayName }}</v-list-item-title>
        <v-list-item-subtitle class="menu-user-info-sub">
            <span>{{ useUserPreferenceStore().activeSpace.name }}</span>
            <template v-if="useUserPreferenceStore().activeUserSpace != null && useUserPreferenceStore().activeUserSpace.household != null">
                · <router-link :to="{name: 'ModelListPage', params: {model: 'household'}}" class="text-medium-emphasis">{{ useUserPreferenceStore().activeUserSpace.household.name }}</router-link>
            </template>
            <template v-else>
                · <router-link :to="{name: 'ModelListPage', params: {model: 'UserSpace'}}" class="text-medium-emphasis">{{ $t('NoHousehold') }}</router-link>
            </template>
        </v-list-item-subtitle>
    </v-list-item>
</template>

<script setup lang="ts">

import {useUserPreferenceStore} from "@/stores/UserPreferenceStore.ts";
import {useRouter} from "vue-router";

let router = useRouter()
</script>

<style scoped>
.menu-user-info {
    min-height: 52px !important;
}

.menu-user-info-sub {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.menu-user-info-sub a {
    text-decoration: none;
}

.menu-user-info-sub a:hover {
    text-decoration: underline;
}
</style>