<template>
    <span class="d-none"></span>
</template>

<script setup lang="ts">
// home fork: a handheld Bluetooth/USB barcode scanner pairs as a keyboard and "types" the code
// much faster than a person, ending with Enter, Tab or Down Arrow (the PecuMecu sends Down
// Arrow). When such a burst arrives while no text field has focus, treat it as a scan. With a
// text field focused the scanner just types into it as usual. (Same logic as in Homebox.)
import {onBeforeUnmount, onMounted} from "vue";
import {scanned} from "@/composables/useScan";

const MAX_GAP_MS = 80
const MIN_LENGTH = 4   // pantry labels are short hex codes
const END_KEYS = new Set(['Enter', 'Tab', 'ArrowDown'])
const IDLE_MS = 150
const MIN_LENGTH_NO_END_KEY = 8

let buffer = ''
let lastKeyAt = 0
let idleTimer: ReturnType<typeof setTimeout> | undefined

function isEditable(el: Element | null): boolean {
    if (!el) return false
    const tag = el.tagName
    return tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || (el as HTMLElement).isContentEditable
}

function onKeydown(e: KeyboardEvent) {
    clearTimeout(idleTimer)
    if (e.ctrlKey || e.metaKey || e.altKey || e.repeat) {
        buffer = ''
        return
    }
    const now = performance.now()
    if (now - lastKeyAt > MAX_GAP_MS) buffer = ''
    lastKeyAt = now

    if (END_KEYS.has(e.key)) {
        const code = buffer.trim()
        buffer = ''
        if (code.length < MIN_LENGTH || isEditable(document.activeElement)) return
        // a short burst must look like a scan: digits (barcode) or a hex pantry label
        if (!/^[0-9A-Fa-f]+$/.test(code)) return
        e.preventDefault()
        e.stopPropagation()
        scanned(code, 'handheld')
        return
    }
    if (e.key.length !== 1) {
        buffer = ''
        return
    }
    buffer += e.key
    idleTimer = setTimeout(() => {
        const code = buffer.trim()
        buffer = ''
        if (code.length >= MIN_LENGTH_NO_END_KEY && /^[0-9]+$/.test(code) && !isEditable(document.activeElement)) scanned(code, 'handheld')
    }, IDLE_MS)
}

onMounted(() => window.addEventListener('keydown', onKeydown, true))
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown, true))
</script>
