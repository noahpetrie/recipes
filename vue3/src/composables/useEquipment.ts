// home fork: kitchen equipment (cookbook/views/home_equipment.py)
import {ref} from 'vue'
import {useDjangoUrls} from '@/composables/useDjangoUrls'
import {getCookie} from '@/utils/cookie'

export type Equipment = {
    id: number, name: string, owned: boolean, hidden: boolean, homebox: boolean, image: string | null,
    general: { id: number, name: string } | null, kind: boolean, basic: boolean,
    have: boolean, via: string | null, recipes?: number,
}
export type RecipeEquipmentLine = Equipment & { optional: boolean, note: string }

/** bumped whenever equipment changes, so open pages reload */
export const equipmentVersion = ref(0)

export async function equipmentApi(path: string, method = 'GET', body?: any) {
    const {getDjangoUrl} = useDjangoUrls()
    const r = await fetch(getDjangoUrl(`api/home/equipment/${path}`), {
        method, credentials: 'same-origin',
        headers: {'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') ?? ''},
        body: body === undefined ? undefined : JSON.stringify(body),
    })
    if (!r.ok) {
        let msg = `Couldn’t save (${r.status}).`
        try { msg = (await r.json()).error || msg } catch { /* not json */ }
        throw new Error(msg)
    }
    if (method != 'GET') equipmentVersion.value++
    return r.status == 204 ? null : r.json()
}

/** "Breville the Smart Oven Air" for a need met by something else, else "" */
export function viaText(e: Equipment) {
    return e.via ? `Using your ${e.via}` : ''
}
