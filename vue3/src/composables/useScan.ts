// home fork: pantry barcode scanning. Scans (handheld scanner, camera or typed) go to the scan
// panel (PantryScanPanel). Scanning only *finds* things; stock changes through an explicit action.
import {reactive, ref} from "vue";
import {useDjangoUrls} from "@/composables/useDjangoUrls";
import {getCookie} from "@/utils/cookie";

export type ScanSource = 'camera' | 'handheld' | 'typed'
export type ScanMode = 'lookup' | 'restock' | 'count'

export const scanRequest = ref<{ code: string, source: ScanSource, at: number } | null>(null)
export const cameraOpen = ref(false)
/** bumped after any stock change made from the panel, so open pantry lists refresh */
export const pantryVersion = ref(0)

const KEEP_MODE_KEY = 'kitchen:scanKeepMode'
const MODE_KEY = 'kitchen:scanMode'

function stored(key: string): string | null {
    try { return localStorage.getItem(key) } catch (e) { return null }
}

export function store(key: string, value: string | null) {
    try { value == null ? localStorage.removeItem(key) : localStorage.setItem(key, value) } catch (e) { /* private mode */ }
}

export const scanPanel = reactive({
    open: false,
    mode: 'lookup' as ScanMode,
    keepMode: stored(KEEP_MODE_KEY) == '1',
    /** set by openScanPanel to show a food or batch without scanning */
    target: null as null | { foodId?: number, entryId?: number, tab?: string },
    at: 0,
})

/** open the panel; it starts in Lookup unless the person chose to keep the last mode */
export function openScanPanel(o: { mode?: ScanMode, foodId?: number, entryId?: number, tab?: string } = {}) {
    scanPanel.mode = o.mode ?? (scanPanel.keepMode ? (stored(MODE_KEY) as ScanMode) ?? 'lookup' : 'lookup')
    scanPanel.target = o.foodId || o.entryId ? {foodId: o.foodId, entryId: o.entryId, tab: o.tab} : null
    scanPanel.open = true
    scanPanel.at = Date.now()
}

export function rememberMode(mode: ScanMode, keep: boolean) {
    store(MODE_KEY, mode)
    store(KEEP_MODE_KEY, keep ? '1' : null)
    scanPanel.keepMode = keep
}

export function scanned(code: string, source: ScanSource) {
    if (!scanPanel.open) openScanPanel()
    scanRequest.value = {code: code.trim(), source, at: Date.now()}
}

// ---- api ---------------------------------------------------------------------------------------

export class PantryError extends Error {
    status: number
    body: any

    constructor(status: number, body: any) {
        super(body?.error ?? `Request failed (${status})`)
        this.status = status
        this.body = body
    }
}

export async function pantryApi(path: string, body?: any, method?: string): Promise<any> {
    const {getDjangoUrl} = useDjangoUrls()
    const [p, q] = path.split('?')
    const url = getDjangoUrl(`api/pantry/${p}`) + (q ? `?${q}` : '')
    const r = await fetch(url, {
        method: method ?? (body === undefined ? 'GET' : 'POST'),
        credentials: 'same-origin',
        headers: {'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') ?? ''},
        body: body === undefined ? undefined : JSON.stringify(body),
    })
    let data: any = null
    try { data = await r.json() } catch (e) { /* empty */ }
    if (!r.ok) throw new PantryError(r.status, data)
    return data
}

export function newRequestId(): string {
    return (crypto as any).randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`
}

// ---- formatting --------------------------------------------------------------------------------

export type PUnit = { id: number, name: string, plural_name: string } | null

export function fmtAmount(n: number): string {
    return Number.isInteger(n) ? String(n) : n.toLocaleString(undefined, {maximumFractionDigits: 2})
}

export function qty(n: number, unit: PUnit): string {
    if (!unit) return fmtAmount(n)
    return `${fmtAmount(n)} ${n == 1 ? unit.name : (unit.plural_name || unit.name)}`
}

export function fmtDate(iso: string | null): string {
    if (!iso) return ''
    const d = new Date(iso.length == 10 ? iso + 'T12:00:00' : iso)
    return d.toLocaleDateString(undefined, {month: 'short', day: 'numeric', year: 'numeric'})
}

export function daysUntil(iso: string | null): number | null {
    if (!iso) return null
    const d = new Date(iso + 'T12:00:00').getTime()
    const today = new Date()
    today.setHours(12, 0, 0, 0)
    return Math.round((d - today.getTime()) / 86400000)
}

const NOTE_LABELS: Record<string, string> = {consumed: 'used', discarded: 'thrown out', spoiled: 'spoiled', donated: 'given away', other: 'other reason'}

/** a booking note as people would say it (internal markers like "count #3" or "undid #12" are dropped) */
export function noteText(type: string, note: string): string {
    if (!note || type == 'undo' || /^count( #\d+)?$/.test(note) || /^from #/.test(note)) return ''
    const [first, ...rest] = note.split(' ')
    return NOTE_LABELS[first!] ? [type == 'remove' ? '' : NOTE_LABELS[first!], ...rest].filter(Boolean).join(' ') : note
}
