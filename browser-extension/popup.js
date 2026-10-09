// Add to Kitchen: read the recipe on the current tab (with the person's own logins) and save it to
// Kitchen through /api/home/clip/ (cookbook/views/home_clip.py). Kitchen does the conversion.

const DEFAULT_BASE = 'https://kitchen.madiba.ca'
const view = document.getElementById('view')

const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]))

async function settings() {
    const s = await chrome.storage.local.get(['base', 'token'])
    return {base: (s.base || DEFAULT_BASE).replace(/\/+$/, ''), token: s.token || null}
}

function show(html) {
    view.innerHTML = html
}

function showState(text, spinner = true) {
    show(`<div class="state">${spinner ? '<div class="spinner" aria-hidden="true"></div>' : ''}<p class="muted">${esc(text)}</p></div>`)
}

function showError(text, extra = '') {
    show(`<div class="notice error" role="alert">${esc(text)}</div>${extra}`)
}

// ---- the page --------------------------------------------------------------------------------

/** runs inside the page (MAIN world) so it sees the page's own data and the person's cookies */
async function readPage() {
    async function chefstepsMemberRecipe(articleId) {
        const token = localStorage.getItem('access_token')
        if (!token || !articleId || !window.webpackChunk_N_E) return null
        let req
        try { window.webpackChunk_N_E.push([[Symbol('kitchen')], {}, r => { req = r }]) } catch (e) { return null }
        if (!req?.m) return null
        const src = id => { try { return String(req.m[id]) } catch (e) { return '' } }
        const ids = Object.keys(req.m)
        const loaderId = ids.find(id => src(id).includes('fetchFullArticle failed'))
        const converterId = ids.find(id => src(id).includes('embedded-entry-inline') && src(id).includes('RELATED RECIPE'))
        if (!loaderId || !converterId) return null
        const pick = (mod, test) => Object.values(mod).find(f => typeof f == 'function' && test(String(f)))
        const load = pick(req(loaderId), f => f.includes('api/articles'))
        const converters = Object.values(req(converterId)).filter(f => typeof f == 'function')
        if (!load || !converters.length) return null
        try {
            const entry = await load(articleId, token)
            if (!entry?.rawEntry) return null
            for (const convert of converters) {
                const out = convert(entry.rawEntry, entry.linkedEntriesMap || {})
                if (out?.recipe?.steps?.length) return out.recipe
            }
        } catch (e) { /* fall through to the other routes */ }
        return null
    }

    const out = {url: location.href, title: document.title}
    if (/(^|\.)chefsteps\.com$/.test(location.hostname)) {
        // ChefSteps is a Next.js site: the whole recipe is in the page data for members
        let page = window.__NEXT_DATA__?.props?.pageProps
        const slug = location.pathname.split('/').filter(Boolean).pop()
        const stale = !page?.data || page.data.slug !== slug
        if (stale || !(page?.data?.steps || []).length) {
            // client-side navigation leaves old data behind, so ask for this page's data
            try {
                const build = window.__NEXT_DATA__?.buildId
                const r = await fetch(`/_next/data/${build}${location.pathname.replace(/\/$/, '')}.json`, {credentials: 'include'})
                if (r.ok) {
                    const j = await r.json()
                    if (j?.pageProps?.data) page = j.pageProps
                }
            } catch (e) { /* keep what we have */ }
        }
        if (page?.data && !(page.data.steps || []).length) {
            // Members-only recipes aren't in the page data: ChefSteps' own code fetches them with the
            // sign-in key it keeps in this browser, then converts them. Use those same two functions,
            // found by what they contain (their minified names change with every ChefSteps release).
            const member = await chefstepsMemberRecipe(page.data.id)
            if (member) page = {...page, data: {...page.data, ...member}, isContentLimited: false}
            else out.chefstepsSignedIn = !!localStorage.getItem('access_token')
        }
        if (page?.data) out.chefsteps = page
        // the page as displayed too, in case neither of the above has the steps
    }
    const html = document.documentElement.outerHTML
    out.html = html.length > 4_000_000 ? html.slice(0, 4_000_000) : html
    return out
}

async function targetTab() {
    const want = new URLSearchParams(location.search).get('tab')  // for testing from a normal tab
    if (want) return chrome.tabs.get(Number(want))
    const [tab] = await chrome.tabs.query({active: true, currentWindow: true})
    return tab
}

// ---- Kitchen ---------------------------------------------------------------------------------

class SignInNeeded extends Error {}

async function getToken(base, force = false) {
    const s = await settings()
    if (s.token && !force) return s.token
    let r
    try {
        r = await fetch(`${base}/api/home/extension-token/`, {credentials: 'include'})
    } catch (e) {
        throw new Error(`Can’t reach Kitchen at ${base}. Are you on your home network?`)
    }
    if (r.status == 401 || r.status == 403 || r.redirected) throw new SignInNeeded()
    if (!r.ok) throw new Error(`Kitchen answered ${r.status}.`)
    const j = await r.json()
    await chrome.storage.local.set({token: j.token})
    return j.token
}

