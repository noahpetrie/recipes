// home fork: days away are a meal plan entry with the "Away" meal type (created the first time it's used),
// spanning the trip, with the place as its title. Older entries titled "Traveling" etc. count too.
import {ApiApi, MealPlan, MealType} from '@/openapi'
import {useMealPlanStore} from '@/stores/MealPlanStore'

export const AWAY_TYPE = 'Away'
// same words the restock suggestions use (cookbook/views/home_restock.py)
const AWAY_WORDS = /travel|away|trip|vacation|holiday|cottage|out of town/i

export function isAway(plan: MealPlan): boolean {
    return plan.mealType?.name == AWAY_TYPE || (!plan.recipe && AWAY_WORDS.test(plan.title || ''))
}

/** what an away day shows after "Away": the place, unless the title is just a word like "Away" or "Traveling" */
export function awayPlace(plan: MealPlan): string {
    const t = (plan.title || '').trim()
    return !t || /^(away|travell?ing|trip|vacation|holiday)$/i.test(t) ? '' : t
}

async function awayType(): Promise<MealType> {
    const api = new ApiApi()
    const found = (await api.apiMealTypeList({pageSize: 100})).results.find(t => t.name.toLowerCase() == AWAY_TYPE.toLowerCase())
    if (found) return found
    return api.apiMealTypeCreate({mealType: {name: AWAY_TYPE, color: '#8D99AE', order: 99} as MealType})
}

export async function markAway(from: Date, to: Date, place: string) {
    const mealType = await awayType()
    return useMealPlanStore().createObject({title: place.trim() || AWAY_TYPE, fromDate: from, toDate: to, mealType, servings: 1} as MealPlan)
}
