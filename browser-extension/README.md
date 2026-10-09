# Add to Kitchen (Chrome extension)

Saves the recipe on the page you're looking at to Kitchen (https://kitchen.madiba.ca), with its
steps, ingredients, photos (including step photos) and a link back to where it came from.

- **ChefSteps**: reads the recipe data from your open tab, so members-only recipes work when
  you're signed in to ChefSteps in Chrome.
- **Other sites**: sends the page to Kitchen's normal recipe importer (schema.org / recipe-scrapers).
- Already saved? It says so and links to the copy in Kitchen.

## Install

1. Chrome → `chrome://extensions` → turn on **Developer mode** (top right).
2. **Load unpacked** → choose this folder (`~/Developer/kitchen/browser-extension`).
3. Pin it: puzzle-piece icon in the toolbar → pin **Add to Kitchen**.
4. Be signed in to Kitchen in Chrome. The first save creates the extension's own access key
   (Kitchen → Settings → API lists it; delete it there to revoke).

Kitchen is only reachable on the home network, so the extension works at home.

## How it works

- `popup.js` reads the page in the tab (`chrome.scripting`, only after you click the button),
  then posts it to `POST /api/home/clip/` — first as a preview (`dry_run`), then to save.
- The access key comes from `GET /api/home/extension-token/` using your Kitchen login cookie;
  saves send only the key (`credentials: 'omit'`) so Django's CSRF check doesn't apply.
- The conversion (ChefSteps JSON → Tandoor recipe, temperatures, step photos) lives in
  `cookbook/views/home_clip.py`.
