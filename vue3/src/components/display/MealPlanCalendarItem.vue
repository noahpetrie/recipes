<template>
    <v-card class="card cv-item pa-0" hover
            :style="{'top': itemTop, 'height': itemHeight, 'border-color': mealPlan.mealType.color}"
            :draggable="true"
            :key="value.id"
            @dragstart="emit('onDragStart', value, $event)"
            @contextmenu="onContextMenu"
            :class="value.classes">
        <v-card-text class="pa-0">
            <div class="d-flex flex-row align-items-center">
                <div class="flex-column" v-if="detailedItems">
                    <recipe-image :height="itemHeight" :width="itemHeight" :recipe="mealPlan.recipe"></recipe-image>
                </div>
                <div class="flex-column flex-grow-1 pa-1 cal-item-text">
                    <span class="font-light" :class="{'three-line-text': detailedItems,'one-line-text': !detailedItems,}">
                       <i class="fas fa-shopping-cart fa-xs float-left" v-if="mealPlan.shopping"/>
                        {{ itemTitle }}
                    </span>
                </div>
            </div>
            <model-edit-dialog model="MealPlan" :item="mealPlan" @delete="(args: MealPlan) => emit('delete', args)"></model-edit-dialog>
        </v-card-text>
    </v-card>
    <!-- home: right-click a planned meal for the same menu as on the home page -->
    <meal-plan-context-menu ref="contextMenu" :plan="mealPlan" hide-button></meal-plan-context-menu>
</template>

<script setup lang="ts">

import {computed, PropType, ref} from "vue";
import MealPlanContextMenu from "@/components/inputs/MealPlanContextMenu.vue";
import {IMealPlanNormalizedCalendarItem} from "@/types/MealPlan";
import RecipeImage from "@/components/display/RecipeImage.vue";
import ModelEditDialog from "@/components/dialogs/ModelEditDialog.vue";
import {MealPlan} from "@/openapi";

const emit = defineEmits({
    onDragStart: (value: IMealPlanNormalizedCalendarItem, event: DragEvent) => {
        return true
    },
    delete: (value: MealPlan) => {
        return true
    }
})

let props = defineProps({
    value: {type: {} as PropType<IMealPlanNormalizedCalendarItem>, required: true},
    itemHeight: {type: String,},
    itemTop: {type: String,},
    detailedItems: {type: Boolean, default: true}
})

const contextMenu = ref<InstanceType<typeof MealPlanContextMenu> | null>(null)

function onContextMenu(e: MouseEvent) {
    if (e.shiftKey || !contextMenu.value) return
    e.preventDefault()
    e.stopPropagation()
    contextMenu.value.openAt(e)
}

const mealPlan = computed(() => {
    return props.value.originalItem.mealPlan
})

const itemTitle = computed(() => {
    if (mealPlan.value.recipe != undefined) {
        return mealPlan.value.recipe.name
    } else if (mealPlan.value.title != null && mealPlan.value.title !== "") {
        return mealPlan.value.title
    } else {
        return 'ERROR'
    }
})


</script>

<style scoped>
/* home: let long recipe names wrap instead of running off the card */
.cal-item-text {
    min-width: 0;
    white-space: normal;
    overflow-wrap: anywhere;
    line-height: 1.25;
}

.two-line-text {
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
}

.one-line-text {
    display: -webkit-box;
    -webkit-line-clamp: 1;
    -webkit-box-orient: vertical;
    width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
}

.three-line-text {
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
}
</style>
