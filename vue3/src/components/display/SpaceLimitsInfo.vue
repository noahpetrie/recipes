<template>
    <!-- home: compact usage tiles; a bar only where there is a limit (0 means unlimited) -->
    <div class="space-stats" v-if="props.space.name != undefined">
        <router-link class="space-stat" :to="{name: 'SearchPage'}">
            <span class="space-stat__icon"><i class="fa-solid fa-book"></i></span>
            <span class="space-stat__label">{{ $t('Recipes') }}</span>
            <span class="space-stat__value">{{ $n(props.space.recipeCount) }}<span v-if="props.space.maxRecipes > 0" class="space-stat__max"> / {{ $n(props.space.maxRecipes) }}</span></span>
            <v-progress-linear v-if="props.space.maxRecipes > 0" :color="isSpaceAboveRecipeLimit(props.space) ? 'error' : 'primary'" height="4" rounded
                               :model-value="(props.space.recipeCount / props.space.maxRecipes) * 100"></v-progress-linear>
        </router-link>
        <router-link class="space-stat" :to="{name: 'ModelListPage', params: {model: 'UserSpace'}}">
            <span class="space-stat__icon"><i class="fa-solid fa-users"></i></span>
            <span class="space-stat__label">{{ $t('Users') }}</span>
            <span class="space-stat__value">{{ $n(props.space.userCount) }}<span v-if="props.space.maxUsers > 0" class="space-stat__max"> / {{ $n(props.space.maxUsers) }}</span></span>
            <v-progress-linear v-if="props.space.maxUsers > 0" :color="isSpaceAboveUserLimit(props.space) ? 'error' : 'primary'" height="4" rounded
                               :model-value="(props.space.userCount / props.space.maxUsers) * 100"></v-progress-linear>
        </router-link>
        <router-link class="space-stat" :to="{name: 'ModelListPage', params: {model: 'UserFile'}}">
            <span class="space-stat__icon"><i class="fa-solid fa-file"></i></span>
            <span class="space-stat__label">{{ $t('Files') }}</span>
            <span class="space-stat__value" v-if="props.space.maxFileStorageMb > -1">{{ $n(Math.round(props.space.fileSizeMb)) }} MB<span v-if="props.space.maxFileStorageMb > 0" class="space-stat__max"> / {{ $n(props.space.maxFileStorageMb) }} MB</span></span>
            <span class="space-stat__value text-body-2" v-else>{{ $t('file_upload_disabled') }}</span>
            <v-progress-linear v-if="props.space.maxFileStorageMb > 0" :color="isSpaceAboveStorageLimit(props.space) ? 'error' : 'primary'" height="4" rounded
                               :model-value="(props.space.fileSizeMb / props.space.maxFileStorageMb) * 100"></v-progress-linear>
        </router-link>

        <!-- AI credits only matter on the hosted service or when a monthly allowance is set -->
        <template v-if="useUserPreferenceStore().serverSettings.hosted || (props.space.aiMonthlyCreditsUsed ?? 0) > 0 || (props.space.aiCreditsBalance ?? 0) > 0">
            <router-link class="space-stat" :to="{name: 'ModelListPage', params: {model: 'AiLog'}}">
                <span class="space-stat__icon"><i class="fa-solid fa-hand-holding-dollar"></i></span>
                <span class="space-stat__label">{{ $t('MonthlyCredits') }}</span>
                <span class="space-stat__value">{{ $n(props.space.aiMonthlyCreditsUsed) }}<span class="space-stat__max"> / {{ $n(props.space.aiCreditsMonthly) }}</span></span>
                <v-progress-linear :model-value="props.space.aiMonthlyCreditsUsed" :max="props.space.aiCreditsMonthly || 1" height="4" rounded color="primary"></v-progress-linear>
            </router-link>
            <router-link class="space-stat" :to="{name: 'ModelListPage', params: {model: 'AiLog'}}">
                <span class="space-stat__icon"><i class="fa-solid fa-coins"></i></span>
                <span class="space-stat__label">{{ $t('AiCreditsBalance') }}</span>
                <span class="space-stat__value">{{ $n(props.space.aiCreditsBalance) }}</span>
            </router-link>
        </template>
    </div>
</template>


<script setup lang="ts">

import {PropType} from "vue";
import {Space} from "@/openapi";
import {isSpaceAboveRecipeLimit, isSpaceAboveStorageLimit, isSpaceAboveUserLimit} from "@/utils/logic_utils.ts";
import {useUserPreferenceStore} from "@/stores/UserPreferenceStore.ts";

const props = defineProps({
    space: {type: {} as PropType<Space>, required: true},
})

</script>

<style scoped>
.space-stats {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(170px, 1fr));
    gap: 12px;
}

.space-stat {
    display: grid;
    grid-template-columns: auto 1fr;
    grid-template-areas: "icon label" "value value" "bar bar";
    align-items: center;
    column-gap: 10px;
    row-gap: 6px;
    padding: 14px 16px;
    border-radius: 10px;
    border: 1px solid var(--home-hairline);
    background: rgb(var(--v-theme-surface));
    color: inherit;
    text-decoration: none;
}

.space-stat:hover {
    border-color: var(--home-border);
}

.space-stat__icon {
    grid-area: icon;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 28px;
    height: 28px;
    border-radius: 8px;
    background: rgba(var(--v-theme-primary), 0.10);
    color: rgb(var(--v-theme-primary));
    font-size: 13px;
}

.space-stat__label {
    grid-area: label;
    font-size: 0.8125rem;
    color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}

.space-stat__value {
    grid-area: value;
    font-size: 1.25rem;
    font-weight: 600;
    letter-spacing: -0.01em;
}

.space-stat__max {
    font-size: 0.875rem;
    font-weight: 400;
    color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}

.space-stat :deep(.v-progress-linear) {
    grid-area: bar;
}
</style>