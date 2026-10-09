<template>
    <!-- home fork: one panel for pantry scanning. A scan finds the product or labelled item and shows
         what's on hand; stock only changes through the action chosen below it (Add, Count, Use, Move). -->
    <v-dialog v-model="scanPanel.open" max-width="640" :fullscreen="xs" scrollable class="psp-dialog">
        <v-card class="psp" ref="panelCard">
            <!-- header -->
            <div class="psp-head">
                <div class="d-flex align-center ga-2">
                    <v-icon icon="fa-solid fa-barcode" size="small" class="opacity-60"></v-icon>
                    <span class="psp-title">{{ $t('HomeScan', 'Scan') }}</span>
                    <v-spacer></v-spacer>
                    <v-btn icon="$close" variant="text" size="small" :aria-label="$t('Close')" @click="scanPanel.open = false"></v-btn>
                </div>
                <div class="psp-modes" role="tablist" :aria-label="$t('HomeScanMode', 'What scanning does')">
                    <button v-for="m in modes" :key="m.value" type="button" role="tab" :aria-selected="scanPanel.mode == m.value"
                            :class="{active: scanPanel.mode == m.value}" @click="setMode(m.value)">
                        <v-icon :icon="m.icon" size="x-small" class="me-1"></v-icon>{{ m.title }}
                    </button>
                </div>
                <p class="psp-mode-help">{{ modeHelp }}</p>

                <!-- the scan input: a handheld scanner types here (or anywhere outside a text box) -->
                <div class="d-flex align-center ga-2">
                    <v-text-field ref="codeInput" v-model="codeText" hide-details :placeholder="$t('HomeScanOrType', 'Scan or type a barcode')"
                                  prepend-inner-icon="fa-solid fa-barcode" autocomplete="off" inputmode="numeric" class="flex-grow-1"
                                  :aria-label="$t('HomeBarcode', 'Barcode')" @keydown="onCodeKey"></v-text-field>
                    <v-btn variant="outlined" icon="fa-solid fa-camera" :aria-label="$t('HomeScanWithCamera', 'Scan with the camera')" @click="cameraOpen = true"></v-btn>
                </div>

                <!-- restock / count context -->
                <div v-if="scanPanel.mode == 'restock'" class="psp-context">
                    <span>{{ $t('HomeAddingTo', 'Adding to') }}</span>
                    <v-select v-model="restockLocationId" :items="locations" item-title="name" item-value="id" hide-details density="compact" class="psp-inline-select"></v-select>
                    <v-spacer></v-spacer>
                    <v-switch v-model="quickAdd" hide-details density="compact" color="primary" :label="$t('HomeQuickAdd', 'Quick add 1 per scan')"></v-switch>
                </div>
                <div v-if="scanPanel.mode == 'count'" class="psp-context">
                    <template v-if="count">
                        <span>{{ $t('HomeCounting', 'Counting') }} <b>{{ count.location.name }}</b> · {{ count.counted }} {{ $t('HomeCountedLower', 'counted') }}<template v-if="count.discrepancies"> · {{ count.discrepancies }} {{ $t('HomeDifferent', 'different') }}</template></span>
                        <v-spacer></v-spacer>
                        <v-switch v-model="countRepeat" hide-details density="compact" color="primary" :label="$t('HomeEachScanAddsOne', 'Each scan adds 1')"></v-switch>
                        <v-btn size="small" variant="outlined" :to="{name: 'StockCountPage', params: {id: count.id}}" @click="scanPanel.open = false">{{ $t('HomeReview', 'Review') }}</v-btn>
                    </template>
                </div>
            </div>
            <v-divider></v-divider>

            <v-card-text class="psp-body">
                <!-- count mode needs a count first -->
                <div v-if="scanPanel.mode == 'count' && !count" class="psp-empty">
                    <div class="psp-section-title mt-0">{{ $t('HomeStartCount', 'Start a stock count') }}</div>
                    <p class="text-body-2 text-medium-emphasis">{{ $t('HomeStartCountHelp', 'Scan each product in one place and enter how many you actually have. Nothing changes until you review and apply the count. Products you don’t scan are left alone.') }}</p>
                    <div class="d-flex ga-2 align-center">
                        <v-select v-model="countLocationId" :items="locations" item-title="name" item-value="id" :label="$t('HomeWhere', 'Where')" hide-details class="flex-grow-1"></v-select>
                        <v-btn color="primary" variant="flat" :disabled="!countLocationId" :loading="busy" @click="startCount">{{ $t('HomeStart', 'Start') }}</v-btn>
                    </div>
                    <div v-if="openCounts.length" class="mt-4">
                        <div class="psp-section-title">{{ $t('HomeOpenCounts', 'Counts in progress') }}</div>
                        <div v-for="c in openCounts" :key="c.id" class="psp-row">
                            <span class="flex-grow-1">{{ c.location.name }} · {{ c.counted }} {{ $t('HomeCountedLower', 'counted') }} · {{ fmtDate(c.created_at) }}</span>
                            <v-btn size="small" variant="outlined" @click="resumeCount(c.id)">{{ $t('HomeResume', 'Resume') }}</v-btn>
                        </div>
                    </div>
                </div>

                <!-- nothing scanned yet -->
                <div v-else-if="state == 'idle'" class="psp-empty">
                    <p class="text-body-2 text-medium-emphasis mb-3">{{ idleHelp }}</p>
                    <label class="psp-label">{{ $t('HomeNoBarcode', 'No barcode? Find a food') }}</label>
                    <v-model-select model="Food" v-model="pickFood" hide-details @update:model-value="f => f && showFood(f.id)"></v-model-select>
                </div>

                <div v-else-if="state == 'loading'" class="psp-empty text-center py-8" aria-live="polite">
                    <v-progress-circular indeterminate size="22" width="2" class="mb-2"></v-progress-circular>
                    <div class="text-body-2 text-medium-emphasis">{{ $t('HomeLookingUpProduct', 'Looking up product…') }}</div>
                </div>

                <!-- something to fix about the scan itself -->
                <v-alert v-else-if="state == 'error'" type="warning" variant="tonal" density="compact" class="mb-2" role="alert">
                    {{ error }}
                    <div class="text-body-2 mt-1">{{ $t('HomeScanAgainOrType', 'Scan again, or type the number under the barcode.') }}</div>
                </v-alert>

                <!-- a code that is both a label and a product barcode -->
                <div v-else-if="state == 'ambiguous'" class="psp-empty">
                    <p class="mb-3">{{ $t('HomeAmbiguous', 'This code is both a pantry label and a product barcode. Which did you scan?') }}</p>
                    <div class="d-flex ga-2 flex-wrap">
                        <v-btn variant="outlined" @click="state = 'label'">{{ $t('HomeTheLabel', 'The label on') }} #{{ result.label_entry.code }}</v-btn>
                        <v-btn variant="outlined" @click="state = 'product'">{{ result.food.name }} ({{ $t('HomeProduct', 'product') }})</v-btn>
                    </div>
                </div>

                <!-- unknown product: say which food it is (remembered for next time) -->
                <template v-else-if="state == 'unknown'">
                    <div class="psp-product">
                        <div class="psp-thumb">
                            <img v-if="result.product?.image" :src="result.product.image" alt="">
                            <v-icon v-else icon="fa-solid fa-jar" class="opacity-40"></v-icon>
                        </div>
                        <div class="min-w-0 flex-grow-1">
                            <div class="psp-name">{{ result.product?.name ?? $t('HomeUnknownProduct', 'Unknown product') }}</div>
                            <div class="psp-meta">{{ [result.product?.brand, result.product?.quantity].filter(Boolean).join(' · ') || $t('HomeNotFoundOnline', 'Not found in the online product databases.') }}</div>
                            <div class="psp-code">{{ result.code }}</div>
                        </div>
                    </div>
                    <div class="psp-section-title">{{ $t('HomeWhichFood', 'Which food is this?') }}</div>
                    <p class="text-body-2 text-medium-emphasis mb-3">{{ $t('HomeWhichFoodHelp', 'Kitchen will remember this barcode, so next time it goes straight to the food.') }}</p>
                    <div class="psp-fields">
                        <div>
                            <label class="psp-label">{{ $t('HomeNewFood', 'Create a new food') }}</label>
                            <v-text-field v-model="newName" :disabled="!!linkFood" hide-details :placeholder="$t('Name')" @keydown.enter="linkBarcode"></v-text-field>
                        </div>
                        <div class="psp-or"><span>{{ $t('or') }}</span></div>
                        <div>
                            <label class="psp-label">{{ $t('HomeExistingFood', 'Use a food you already have') }}</label>
                            <v-model-select model="Food" v-model="linkFood" hide-details></v-model-select>
                        </div>
                    </div>
                    <div class="d-flex justify-end mt-4">
                        <v-btn color="primary" variant="flat" :loading="busy" :disabled="!linkFood && !newName.trim()" @click="linkBarcode">{{ $t('HomeSaveAndContinue', 'Save and continue') }}</v-btn>
                    </div>
                </template>

                <!-- a product, or one labelled item -->
                <template v-else-if="(state == 'product' || state == 'label') && result">
                    <div class="psp-product">
                        <div class="psp-thumb">
                            <img v-if="product?.image" :src="product.image" alt="">
                            <v-icon v-else icon="fa-solid fa-jar" class="opacity-40"></v-icon>
                        </div>
                        <div class="min-w-0 flex-grow-1">
                            <div class="psp-name">{{ result.food.name }}</div>
                            <div class="psp-meta">{{ [product?.brand, product?.quantity && `${product.quantity} ${$t('HomePerPackage', 'per package')}`].filter(Boolean).join(' · ') }}</div>
                            <div v-if="result.food.barcodes?.length" class="psp-code">{{ result.food.barcodes.join(', ') }}</div>
                        </div>
                        <v-btn v-if="result.code && state == 'product'" size="small" variant="text" @click="changeProduct">{{ $t('HomeChange', 'Change') }}</v-btn>
                    </div>

                    <!-- the one item behind a scanned label -->
                    <div v-if="state == 'label' && labelEntry" class="psp-item">
                        <div class="psp-section-title mt-0">{{ $t('HomeLabelledItem', 'Labelled item') }} #{{ labelEntry.code }}</div>
                        <div class="psp-batch">
                            <div class="flex-grow-1 min-w-0">
                                <div class="font-weight-medium">{{ qty(labelEntry.amount, labelEntry.unit) }}</div>
                                <div class="psp-meta">{{ where(labelEntry) }}</div>
                            </div>
                            <span v-if="labelEntry.expires" class="psp-expiry" :class="expiryClass(labelEntry.expires)">{{ expiryText(labelEntry.expires) }}</span>
                        </div>
                        <div v-if="labelEntry.amount == 0" class="text-body-2 text-medium-emphasis mt-1">{{ $t('HomeUsedUp', 'This item is used up.') }}</div>
                    </div>

                    <!-- what's on hand -->
                    <div class="psp-stock" aria-live="polite">
                        <template v-if="stock.totals.length">
                            <div class="psp-total">
                                <span v-for="(t, i) in stock.totals" :key="i">{{ qty(t.amount, t.unit) }}<template v-if="i < stock.totals.length - 1"> + </template></span>
                                <span class="psp-total-sub">{{ stock.locations.length > 1 ? $t('HomeAcrossLocations', {n: stock.locations.length}, 'across {n} places') : $t('HomeOnHand', 'on hand') }}</span>
                            </div>
                            <div class="psp-locs">
                                <span v-for="l in stock.locations" :key="l.location.id" class="psp-chip">
                                    <v-icon v-if="l.location.is_freezer" icon="fa-solid fa-snowflake" size="x-small" class="me-1"></v-icon>
                                    {{ l.location.name }} {{ l.totals.map(t => qty(t.amount, t.unit)).join(' + ') }}
                                </span>
                            </div>
                            <p v-if="stock.mixed_units" class="psp-warn"><v-icon icon="fa-solid fa-circle-info" size="x-small" class="me-1"></v-icon>{{ $t('HomeMixedUnits', 'Counted in different units, so they’re shown separately rather than added up.') }}</p>
                            <p v-if="stock.expired" class="psp-warn text-error"><v-icon icon="fa-solid fa-triangle-exclamation" size="x-small" class="me-1"></v-icon>{{ $t('HomeExpiredBatches', {n: stock.expired}, '{n} batch(es) past their date') }}</p>
                            <details class="psp-batches" :open="stock.batches.length > 1 && stock.batches.length <= 4">
                                <summary>{{ $t('HomeBatches', 'Batches') }} ({{ stock.batches.length }})</summary>
                                <div v-for="b in stock.batches" :key="b.id" class="psp-batch">
                                    <div class="flex-grow-1 min-w-0">
                                        <div>{{ qty(b.amount, b.unit) }} <span class="psp-meta">· #{{ b.code }}</span></div>
                                        <div class="psp-meta">{{ where(b) }}<template v-if="b.counted_at"> · {{ $t('HomeCounted', 'counted') }} {{ fmtDate(b.counted_at) }}</template></div>
                                    </div>
                                    <span v-if="b.expires" class="psp-expiry" :class="expiryClass(b.expires)">{{ expiryText(b.expires) }}</span>
                                    <v-btn size="small" variant="text" icon="fa-solid fa-ellipsis" :aria-label="$t('HomeBatchDetails', 'Batch details')" @click="openBatch(b)"></v-btn>
                                </div>
                            </details>
                        </template>
                        <div v-else class="d-flex align-center flex-wrap ga-2">
                            <div class="psp-total psp-none flex-grow-1">{{ $t('HomeNotStocked', 'Not currently stocked') }}</div>
                            <v-btn size="small" variant="outlined" prepend-icon="fa-solid fa-cart-shopping" :loading="shopping" @click="addToShopping">{{ $t('HomeAddToShopping', 'Add to shopping list') }}</v-btn>
                        </div>
                    </div>

                    <!-- count mode: record a count (a draft until reviewed) -->
                    <div v-if="scanPanel.mode == 'count' && count" class="psp-form">
                        <div class="psp-form-title">{{ $t('HomeHowManyHere', {place: count.location.name}, 'How many do you have in {place}?') }}</div>
                        <div class="d-flex align-center ga-2 flex-wrap">
                            <div class="psp-stepper">
                                <v-btn icon="fa-solid fa-minus" variant="text" size="small" :disabled="countValue <= 0" @click="countValue = Math.max(0, countValue - 1)"></v-btn>
                                <input v-model.number="countValue" type="number" min="0" step="any" inputmode="decimal" :aria-label="$t('HomeCountedAmount', 'Counted amount')" @keydown.enter.prevent="saveCountLine()">
                                <v-btn icon="fa-solid fa-plus" variant="text" size="small" @click="countValue++"></v-btn>
                            </div>
                            <v-select v-model="countUnitId" :items="unitItems" item-title="title" item-value="value" hide-details density="compact" class="psp-unit"></v-select>
                        </div>
                        <p class="psp-preview">{{ $t('HomeOnFile', 'On file') }} {{ qty(countRecorded, unitById(countUnitId)) }} → {{ $t('HomeCounted', 'counted') }} {{ qty(countValue, unitById(countUnitId)) }}
                            <b :class="countValue - countRecorded == 0 ? '' : (countValue > countRecorded ? 'text-success' : 'text-error')">({{ deltaText(countValue - countRecorded) }})</b>
                        </p>
                        <div class="d-flex justify-end">
                            <v-btn color="primary" variant="flat" :loading="busy" @click="saveCountLine">{{ $t('HomeSaveCount', 'Save count') }}</v-btn>
                        </div>
                    </div>

                    <!-- actions -->
                    <template v-else>
                        <div class="psp-actions" role="tablist">
                            <button v-for="a in actions" :key="a.value" type="button" role="tab" :aria-selected="tab == a.value" :class="{active: tab == a.value}"
                                    :disabled="a.disabled" @click="selectTab(a.value)">
                                <v-icon :icon="a.icon" size="x-small" class="me-1"></v-icon>{{ a.title }}
                            </button>
                        </div>

                        <!-- Add -->
                        <div v-if="tab == 'add'" class="psp-form">
                            <div class="psp-form-title">{{ $t('HomeHowManyAdding', 'How many are you adding?') }}</div>
                            <div class="d-flex align-center ga-2 flex-wrap">
                                <div class="psp-stepper">
                                    <v-btn icon="fa-solid fa-minus" variant="text" size="small" :disabled="addAmount <= 1" @click="addAmount = Math.max(1, addAmount - 1)"></v-btn>
                                    <input v-model.number="addAmount" type="number" min="0" step="any" inputmode="decimal" :aria-label="$t('Amount')" @keydown.enter.prevent="doAdd">
                                    <v-btn icon="fa-solid fa-plus" variant="text" size="small" @click="addAmount++"></v-btn>
                                </div>
                                <v-select v-model="addUnitId" :items="unitItems" item-title="title" item-value="value" hide-details density="compact" class="psp-unit"></v-select>
                                <span class="text-body-2 text-medium-emphasis">{{ $t('HomeTo', 'to') }}</span>
                                <v-select v-model="addLocationId" :items="locations" item-title="name" item-value="id" hide-details density="compact" class="psp-unit"></v-select>
                            </div>
                            <div class="d-flex align-center ga-2 mt-3 flex-wrap">
                                <label class="psp-label mb-0">{{ $t('HomeBestBefore', 'Best before') }}</label>
                                <input v-model="addExpires" type="date" class="psp-date" :aria-label="$t('HomeBestBefore', 'Best before')">
                                <span class="text-body-2 text-medium-emphasis">{{ $t('HomeOptional', 'optional') }}</span>
                            </div>
                            <details class="psp-more">
                                <summary>{{ $t('HomeMoreDetails', 'More details') }}</summary>
                                <div class="psp-fields mt-2">
                                    <v-text-field v-model="addShelf" :label="$t('HomeShelf', 'Shelf or bin')" hide-details></v-text-field>
                                    <v-text-field v-model="addCode" :label="$t('HomeLabelCode', 'Label code (optional)')" persistent-hint
                                                  :hint="$t('HomeLabelCodeHelp', 'For one item you’ll put a label on. Leave empty and Kitchen makes one.')"></v-text-field>
                                    <v-checkbox v-model="addNewBatch" hide-details density="compact" :label="$t('HomeSeparateBatch', 'Keep as a separate batch')"></v-checkbox>
                                </div>
                            </details>
                            <p class="psp-preview">
                                {{ addTargetText }} · {{ locName(addLocationId) }} {{ qty(addHere, unitById(addUnitId)) }} → {{ qty(addHere + (addAmount || 0), unitById(addUnitId)) }}
                                <b class="text-success">(+{{ fmtAmount(addAmount || 0) }})</b>
                            </p>
                            <div class="d-flex justify-end ga-2">
                                <v-btn color="create" variant="flat" :loading="busy" :disabled="!(addAmount > 0) || !addLocationId" @click="doAdd">
                                    {{ scanPanel.mode == 'restock' ? $t('HomeAddAndScanNext', 'Add & scan next') : $t('HomeAddN', {q: qty(addAmount || 0, unitById(addUnitId))}, 'Add {q}') }}
                                </v-btn>
                            </div>
                        </div>

                        <!-- Count / correct -->
                        <div v-if="tab == 'count'" class="psp-form">
                            <div class="psp-form-title">{{ $t('HomeHowManyHave', 'How many do you physically have?') }}</div>
                            <div class="d-flex align-center ga-2 flex-wrap">
                                <span class="text-body-2">{{ $t('HomeIn', 'In') }}</span>
                                <v-select v-model="setLocationId" :items="locations" item-title="name" item-value="id" hide-details density="compact" class="psp-unit"></v-select>
                                <div class="psp-stepper">
                                    <v-btn icon="fa-solid fa-minus" variant="text" size="small" :disabled="setValue <= 0" @click="setValue = Math.max(0, setValue - 1)"></v-btn>
                                    <input v-model.number="setValue" type="number" min="0" step="any" inputmode="decimal" :aria-label="$t('HomeCountedAmount', 'Counted amount')" @keydown.enter.prevent="doSet">
                                    <v-btn icon="fa-solid fa-plus" variant="text" size="small" @click="setValue++"></v-btn>
                                </div>
                                <v-select v-model="setUnitId" :items="unitItems" item-title="title" item-value="value" hide-details density="compact" class="psp-unit"></v-select>
                            </div>
                            <div v-if="setBatches.length > 1 && setValue != setRecorded" class="mt-3">
                                <label class="psp-label">{{ $t('HomeWhichBatchChanged', 'Which batch changed?') }}</label>
                                <v-select v-model="setEntry" :items="setBatchItems" item-title="title" item-value="value" hide-details density="compact"></v-select>
                            </div>
                            <p class="psp-preview">{{ $t('HomeRecorded', 'Recorded') }} {{ qty(setRecorded, unitById(setUnitId)) }} → {{ $t('HomeCounted', 'counted') }} {{ qty(setValue || 0, unitById(setUnitId)) }}
                                <b :class="setValue == setRecorded ? '' : (setValue > setRecorded ? 'text-success' : 'text-error')">({{ setValue == setRecorded ? $t('HomeNoChange', 'no change') : deltaText(setValue - setRecorded) }})</b>
                            </p>
                            <div class="d-flex justify-end">
                                <v-btn color="primary" variant="flat" :loading="busy" :disabled="setValue < 0 || setValue === '' || (setBatches.length > 1 && setValue != setRecorded && !setEntry)" @click="doSet">
                                    {{ setValue == setRecorded ? $t('HomeConfirmCount', 'Confirm count') : $t('HomeSetTo', {q: qty(setValue || 0, unitById(setUnitId))}, 'Set to {q}') }}
                                </v-btn>
                            </div>
                        </div>

                        <!-- Use / remove -->
                        <div v-if="tab == 'use'" class="psp-form">
                            <div class="psp-form-title">{{ $t('HomeHowManyRemoving', 'How many are you using or removing?') }}</div>
                            <label class="psp-label">{{ $t('HomeFromBatch', 'From') }}</label>
                            <v-select v-model="useEntryId" :items="batchItems" item-title="title" item-value="value" hide-details density="compact" class="mb-3"></v-select>
                            <div class="d-flex align-center ga-2 flex-wrap">
                                <div class="psp-stepper">
                                    <v-btn icon="fa-solid fa-minus" variant="text" size="small" :disabled="useAmount <= 1" @click="useAmount = Math.max(1, useAmount - 1)"></v-btn>
                                    <input v-model.number="useAmount" type="number" min="0" step="any" inputmode="decimal" :aria-label="$t('Amount')" @keydown.enter.prevent="doUse">
                                    <v-btn icon="fa-solid fa-plus" variant="text" size="small" :disabled="!useBatch || useAmount >= useBatch.amount" @click="useAmount++"></v-btn>
                                </div>
                                <span class="text-body-2 text-medium-emphasis">{{ useBatch?.unit ? (useAmount == 1 ? useBatch.unit.name : useBatch.unit.plural_name) : '' }}</span>
                                <v-btn size="small" variant="text" :disabled="!useBatch" @click="useAmount = useBatch!.amount">{{ $t('HomeAll', 'All') }}</v-btn>
                            </div>
                            <div class="psp-reasons" role="radiogroup" :aria-label="$t('HomeReason', 'Reason')">
                                <button v-for="r in reasons" :key="r.value" type="button" role="radio" :aria-checked="useReason == r.value" :class="{active: useReason == r.value}" @click="useReason = r.value">{{ r.title }}</button>
                            </div>
                            <p v-if="useBatch" class="psp-preview">#{{ useBatch.code }} {{ qty(useBatch.amount, useBatch.unit) }} → {{ qty(Math.max(0, useBatch.amount - (useAmount || 0)), useBatch.unit) }}
                                <b class="text-error">(−{{ fmtAmount(useAmount || 0) }})</b>
                                <span v-if="(useAmount || 0) > useBatch.amount" class="text-error"> · {{ $t('HomeOnlyN', {q: qty(useBatch.amount, useBatch.unit)}, 'only {q} there') }}</span>
                            </p>
                            <div class="d-flex justify-end">
                                <v-btn color="primary" variant="flat" :loading="busy" :disabled="!useBatch || !(useAmount > 0) || useAmount > useBatch.amount" @click="doUse">
                                    {{ $t('HomeRemoveN', {q: useBatch ? qty(useAmount || 0, useBatch.unit) : ''}, 'Remove {q}') }}
                                </v-btn>
                            </div>
                        </div>

                        <!-- Move -->
                        <div v-if="tab == 'move'" class="psp-form">
                            <div class="psp-form-title">{{ $t('HomeMoveWhere', 'Move to another place') }}</div>
                            <label class="psp-label">{{ $t('HomeFromBatch', 'From') }}</label>
                            <v-select v-model="moveEntryId" :items="batchItems" item-title="title" item-value="value" hide-details density="compact" class="mb-3"></v-select>
                            <div class="d-flex align-center ga-2 flex-wrap">
                                <div class="psp-stepper">
                                    <v-btn icon="fa-solid fa-minus" variant="text" size="small" :disabled="moveAmount <= 1" @click="moveAmount = Math.max(1, moveAmount - 1)"></v-btn>
                                    <input v-model.number="moveAmount" type="number" min="0" step="any" inputmode="decimal" :aria-label="$t('Amount')">
                                    <v-btn icon="fa-solid fa-plus" variant="text" size="small" :disabled="!moveBatch || moveAmount >= moveBatch.amount" @click="moveAmount++"></v-btn>
                                </div>
                                <span class="text-body-2 text-medium-emphasis">{{ $t('HomeTo', 'to') }}</span>
                                <v-select v-model="moveToId" :items="locations.filter(l => l.id != moveBatch?.location.id)" item-title="name" item-value="id" hide-details density="compact" class="psp-unit"></v-select>
                                <v-text-field v-model="moveShelf" :placeholder="$t('HomeShelf', 'Shelf or bin')" hide-details density="compact" class="psp-unit"></v-text-field>
                            </div>
                            <p v-if="moveBatch && moveToId" class="psp-preview">{{ moveBatch.location.name }} −{{ fmtAmount(moveAmount || 0) }} · {{ locName(moveToId) }} +{{ fmtAmount(moveAmount || 0) }} · {{ $t('HomeTotalUnchanged', 'total unchanged') }}</p>
                            <div class="d-flex justify-end">
                                <v-btn color="primary" variant="flat" :loading="busy" :disabled="!moveBatch || !moveToId || !(moveAmount > 0) || moveAmount > moveBatch.amount" @click="doMove">
                                    {{ $t('HomeMoveN', {q: moveBatch ? qty(moveAmount || 0, moveBatch.unit) : ''}, 'Move {q}') }}
                                </v-btn>
                            </div>
                        </div>

                        <!-- Details: one batch (expiry, shelf, label), duplicate, print, history -->
                        <div v-if="tab == 'details'" class="psp-form">
                            <template v-if="detailBatch">
                                <div class="psp-form-title">{{ $t('HomeBatch', 'Batch') }} #{{ detailBatch.code }} · {{ qty(detailBatch.amount, detailBatch.unit) }} · {{ where(detailBatch) }}</div>
                                <div class="psp-fields">
                                    <div class="d-flex align-center ga-2 flex-wrap">
                                        <label class="psp-label mb-0">{{ $t('HomeBestBefore', 'Best before') }}</label>
                                        <input v-model="editExpires" type="date" class="psp-date">
                                        <v-btn v-if="editExpires" size="small" variant="text" @click="editExpires = ''">{{ $t('HomeClear', 'Clear') }}</v-btn>
                                    </div>
                                    <v-text-field v-model="editShelf" :label="$t('HomeShelf', 'Shelf or bin')" hide-details></v-text-field>
                                    <v-text-field v-model="editCode" :label="$t('HomeLabelCodeShort', 'Label code')" hide-details></v-text-field>
                                </div>
                                <div class="d-flex flex-wrap ga-2 mt-3">
                                    <v-btn variant="flat" color="primary" :loading="busy" @click="doEdit">{{ $t('Save') }}</v-btn>
                                    <v-btn variant="outlined" prepend-icon="fa-regular fa-copy" @click="duplicateOpen = !duplicateOpen">{{ $t('HomeDuplicate', 'Duplicate') }}</v-btn>
                                    <v-btn variant="outlined" prepend-icon="fa-solid fa-print" @click="printLabel(detailBatch)">{{ $t('HomePrintLabel', 'Print label') }}</v-btn>
                                    <v-btn variant="outlined" prepend-icon="fa-regular fa-clipboard" @click="copyCode(detailBatch.code)">{{ $t('HomeCopyCode', 'Copy code') }}</v-btn>
                                </div>
                                <div v-if="duplicateOpen" class="psp-duplicate">
                                    <div class="psp-label">{{ $t('HomeCopyFields', 'Start a new batch with the same:') }}</div>
                                    <div class="d-flex flex-wrap ga-1">
                                        <v-chip v-for="f in copyFieldOptions" :key="f.value" :variant="copyFields.includes(f.value) ? 'flat' : 'outlined'" size="small" filter
                                                :color="copyFields.includes(f.value) ? 'primary' : undefined" @click="toggleCopy(f.value)">{{ f.title }}</v-chip>
                                    </div>
                                    <p class="text-body-2 text-medium-emphasis mt-2 mb-2">{{ $t('HomeDuplicateHelp', 'The new batch gets its own label code. Nothing is added until you save it on the Add tab.') }}</p>
                                    <v-btn size="small" variant="flat" color="primary" @click="duplicateBatch">{{ $t('HomeContinueToAdd', 'Continue to Add') }}</v-btn>
                                </div>
                            </template>
                            <p v-else class="text-body-2 text-medium-emphasis">{{ $t('HomeChooseBatch', 'Choose a batch above (…) to change its date, shelf or label.') }}</p>

                            <div class="psp-section-title">{{ $t('HomeRecentActivity', 'Recent activity') }}</div>
                            <div v-if="!history.length" class="text-body-2 text-medium-emphasis">{{ $t('HomeNoActivity', 'Nothing yet.') }}</div>
                            <div v-for="h in history" :key="h.id" class="psp-history">
                                <span class="psp-history-kind" :class="'k-' + h.type">{{ kindLabel(h.type, h.note) }}</span>
                                <span class="flex-grow-1">{{ historyText(h) }}</span>
                                <span class="psp-meta text-no-wrap">{{ fmtDate(h.created_at) }}</span>
                            </div>
                        </div>
                    </template>
                </template>
            </v-card-text>

            <!-- non-blocking result of the last action, with Undo -->
            <div v-if="toast" class="psp-toast" :class="toast.kind" role="status" aria-live="polite">
                <v-icon :icon="toast.kind == 'error' ? 'fa-solid fa-circle-exclamation' : 'fa-solid fa-circle-check'" size="small"></v-icon>
                <span class="flex-grow-1">{{ toast.text }}</span>
                <v-btn v-if="toast.logId" size="small" variant="text" :loading="undoing" @click="undo(toast.logId)">{{ $t('HomeUndo', 'Undo') }}</v-btn>
                <v-btn v-if="toast.retry" size="small" variant="text" @click="toast.retry()">{{ $t('HomeRetry', 'Retry') }}</v-btn>
                <v-btn icon="$close" size="x-small" variant="text" :aria-label="$t('Close')" @click="toast = null"></v-btn>
            </div>
        </v-card>
    </v-dialog>
