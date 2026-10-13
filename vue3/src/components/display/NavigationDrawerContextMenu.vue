<template>

<!--    <template v-if="route.name == 'ModelListPage'">-->
<!--        <v-divider></v-divider>-->
<!--        <v-list-item v-for="m in getListModels()"-->
<!--                     :to="{ name: 'ModelListPage', params: {model: m.name.toLowerCase()} }">-->
<!--            <template #prepend>-->
<!--                <v-icon :icon="m.icon"></v-icon>-->
<!--            </template>-->
<!--            {{ $t(m.localizationKey) }}-->
<!--        </v-list-item>-->
<!--    </template>-->

    <!-- home fork: the meal plan's auto planner, calendar feed and view settings live in its toolbar (MealPlanCalendarHeader) -->


</template>

<script setup lang="ts">

import {useRoute} from "vue-router";
import {getListModels} from "@/types/Models";
import {useUserPreferenceStore} from "@/stores/UserPreferenceStore";

const route = useRoute()

</script>

<style scoped>

</style>