<template>
    <v-app>
        <v-app-bar color="surface" flat density="comfortable" v-if="!useUserPreferenceStore().isAuthenticated && !useUserPreferenceStore().isPrintMode">
            <a href="https://tandoor.dev">
                <v-img src="../../assets/brand_logo.svg" width="140px" class="ms-2" ></v-img>
            </a>
        </v-app-bar>
        <v-app-bar :color="navBgColor"
                   flat density="comfortable" v-if="useUserPreferenceStore().isAuthenticated && !useUserPreferenceStore().isPrintMode"
                   :absolute="!useUserPreferenceStore().userSettings.navSticky"
                   :scroll-behavior="useUserPreferenceStore().userSettings.navSticky ? 'elevate' : ''">
            <!-- home: with an app name set for the space ("white label"), show its icon and name as text -->
            <router-link :to="{ name: 'StartPage', params: {} }" class="home-brand ms-3"
                         v-if="useUserPreferenceStore().userSettings.navShowLogo && useUserPreferenceStore().activeSpace.appName">
                <img :src="spaceIcon" alt="" class="home-brand-icon">
                <span class="home-brand-name">{{ useUserPreferenceStore().activeSpace.appName }}</span>
            </router-link>
            <router-link :to="{ name: 'StartPage', params: {} }" v-else>
                <v-img :src="theme.global.current.value.dark ? brandLogoDark : brandLogo" width="140px" class="ms-2"
                       v-if="useUserPreferenceStore().userSettings.navShowLogo && !useUserPreferenceStore().activeSpace.navLogo"></v-img>
                <v-img :src="useUserPreferenceStore().activeSpace.navLogo.preview" width="140px" class="ms-2"
                       v-if="useUserPreferenceStore().userSettings.navShowLogo && useUserPreferenceStore().activeSpace.navLogo != undefined"></v-img>
            </router-link>

            <v-spacer></v-spacer>
            <global-search-dialog></global-search-dialog>
            <v-btn icon="$add" class="d-print-none">
                <v-icon icon="$add" class="fa-fw"></v-icon>
                <v-menu activator="parent">
                    <v-list>
                        <v-list-item prepend-icon="$add" :to="{ name: 'ModelEditPage', params: {model: 'recipe'} }">{{ $t('Create Recipe') }}</v-list-item>
                        <v-list-item prepend-icon="fa-solid fa-globe" :to="{ name: 'RecipeImportPage', params: {} }">{{ $t('Import Recipe') }}</v-list-item>
                    </v-list>
                </v-menu>
            </v-btn>

            <v-avatar color="primary" class="me-2 cursor-pointer d-print-none">{{ useUserPreferenceStore().userSettings.user.displayName.charAt(0) }}
                <v-menu activator="parent">

                    <v-list density="compact">
                        <menu-user-info></menu-user-info>
                        <v-divider></v-divider>

                        <component :is="item.component" :="item" :key="item.title" v-for="item in useNavigation().getUserNavigation()"></component>
                    </v-list>
                </v-menu>
            </v-avatar>

        </v-app-bar>
        <v-app-bar color="info"
                   v-if="useUserPreferenceStore().isAuthenticated && useUserPreferenceStore().activeSpace.maxRecipes == 10 && useUserPreferenceStore().serverSettings.hosted">
            <p class="text-center w-100">
                {{ $t('HostedFreeVersion') }}
                <v-btn color="success" size="small" variant="flat" :to="{name: 'EnterpriseSettingsBillingSubscription'}">{{ $t('UpgradeNow') }}</v-btn>
            </p>
        </v-app-bar>
        <v-app-bar color="warning" v-if="useUserPreferenceStore().isAuthenticated && isSpaceAboveLimit(useUserPreferenceStore().activeSpace)">
            <p class="text-center w-100">
                {{ $t('SpaceLimitExceeded') }}
                <v-btn color="success" size="small" variant="flat" :to="{name: 'SpaceSettings'}">{{ $t('SpaceSettings') }}</v-btn>
            </p>
        </v-app-bar>

        <v-app-bar color="info" density="compact"
                   v-if="useUserPreferenceStore().isAuthenticated && useUserPreferenceStore().activeSpace.message != '' && !useUserPreferenceStore().isPrintMode">
            <p class="text-center w-100">
                {{ useUserPreferenceStore().activeSpace.message }}
            </p>
        </v-app-bar>

        <v-main>
            <router-view></router-view>
        </v-main>

        <!-- completely hide in print mode because setting d-print-node keeps layout -->
        <v-navigation-drawer v-if="lgAndUp && useUserPreferenceStore().isAuthenticated && !useUserPreferenceStore().isPrintMode">
            <v-list>
                <!-- home: who you are lives in the account menu (top right), so the sidebar starts with navigation -->
                <component :is="item.component" :="item" :key="item.title" v-for="item in useNavigation().getNavigationDrawer()"></component>

                <navigation-drawer-context-menu></navigation-drawer-context-menu>
            </v-list>

            <template #append>
                <v-list nav>
                    <v-list-item prepend-icon="fas fa-sliders" :title="$t('Settings')" :to="{ name: 'SettingsPage', params: {} }"></v-list-item>
                    <v-list-item link class="drawer-version">
                        <span class="text-caption text-medium-emphasis">Tandoor {{ useUserPreferenceStore().serverSettings.version }}</span>
                        <help-dialog></help-dialog>
                    </v-list-item>
                </v-list>
            </template>

        </v-navigation-drawer>

        <v-bottom-navigation grow v-if="useUserPreferenceStore().isAuthenticated && !lgAndUp && !useUserPreferenceStore().isPrintMode">
            <v-btn value="recent" :to="{ name: 'StartPage', params: {} }">
                <v-icon icon="fa-fw fas fa-book "/>
            </v-btn>

            <v-btn value="favorites" to="/mealplan">
                <v-icon icon="fa-fw fas fa-calendar-alt"></v-icon>
            </v-btn>

            <v-btn value="nearby" to="/shopping">
                <v-icon icon="fa-fw fas fa-shopping-cart"></v-icon>
            </v-btn>

            <v-btn value="nearby">
                <v-icon icon="fa-fw fas fa-bars"></v-icon>
                <v-bottom-sheet activator="parent" close-on-content-click>
                    <v-list nav>
                        <menu-user-info></menu-user-info>
                        <component :is="item.component" :="item" :key="item.title" v-for="item in useNavigation().getBottomNavigation()"></component>
                    </v-list>
                </v-bottom-sheet>
            </v-btn>
        </v-bottom-navigation>

        <v-snackbar-queued
            :vertical="true"
            location="top center"
        ></v-snackbar-queued>

    </v-app>

