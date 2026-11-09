<template>
    <v-container>
        <!-- home: phones get a section picker instead of the full 12-item list above every settings page -->
        <div v-if="smAndDown" class="settings-picker mb-4">
            <v-menu>
                <template #activator="{props}">
                    <v-btn v-bind="props" variant="outlined" block class="settings-picker__btn" :prepend-icon="current?.icon ?? '$settings'" append-icon="fa-solid fa-chevron-down">
                        <span class="text-medium-emphasis me-1">{{ $t('Settings') }} ·</span> {{ current ? current.title : '' }}
                    </v-btn>
                </template>
                <v-list class="home-subnav" density="compact">
                    <template v-for="g in groups" :key="g.title">
                        <v-list-subheader v-if="g.title">{{ g.title }}</v-list-subheader>
                        <v-list-item v-for="i in g.items" :key="i.title" v-bind="i.link" :prepend-icon="i.icon">{{ i.title }}</v-list-item>
                        <template v-if="g.plugins">
                            <template v-for="p in TANDOOR_PLUGINS" :key="p.name">
                                <component :is="p.settingsComponent" v-if="p.settingsComponent"></component>
                            </template>
                        </template>
                    </template>
                </v-list>
            </v-menu>
        </div>

        <v-row>
            <v-col cols="12" md="3" offset-lg="0" offset-xl="1" xl="2" v-if="!smAndDown">
                <v-list class="bg-transparent home-subnav">
                    <template v-for="(g, gi) in groups" :key="g.title">
                        <v-divider v-if="gi > 0" class="my-1"></v-divider>
                        <v-list-subheader v-if="g.title">{{ g.title }}</v-list-subheader>
                        <v-list-item v-for="i in g.items" :key="i.title" v-bind="i.link" :prepend-icon="i.icon">{{ i.title }}</v-list-item>
                        <template v-if="g.plugins">
                            <template v-for="p in TANDOOR_PLUGINS" :key="p.name">
                                <component :is="p.settingsComponent" v-if="p.settingsComponent"></component>
                            </template>
                        </template>
                    </template>
                </v-list>
            </v-col>
            <v-col cols="12" md="9" lg="8" xl="7">
                <router-view/>
            </v-col>
        </v-row>
    </v-container>
</template>

<script setup lang="ts">

import {useDjangoUrls} from "@/composables/useDjangoUrls";
import {TANDOOR_PLUGINS} from "@/types/Plugins.ts";
import {computed} from "vue";
import {useDisplay} from "vuetify";
import {useRoute} from "vue-router";
import {useI18n} from "vue-i18n";

const {getDjangoUrl} = useDjangoUrls()
const {smAndDown} = useDisplay()
const route = useRoute()
const {t} = useI18n()

type NavItem = { title: string, icon: string, name?: string, link: Record<string, any> }
function item(title: string, icon: string, name: string): NavItem {
    return {title, icon, name, link: {to: {name}}}
}

const groups = computed(() => [
    {title: '', items: [item(t('Profile'), 'fa-solid fa-user', 'ProfileSettings'), item(t('Account'), 'fa-solid fa-lock', 'AccountSettings')]},
    {title: t('Settings'), items: [
        item(t('Cosmetic'), 'fa-solid fa-palette', 'CosmeticSettings'),
        item(t('Shopping_list'), '$shopping', 'ShoppingSettings'),
        item(t('Meal_Plan'), '$mealplan', 'MealPlanSettings'),
        item(t('Search'), '$search', 'SearchSettings'),
    ]},
    {title: 'Space', plugins: true, items: [
        item(t('SpaceSettings'), '$settings', 'SpaceSettings'),
        item(t('Open_Data_Import'), 'fa-solid fa-cloud-arrow-down', 'OpenDataImportSettings'),
        item(t('Export'), 'fa-solid fa-file-export', 'ExportDataSettings'),
    ]},
    {title: 'Admin', items: [
        item(t('API'), 'fa-solid fa-code', 'ApiSettings'),
        {title: t('System'), icon: 'fa-solid fa-server', link: {href: getDjangoUrl('system'), target: '_blank'}} as NavItem,
    ]},
])

const current = computed(() => groups.value.flatMap(g => g.items).find(i => i.name && route.matched.some(r => r.name == i.name)))

</script>


<style scoped>
.settings-picker__btn {
    justify-content: flex-start;
    height: 44px !important;
}

.settings-picker__btn :deep(.v-btn__content) {
    flex: 1 1 auto;
    justify-content: flex-start;
}
</style>