</template>

<script setup lang="ts">
import {computed, nextTick, onMounted, ref, watch} from "vue";
import {useDisplay} from "vuetify";
import {useI18n} from "vue-i18n";
import JsBarcode from "jsbarcode";
import VModelSelect from "@/components/inputs/VModelSelect.vue";
import {ApiApi, Food} from "@/openapi";
import {
    cameraOpen, daysUntil, fmtAmount, fmtDate, newRequestId, noteText, pantryApi, PantryError, pantryVersion, PUnit, qty, rememberMode,
    scanPanel, scanRequest, ScanMode, store,
} from "@/composables/useScan";

const {t} = useI18n()
const {xs} = useDisplay()

type Batch = { id: number, code: string, amount: number, unit: PUnit, location: { id: number, name: string, is_freezer: boolean }, sub_location: string, expires: string | null, note: string, counted_at: string | null }
type Stock = { totals: { unit: PUnit, amount: number }[], locations: { location: any, totals: { unit: PUnit, amount: number }[] }[], batches: Batch[], earliest_expiry: string | null, expired: number, mixed_units: boolean }

const LAST_LOCATION_KEY = 'kitchen:lastInventoryLocation'
const QUICK_ADD_KEY = 'kitchen:quickAdd'

const modes = computed(() => [
    {value: 'lookup' as ScanMode, title: t('HomeLookup', 'Look up'), icon: 'fa-solid fa-magnifying-glass'},
    {value: 'restock' as ScanMode, title: t('HomeRestock', 'Restock'), icon: 'fa-solid fa-basket-shopping'},
    {value: 'count' as ScanMode, title: t('HomeStockCount', 'Stock count'), icon: 'fa-solid fa-list-check'},
])
const modeHelp = computed(() => ({
    lookup: t('HomeLookupHelp', 'Scanning shows what you have. Nothing changes until you choose an action.'),
    restock: t('HomeRestockHelp', 'For unpacking groceries: each scan opens Add with the product filled in.'),
    count: t('HomeCountHelp', 'Count what’s really there. Counts are saved as a draft and applied after review.'),
}[scanPanel.mode]))
const idleHelp = computed(() => scanPanel.mode == 'restock'
    ? t('HomeIdleRestock', 'Scan a product to add it. A handheld scanner works anywhere in Kitchen.')
    : t('HomeIdleLookup', 'Scan a product or a pantry label to see what you have. A handheld scanner works anywhere in Kitchen.'))

