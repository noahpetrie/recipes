import type {InventoryEntry, Unit} from '../openapi'

export const EXPIRY_WINDOW_DAYS = 30
export type Total = {unit: Unit | null, amount: string}

/** Sum the decimal representations delivered by the API without floating-point accumulation. */
export function decimalSum(values: (number | string)[]): string {
    const parts = values.map(value => {
        const [mantissa, exponent = '0'] = String(value).toLowerCase().split('e')
        const [whole, fraction = ''] = mantissa!.split('.')
        const scale = fraction.length - Number(exponent)
        return {digits: BigInt(whole! + fraction), scale}
    })
    const scale = Math.max(0, ...parts.map(p => p.scale))
    const sum = parts.reduce((sum, p) => sum + p.digits * BigInt(10) ** BigInt(scale - p.scale), BigInt(0))
    const sign = sum < 0 ? '-' : ''
    const digits = (sum < 0 ? -sum : sum).toString().padStart(scale + 1, '0')
    return sign + (scale ? `${digits.slice(0, -scale)}.${digits.slice(-scale)}`.replace(/\.?0+$/, '') : digits)
}

// home fork: a product under a general food (Eggs Omega 3 under Egg(s), cookbook/helper/home_products.py)
// arrives with the general food and, when its size is known, its amount in the general food's unit
export type Group = {food: {id: number, name: string, product_image: string}, amount: string | null, unit: {id: number, name: string, plural_name: string} | null}
export function entryGroup(entry: InventoryEntry): Group | null {
    return entry.group ?? null
}

/** amount and unit an entry adds to its line: the general food's unit when it converts */
function counted(entry: InventoryEntry): {unit: Unit | null, amount: number | string} {
    const g = entryGroup(entry)
    if (g?.amount != null && g.unit) return {unit: {id: g.unit.id, name: g.unit.name, pluralName: g.unit.plural_name} as Unit, amount: g.amount}
    return {unit: entry.unit ?? null, amount: entry.amount ?? 0}
}

export function totals(entries: InventoryEntry[]): Total[] {
    const groups = new Map<number | null, {unit: Unit | null, amount: number | string}[]>()
    for (const entry of entries) {
        const c = counted(entry)
        const key = c.unit?.id ?? null
        if (!groups.has(key)) groups.set(key, [])
        groups.get(key)!.push(c)
    }
    return [...groups.values()].map(rows => ({unit: rows[0]!.unit, amount: decimalSum(rows.map(c => c.amount))}))
}

export function quantity(amount: number | string, unit?: Unit | null): string {
    const name = unit ? (Math.abs(Number(amount)) === 1 ? unit.name : unit.pluralName || unit.name) : ''
    return `${amount}${name ? ` ${name}` : ''}`
}

export function totalText(values: Total[]): string {
    return values.map(t => quantity(t.amount, t.unit)).join(' · ')
}

// The generated client parses date-only fields as UTC dates. Preserve the original calendar day.
export function expiryDay(entry: InventoryEntry): string | null {
    return entry.expires ? entry.expires.toISOString().slice(0, 10) : null
}

export function groupProducts(entries: InventoryEntry[]) {
    const groups = new Map<string, InventoryEntry[]>()
    for (const entry of entries) {
        // The list endpoint returns positive stock only. Keep that domain rule for fixtures too.
        if (!(Number(entry.amount) > 0)) continue
        const g = entryGroup(entry)
        const key = g ? `food:${g.food.id}` : entry.food?.id == null ? `entry:${entry.id}` : `food:${entry.food.id}`
        if (!groups.has(key)) groups.set(key, [])
        groups.get(key)!.push(entry)
    }
    return [...groups.entries()].map(([key, batches]) => {
        const locations = new Map<number | null, InventoryEntry[]>()
        for (const batch of batches) {
            const id = batch.inventoryLocation?.id ?? null
            if (!locations.has(id)) locations.set(id, [])
            locations.get(id)!.push(batch)
        }
        const dates = batches.map(expiryDay).filter((d): d is string => !!d).sort()
        // a general food's line shows the general food; its own stock (if any) supplies the rest
        const g = batches.map(entryGroup).find(Boolean)
        const own = batches.find(b => !entryGroup(b))?.food
        const food = g ? {...(own ?? batches[0]!.food), id: g.food.id, name: g.food.name, productImage: own?.productImage || g.food.product_image, barcodes: own?.barcodes ?? ''} : batches[0]!.food
        return {
            key, food, grouped: !!g, batches, totals: totals(batches),
            locations: [...locations.entries()].map(([id, rows]) => ({id, name: rows[0]!.inventoryLocation?.name || 'Unassigned', totals: totals(rows)})),
            earliestExpiry: dates[0] ?? null, unknownExpiry: batches.length - dates.length,
        }
    }).sort((a, b) => (a.food?.name ?? '').localeCompare(b.food?.name ?? '') || a.key.localeCompare(b.key))
}

export type PantryProduct = ReturnType<typeof groupProducts>[number]

/** Never publish a partial total. Follow pagination even when the server caps page size. */
export async function loadInventory(fetchPage: (page: number) => Promise<{results: InventoryEntry[], next?: string | null, count: number}>) {
    const entries = new Map<number, InventoryEntry>()
    let page = 1
    while (true) {
        const result = await fetchPage(page++)
        for (const entry of result.results) entries.set(entry.id!, entry)
        if (!result.next) {
            if (entries.size !== result.count) throw new Error('Inventory changed while loading. Please refresh.')
            return [...entries.values()]
        }
        if (!result.results.length) throw new Error('Could not load all inventory pages.')
    }
}
