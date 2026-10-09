import '@fortawesome/fontawesome-free/css/all.css'
import 'vuetify/styles'
import {aliases, fa} from 'vuetify/iconsets/fa'

// Composables
import {createVuetify} from 'vuetify'
import {DateTime} from "luxon";
import * as vuetifyLocales from "vuetify/locale";

// https://vuetifyjs.com/en/introduction/why-vuetify/#feature-guides
export default createVuetify({
    defaults: {
        // disabled as this leads to cards overflowing if not careful, manually set on cards containing a multiselect until proper solution is found
        // VCard: {
        //     class: 'overflow-visible' // this is needed so that vue-multiselect options show above a card, vuetify uses overlay container to avoid this
        // },
        // without this action buttons are left aligned in normal cards but right aligned in dialogs (I think)
        VCardActions: {
            class: 'float-right'
        },
        // limiting max width of base container so UIs dont become too wide
        VContainer: {
            maxWidth: '1400px'
        },
        // always localize the date display of DateInputs
        // VDateInput: {
        //     displayFormat: (date: Date) => DateTime.fromJSDate(date).toLocaleString()
        // },
        // always use color for switches to properly see if enabled or not
        VSwitch: {
            color: 'primary'
        },
        // globally set the correct decimal seperator
        // VNumberInput: {
        //     decimalSeparator: 0.1.toLocaleString().replace(/\d/g, '')
        // }
        // chips use the close icon defined as delete in the aliases but trash can does not look good
        VChip: {
            closeIcon: 'fa-solid fa-circle-xmark'
        },
        // Home theme: softer corners
        VCard: {
            rounded: 'lg'
        },
        VDialog: {
            VCard: {rounded: 'xl'}
        },
        // Home theme: compact outlined form fields (40px, shadcn/ui-style) instead of 56px underlined/filled ones
        VTextField: {variant: 'outlined', density: 'compact'},
        VTextarea: {variant: 'outlined', density: 'compact'},
        VSelect: {variant: 'outlined', density: 'compact'},
        VAutocomplete: {variant: 'outlined', density: 'compact'},
        VCombobox: {variant: 'outlined', density: 'compact'},
        VNumberInput: {variant: 'outlined', density: 'compact'},
        VFileInput: {variant: 'outlined', density: 'compact'},
        // date pickers: one "October 2026 ▾" label with ‹ › (shadcn calendar), faded days from the next/previous month
        VDatePicker: {controlVariant: 'modal', showAdjacentMonths: true},
        // flat buttons: no drop shadows
        VBtn: {rounded: 'lg', elevation: 0},
    },
    locale: {
        locale: 'en',
        fallback: 'en',
        messages: vuetifyLocales,
    },
    theme: {
        defaultTheme: 'light',
        themes: {
            // Home theme: lighter warm neutrals and a deeper terracotta accent so white text on
            // primary meets WCAG AA (the stock #b98766 was ~3.1:1).
            light: {
                colors: {
                    background: '#f7f4ef',
                    surface: '#ffffff',
                    'surface-variant': '#ece6de',
                    'on-surface-variant': '#4a3f36',
                    tandoor: '#ddbf86',
                    primary: '#a05a38',
                    secondary: '#9c4a3c',
                    success: '#4f8a5b',
                    info: '#2f5f8a',
                    warning: '#c98a12',
                    error: '#a7240e',

                    save: '#4f8a5b',
                    create: '#4f8a5b',
                    edit: '#2f5f8a',
                    delete: '#a7240e',
                    cancel: '#c98a12',

                    recipeImagePlaceholderBg: '#f1ece5',
                },
            },
            dark: {
                colors: {
                    background: '#131315',
                    surface: '#1c1c1f',
                    'surface-variant': '#2a2a2e',
                    'on-surface-variant': '#d6cfc7',
                    tandoor: '#ddbf86',
                    primary: '#d9a07a',
                    secondary: '#d98b7a',
                    success: '#7fb48a',
                    info: '#7aa7d1',
                    warning: '#e6b04a',
                    error: '#e06a55',

                    save: '#7fb48a',
                    create: '#7fb48a',
                    edit: '#7aa7d1',
                    delete: '#e06a55',
                    cancel: '#e6b04a',

                    recipeImagePlaceholderBg: '#26262a',
                },
            },
        },
    },
    icons: {
        defaultSet: 'fa',
        aliases: {
            ...aliases,
            save: 'fa-solid fa-floppy-disk',
            delete: 'fa-solid fa-trash-can',
            edit: 'fa-solid fa-pencil',
            create: 'fa-solid fa-plus',
            upload: 'fa-solid fa-file-arrow-up',
            search: 'fa-solid fa-magnifying-glass',
            copy: 'fa-solid fa-copy',
            add: 'fa-solid fa-plus',
            close: 'fa-solid fa-xmark',
            help: 'fa-solid fa-info',
            settings: 'fa-solid fa-sliders',
            dragHandle: 'fa-solid fa-grip-vertical',
            spaces: 'fa-solid fa-database',
            shopping: 'fa-solid fa-cart-shopping',
            mealplan: 'fa-solid fa-calendar-days',
            recipes: 'fa-solid fa-book',
            books: 'fa-solid fa-book-bookmark',
            menu: 'fa-solid fa-ellipsis-vertical',
            import: 'fa-solid fa-globe',
            properties: 'fa-solid fa-database',
            pantry: 'fas fa-jar',
            automation: 'fa-solid fa-robot',
            ai: 'fa-solid fa-wand-magic-sparkles',
            reset: 'fa-solid fa-circle-xmark'
        },
        sets: {
            fa,
        },
    },
})

export type VDataTableUpdateOptions = {
    page: number;
    itemsPerPage: number;
    search: string;
    sortBy?: string;
    groupBy?: string;
}

const VUETIFY_LOCALES = new Set(Object.keys(vuetifyLocales))

const VUETIFY_LOCALE_MAP: Record<string, string> = {
    'nb-no': 'no',
    'nb': 'no',
    'pt-br': 'pt',
    'zh-hans': 'zhHans',
    'zh-hant': 'zhHant',
    'sr-cyrl': 'srCyrl',
    'sr-latn': 'srLatn',
}

export function toVuetifyLocale(djangoCode: string): string {
    const lc = djangoCode.toLowerCase()
    const mapped = VUETIFY_LOCALE_MAP[lc] || lc
    return VUETIFY_LOCALES.has(mapped) ? mapped : 'en'
}