const reasons = computed(() => [
    {value: 'consumed', title: t('HomeConsumed', 'Used')},
    {value: 'discarded', title: t('HomeDiscarded', 'Thrown out')},
    {value: 'spoiled', title: t('HomeSpoiled', 'Spoiled')},
    {value: 'donated', title: t('HomeDonated', 'Given away')},
    {value: 'other', title: t('HomeOther', 'Other')},
])

// ---- reference data ----
const locations = ref<{ id: number, name: string }[]>([])
const units = ref<{ id: number, name: string, plural_name: string }[]>([])
const unitItems = computed(() => [{title: t('HomeNoUnit', 'each'), value: 0}, ...units.value.map(u => ({title: u.plural_name || u.name, value: u.id}))])
const unitById = (id: number | null) => units.value.find(u => u.id == id) ?? null
const locName = (id: number | null) => locations.value.find(l => l.id == id)?.name ?? ''

let referencePromise: Promise<void> | null = null

/** locations and units, loaded once (and awaited before any form gets its defaults) */
function ensureReference(): Promise<void> {
    if (!referencePromise) referencePromise = loadReference().catch(e => { referencePromise = null; throw e })
    return referencePromise
}

async function loadReference() {
    const api = new ApiApi()
    const [l, u] = await Promise.all([api.apiInventoryLocationList({pageSize: 100}), api.apiUnitList({pageSize: 300})])
    locations.value = l.results.map(x => ({id: x.id!, name: x.name}))
    units.value = u.results.map(x => ({id: x.id!, name: x.name, plural_name: x.pluralName || x.name}))
}

