*Disclaimer: The below readme, and all of the code in this repository were written by AI (Cursor in auto mode). I have personally tested this on a theme and it works, but use this at your own discretion.*
# shopify-promote-market-theme

A basic python3 program that allows you to promote a market-customized theme on Shopify to be your default theme. As of the time of publishing, Shopify does not allow you to merge a market customized theme or any part of it to the store default theme. Thus, when Shopify users accidentally customize a theme under a specific market, and want it to be the default option, they have to redo all the work. This script merges your market customization (with granularity of single file or entire theme) into the store default.  

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