</template>

<script lang="ts" setup>
import GlobalSearchDialog from "@/components/inputs/GlobalSearchDialog.vue"

import {useDisplay, useLocale, useTheme} from "vuetify"
import brandLogo from "@/assets/brand_logo.svg"
import brandLogoDark from "@/assets/brand_logo_dark.svg"
import logoColor from "@/assets/logo_color.svg"
import {toVuetifyLocale} from "@/vuetify"
import VSnackbarQueued from "@/components/display/VSnackbarQueued.vue";
import {useUserPreferenceStore} from "@/stores/UserPreferenceStore";
import NavigationDrawerContextMenu from "@/components/display/NavigationDrawerContextMenu.vue";
import {computed, nextTick, onMounted, ref, watch} from "vue";
import {isSpaceAboveLimit} from "@/utils/logic_utils";
import {useTitle} from "@vueuse/core";
import HelpDialog from "@/components/dialogs/HelpDialog.vue";
import {useNavigation} from "@/composables/useNavigation.ts";
import {useRouter} from "vue-router";
import {useI18n} from "vue-i18n";
import {THousehold, TSpace} from "@/types/Models.ts";
import MenuUserInfo from "@/components/display/MenuUserInfo.vue";

const {lgAndUp} = useDisplay()
const theme = useTheme()

// Home theme: the stock default nav colour (#ddbf86) becomes a plain surface bar; a colour a
// user or space picked on purpose is still respected.
const LEGACY_NAV_BG = '#ddbf86'
const navBgColor = computed(() => {
    const c = useUserPreferenceStore().activeSpace.navBgColor || useUserPreferenceStore().userSettings.navBgColor
    return (!c || c.toLowerCase() == LEGACY_NAV_BG) ? 'surface' : c
})
const {t} = useI18n()

// home: the space's own icon for the toolbar — the server already puts it in the page as the favicon
// (theme_values.logo_color_svg), which also covers icons the file API can't preview (SVG)
const spaceIcon = computed(() => {
    const sp = useUserPreferenceStore().activeSpace
    const favicon = (document.querySelector('link[rel="icon"]') as HTMLLinkElement | null)?.href
    return sp.logoColorSvg || sp.logoColor192 ? (favicon || logoColor) : logoColor
})

const title = useTitle()

// home: page titles read "Books · Kitchen" using the space's app name (once the space has loaded)
const routeTitle = ref('')

