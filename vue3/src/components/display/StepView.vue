<template>
    <v-card class="step-card" :class="{'step-done': stepChecked}">
        <v-card-title class="d-flex align-center ga-3 step-title">
            <span class="step-number" v-if="props.stepNumber">{{ props.stepNumber }}</span>
            <span class="flex-grow-1 step-name" @click="hasDetails && (stepChecked = !stepChecked)">
                <span v-if="step.name">{{ step.name }}</span>
                <span v-else>{{ $t('Step') }} {{ props.stepNumber }}</span>
            </span>
            <v-btn size="small" variant="tonal" color="info" class="d-print-none" prepend-icon="fas fa-stopwatch"
                   v-if="step.time != undefined && step.time > 0" @click="timerRunning = true">{{ step.time }} min
            </v-btn>
            <v-btn size="small" variant="text" icon class="d-print-none step-check" v-if="hasDetails" @click="stepChecked = !stepChecked"
                   :title="stepChecked ? $t('Show', 'Show') : $t('Done')">
                <v-icon :icon="stepChecked ? 'fa-solid fa-circle-check' : 'fa-regular fa-circle'"></v-icon>
            </v-btn>
        </v-card-title>
        <template v-if="!stepChecked">
            <timer :seconds="step.time != undefined ? step.time*60 : 0" @stop="timerRunning = false" v-if="timerRunning"></timer>
            <v-card-text class="pt-1" v-if="step.ingredients.length > 0 || step.instruction != ''">
                <v-row>
                    <v-col :cols="(useUserPreferenceStore().isPrintMode) ? 6 : 12" md="6" v-if="step.ingredients.length > 0 && (step.showIngredientsTable || step.show_ingredients_table)">
                        <ingredients-table v-model="step.ingredients" :ingredient-factor="ingredientFactor"></ingredients-table>
                    </v-col>
                    <v-col :cols="(useUserPreferenceStore().isPrintMode) ? 6 : 12" md="6" class="markdown-body">
                        <instructions :instructions_html="step.instructionsMarkdown" :ingredient_factor="ingredientFactor"
                                      v-if="step.instructionsMarkdown != undefined"></instructions>
                        <!-- sub recipes dont have a correct schema, thus they use different variable naming -->
                        <instructions :instructions_html="step.instructions_markdown" :ingredient_factor="ingredientFactor" v-else></instructions>
                    </v-col>
                </v-row>
            </v-card-text>

            <template v-if="step.stepRecipe">
                <v-card class="ma-2 border-md">
                    <v-card-title>
                        <v-icon icon="$recipes"></v-icon>
                        {{ step.stepRecipeData.name }}
                        <v-btn icon="fa-solid fa-up-right-from-square" size="x-small" :to="{name: 'RecipeViewPage', params: {id: step.stepRecipeData.id}}" target="_blank" variant="plain"></v-btn>
                    </v-card-title>
                    <v-card-text class="mt-1" v-for="(subRecipeStep, subRecipeStepIndex) in step.stepRecipeData.steps" :key="subRecipeStep.id">
                        <step-view v-model="step.stepRecipeData.steps[subRecipeStepIndex]" :step-number="subRecipeStepIndex+1" :ingredientFactor="ingredientFactor"></step-view>
                    </v-card-text>
                </v-card>
            </template>
            <template v-if="step.file">
                <!-- home fork: a step photo at a readable size, not full width -->
                <v-img :src="step.file.preview" v-if="step.file.preview" class="step-photo" max-height="380" cover rounded="lg"></v-img>
                <a :href="step.file.fileDownload" v-else>{{ $t('Download') }}</a>
            </template>
        </template>

    </v-card>
</template>

<script setup lang="ts">
import {computed, defineComponent, PropType, ref} from 'vue'
import IngredientsTable from "@/components/display/IngredientsTable.vue";
import {Step} from "@/openapi";

import Instructions from "@/components/display/Instructions.vue";
import Timer from "@/components/display/Timer.vue";
import {useUserPreferenceStore} from "@/stores/UserPreferenceStore.ts";

const step = defineModel<Step>({required: true})

const props = defineProps({
    stepNumber: {
        type: Number,
        required: false,
        default: 1
    },
    ingredientFactor: {
        type: Number,
        required: true,
    },
})

const timerRunning = ref(false)
const stepChecked = ref(false)

const hasDetails = computed(() => {
    return step.value.ingredients.length > 0 || (step.value.instruction != undefined && step.value.instruction.length > 0) || step.value.stepRecipeData != undefined || step.value.file != undefined
})

</script>

<style scoped>

</style>