function lastLocationId(): number | null {
    let id: number | null = null
    try { id = Number(localStorage.getItem(LAST_LOCATION_KEY)) || null } catch (e) { /* private mode */ }
    if (id && locations.value.some(l => l.id == id)) return id
    return locations.value.find(l => l.name.toLowerCase() == 'pantry')?.id ?? locations.value[0]?.id ?? null
}

/** package-type unit to count scanned products in when the food has no preferred unit */
function defaultCountUnitId(): number {
    const pick = ['package', 'box', 'pcs', 'piece']
    for (const n of pick) {
        const u = units.value.find(x => x.name.toLowerCase() == n)
        if (u) return u.id
    }
    return 0
}

// ---- state ----
const codeInput = ref<any>(null)
const codeText = ref('')
const state = ref<'idle' | 'loading' | 'error' | 'unknown' | 'ambiguous' | 'product' | 'label'>('idle')
const error = ref('')
const result = ref<any>(null)
const stock = ref<Stock>({totals: [], locations: [], batches: [], earliest_expiry: null, expired: 0, mixed_units: false})
const busy = ref(false)
const tab = ref<string | null>(null)
const toast = ref<null | { text: string, kind: 'ok' | 'error', logId?: number | null, retry?: () => void }>(null)
const undoing = ref(false)
const history = ref<any[]>([])
const pickFood = ref<Food | null>(null)
let toastTimer: ReturnType<typeof setTimeout> | undefined
let lookupSeq = 0

