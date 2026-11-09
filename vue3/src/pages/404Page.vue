<script setup lang="ts">

</script>

<template>
    <v-container class="nf-page">
        <div class="nf">
            <span class="nf__icon"><v-icon icon="fa-solid fa-compass" /></span>
            <h1 class="nf__title">Page not found</h1>
            <p class="home-muted text-body-2">There’s nothing at this address. It may have moved, or the link is wrong.</p>
            <div class="d-flex flex-wrap justify-center ga-2 mt-5">
                <v-btn color="primary" variant="flat" prepend-icon="fa-solid fa-house" :to="{name: 'StartPage'}">{{ $t('Home') }}</v-btn>
                <v-btn variant="outlined" prepend-icon="fa-solid fa-arrow-left" @click="$router.back()">{{ $t('Back') }}</v-btn>
            </div>
        </div>
    </v-container>
</template>

<style scoped>
.nf-page {
    min-height: calc(100vh - 160px);
    display: flex;
    align-items: center;
    justify-content: center;
}

.nf {
    text-align: center;
    max-width: 420px;
}

.nf__icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 52px;
    height: 52px;
    border-radius: 14px;
    background: rgba(var(--v-theme-primary), 0.10);
    color: rgb(var(--v-theme-primary));
    font-size: 22px;
    margin-bottom: 16px;
}

.nf__title {
    font-family: var(--home-display-font);
    font-size: 1.75rem;
    font-weight: 700;
    letter-spacing: -0.02em;
    margin-bottom: 6px;
}
</style>