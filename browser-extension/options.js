const DEFAULT_BASE = 'https://kitchen.madiba.ca'
const base = document.getElementById('base')
const msg = document.getElementById('msg')

function say(text) {
    msg.hidden = false
    msg.textContent = text
}

chrome.storage.local.get(['base']).then(s => { base.value = s.base || DEFAULT_BASE })

document.getElementById('save').addEventListener('click', async () => {
    const value = base.value.trim().replace(/\/+$/, '') || DEFAULT_BASE
    try {
        new URL(value)
    } catch (e) {
        return say('That doesn’t look like a web address.')
    }
    // a Kitchen other than kitchen.madiba.ca (e.g. the test copy) needs Chrome's permission once
    if (value != DEFAULT_BASE) {
        const ok = await chrome.permissions.request({origins: [new URL(value).origin + '/*']})
        if (!ok) return say('Chrome needs your permission for the extension to reach that address.')
    }
    const old = (await chrome.storage.local.get(['base'])).base || DEFAULT_BASE
    await chrome.storage.local.set({base: value})
    if (value != old) await chrome.storage.local.remove('token')  // a key belongs to one Kitchen
    say('Saved.')
})

document.getElementById('reset').addEventListener('click', async () => {
    await chrome.storage.local.remove('token')
    say('Forgotten. The next save signs in again with your Kitchen login.')
})