const product = computed(() => result.value?.food?.product ?? result.value?.product ?? null)
const labelEntry = computed<Batch | null>(() => result.value?.label_entry ?? null)

const actions = computed(() => [
    {value: 'add', title: t('HomeAddStock', 'Add'), icon: 'fa-solid fa-plus'},
    {value: 'count', title: t('HomeCountCorrect', 'Count'), icon: 'fa-solid fa-list-check'},
    {value: 'use', title: t('HomeUseRemove', 'Use'), icon: 'fa-solid fa-minus', disabled: !stock.value.batches.length},
    {value: 'move', title: t('Move'), icon: 'fa-solid fa-arrow-right', disabled: !stock.value.batches.length},
    {value: 'details', title: t('HomeDetails', 'Details'), icon: 'fa-solid fa-ellipsis'},
])

function setMode(m: ScanMode) {
    scanPanel.mode = m
    rememberMode(m, scanPanel.keepMode)
    if (m == 'count') loadOpenCounts()
    if (state.value == 'product' || state.value == 'label') applyModeDefaults()
    focusCode()
}

function focusCode() {
    nextTick(() => codeInput.value?.focus?.())
}

function showToast(text: string, kind: 'ok' | 'error' = 'ok', logId?: number | null, retry?: () => void) {
    toast.value = {text, kind, logId, retry}
    clearTimeout(toastTimer)
    if (kind == 'ok') toastTimer = setTimeout(() => { if (toast.value?.text == text) toast.value = null }, 9000)
}

// ---- scanning ----
function onCodeKey(e: KeyboardEvent) {
    // scanners end a code with Enter, Tab or Down Arrow
    if (['Enter', 'Tab', 'ArrowDown'].includes(e.key) && codeText.value.trim()) {
        e.preventDefault()
        e.stopPropagation()
        lookup(codeText.value.trim(), 'typed')
    }
}

watch(scanRequest, req => {
    if (!req) return
    codeText.value = req.code
    lookup(req.code, req.source)
})

async function lookup(code: string, source: string) {
    const seq = ++lookupSeq
    // count mode with "each scan adds 1": the same product scanned again just counts up
    if (scanPanel.mode == 'count' && count.value && countRepeat.value && (state.value == 'product') && result.value?.food?.barcodes?.includes(code)) {
        countValue.value = (countValue.value || 0) + 1
        await saveCountLine(true)
        return
    }
    state.value = 'loading'
    tab.value = null
    try {
        const [r] = await Promise.all([pantryApi(`lookup/?code=${encodeURIComponent(code)}`), ensureReference()])
        if (seq != lookupSeq) return
        result.value = r
        if (r.kind == 'invalid') {
            error.value = r.error
            state.value = 'error'
        } else if (r.kind == 'unknown') {
            newName.value = suggestName(r.product)
            linkFood.value = null
            state.value = 'unknown'
            if (quickAdd.value && scanPanel.mode == 'restock') showToast(t('HomeQuickPausedUnknown', 'Quick add paused: tell Kitchen which food this is first.'))
        } else {
            stock.value = r.stock
            state.value = r.kind == 'ambiguous' ? 'ambiguous' : r.kind
            await afterFound(r.kind == 'label')
        }
    } catch (err: any) {
        if (seq != lookupSeq) return
        error.value = err instanceof PantryError ? err.message : t('HomeLookupFailed', 'Couldn’t look that up. Check the connection and scan again.')
        state.value = 'error'
    } finally {
        if (seq == lookupSeq) {
            codeText.value = ''
            focusCode()
        }
    }
}

async function afterFound(isLabel: boolean) {
    applyModeDefaults()
    if (isLabel && labelEntry.value) {
        detailBatch.value = stock.value.batches.find(b => b.id == labelEntry.value!.id) ?? null
        useEntryId.value = labelEntry.value.id
        moveEntryId.value = labelEntry.value.id
        if (scanPanel.mode == 'lookup') tab.value = labelEntry.value.amount > 0 ? 'use' : null
    }
    loadHistory()
    // restock "quick add": one package per scan, when everything needed is known
    if (scanPanel.mode == 'restock' && quickAdd.value && !isLabel) {
        if (!addLocationId.value) {
            showToast(t('HomeQuickPausedPlace', 'Quick add paused: choose where things go.'))
        } else if (!result.value.food.preferred_unit) {
            showToast(t('HomeQuickPausedUnit', 'Quick add paused: choose the unit for this product once, then it’s remembered.'))
        } else {
            addAmount.value = 1
            await doAdd()
        }
    }
}

async function showFood(foodId: number, opts: { entryId?: number, tab?: string } = {}) {
    state.value = 'loading'
    try {
        const [r] = await Promise.all([pantryApi(`stock/?food_id=${foodId}`), ensureReference()])
        result.value = {kind: 'product', food: r.food, stock: r.stock, code: null}
        stock.value = r.stock
        state.value = 'product'
        applyModeDefaults()
        loadHistory()
        let targetBatch: Batch | undefined
        if (opts.entryId) {
            const b = stock.value.batches.find(x => x.id == opts.entryId)
            if (b) {
                targetBatch = b
                useEntryId.value = b.id
                moveEntryId.value = b.id
                detailBatch.value = b
                setEditFields(b)
            }
        }
        if (opts.tab === 'duplicate' && targetBatch) {
            duplicateOpen.value = true
            tab.value = 'details'
        } else if (opts.tab) {
            // Direct batch actions retain that batch's location/unit and expiry context.
            tab.value = opts.tab
            if (targetBatch && opts.tab === 'add') {
                addPreferredEntryId.value = targetBatch.id
                addLocationId.value = targetBatch.location.id
                addUnitId.value = targetBatch.unit?.id ?? 0
                addExpires.value = targetBatch.expires ?? ''
                addShelf.value = targetBatch.sub_location ?? ''
            }
            if (targetBatch && opts.tab === 'count') {
                setLocationId.value = targetBatch.location.id
                setUnitId.value = targetBatch.unit?.id ?? 0
                await nextTick()
                resetSetValue()
                setEntry.value = targetBatch.id
            }
        }
    } catch (err: any) {
        error.value = err.message
        state.value = 'error'
    } finally {
        pickFood.value = null
    }
}

// ---- unknown barcode -> food ----
const linkFood = ref<Food | null>(null)
const newName = ref('')

function suggestName(p: any): string {
    if (!p) return ''
    let n: string = p.name || ''
    if (p.brand && n.toLowerCase().startsWith(p.brand.toLowerCase() + ' ')) n = n.slice(p.brand.length + 1)
    return n.trim()
}

async function linkBarcode() {
    if (busy.value || (!linkFood.value && !newName.value.trim())) return
    busy.value = true
    try {
        const r = await pantryApi('link-barcode/', {code: result.value.code, food_id: linkFood.value?.id, name: newName.value.trim(), product: result.value.product})
        const code = result.value.code
        result.value = {kind: 'product', code, food: r.food, stock: r.stock}
        stock.value = r.stock
        state.value = 'product'
        showToast(t('HomeBarcodeRemembered', {code, food: r.food.name}, '{code} now means {food}'))
        await afterFound(false)
    } catch (err: any) {
        showToast(err.message, 'error')
    } finally {
        busy.value = false
    }
}

function changeProduct() {
    // re-point this barcode at a different food
    linkFood.value = null
    newName.value = result.value.food.name
    result.value = {kind: 'unknown', code: result.value.code, product: result.value.food.product}
    state.value = 'unknown'
}

// ---- forms ----
const restockLocationId = ref<number | null>(null)
const quickAdd = ref(false)

const addAmount = ref<any>(1)
const addUnitId = ref<number>(0)
const addLocationId = ref<number | null>(null)
const addExpires = ref('')
const addShelf = ref('')
const addCode = ref('')
const addNewBatch = ref(false)

const setLocationId = ref<number | null>(null)
const setUnitId = ref<number>(0)
const setValue = ref<any>(0)
const setEntry = ref<number | 'new' | null>(null)
let setExpected = 0

const useEntryId = ref<number | null>(null)
const useAmount = ref<any>(1)
const useReason = ref('consumed')

