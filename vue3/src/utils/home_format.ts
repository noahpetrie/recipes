// home fork: numbers the way people read them

/** 450 -> "7 h 30 min", 60 -> "1 h", 25 -> "25 min" */
export function formatMinutes(minutes: number | null | undefined): string {
    const m = Math.round(minutes ?? 0)
    if (m < 60) return `${m} min`
    const h = Math.floor(m / 60), rest = m % 60
    if (h >= 48 && rest == 0 && h % 24 == 0) return `${h / 24} days`
    return rest ? `${h} h ${rest} min` : `${h} h`
}

/** nutrition: whole numbers from 10 up (420 kcal), one decimal below (6.5 g) */
export function roundNutrient(value: number | null | undefined): number {
    const v = value ?? 0
    return Math.abs(v) >= 10 ? Math.round(v) : Math.round(v * 10) / 10
}
