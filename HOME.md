# noahpetrie/recipes: home fork of Tandoor

This fork runs the household Tandoor at https://tandoor.madiba.ca. It is the upstream
release plus a few small commits on the `home` branch. Source for this modified version is
public here, as the AGPL requires.

## What's different from upstream

- **Cmd+K / Cmd+S on macOS.** Global search opens with Cmd+K (Ctrl+K still works) and the
  hint chip shows ⌘K on Apple devices; Cmd+S saves in model editors.
- **Modernized look.** System font (SF Pro on Apple), sentence-case buttons and tabs,
  hairline borders instead of heavy shadows, softer corners, a clean surface app bar
  (only when the nav colour is still the stock `#ddbf86`), pill-shaped navigation and
  keyword chips, a command-palette style search dialog, a deeper terracotta accent that
  passes WCAG AA, refined dark palette, and a light wordmark logo for dark mode.

- **Simpler meal plan dialog.** One column (recipe or title, then date, then details),
  readable date label with arrows and a calendar, day/servings steppers, meal type
  preselected, note behind "Add note", narrower dialog; editors get Cancel and solid
  Create/Save.
- **Pages.** Lighter sidebar; page headers as titles (Database, lists, Pantry, Books);
  icon-chip tiles; outlined form fields; rounded tables; rebuilt Books page with a
  working filter and empty state; pill Settings navigation; "Today / Tomorrow" meal
  plan strip on the home page.
- **Cooking view.** Numbered steps with a round done-check, larger instruction text,
  ingredient notes inline, ticked ingredients struck through, one-line provenance;
  cleaner editor header, calendar (today pill) and shopping list.

- **Books: cookbooks and collections.** A book is either a printed **Cookbook** (author and
  cover photo, shown as a shelf of covers) or a **Collection** of your own recipes (shown as
  albums with a collage of their photos). Adds `kind`, `author` and `cover` to RecipeBook
  (migration `0243_home_recipebook_kind_author_cover`) and a `PUT /api/recipe-book/{id}/cover/`
  action. **On upstream updates:** if upstream adds its own 0243, add a merge migration.
  Opening a book shows its recipes as a grid of recipe cards (BookViewPage.vue); upstream's
  two-up pager with each recipe's ingredient table (BookEntryCard.vue) is no longer used.
- **Right-click menus.** Recipe cards and planned meals on the home page open their menu at
  the pointer (Shift+right-click keeps the browser's). New "Add to book" dialog; planned meals
  get Open recipe / Edit / shopping / book / Remove from plan.
- **Plan a meal.** Pick a recipe from photos of the most recent ones; "No recipe?" reveals
  the title field; Cancel discards without the leave-page prompt.
- **shadcn/ui-style controls.** Compact 40px outlined fields with a focus ring, segmented
  tabs, flat buttons, 6px badges, sentence-case labels, shadcn-style menus. Warm palette kept.

- **White label ("Kitchen").** A space's `app_name` (now in the space API and Space Settings
  → App name) replaces "Tandoor" in the toolbar (space icon + name), browser tab titles
  ("Books · Kitchen") and the sign-in page; icons come from the space's logo fields.
- **Account details** live in the account menu, not the top of the sidebar.
- **Meal plan calendar.** Right-click menu on entries, wrapped names, items clear of the
  day number, shadcn-style toolbar (Today, ‹ ›, date button with picker); compact date
  pickers app-wide; quieter dialog header/footer and secondary buttons.

- **Pantry scanning** (cookbook/views/home_pantry.py, PantryScanPanel.vue, StockCountPage.vue).
  A scan *finds* things; stock changes only through an explicit Add / Count / Use / Move / Edit,
  each previewed, logged (who, reason) and undoable. Retail barcodes live on Food (`barcodes`,
  `product_info`; looked up on Open Food Facts → UPCitemDB); pantry label codes identify one
  batch. Modes: Look up (default), Restock (optional quick add), Stock count (draft counts,
  review page, per-line apply with conflict checks; uncounted ≠ zero). Writes take a request id
  (idempotent) and absolute counts an expected value (409 on stale). Handheld scanners work
  anywhere (HardwareScanner.vue); camera via barcode-detector. Migrations 0244–0245.
  Barcodes match with leading zeros ignored (`barcode_q`, home.15): a camera reads UPC-A
  876131001243 as EAN-13 0876131001243.
  The panel is a side drawer (full screen on phones): product overview (on hand, per location,
  earliest expiry) → Add stock / Set quantity / Use / remove / View batches screens; zero stock
  offers Add to shopping; unknown barcodes offer Create product prefilled from the lookup; item
  labels open that one item (Item label mode forces label lookups). A scan arriving during an
  unsaved edit asks to discard or waits ("Finish this first"); a retail barcode scanned into a
  panel field is taken as a scan and the field restored. Scanner status pill in the Pantry header.
