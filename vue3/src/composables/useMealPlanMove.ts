// home fork: move or copy a planned meal (or a whole trip) to another day, with an Undo toast (HomeUndoToast.vue)
import {ref} from 'vue'
import {DateTime} from 'luxon'
import {ApiApi, MealPlan} from '@/openapi'
import {useMealPlanStore} from '@/stores/MealPlanStore'
import {ErrorMessageType, useMessageStore} from '@/stores/MessageStore'

export const undoToast = ref<{ text: string, undo: () => Promise<unknown> } | null>(null)

export function dayLabel(day: DateTime): string {
    const days = Math.round(day.startOf('day').diff(DateTime.now().startOf('day'), 'days').days)
    return days == 0 ? 'today' : days == 1 ? 'tomorrow' : day.toLocaleString({weekday: 'short', month: 'short', day: 'numeric'})
}

/** the plan's dates moved so it starts on day, same time of day and same length */
function shifted(p: MealPlan, day: DateTime) {
    const from = DateTime.fromJSDate(p.fromDate), to = DateTime.fromJSDate(p.toDate ?? p.fromDate)
    const start = day.set({hour: from.hour, minute: from.minute, second: 0, millisecond: 0})
    return {fromDate: start.toJSDate(), toDate: start.plus(to.diff(from)).toJSDate()}
}

async function put(p: MealPlan) {
    const r = await new ApiApi().apiMealPlanUpdate({id: p.id!, mealPlan: p})
    useMealPlanStore().plans.set(r.id!, r)
    return r
}

export async function movePlan(p: MealPlan, day: DateTime, copy = false) {
    if (DateTime.fromJSDate(p.fromDate).hasSame(day, 'day') && !copy) return
    const name = p.recipe?.name || p.title || 'Meal'
    const api = new ApiApi()
    try {
        if (copy) {
            const r = await api.apiMealPlanCreate({mealPlan: {...p, id: undefined, ...shifted(p, day)} as MealPlan})
            useMealPlanStore().plans.set(r.id!, r)
            undoToast.value = {text: `Copied ${name} to ${dayLabel(day)}`, undo: () => api.apiMealPlanDestroy({id: r.id!}).then(() => useMealPlanStore().plans.delete(r.id!))}
        } else {
            const before = {fromDate: p.fromDate, toDate: p.toDate}
            const r = await put({...p, ...shifted(p, day)})
            undoToast.value = {text: `Moved ${name} to ${dayLabel(day)}`, undo: () => put({...r, ...before})}
        }
    } catch (err) {
        useMessageStore().addError(copy ? ErrorMessageType.CREATE_ERROR : ErrorMessageType.UPDATE_ERROR, err)
    }
}
