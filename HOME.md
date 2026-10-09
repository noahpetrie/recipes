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
