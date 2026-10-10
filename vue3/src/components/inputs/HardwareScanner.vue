<template>
    <span class="d-none"></span>
</template>

<script setup lang="ts">
// home fork: a handheld Bluetooth/USB barcode scanner pairs as a keyboard and "types" the code
// much faster than a person, ending with Enter, Tab or Down Arrow (the PecuMecu sends Down
// Arrow). When such a burst arrives while no text field has focus, treat it as a scan. With a
// text field focused the scanner just types into it as usual (Same logic as in Homebox), except
// in the scan panel ([data-scan-capture]): there a full retail barcode is taken as a scan and
// the field gets back what it held before the burst, so scanning mid-edit can't garble an amount.
import {onBeforeUnmount, onMounted} from "vue";
import {inputPaused, scanned} from "@/composables/useScan";

const MAX_GAP_MS = 80
const MIN_LENGTH = 2   // pantry labels are short hex codes such as 14
const END_KEYS = new Set(['Enter', 'Tab', 'ArrowDown'])
const IDLE_MS = 150
const MIN_LENGTH_NO_END_KEY = 8

let buffer = ''
let lastKeyAt = 0
let idleTimer: ReturnType<typeof setTimeout> | undefined
let burstField: HTMLInputElement | HTMLTextAreaElement | null = null
let burstFieldValue = ''

function isEditable(el: Element | null): boolean {
    if (!el) return false
    const tag = el.tagName
    return tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || (el as HTMLElement).isContentEditable
}

/** a field in the scan panel (but not its own code box, which handles scans itself) */
function capturing(el: Element | null): boolean {
    return !!el && !!el.closest('[data-scan-capture]') && !el.closest('[data-scan-input]')
}

function restoreField(el: Element | null) {
    if (!burstField || burstField !== el) return
    burstField.value = burstFieldValue
    burstField.dispatchEvent(new Event('input', {bubbles: true}))
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
        const el = document.activeElement
        if (code.length < MIN_LENGTH) return
        if (isEditable(el)) {
            if (!capturing(el) || !/^[0-9]{8,}$/.test(code)) return
            restoreField(el)
        } else if (!/^[0-9A-Fa-f]+$/.test(code)) {
            // a short burst must look like a scan: digits (barcode) or a hex pantry label
            return
        }
        e.preventDefault()
        e.stopPropagation()
        scanned(code, 'handheld')
        return
    }
    if (e.key.length !== 1) {
        buffer = ''
        return
    }
    if (!buffer) {
        // first key of what may be a burst: remember the field as it was
        const el = document.activeElement
        burstField = el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') ? el as HTMLInputElement : null
        burstFieldValue = burstField?.value ?? ''
    }
    buffer += e.key
    idleTimer = setTimeout(() => {
        const code = buffer.trim()
        buffer = ''
        if (code.length >= MIN_LENGTH_NO_END_KEY && /^[0-9]+$/.test(code) && !isEditable(document.activeElement)) scanned(code, 'handheld')
    }, IDLE_MS)
}

function onFocusChange() {
    // focusin/out fire before activeElement settles
    setTimeout(() => {
        const el = document.activeElement
        inputPaused.value = isEditable(el) && !el!.closest('[data-scan-capture]')
    })
}

onMounted(() => {
    window.addEventListener('keydown', onKeydown, true)
    window.addEventListener('focusin', onFocusChange)
    window.addEventListener('focusout', onFocusChange)
})
onBeforeUnmount(() => {
    window.removeEventListener('keydown', onKeydown, true)
    window.removeEventListener('focusin', onFocusChange)
    window.removeEventListener('focusout', onFocusChange)
})
</script>
