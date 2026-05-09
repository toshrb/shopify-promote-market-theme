# shopify-promote-market-theme

Small **Python 3** CLI that **merges Shopify Online Store 2.0 market template overrides** into the store-default JSON files, so one market’s layout becomes the main theme.

When you use **Markets**, Shopify can save extra JSON next to a template, for example:

- Store default: `templates/index.json`
- Canada only: `templates/index.context.ca.json`

That context file references a `parent`, a `context.market`, and partial `sections` / `order` data. This tool resolves the same structure the admin would show for that market and **writes the result back into the parent file**. Optionally it **deletes** the `*.context.<market>.json` files after merging so you are left with a flat, single-default theme.

**Requirements:** Python **3.9+** (stdlib only, no pip install).

## What it does

- Finds `templates/*.context.<market>.json` and `sections/*.context.<market>.json`
- For each file, loads the `parent` JSON in the same folder and merges:
  - **`order`** from the context file wins (section order and which sections appear)
  - **`settings`** are shallow-merged per section and block
  - **`blocks` / `block_order`** follow the same override rules as Shopify’s context format
  - **New section IDs** that exist only in the context file are copied in full
- Writes pretty-printed JSON (`sections` then `order`, like typical theme exports)
- Verifies `context.market` in each file matches `--market` so you do not merge the wrong market by mistake
- After a run, **warns** (on stderr) if other markets still have context files pointing at parents you just updated—those deltas were computed against the *old* default and may need a refresh in the admin or a new export

## What it does not do

- No Shopify API calls; run it on a **theme folder** (export, `theme pull`, or git clone)
- Does **not** remove context files for **other** markets (only the `--market` you pass)

## Usage

From anywhere, point `--theme` at your **theme root** (the directory that contains `templates/` and `sections/`):

```bash
python3 /path/to/promote_market_theme.py --theme /path/to/your-theme --market ca
```

Or copy this repo’s script into your theme and run from the theme root:

```bash
cd /path/to/your-theme
python3 /path/to/shopify-promote-market-theme/promote_market_theme.py --theme . --market ca
```

By default, each merged `*.context.<market>.json` is **deleted** after a successful merge. To keep them (for example while testing):

```bash
python3 promote_market_theme.py --theme . --market ca --no-delete-context
```

Preview without changing files:

```bash
python3 promote_market_theme.py --theme . --market ca --dry-run
```

Merge **one** context file only:

```bash
python3 promote_market_theme.py --theme . --market ca \
  --only templates/index.context.ca.json --no-delete-context
```

### Arguments

| Flag | Description |
|------|-------------|
| `--theme` | Theme root directory (default: `.`) |
| `--market` | Market handle; must match `context.market` in each context file (e.g. `ca`, `united-states`) |
| `--dry-run` | Print planned writes/deletes; do not modify files |
| `--only` | Relative path to a single context file under `--theme` |
| `--delete-context` / `--no-delete-context` | Delete context files after merge (default: delete) |

## After merging

1. **Re-open or diff** parent JSON (e.g. `templates/index.json`) to confirm the layout you expect.
2. **Upload** the updated theme (ZIP or Git/GitHub integration) or push with Shopify CLI.
3. If you only promoted **one** market, **other** `*.context.*.json` files may still be in the theme; read the script’s stderr warnings and remove or re-export them if you want a fully flat theme.

## Publishing to GitHub

From this folder (after `git` is initialized and committed):

```bash
cd /path/to/shopify-promote-market-theme
git init
git add README.md LICENSE .gitignore promote_market_theme.py
git commit -m "Initial commit: promote market theme JSON CLI"
git branch -M main
```

Create a new empty repository on GitHub, then:

```bash
git remote add origin https://github.com/YOUR_USER/shopify-promote-market-theme.git
git push -u origin main
```

Or use [GitHub CLI](https://cli.github.com/): `gh repo create shopify-promote-market-theme --public --source=. --push`

## License

See [LICENSE](LICENSE) (MIT).
