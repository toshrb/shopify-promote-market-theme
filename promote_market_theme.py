#!/usr/bin/env python3
"""
Promote Shopify theme market context JSON into the parent (store default) file.

Examples (run from your theme root, or pass --theme /path/to/theme):
  Dry-run merge for homepage only:
    python3 promote_market_theme.py --theme . --market ca \\
      --only templates/index.context.ca.json --dry-run

  Apply homepage merge (keeps context file):
    python3 promote_market_theme.py --theme . --market ca \\
      --only templates/index.context.ca.json --no-delete-context

  Promote one market everywhere under templates/ and sections/, remove its context files:
    python3 promote_market_theme.py --theme . --market ca

After promoting one market, other *.context.*.json files for the same parents may be
stale until re-edited in the admin. The script prints warnings for those files.

Verify a homepage merge before uploading:
  grep -n video_XCaME templates/index.json && grep -n 17409511130d7d5b7b templates/index.json
If those lines are missing, index.json was not merged (wrong directory, reverted file,
or a fresh theme download from Shopify overwrote local changes).
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def write_json_pretty(path: Path, data: dict[str, Any]) -> None:
    text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    path.write_text(text, encoding="utf-8")


def merge_settings(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    out.update(overlay)
    return out


def merge_block(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(base)
    if "type" in overlay:
        result["type"] = overlay["type"]
    if "disabled" in overlay:
        result["disabled"] = overlay["disabled"]
    result["settings"] = merge_settings(
        base.get("settings", {}), overlay.get("settings", {})
    )
    for key, val in overlay.items():
        if key in ("type", "settings", "disabled"):
            continue
        result[key] = copy.deepcopy(val)
    return result


def merge_section(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    if not overlay:
        return copy.deepcopy(base)

    result = copy.deepcopy(base)
    if "type" in overlay:
        result["type"] = overlay["type"]
    if "disabled" in overlay:
        result["disabled"] = overlay["disabled"]
    if "custom_css" in overlay:
        result["custom_css"] = overlay["custom_css"]

    result["settings"] = merge_settings(
        base.get("settings", {}), overlay.get("settings", {})
    )

    base_blocks = base.get("blocks") or {}
    overlay_blocks = overlay.get("blocks") or {}

    if "block_order" in overlay:
        block_order = overlay["block_order"]
    else:
        block_order = base.get("block_order") or []

    merged_blocks: dict[str, Any] = {}
    for bid in block_order:
        bo = overlay_blocks.get(bid)
        bb = base_blocks.get(bid)
        if bb is not None and bo is not None:
            merged_blocks[bid] = merge_block(bb, bo)
        elif bb is not None:
            merged_blocks[bid] = copy.deepcopy(bb)
        elif bo is not None:
            merged_blocks[bid] = copy.deepcopy(bo)
        else:
            raise ValueError(
                f"Block {bid!r} missing from both parent and context section data"
            )

    result["blocks"] = merged_blocks
    result["block_order"] = list(block_order)

    handled = {
        "type",
        "disabled",
        "custom_css",
        "settings",
        "blocks",
        "block_order",
    }
    for key, val in overlay.items():
        if key in handled:
            continue
        result[key] = copy.deepcopy(val)

    return result


def merge_theme_payload(parent: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    overlay_sections = context.get("sections") or {}
    final_order = context.get("order")
    if final_order is None:
        final_order = parent.get("order") or []

    parent_sections = parent.get("sections") or {}
    merged_sections: dict[str, Any] = {}

    for sec_id in final_order:
        if sec_id in parent_sections:
            overlay = overlay_sections.get(sec_id, {})
            merged_sections[sec_id] = merge_section(parent_sections[sec_id], overlay)
        elif sec_id in overlay_sections:
            merged_sections[sec_id] = copy.deepcopy(overlay_sections[sec_id])
        else:
            raise ValueError(
                f"Section {sec_id!r} is listed in order but missing from "
                f"parent and context sections"
            )

    # Key order matches Shopify theme exports: sections before order (and
    # name/type first for section groups) so Admin diffs reflect real edits.
    result: dict[str, Any] = {}
    if "name" in parent:
        result["name"] = parent["name"]
    if "type" in parent:
        result["type"] = parent["type"]
    result["sections"] = merged_sections
    result["order"] = list(final_order)
    return result


def validate_context_market(data: dict[str, Any], expected: str, path: Path) -> None:
    ctx = data.get("context")
    if not isinstance(ctx, dict):
        raise SystemExit(f"{path}: missing or invalid 'context' object")
    found = ctx.get("market")
    if found != expected:
        raise SystemExit(
            f"{path}: context.market is {found!r}, expected {expected!r} "
            f"(refusing to run)"
        )


def find_context_files_for_market(theme_root: Path, market: str) -> list[Path]:
    out: list[Path] = []
    for sub in ("templates", "sections"):
        d = theme_root / sub
        if d.is_dir():
            out.extend(sorted(d.glob(f"*.context.{market}.json")))
    return sorted(out)


def find_stale_other_market_contexts(
    theme_root: Path,
    promoted_market: str,
    updated_parent_paths: set[Path],
) -> list[tuple[Path, str]]:
    """Return (context_path, market) for non-promoted context files targeting updated parents."""
    warnings: list[tuple[Path, str]] = []
    for sub in ("templates", "sections"):
        d = theme_root / sub
        if not d.is_dir():
            continue
        for p in d.glob("*.context.*.json"):
            stem = p.name[: -len(".json")]
            if stem.endswith(f".context.{promoted_market}"):
                continue
            try:
                data = load_json(p)
            except (OSError, json.JSONDecodeError) as e:
                print(f"Warning: could not read {p}: {e}", file=sys.stderr)
                continue
            parent_name = data.get("parent")
            if not parent_name or not isinstance(parent_name, str):
                continue
            parent_path = d / parent_name
            if parent_path not in updated_parent_paths:
                continue
            m = (data.get("context") or {}).get("market", "?")
            warnings.append((p, str(m)))
    return sorted(warnings, key=lambda x: str(x[0]))


def process_one(
    theme_root: Path,
    context_path: Path,
    market: str,
    dry_run: bool,
    delete_context: bool,
) -> Path:
    """Merge context_path into its parent; return resolved parent path."""
    context_path = (theme_root / context_path).resolve() if not context_path.is_absolute() else context_path
    if not context_path.is_file():
        raise SystemExit(f"Context file not found: {context_path}")

    ctx_data = load_json(context_path)
    validate_context_market(ctx_data, market, context_path)

    parent_name = ctx_data.get("parent")
    if not parent_name or not isinstance(parent_name, str):
        raise SystemExit(f"{context_path}: missing 'parent' string")

    parent_path = (context_path.parent / parent_name).resolve()
    if not parent_path.is_file():
        raise SystemExit(f"Parent JSON not found: {parent_path} (from {context_path})")

    parent_data = load_json(parent_path)
    merged = merge_theme_payload(parent_data, ctx_data)

    rel_parent = parent_path.relative_to(theme_root.resolve())
    rel_ctx = context_path.relative_to(theme_root.resolve())

    if dry_run:
        print(f"[dry-run] would write {rel_parent}")
        if delete_context:
            print(f"[dry-run] would delete {rel_ctx}")
        else:
            print(f"[dry-run] would keep {rel_ctx}")
    else:
        write_json_pretty(parent_path, merged)
        print(f"Wrote {rel_parent}")
        if delete_context:
            context_path.unlink()
            print(f"Deleted {rel_ctx}")
        else:
            print(f"Kept {rel_ctx}")

    return parent_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Merge Shopify theme market context JSON into store-default parent files."
    )
    parser.add_argument(
        "--theme",
        type=Path,
        default=Path("."),
        help="Theme root directory (default: .)",
    )
    parser.add_argument(
        "--market",
        required=True,
        help="Market handle, e.g. ca (must match context.market in each file)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print actions without writing or deleting files",
    )
    parser.add_argument(
        "--only",
        type=str,
        default=None,
        help="Process a single context file path relative to --theme",
    )
    parser.add_argument(
        "--delete-context",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Delete context JSON after a successful merge (default: true)",
    )
    args = parser.parse_args()

    theme_root = args.theme.resolve()
    if not theme_root.is_dir():
        raise SystemExit(f"Not a directory: {theme_root}")

    updated_parents: set[Path] = set()

    if args.only:
        cp = Path(args.only)
        updated_parents.add(
            process_one(
                theme_root,
                cp,
                args.market,
                args.dry_run,
                args.delete_context,
            )
        )
    else:
        files = find_context_files_for_market(theme_root, args.market)
        if not files:
            print(
                f"No files matching *.context.{args.market}.json under "
                f"templates/ or sections/",
                file=sys.stderr,
            )
            sys.exit(1)
        for context_path in files:
            updated_parents.add(
                process_one(
                    theme_root,
                    context_path.relative_to(theme_root),
                    args.market,
                    args.dry_run,
                    args.delete_context,
                )
            )

    stale = find_stale_other_market_contexts(
        theme_root, args.market, updated_parents
    )
    if stale:
        print(
            "\nOther market context files still target parents that were updated. "
            "Their diffs were based on the old default; review or re-export:",
            file=sys.stderr,
        )
        for p, m in stale:
            try:
                rel = p.relative_to(theme_root)
            except ValueError:
                rel = p
            print(f"  {rel} (market={m})", file=sys.stderr)


if __name__ == "__main__":
    main()