function applyTitle() {
    const appName = useUserPreferenceStore().activeSpace?.appName || 'Tandoor'
    title.value = routeTitle.value ? `${routeTitle.value} · ${appName}` : appName
}

watch(() => useUserPreferenceStore().activeSpace?.appName, (now, before) => {
    // only touch the title if it is still the generic one (recipe pages set their own)
    const before_ = before || 'Tandoor'
    if (title.value == before_ || title.value?.endsWith(` · ${before_}`)) applyTitle()
})
const router = useRouter()

onMounted(() => {
    useUserPreferenceStore().init().then(() => {
        if (useUserPreferenceStore().activeSpace.spaceSetupCompleted != undefined && !useUserPreferenceStore().activeSpace.spaceSetupCompleted) {
            router.push({name: 'WelcomePage'})
        }
    })


    const {current} = useLocale()
    let locale = document.querySelector('html')!.getAttribute('lang')
    if (locale != null) {
        current.value = toVuetifyLocale(locale.toLowerCase())
    }
})

/**
 * global title update handler, might be overridden by page specific handlers
 */
router.afterEach((to, from) => {
    if (to.name == 'StartPage' && useUserPreferenceStore().initCompleted && !useUserPreferenceStore().activeSpace.spaceSetupCompleted != undefined && !useUserPreferenceStore().activeSpace.spaceSetupCompleted && useUserPreferenceStore().activeSpace.createdBy.id! == useUserPreferenceStore().userSettings.user.id!) {
        router.push({name: 'WelcomePage'})
    } else if (to.name == 'StartPage' &&
        useUserPreferenceStore().initCompleted &&
        useUserPreferenceStore().activeSpace.spaceSetupCompleted &&
        !useUserPreferenceStore().activeSpace.householdSetupCompleted != undefined &&
        !useUserPreferenceStore().activeSpace.householdSetupCompleted &&
        useUserPreferenceStore().activeSpace.createdBy.id! == useUserPreferenceStore().userSettings.user.id! &&
        useUserPreferenceStore().activeUserSpace?.household == undefined ) {
        router.push({name: 'HouseholdPage'})
    }
    nextTick(() => {
        routeTitle.value = to.meta.title ? t(to.meta.title as string) : ''
        applyTitle()
    })
})

</script>

<style>