const moveEntryId = ref<number | null>(null)
const moveAmount = ref<any>(1)
const moveToId = ref<number | null>(null)
const moveShelf = ref('')

const detailBatch = ref<Batch | null>(null)
const editExpires = ref('')
const editShelf = ref('')
const editCode = ref('')
const duplicateOpen = ref(false)
const copyFieldOptions = computed(() => [
    {value: 'location', title: t('HomePlace', 'Place')}, {value: 'amount', title: t('Amount')},
    {value: 'expires', title: t('HomeBestBefore', 'Best before')}, {value: 'shelf', title: t('HomeShelf', 'Shelf or bin')},
])
const copyFields = ref<string[]>(['location', 'amount', 'expires', 'shelf'])

function unitOfFood(): number {
    return result.value?.food?.preferred_unit?.id ?? (stock.value.totals.length == 1 ? stock.value.totals[0]!.unit?.id ?? 0 : defaultCountUnitId())
}

const addPreferredEntryId = ref<number | null>(null)

function applyModeDefaults() {
    addPreferredEntryId.value = null
    const unit = unitOfFood()
    addAmount.value = 1
    addUnitId.value = unit
    addLocationId.value = scanPanel.mode == 'restock' ? (restockLocationId.value ?? lastLocationId()) : lastLocationId()
    addExpires.value = ''
    addShelf.value = ''
    addCode.value = ''
    addNewBatch.value = false
    // count: where it is if it's in one place, otherwise the usual place
    setLocationId.value = stock.value.locations.length == 1 ? stock.value.locations[0]!.location.id : lastLocationId()
    setUnitId.value = unit
    resetSetValue()
    // use / move: soonest expiry first
    const first = stock.value.batches[0]
    useEntryId.value = first?.id ?? null
    useAmount.value = 1
    useReason.value = 'consumed'
    moveEntryId.value = first?.id ?? null
    moveAmount.value = first?.amount ?? 1
    moveToId.value = null
    moveShelf.value = ''
    if (scanPanel.mode == 'restock' && state.value == 'product') tab.value = 'add'
    if (scanPanel.mode == 'count' && count.value) {
        countUnitId.value = unit
        const line = count.value.lines?.find((l: any) => l.food.id == result.value.food.id && (l.unit?.id ?? 0) == unit && !l.applied)
        countRecorded.value = line ? line.recorded : recordedAt(count.value.location.id, unit)
        countValue.value = line ? line.counted : (countRepeat.value ? 1 : countRecorded.value)
        if (countRepeat.value && !line) nextTick(() => saveCountLine(true))
    }
}

function recordedAt(locationId: number | null, unitId: number): number {
    return stock.value.batches.filter(b => b.location.id == locationId && (b.unit?.id ?? 0) == unitId).reduce((s, b) => s + b.amount, 0)
}

const addHere = computed(() => recordedAt(addLocationId.value, addUnitId.value))
const addTarget = computed(() => {
    if (addNewBatch.value || addCode.value.trim()) return null
    const matching = stock.value.batches.filter(b => b.location.id == addLocationId.value && (b.unit?.id ?? 0) == addUnitId.value
        && (b.sub_location || '') == addShelf.value.trim() && (b.expires || '') == (addExpires.value || ''))
    return matching.find(b => b.id === addPreferredEntryId.value) ?? matching[0] ?? null
})
const addTargetText = computed(() => addTarget.value ? t('HomeJoinsBatch', {code: addTarget.value.code}, 'Joins batch #{code}') : t('HomeNewBatch', 'New batch'))

const setBatches = computed(() => stock.value.batches.filter(b => b.location.id == setLocationId.value && (b.unit?.id ?? 0) == setUnitId.value))
const setRecorded = computed(() => setBatches.value.reduce((s, b) => s + b.amount, 0))
const setBatchItems = computed(() => [
    ...setBatches.value.map(b => ({title: batchTitle(b), value: b.id})),
    ...(setValue.value > setRecorded.value ? [{title: t('HomeAsNewBatch', 'A new batch'), value: 'new'}] : []),
])

function resetSetValue() {
    setValue.value = recordedAt(setLocationId.value, setUnitId.value)
    setExpected = setValue.value
    setEntry.value = null
}

watch([setLocationId, setUnitId], resetSetValue)

const batchItems = computed(() => stock.value.batches.map(b => ({title: batchTitle(b), value: b.id})))
const useBatch = computed(() => stock.value.batches.find(b => b.id == useEntryId.value) ?? null)
const moveBatch = computed(() => stock.value.batches.find(b => b.id == moveEntryId.value) ?? null)
watch(moveEntryId, () => { moveAmount.value = moveBatch.value?.amount ?? 1 })

function batchTitle(b: Batch) {
    return `${qty(b.amount, b.unit)} · ${b.location.name}${b.sub_location ? ' · ' + b.sub_location : ''}${b.expires ? ' · ' + expiryText(b.expires) : ''} · #${b.code}`
}

function selectTab(v: string) {
    tab.value = tab.value == v ? null : v
    if (v == 'count') resetSetValue()
    if (v == 'details') loadHistory()
}

function openBatch(b: Batch) {
    detailBatch.value = b
    setEditFields(b)
    useEntryId.value = b.id
    moveEntryId.value = b.id
    tab.value = 'details'
    duplicateOpen.value = false
}

function setEditFields(b: Batch) {
    editExpires.value = b.expires ?? ''
    editShelf.value = b.sub_location ?? ''
    editCode.value = b.code
}

function toggleCopy(v: string) {
    copyFields.value = copyFields.value.includes(v) ? copyFields.value.filter(x => x != v) : [...copyFields.value, v]
}

function duplicateBatch() {
    const b = detailBatch.value!
    applyModeDefaults()
    if (copyFields.value.includes('location')) addLocationId.value = b.location.id
    if (copyFields.value.includes('amount')) { addAmount.value = b.amount; addUnitId.value = b.unit?.id ?? 0 }
    if (copyFields.value.includes('expires')) addExpires.value = b.expires ?? ''
    if (copyFields.value.includes('shelf')) addShelf.value = b.sub_location ?? ''
    addNewBatch.value = true
    addCode.value = ''
    duplicateOpen.value = false
    tab.value = 'add'
}

// ---- writes ----
let pendingRequest: { key: string, id: string } | null = null

/** one request id per intended change; a retry of the same change reuses it */
function requestIdFor(body: any): string {
    const key = JSON.stringify(body)
    if (pendingRequest?.key != key) pendingRequest = {key, id: newRequestId()}
    return pendingRequest.id
}

async function write(body: any, after?: (r: any) => void) {
    if (busy.value) return
    busy.value = true
    const request_id = requestIdFor(body)
    try {
        const r = await pantryApi('adjust/', {...body, request_id})
        pendingRequest = null
        stock.value = r.stock
        if (r.food) result.value = {...result.value, food: r.food}
        if (labelEntry.value) {
            const fresh = r.stock.batches.find((b: Batch) => b.id == labelEntry.value!.id)
            result.value = {...result.value, label_entry: fresh ?? {...labelEntry.value, amount: 0}}
        }
        pantryVersion.value++
        showToast(r.message, 'ok', r.log_id)
        after?.(r)
        loadHistory()
    } catch (err: any) {
        if (err instanceof PantryError && err.status == 409) {
            pendingRequest = null
            if (err.body?.stock) stock.value = err.body.stock
            if (err.body?.needs_batch) {
                showToast(err.body.error, 'error')
            } else {
                showToast(err.body?.error ?? t('HomeChangedMeanwhile', 'This changed in the meantime. The numbers above are up to date — check and try again.'), 'error')
                resetSetValue()
            }
        } else if (err instanceof PantryError && err.status < 500) {
            pendingRequest = null
            showToast(err.message, 'error')
        } else {
            // network or server trouble: keep everything as entered, offer the same request again
            showToast(t('HomeSaveFailed', 'Couldn’t save — nothing was changed. Your entries are kept.'), 'error', null, () => { toast.value = null; write(body, after) })
        }
    } finally {
        busy.value = false
        focusCode()
    }
}

async function doAdd() {
    if (!(addAmount.value > 0) || !addLocationId.value) return
    await write({
        action: 'add', food_id: result.value.food.id, unit_id: addUnitId.value || null, amount: addAmount.value,
        location_id: addLocationId.value, expires: addExpires.value || null, sub_location: addShelf.value.trim(),
        code: addCode.value.trim() || null, new_batch: addNewBatch.value, entry_id: addTarget.value?.id ?? null,
        remember_unit: (result.value.food.preferred_unit?.id ?? 0) != addUnitId.value,
    }, () => {
        store(LAST_LOCATION_KEY, String(addLocationId.value))
        if (scanPanel.mode == 'restock') restockLocationId.value = addLocationId.value
        addAmount.value = 1
        addCode.value = ''
        addNewBatch.value = false
        if (scanPanel.mode != 'restock') tab.value = null
    })
}

async function doSet() {
    await write({
        action: 'set', food_id: result.value.food.id, unit_id: setUnitId.value || null, location_id: setLocationId.value,
        counted: setValue.value, expected: setExpected, entry_id: setBatches.value.length > 1 && setValue.value != setRecorded.value ? setEntry.value : null,
    }, () => { tab.value = null })
}

