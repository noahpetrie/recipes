// home fork: "have I made this?" comes from the cook log (lastCooked); marking it made adds a cook log entry
import {ApiApi, CookLog, Recipe, RecipeOverview} from "@/openapi";
import {ErrorMessageType, MessageType, useMessageStore} from "@/stores/MessageStore";

export async function markMade(recipe: Recipe | RecipeOverview, servings?: number) {
    try {
        const log = await new ApiApi().apiCookLogCreate({
            cookLog: {recipe: recipe.id!, servings: servings ?? recipe.servings, createdAt: new Date()} as CookLog
        })
        ;(recipe as any).lastCooked = log.createdAt ?? new Date()
        useMessageStore().addMessage(MessageType.SUCCESS, `Marked ${recipe.name} as made.`, 3000)
        return log
    } catch (err) {
        useMessageStore().addError(ErrorMessageType.CREATE_ERROR, err)
    }
}
