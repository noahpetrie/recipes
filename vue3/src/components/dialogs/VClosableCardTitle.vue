<template>
    <v-card-title class="home-dialog-title">
        <div class="home-dialog-title__text">
            <slot name="content">
                <div class="home-dialog-title__main">
                    <span v-if="props.icon != ''" class="home-dialog-title__icon"><i :class="props.icon"></i></span>
                    <span class="text-truncate">{{ props.title }}</span>
                </div>
                <v-card-subtitle class="pa-0" v-if="props.subTitle != ''">{{ props.subTitle }}</v-card-subtitle>
            </slot>
        </div>
        <v-btn class="home-dialog-title__close" icon="$close" variant="text" size="small" density="comfortable" :aria-label="$t('Close')"
               @click="model = false; emit('close')" v-if="!props.hideClose"></v-btn>
    </v-card-title>
</template>

<script setup lang="ts">
/**
 * Component used to render a VCardTitle with a "close" button that can either close the model bound dialog given via v-model or
 * emit a close event a parent dialog can listen to
 *
 * Should be used for all dialogs that have a "close" function (which likely all dialogs should have)
 */
const emit = defineEmits(['close'])

const props = defineProps({
    title: {type: String, default: ''},
    icon: {type: String, default: ''},
    subTitle: {type: String, default: ''},
    hideClose: {type: Boolean, default: false},
})

const model = defineModel<Boolean>()

</script>

<style scoped>
.home-dialog-title {
    display: flex;
    align-items: flex-start;
    gap: 8px;
}

.home-dialog-title__text {
    flex: 1 1 auto;
    min-width: 0;
    padding-top: 4px;
}

.home-dialog-title__main {
    display: flex;
    align-items: center;
    gap: 10px;
    min-width: 0;
}

/* the icon in a small tinted chip, like the page headers */
.home-dialog-title__icon {
    flex: 0 0 auto;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 28px;
    height: 28px;
    border-radius: 8px;
    background: rgba(var(--v-theme-primary), 0.10);
    color: rgb(var(--v-theme-primary));
    font-size: 13px;
}

.home-dialog-title__close {
    flex: 0 0 auto;
    margin: -2px -6px 0 0;
}
</style>