async function doUse() {
    if (!useBatch.value) return
    await write({action: 'remove', entry_id: useBatch.value.id, amount: useAmount.value, reason: useReason.value}, () => {
        useAmount.value = 1
        if (!stock.value.batches.find(b => b.id == useEntryId.value)) useEntryId.value = stock.value.batches[0]?.id ?? null
        tab.value = null
    })
}

async function doMove() {
    if (!moveBatch.value) return
    await write({action: 'move', entry_id: moveBatch.value.id, amount: moveAmount.value, to_location_id: moveToId.value, to_sub_location: moveShelf.value.trim()},
        () => { tab.value = null })
}

async function doEdit() {
    if (!detailBatch.value) return
    await write({action: 'edit', entry_id: detailBatch.value.id, expires: editExpires.value || null, sub_location: editShelf.value.trim(), code: editCode.value.trim()},
        () => { detailBatch.value = stock.value.batches.find(b => b.id == detailBatch.value!.id) ?? null })
}

async function undo(logId: number) {
    undoing.value = true
    try {
        const r = await pantryApi('adjust/', {action: 'undo', log_id: logId, request_id: newRequestId()})
        stock.value = r.stock
        pantryVersion.value++
        showToast(r.message)
        loadHistory()
    } catch (err: any) {
        if (err.body?.stock) stock.value = err.body.stock
        showToast(err.message, 'error')
    } finally {
        undoing.value = false
        focusCode()
    }
}

// ---- shopping ----
const shopping = ref(false)

async function addToShopping() {
    shopping.value = true
    try {
        const api = new ApiApi()
        const food = result.value.food
        await api.apiShoppingListEntryCreate({shoppingListEntry: {food: {id: food.id, name: food.name} as any, amount: 1, unit: food.preferred_unit ? {id: food.preferred_unit.id, name: food.preferred_unit.name} as any : null} as any})
        showToast(t('HomeAddedToShopping', {food: food.name}, 'Added {food} to the shopping list'))
    } catch (err: any) {
        showToast(t('HomeShoppingFailed', 'Couldn’t add it to the shopping list.'), 'error')
    } finally {
        shopping.value = false
        focusCode()
    }
}

// ---- history ----
async function loadHistory() {
    if (!result.value?.food?.id) return
    try {
        history.value = (await pantryApi(`activity/?food_id=${result.value.food.id}&limit=8`)).results
    } catch (e) { history.value = [] }
}

function kindLabel(k: string, note = '') {
    if (k == 'remove') {
        const r = note.split(' ')[0]
        const label = reasons.value.find(x => x.value == r)
        if (label && r != 'consumed') return label.title
    }
    return ({add: t('HomeKAdd', 'Added'), remove: t('HomeKRemove', 'Used'), move: t('HomeKMove', 'Moved'), count: t('HomeKCount', 'Counted'),
        edit: t('HomeKEdit', 'Edited'), undo: t('HomeKUndo', 'Undone')} as any)[k] ?? k
}

function historyText(h: any) {
    const d = h.delta
    const change = d == 0 ? '' : `${d > 0 ? '+' : '−'}${qty(Math.abs(d), h.unit)} `
    const place = h.type == 'move' && h.old_location?.id != h.new_location?.id ? `${h.old_location.name} → ${h.new_location.name}` : h.new_location?.name
    return `${change}${place} · #${h.code}${noteText(h.type, h.note) ? ' · ' + noteText(h.type, h.note) : ''}${h.by ? ' · ' + h.by : ''}`
}

// ---- stock count ----
const count = ref<any>(null)
const openCounts = ref<any[]>([])
const countLocationId = ref<number | null>(null)
const countRepeat = ref(false)
const countValue = ref<any>(0)
const countUnitId = ref<number>(0)
const countRecorded = ref(0)
const COUNT_KEY = 'kitchen:openCount'

async function loadOpenCounts() {
    await ensureReference()
    try {
        openCounts.value = (await pantryApi('counts/?status=open')).results
        let saved: number | null = null
        try { saved = Number(localStorage.getItem(COUNT_KEY)) || null } catch (e) { /* private mode */ }
        if (!count.value && saved && openCounts.value.some(c => c.id == saved)) await resumeCount(saved)
    } catch (e) { openCounts.value = [] }
    if (!countLocationId.value) countLocationId.value = lastLocationId()
}

async function startCount() {
    busy.value = true
    try {
        count.value = await pantryApi('counts/', {location_id: countLocationId.value})
        store(COUNT_KEY, String(count.value.id))
        showToast(t('HomeCountStarted', {place: count.value.location.name}, 'Counting {place}. Scan each product and enter how many you have.'))
    } catch (err: any) {
        showToast(err.message, 'error')
    } finally {
        busy.value = false
        focusCode()
    }
}

async function resumeCount(id: number) {
    count.value = await pantryApi(`counts/${id}/`)
    store(COUNT_KEY, String(id))
    focusCode()
}

watch(countUnitId, () => {
    if (scanPanel.mode != 'count' || !count.value || !result.value?.food) return
    countRecorded.value = recordedAt(count.value.location.id, countUnitId.value)
})

async function saveCountLine(quiet = false) {
    if (!count.value || !result.value?.food || busy.value) return
    busy.value = true
    try {
        const r = await pantryApi(`counts/${count.value.id}/line/`, {food_id: result.value.food.id, unit_id: countUnitId.value || null, counted: countValue.value})
        count.value = r.count
        countRecorded.value = r.recorded
        showToast(r.message)
    } catch (err: any) {
        showToast(err.message, 'error')
    } finally {
        busy.value = false
        focusCode()
    }
}

function deltaText(d: number) {
    return d == 0 ? '±0' : `${d > 0 ? '+' : '−'}${fmtAmount(Math.abs(d))}`
}

// ---- labels ----
function where(b: Batch) {
    return [b.location.name, b.sub_location].filter(Boolean).join(' · ')
}

function expiryText(iso: string) {
    const d = daysUntil(iso)!
    if (d < 0) return t('HomeExpiredOn', {date: fmtDate(iso)}, 'expired {date}')
    if (d == 0) return t('HomeExpiresToday', 'best before today')
    if (d <= 14) return t('HomeExpiresInDays', {date: fmtDate(iso), n: d}, 'best before {date} ({n}d)')
    return t('HomeBestBeforeDate', {date: fmtDate(iso)}, 'best before {date}')
}

function expiryClass(iso: string) {
    const d = daysUntil(iso)!
    return d < 0 ? 'expired' : d <= 14 ? 'soon' : ''
}

async function copyCode(code: string) {
    try {
        await navigator.clipboard.writeText(code)
        showToast(t('HomeCopied', {code}, 'Copied #{code}'))
    } catch (e) {
        showToast(code)
    }
}

function printLabel(b: Batch) {
    // a small printable label: food, code as a Code 128 barcode, best-before
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg')
    JsBarcode(svg, b.code, {format: 'CODE128', displayValue: true, height: 46, margin: 0, fontSize: 14, width: 2})
    const w = window.open('', '_blank', 'width=420,height=320')
    if (!w) return
    const food = result.value.food.name
    w.document.write(`<!doctype html><html><head><meta charset="utf-8"><title>#${b.code}</title><style>
        @page { size: 62mm 40mm; margin: 3mm }
        body { font-family: -apple-system, sans-serif; margin: 0; padding: 8px }
        .name { font-weight: 700; font-size: 15px; margin-bottom: 4px }
        .meta { font-size: 11px; color: #444; margin-top: 4px }
    </style></head><body><div class="name">${food.replace(/</g, '&lt;')}</div>${svg.outerHTML}
    <div class="meta">${[b.expires ? 'Best before ' + fmtDate(b.expires) : '', where(b)].filter(Boolean).join(' · ').replace(/</g, '&lt;')}</div>
    <script>window.onload = () => { window.print() }<\/script></body></html>`)
    w.document.close()
}

// ---- password managers ----
// The scan box looks like a login field to 1Password & co. Mark every field in the panel as "not a
// login" (each manager has its own attribute); a MutationObserver catches fields added later.
const panelCard = ref<any>(null)
let fieldObserver: MutationObserver | null = null

function ignorePasswordManagers(root: Element) {
    root.querySelectorAll('input, textarea').forEach(el => {
        el.setAttribute('data-1p-ignore', 'true')
        el.setAttribute('data-lpignore', 'true')
        el.setAttribute('data-bwignore', 'true')
        el.setAttribute('data-form-type', 'other')
        el.setAttribute('autocomplete', 'off')
    })
}

watch(() => scanPanel.open, open => {
    if (!open) {
        fieldObserver?.disconnect()
        fieldObserver = null
        return
    }
    nextTick(() => {
        const root: Element | undefined = panelCard.value?.$el
        if (!root) return
        ignorePasswordManagers(root)
        fieldObserver?.disconnect()
        fieldObserver = new MutationObserver(() => ignorePasswordManagers(root))
        fieldObserver.observe(root, {childList: true, subtree: true})
    })
}, {flush: 'post'})

