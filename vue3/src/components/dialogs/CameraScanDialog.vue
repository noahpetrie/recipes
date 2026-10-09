<template>
    <!-- home fork: scan a product barcode with the camera (zxing-cpp via barcode-detector, as in Homebox) -->
    <v-dialog v-model="cameraOpen" max-width="520">
        <v-card>
            <v-closable-card-title v-model="cameraOpen" :title="$t('HomeScanBarcode', 'Scan a barcode')" icon="fa-solid fa-barcode"></v-closable-card-title>
            <v-divider></v-divider>
            <v-card-text>
                <div class="scan-frame">
                    <video ref="video" autoplay muted playsinline></video>
                    <div class="scan-guide"></div>
                    <div v-if="starting" class="scan-msg">{{ $t('HomeStartingCamera', 'Starting camera…') }}</div>
                </div>
                <v-alert v-if="error" type="warning" variant="tonal" density="compact" class="mt-3">{{ error }}</v-alert>
                <div class="d-flex align-center ga-2 mt-3">
                    <v-select v-if="cameras.length > 1" v-model="cameraId" :items="cameras" item-title="label" item-value="deviceId"
                              :label="$t('HomeCamera', 'Camera')" hide-details class="flex-grow-1"></v-select>
                    <p v-else class="text-body-2 text-medium-emphasis flex-grow-1 mb-0">
                        {{ $t('HomeScanHint', 'Hold the barcode inside the frame. A handheld scanner works anywhere in Kitchen too.') }}
                    </p>
                </div>
            </v-card-text>
        </v-card>
    </v-dialog>
</template>

<script setup lang="ts">
import {nextTick, onBeforeUnmount, ref, watch} from "vue";
import {BarcodeDetector, prepareZXingModule} from "barcode-detector";
import {useI18n} from "vue-i18n";
import VClosableCardTitle from "@/components/dialogs/VClosableCardTitle.vue";
import {cameraOpen, scanned} from "@/composables/useScan";

const {t} = useI18n()

const FORMATS = ['ean_13', 'ean_8', 'upc_a', 'upc_e', 'code_128', 'qr_code']
const SCAN_INTERVAL_MS = 120
const CAMERA_KEY = 'kitchen:scannerCameraId'

const video = ref<HTMLVideoElement>()
const starting = ref(false)
const error = ref('')
const cameras = ref<MediaDeviceInfo[]>([])
const cameraId = ref<string | null>(null)

let detector: BarcodeDetector | null = null
let stream: MediaStream | null = null
let timer: ReturnType<typeof setTimeout> | null = null
let session = 0
let lastCode = ''

// iPhones list many cameras; the virtual multi-lens ones switch to macro up close, which suits barcodes
function cameraScore(label: string): number {
    const l = label.toLowerCase()
    if (l.includes('front')) return 0
    if (l.includes('triple')) return 6
    if (l.includes('dual wide')) return 5
    if (l.includes('dual')) return 4
    if (l.includes('telephoto') || l.includes('ultra')) return 1
    if (l.includes('back') || l.includes('rear') || l.includes('environment')) return 3
    return 2
}

function stopStream() {
    session++
    if (timer) clearTimeout(timer)
    timer = null
    stream?.getTracks().forEach(tr => tr.stop())
    stream = null
    if (video.value) video.value.srcObject = null
}

async function start() {
    error.value = ''
    lastCode = ''
    if (!navigator.mediaDevices?.getUserMedia) {
        error.value = t('HomeCameraUnsupported', 'This browser can’t use the camera here (it needs https).')
        return
    }
    starting.value = true
    prepareZXingModule({fireImmediately: true}).catch(e => console.warn('zxing preload failed', e))
    try {
        const probe = await navigator.mediaDevices.getUserMedia({video: {facingMode: {ideal: 'environment'}}})
        probe.getTracks().forEach(tr => tr.stop())
        const devices = (await navigator.mediaDevices.enumerateDevices()).filter(d => d.kind === 'videoinput')
        cameras.value = devices
        let saved: string | null = null
        try { saved = localStorage.getItem(CAMERA_KEY) } catch (e) { /* private mode */ }
        const best = [...devices].sort((a, b) => cameraScore(b.label) - cameraScore(a.label))[0]
        const pick = devices.find(d => d.deviceId === saved)?.deviceId ?? best?.deviceId ?? null
        if (cameraId.value === pick) await openCamera(pick)
        else cameraId.value = pick
    } catch (e: any) {
        starting.value = false
        error.value = e?.name === 'NotAllowedError'
            ? t('HomeCameraDenied', 'Camera access was blocked. Allow it in the browser’s site settings, or use the handheld scanner.')
            : t('HomeCameraError', 'Couldn’t start the camera.')
    }
}

async function openCamera(id: string | null) {
    stopStream()
    const mySession = session
    starting.value = true
    try {
        stream = await navigator.mediaDevices.getUserMedia({
            video: id ? {deviceId: {exact: id}, width: {ideal: 1920}, height: {ideal: 1080}} : {facingMode: {ideal: 'environment'}},
        })
        if (mySession !== session) return stream.getTracks().forEach(tr => tr.stop())
        await nextTick()
        if (video.value) {
            video.value.srcObject = stream
            await video.value.play().catch(() => {})
        }
        detector = detector ?? new BarcodeDetector({formats: FORMATS as any})
        starting.value = false
        loop(mySession)
    } catch (e) {
        starting.value = false
        error.value = t('HomeCameraError', 'Couldn’t start the camera.')
    }
}

async function loop(mySession: number) {
    if (mySession !== session) return
    const el = video.value
    if (detector && el && el.readyState >= 2) {
        try {
            const found = await detector.detect(el)
            if (mySession !== session) return
            const hit = found[0]
            if (hit) {
                // two matching reads in a row, so a half-seen barcode can't slip through
                if (hit.rawValue === lastCode) {
                    navigator.vibrate?.(60)
                    stopStream()
                    cameraOpen.value = false
                    scanned(hit.rawValue, 'camera')
                    return
                }
                lastCode = hit.rawValue
            }
        } catch (e) {
            console.debug('detect failed', e)
        }
    }
    if (mySession === session) timer = setTimeout(() => loop(mySession), SCAN_INTERVAL_MS)
}

watch(cameraOpen, open => open ? start() : stopStream())
watch(cameraId, (id, old) => {
    if (!cameraOpen.value) return
    if (old != null) {
        try { if (id) localStorage.setItem(CAMERA_KEY, id) } catch (e) { /* private mode */ }
    }
    openCamera(id)
})
onBeforeUnmount(stopStream)
</script>

<style scoped>
.scan-frame {
    position: relative;
    aspect-ratio: 4 / 3;
    border-radius: 10px;
    overflow: hidden;
    background: #111;
}

.scan-frame video {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
}

.scan-guide {
    position: absolute;
    inset: 30% 12%;
    border: 2px solid rgba(255, 255, 255, 0.85);
    border-radius: 10px;
    box-shadow: 0 0 0 9999px rgba(0, 0, 0, 0.25);
}

.scan-msg {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #fff;
    font-size: 0.875rem;
}
</style>