- **Cookbooks from Homebox** (`manage.py sync_homebox_cookbooks`, run every 5 min by launchd in
  home-site): Homebox books tagged "Cookbook" (auto-tagged once from Open Library subjects)
  appear on the Books shelf with cover, author and description.

- **"Add to Kitchen" Chrome extension** (`browser-extension/`, see its README). Saves the recipe
  on the current tab via `POST /api/home/clip/` (cookbook/views/home_clip.py): ChefSteps recipes
  from the page data — members-only ones through ChefSteps' own loader with the browser's
  sign-in — with step photos, °F/°C, equipment, tips and video link; other sites through the
  normal scraper. Access key from `GET /api/home/extension-token/` (session login). Step photos
  shown at card size.

- **Groceries in, shopping out** (home.13):
  - *Add groceries* (`/pantry/groceries`, `cookbook/views/home_groceries.py`): tick what you
    bought or paste a receipt / order email (`POST /api/home/groceries/match/`); each item gets a
    place (Pantry/Fridge/Freezer) and expiry from `cookbook/helper/home_aisles.py`, and the whole
    shop is booked through the pantry's own add (logged, undoable).
  - Staples: one-tap setup on /cook (suggested staples preselected; `POST /api/home/staples/`
    takes `foods: [ids]`).
  - Shopping leaves out staples *and* foods in the pantry: `shopping_helper.get_recipe_ingredients`
    (meal plan auto-add, Shop for the week) and the Add to shopping dialog (`GET /api/home/kitchen/`).
    *Shop for the week* on the meal plan (`POST /api/home/shop-plan/`).
  - Aisles: `manage.py home_shop_setup` removes open data's sample supermarkets, adds one
    "Grocery store" in store-walk order and fills missing food aisles; new foods get one
    automatically (`fill_new_food`). The shopping list picks the store when there is only one.
  - Start page: Use it up / Ready to cook / Almost ready rows (`HomeKitchenRows.vue`); the
    repeating recipe rows only appear in bigger libraries. Times read "7 h 30 min"
    (`utils/home_format.ts`), nutrition is rounded.

- **Simpler screens** (home.16–17):
  - Pantry: one-line rows that load 40 more as you scroll (no pagination), full width.
  - Sidebar: Home, Meal Plan, Ready to Cook (`/cook`, was "What can I make"), Shopping, Pantry,
    Books. Search is the top bar's ⌘K, Import is in the + menu, Database and Settings are in the
    account menu; no version footer. The ☰ button left of the logo collapses it to icons
    (`localStorage` `home-sidebar-rail`). Phones get Pantry in the bottom bar.
  - Meal plan: Auto-Planner, view options and the calendar feed in the calendar toolbar
    (`MealPlanCalendarHeader.vue`) instead of the sidebar.
  - Shopping: page title with items left, labelled Select/Undo, 44px rows with an amount column
    and an empty circle to tick off, light aisle labels.

- **Equipment** (home.30; `cookbook/helper/home_equipment.py`, `cookbook/views/home_equipment.py`,
  `EquipmentPage.vue`, `RecipeEquipmentCard.vue`, migration `0247_home_equipment`). Like Mealie's "tools":
  - `Equipment` (a general kind such as *Stand mixer*, or a product filed under one) and `RecipeEquipment`
    (recipe, equipment, optional, size note). Kinds come from `CATALOG`; basic cookware and supplies start owned.
  - A need is met by the piece, anything under it, another product of the same kind (ChefSteps' Smart Oven
    Air Fryer Pro → your Smart Oven Air), or a kind that does the job (stand mixer covers hand mixer).
  - Each recipe is read once (`Recipe.equipment_checked`): a ChefSteps/website "Equipment" step (website
    imports add one from schema.org `tool`) becomes the list and the step is removed; otherwise the step text
    is scanned ("a blender or food processor" → both optional).
  - `sync_homebox_cookbooks` also brings every Homebox item in the Kitchen location over as owned equipment
    (unknown kinds come over hidden); items that leave the Kitchen stop counting. Homebox decides "owned" for those.
  - Recipe page card (✓ / don't have, "I have this", edit list), `/equipment` page (Recipes need / You have / All),
    Ready to Cook and the start-page rows count missing equipment like missing ingredients.
  - API: `GET/POST /api/home/equipment/`, `PATCH/DELETE /api/home/equipment/<id>/`,
    `GET/PUT /api/home/equipment/recipe/<id>/`; `cookable` returns `equipment_missing`.

Almost all of the styling lives in `vue3/src/home-theme.css` and the palette/defaults in
`vue3/src/vuetify.ts`, so upstream merges rarely conflict.

## Updating to a new upstream release

```bash
git fetch upstream --tags
git rebase --onto <new-tag> <old-tag> home      # replay the home commits
cd vue3 && npm ci && npm run build && cd ..
docker build -t home/tandoor:<new-tag>-noah1 .
```

Then back up the database, change the image tag in
`~/Developer/home-site/docker/compose.yml`, and `docker compose up -d tandoor`.