// ---- open / close ----
watch(() => scanPanel.at, async () => {
    if (!scanPanel.open) return
    await ensureReference()
    restockLocationId.value = restockLocationId.value ?? lastLocationId()
    try { quickAdd.value = localStorage.getItem(QUICK_ADD_KEY) == '1' } catch (e) { /* private mode */ }
    if (scanPanel.mode == 'count') await loadOpenCounts()
    const target = scanPanel.target
    if (target?.foodId) {
        await showFood(target.foodId, {entryId: target.entryId, tab: target.tab})
    } else if (!scanRequest.value || Date.now() - scanRequest.value.at > 1000) {
        state.value = 'idle'
        result.value = null
        toast.value = null
    }
    focusCode()
})

watch(() => scanPanel.open, open => {
    if (!open) {
        lookupSeq++
        toast.value = null
    }
})

watch(quickAdd, v => store(QUICK_ADD_KEY, v ? '1' : null))
watch(restockLocationId, v => { if (scanPanel.mode == 'restock' && v && tab.value == 'add') addLocationId.value = v })

onMounted(() => { /* reference data loads the first time the panel opens */ })
</script>

<style scoped>
.psp-head {
    padding: 14px 18px 12px;
    display: flex;
    flex-direction: column;
    gap: 10px;
}

.psp-title {
    font-size: 1.125rem;
    font-weight: 600;
}

.psp-modes, .psp-actions {
    display: inline-flex;
    gap: 2px;
    padding: 3px;
    border-radius: 10px;
    background: rgba(var(--v-theme-on-surface), 0.05);
    align-self: flex-start;
    flex-wrap: wrap;
}

.psp-modes button, .psp-actions button {
    height: 30px;
    padding: 0 12px;
    border-radius: 7px;
    font-size: 0.8125rem;
    font-weight: 500;
    color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}

.psp-modes button.active, .psp-actions button.active {
    background: rgb(var(--v-theme-surface));
    color: rgb(var(--v-theme-on-surface));
    box-shadow: 0 0 0 1px rgba(var(--v-theme-on-surface), 0.08), 0 1px 2px rgba(0, 0, 0, 0.08);
}

@media (max-width: 600px) {
    .psp-actions button, .psp-modes button {
        padding: 0 8px;
    }

    .psp-actions button .v-icon {
        display: none;
    }
}

.psp-actions button:disabled {
    opacity: 0.4;
}

.psp-modes button:focus-visible, .psp-actions button:focus-visible, .psp-reasons button:focus-visible {
    outline: 2px solid rgb(var(--v-theme-primary));
    outline-offset: 1px;
}

.psp-mode-help {
    margin: -4px 0 0;
    font-size: 0.8125rem;
    color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}

.psp-context {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
    font-size: 0.875rem;
}

.psp-inline-select {
    max-width: 180px;
}

.psp-body {
    padding: 16px 18px 18px !important;
    min-height: 220px;
}

.psp-empty {
    padding: 4px 0;
}

.psp-label {
    display: block;
    margin-bottom: 6px;
    font-size: 0.8125rem;
    font-weight: 500;
}

.psp-section-title {
    margin: 18px 0 8px;
    font-size: 0.8125rem;
    font-weight: 600;
    color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}

.psp-product {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 10px;
    border-radius: 10px;
    box-shadow: inset 0 0 0 1px rgba(var(--v-theme-on-surface), 0.12);
}

.psp-thumb {
    width: 56px;
    height: 56px;
    flex-shrink: 0;
    border-radius: 8px;
    overflow: hidden;
    display: flex;
    align-items: center;
    justify-content: center;
    background: #fff;
    box-shadow: inset 0 0 0 1px rgba(var(--v-theme-on-surface), 0.08);
}

.psp-thumb img {
    width: 100%;
    height: 100%;
    object-fit: contain;
}

.psp-name {
    font-weight: 600;
    line-height: 1.3;
}

.psp-meta {
    font-size: 0.8125rem;
    color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}

.psp-code {
    font-family: ui-monospace, "SF Mono", Menlo, monospace;
    font-size: 0.75rem;
    color: rgba(var(--v-theme-on-surface), 0.55);
}

.psp-item {
    margin-top: 12px;
}

.psp-stock {
    margin-top: 14px;
}

.psp-total {
    font-size: 1.375rem;
    font-weight: 650;
    letter-spacing: -0.01em;
}

.psp-total-sub {
    margin-left: 8px;
    font-size: 0.875rem;
    font-weight: 400;
    color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}

.psp-none {
    font-size: 1rem;
    font-weight: 500;
    color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}

.psp-locs {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: 6px;
}

.psp-chip {
    display: inline-flex;
    align-items: center;
    padding: 2px 8px;
    border-radius: 6px;
    font-size: 0.8125rem;
    background: rgba(var(--v-theme-on-surface), 0.05);
}

.psp-warn {
    margin: 6px 0 0;
    font-size: 0.8125rem;
    color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}

.psp-batches, .psp-more {
    margin-top: 8px;
}

.psp-batches summary, .psp-more summary {
    cursor: pointer;
    font-size: 0.8125rem;
    font-weight: 500;
    color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
    padding: 4px 0;
}

.psp-batch {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 0;
    border-top: 1px solid rgba(var(--v-theme-on-surface), 0.08);
}

.psp-expiry {
    font-size: 0.75rem;
    padding: 2px 6px;
    border-radius: 6px;
    background: rgba(var(--v-theme-on-surface), 0.05);
    white-space: nowrap;
}

.psp-expiry.soon {
    background: rgba(var(--v-theme-warning), 0.15);
}

.psp-expiry.expired {
    background: rgba(var(--v-theme-error), 0.12);
    color: rgb(var(--v-theme-error));
}

.psp-actions {
    margin-top: 16px;
}

.psp-form {
    margin-top: 12px;
    padding: 14px;
    border-radius: 10px;
    box-shadow: inset 0 0 0 1px rgba(var(--v-theme-on-surface), 0.10);
}

.psp-form-title {
    font-weight: 600;
    margin-bottom: 10px;
}

.psp-stepper {
    display: inline-flex;
    align-items: center;
    height: 40px;
    border-radius: 8px;
    box-shadow: inset 0 0 0 1px rgba(var(--v-theme-on-surface), 0.14);
}

.psp-stepper input {
    width: 56px;
    text-align: center;
    font-size: 1rem;
    font-variant-numeric: tabular-nums;
    outline: none;
    background: transparent;
    -moz-appearance: textfield;
}

.psp-stepper input::-webkit-outer-spin-button, .psp-stepper input::-webkit-inner-spin-button {
    -webkit-appearance: none;
}

.psp-unit {
    max-width: 170px;
    min-width: 120px;
}

.psp-date {
    height: 36px;
    padding: 0 10px;
    border-radius: 8px;
    box-shadow: inset 0 0 0 1px rgba(var(--v-theme-on-surface), 0.14);
    font: inherit;
    font-size: 0.875rem;
    color: inherit;
    background: transparent;
}

.psp-fields {
    display: flex;
    flex-direction: column;
    gap: 12px;
}

.psp-or {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 0.75rem;
    color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}

.psp-or::before, .psp-or::after {
    content: '';
    flex: 1;
    border-top: 1px solid rgba(var(--v-theme-on-surface), 0.1);
}

.psp-preview {
    margin: 12px 0 10px;
    font-size: 0.875rem;
    font-variant-numeric: tabular-nums;
    color: rgba(var(--v-theme-on-surface), 0.8);
}

.psp-reasons {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: 12px;
}

.psp-reasons button {
    height: 28px;
    padding: 0 10px;
    border-radius: 6px;
    font-size: 0.8125rem;
    box-shadow: inset 0 0 0 1px rgba(var(--v-theme-on-surface), 0.14);
}

.psp-reasons button.active {
    box-shadow: inset 0 0 0 1px rgb(var(--v-theme-primary));
    background: rgba(var(--v-theme-primary), 0.08);
    color: rgb(var(--v-theme-primary));
}

.psp-duplicate {
    margin-top: 12px;
    padding: 12px;
    border-radius: 8px;
    background: rgba(var(--v-theme-on-surface), 0.03);
}

.psp-history {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 0;
    font-size: 0.8125rem;
    border-top: 1px solid rgba(var(--v-theme-on-surface), 0.06);
}

.psp-history-kind {
    min-width: 64px;
    font-weight: 600;
}

.psp-history-kind.k-add { color: rgb(var(--v-theme-success)); }
.psp-history-kind.k-remove { color: rgb(var(--v-theme-error)); }

.psp-row {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 0;
    font-size: 0.875rem;
}

.psp-toast {
    display: flex;
    align-items: center;
    gap: 8px;
    margin: 0 12px 12px;
    padding: 8px 8px 8px 12px;
    border-radius: 10px;
    font-size: 0.875rem;
    background: #1c1917;
    color: #fafaf9;
}

.psp-toast.error {
    background: rgb(var(--v-theme-error));
}

.psp-toast :deep(.v-btn) {
    color: inherit;
}
</style>
