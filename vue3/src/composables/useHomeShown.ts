import {computed, inject, provide, reactive} from 'vue'

// home fork: the start page's rows skip recipes an earlier row already shows.
// Rows claim the recipes they show under their position (0 = top); a row hides what a row above it claimed.
const KEY = Symbol('home-shown')

export function provideHomeShown() {
    provide(KEY, reactive(new Map<number, number[]>()))
}

export function useHomeShown(order: number) {
    const rows = order < 0 ? null : inject<Map<number, number[]> | null>(KEY, null)
    return {
        claim(ids: number[]) {
            // only on a change: every claim re-runs the rows' filters, which claim again
            if (rows && rows.get(order)?.join() !== ids.join()) rows.set(order, ids)
        },
        taken: computed(() => {
            const s = new Set<number>()
            rows?.forEach((ids, o) => {
                if (o < order) ids.forEach(i => s.add(i))
            })
            return s
        }),
    }
}