.v-theme--dark {

    a:not([class]) {
        color: #b98766;
        text-decoration: none;
        background-color: transparent
    }

    a:hover {
        color: #fff;
        text-decoration: none
    }

    a:not([href]):not([tabindex]), a:not([href]):not([tabindex]):focus, a:not([href]):not([tabindex]):hover {
        color: inherit;
        text-decoration: none
    }

    a:not([href]):not([tabindex]):focus {
        outline: 0
    }

    /* Meal-Plan */

    .cv-header {
        background-color: #303030 !important;
    }

    .cv-weeknumber, .cv-header-day {
        background-color: #303030 !important;
        color: #fff !important;
    }

    .cv-day.past {
        background-color: #333333 !important;
    }

    .cv-day.today {
        background-color: rgba(185, 135, 102, 0.2) !important;
    }

    .cv-day.outsideOfMonth {
        background-color: #0d0d0d !important;
    }

    .cv-item {
        background-color: #4E4E4E !important;
    }

    .d01 .cv-day-number {
        background-color: #b98766 !important;
    }

    /* mavon-editor link/image dialog */

    .add-image-link {
        background-color: #212121 !important;
        color: #fff !important;
    }

    .add-image-link > i {
        color: rgba(255, 255, 255, 0.7) !important;
    }

    .add-image-link .input-wrapper {
        border-color: #555 !important;
    }

    .add-image-link .input-wrapper input {
        background-color: #212121 !important;
        color: #fff !important;
    }

    .add-image-link .op-btn {
        color: #fff !important;
    }

    /* mavon-editor dark mode — container + toolbar */

    .v-note-wrapper {
        background-color: #212121 !important;
        border-color: #555 !important;
    }

    .v-note-wrapper .v-note-op {
        background-color: #303030 !important;
        border-bottom-color: #555 !important;
    }

    /* mavon-editor dark mode — toolbar icons */

    .v-note-wrapper .op-icon {
        color: rgba(255, 255, 255, 0.7) !important;
    }

    .v-note-wrapper .op-icon:hover {
        color: #fff !important;
        background-color: rgba(255, 255, 255, 0.1) !important;
    }

    .v-note-wrapper .op-icon.selected {
        color: #fff !important;
        background-color: rgba(255, 255, 255, 0.15) !important;
    }

    .v-note-wrapper .op-icon-divider {
        border-left-color: #555 !important;
    }

    /* mavon-editor dark mode — textarea and wrappers */

    .auto-textarea-input,
    .content-input-wrapper,
    .auto-textarea-wrapper {
        color: #e0e0e0 !important;
        background-color: #212121 !important;
    }

    .v-note-wrapper .v-show-content,
    .v-note-wrapper .v-show-content-html,
    .v-note-wrapper .v-note-read-model {
        background-color: #212121 !important;
    }

    .v-note-wrapper .v-note-navigation-wrapper {
        background-color: rgba(33, 33, 33, 0.98) !important;
    }

    .v-note-wrapper .op-header.popup-dropdown {
        background-color: #303030 !important;
        border-color: #555 !important;
        box-shadow: 0 2px 12px rgba(0, 0, 0, 0.3) !important;
    }

    /* mavon-editor dark mode — preview panel */

    .v-note-wrapper .markdown-body {
        color: #e0e0e0 !important;
    }

    .v-note-wrapper .markdown-body a {
        color: #b98766 !important;
    }

    .v-note-wrapper .markdown-body h1,
    .v-note-wrapper .markdown-body h2 {
        border-bottom-color: #555 !important;
    }

    .v-note-wrapper .markdown-body h6 {
        color: #999 !important;
    }

    .v-note-wrapper .markdown-body hr {
        background-color: #555 !important;
    }

    .v-note-wrapper .markdown-body blockquote {
        color: #999 !important;
        border-left-color: #555 !important;
        background-color: rgba(255, 255, 255, 0.05) !important;
    }

    .v-note-wrapper .markdown-body table tr {
        background-color: #212121 !important;
        border-top-color: #555 !important;
    }

    .v-note-wrapper .markdown-body table tr:nth-child(2n) {
        background-color: #2a2a2a !important;
    }

    .v-note-wrapper .markdown-body table td,
    .v-note-wrapper .markdown-body table th {
        border-color: #555 !important;
    }

    .v-note-wrapper .markdown-body code {
        background-color: rgba(255, 255, 255, 0.1) !important;
        color: #e0e0e0 !important;
    }

    .v-note-wrapper .markdown-body .highlight pre,
    .v-note-wrapper .markdown-body pre {
        background-color: #2a2a2a !important;
        color: #e0e0e0 !important;
    }

    .v-note-wrapper .markdown-body kbd {
        color: #e0e0e0 !important;
        background-color: #333 !important;
        border-color: #555 !important;
        box-shadow: inset 0 -1px 0 #444 !important;
    }

    .v-note-wrapper .markdown-body img {
        background-color: transparent !important;
    }

    /* mavon-editor dark mode — dropdown menus */

    .v-note-wrapper .op-icon.dropdown-wrapper .dropdown-item {
        color: #e0e0e0 !important;
        background-color: #303030 !important;
    }

    .v-note-wrapper .op-icon.dropdown-wrapper .dropdown-item:hover {
        color: #fff !important;
        background-color: #424242 !important;
    }

    /* mavon-editor dark mode — scrollbar */

    .v-note-wrapper .scroll-style::-webkit-scrollbar {
        background-color: #333 !important;
    }

    .v-note-wrapper .scroll-style::-webkit-scrollbar-thumb {
        background-color: #555 !important;
    }

    /* markdown display (read-only view in StepView) */

    .markdown-body {
        color: #e0e0e0 !important;
    }

    .markdown-body a {
        color: #b98766 !important;
    }

    .markdown-body blockquote {
        background: rgba(255, 255, 255, 0.05) !important;
        border-left-color: #555 !important;
    }

    .markdown-body code {
        background-color: rgba(255, 255, 255, 0.1) !important;
        color: #e0e0e0 !important;
    }
}

.v-theme--light {
    a:not([class]) {
        color: #b98766;
        text-decoration: none;
        background-color: transparent
    }

    a:hover {
        color: #000;
        text-decoration: none
    }

    a:not([href]):not([tabindex]), a:not([href]):not([tabindex]):focus, a:not([href]):not([tabindex]):hover {
        color: inherit;
        text-decoration: none
    }

    a:not([href]):not([tabindex]):focus {
        outline: 0
    }

}

/* vueform/multiselect */

.multiselect-option.is-pointed {
    background: #b98766 !important;
}

.multiselect-option.is-selected {
    background: #b55e4f !important;
}

</style>
