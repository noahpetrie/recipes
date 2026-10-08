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
