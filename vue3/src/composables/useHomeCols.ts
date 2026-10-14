// home fork: how many recipe cards fit across the start page, about 230 px each (2 on a phone, 4 on a laptop, 6–7 on a wide screen)
import {computed} from 'vue'
import {useDisplay} from 'vuetify'

export function useHomeCols() {
    const {width, mdAndUp} = useDisplay()
    return computed(() => {
        // the side navigation takes about 260 px on wide screens
        const room = width.value - (mdAndUp.value ? 300 : 32)
        return Math.min(7, Math.max(2, Math.floor(room / 230)))
    })
}