async function clip(base, body) {
    for (let attempt = 0; attempt < 2; attempt++) {
        const token = await getToken(base, attempt > 0)
        let r
        try {
            r = await fetch(`${base}/api/home/clip/`, {
                method: 'POST',
                // the key only: with the Kitchen login cookie attached, Kitchen would treat this as a
                // browser form post and reject it (CSRF), before ever looking at the key
                credentials: 'omit',
                headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${token}`},
                body: JSON.stringify(body),
            })
        } catch (e) {
            throw new Error(`Can’t reach Kitchen at ${base}. Are you on your home network?`)
        }
        if (r.status == 401 || r.status == 403) {
            await chrome.storage.local.remove('token')   // revoked or expired: get a fresh one once
            continue
        }
        let j = {}
        try { j = await r.json() } catch (e) { /* empty */ }
        return {status: r.status, body: j}
    }
    throw new SignInNeeded()
}

// ---- screens ---------------------------------------------------------------------------------

function minutes(n) {
    if (!n) return ''
    return n >= 60 ? `${Math.floor(n / 60)} h${n % 60 ? ` ${n % 60} min` : ''}` : `${n} min`
}

function previewCard(p) {
    const facts = [
        p.ingredients ? `${p.ingredients} ingredients` : '',
        p.steps ? `${p.steps} steps` : '',
        p.step_images ? `${p.step_images} step photos` : '',
        p.servings_text || (p.servings ? `serves ${p.servings}` : ''),
        p.working_time ? `${minutes(p.working_time)} active` : '',
        p.working_time + p.waiting_time ? `${minutes(p.working_time + p.waiting_time)} total` : '',
    ].filter(Boolean)
    let host = ''
    try { host = new URL(p.source_url).hostname.replace(/^www\./, '') } catch (e) { /* none */ }
    return `<div class="card">
        ${p.image ? `<img class="hero" src="${esc(p.image)}" alt="">` : ''}
        <div class="body">
            <div class="title">${esc(p.name)}</div>
            ${p.description ? `<div class="desc">${esc(p.description)}</div>` : ''}
            <div class="facts">${facts.map(f => `<span class="chip">${esc(f)}</span>`).join('')}</div>
            <div class="source">From ${esc(host)}</div>
        </div>
    </div>`
}

function showSignIn(base) {
    show(`<div class="state">
        <p><b>Sign in to Kitchen first</b></p>
        <p class="muted small">Then click the Kitchen button again. You only need to do this once.</p>
        <div class="actions" style="justify-content:center"><a class="btn primary" href="${esc(base)}/accounts/login/?next=/" target="_blank">Open Kitchen</a></div>
    </div>`)
}

async function main() {
    const {base} = await settings()
    const tab = await targetTab()
    if (!tab || !/^https?:/.test(tab.url || '')) {
        showError('Open a recipe page, then click the Kitchen button.')
        return
    }
    if (tab.url.startsWith(base)) {
        showError('This is Kitchen itself. Open a recipe on another site.')
        return
    }

    let page
    try {
        const [res] = await chrome.scripting.executeScript({target: {tabId: tab.id}, world: 'MAIN', func: readPage})
        page = res?.result
    } catch (e) {
        showError('Chrome won’t let extensions read this page.')
        return
    }
    if (!page) {
        showError('Couldn’t read this page.')
        return
    }

    showState('Looking for the recipe…')
    let r
    try {
        r = await clip(base, {...page, dry_run: true})
    } catch (e) {
        if (e instanceof SignInNeeded) return showSignIn(base)
        return showError(e.message)
    }
    if (r.status != 200) return showError(r.body.error || 'Kitchen couldn’t read a recipe from this page.')

    const p = r.body.preview
    const dup = p.duplicates?.[0]
    show(`${previewCard(p)}
        ${dup ? `<div class="notice">Already in Kitchen as <a href="${esc(base + dup.url)}" target="_blank">${esc(dup.name)}</a>.</div>` : ''}
        <div class="actions">
            ${dup ? `<a class="btn outline" href="${esc(base + dup.url)}" target="_blank">Open it</a>` : ''}
            <button id="add" class="primary">${dup ? 'Add another copy' : 'Add to Kitchen'}</button>
        </div>`)
    const add = document.getElementById('add')
    add.focus()
    add.addEventListener('click', async () => {
        add.disabled = true
        add.textContent = p.step_images ? 'Saving recipe and photos…' : 'Saving…'
        let s
        try {
            s = await clip(base, {...page, force: !!dup})
        } catch (e) {
            if (e instanceof SignInNeeded) return showSignIn(base)
            add.disabled = false
            add.textContent = 'Try again'
            return showErrorBelow(e.message)
        }
        if (s.status != 201) {
            add.disabled = false
            add.textContent = 'Try again'
            return showErrorBelow(s.body.error || 'Kitchen couldn’t save it.')
        }
        const photos = [s.body.image ? 'photo' : '', s.body.step_images ? `${s.body.step_images} step photos` : ''].filter(Boolean).join(' and ')
        show(`<div class="done">
            <div class="check" aria-hidden="true">✓</div>
            <div class="title">Added to Kitchen</div>
            <p class="muted small">${esc(s.body.name)} · ${s.body.steps} steps${photos ? ` · ${esc(photos)}` : ''}</p>
            <div class="actions" style="justify-content:center"><a id="open" class="btn primary" href="${esc(base + s.body.url)}" target="_blank">Open in Kitchen</a></div>
        </div>`)
        document.getElementById('open').focus()
    })
}

function showErrorBelow(text) {
    let n = document.getElementById('err')
    if (!n) {
        n = document.createElement('div')
        n.id = 'err'
        n.className = 'notice error'
        n.setAttribute('role', 'alert')
        view.appendChild(n)
    }
    n.textContent = text
}

main()
