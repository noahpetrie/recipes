// home fork: store links, "I have it" and restock suggestions for the shopping list (cookbook/views/home_restock.py)
import {ref} from 'vue'
import {useDjangoUrls} from '@/composables/useDjangoUrls'
import {getCookie} from '@/utils/cookie'

export type StoreLink = { name: string, url: string, store: string, image: string }

/** food id -> the store product usually bought for it, for foods on the shopping list */
export const storeLinks = ref<Record<number, StoreLink>>({})

export async function homeApi(path: string, body?: any) {
    const {getDjangoUrl} = useDjangoUrls()
    const r = await fetch(getDjangoUrl(`api/home/${path}`), {
        method: body === undefined ? 'GET' : 'POST', credentials: 'same-origin',
        headers: {'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') ?? ''},
        body: body === undefined ? undefined : JSON.stringify(body),
    })
    const data = await r.json().catch(() => ({}))
    if (!r.ok) throw new Error(data.error || `${r.status}`)
    return data
}

let linkSeq = 0
export async function loadStoreLinks() {
    const seq = ++linkSeq
    try {
        const r = await homeApi('store-links/')
        if (seq == linkSeq) storeLinks.value = r.links
    } catch {
        // rows just show no store link
    }
}

/** "I have it": books enough for any recipe into the pantry and takes the food off the list */
export async function haveFood(foodId: number): Promise<string> {
    const r = await homeApi('have/', {food_id: foodId})
    return r.message
}
