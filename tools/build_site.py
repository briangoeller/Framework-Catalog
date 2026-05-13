#!/usr/bin/env python3
"""Build the framework-catalog static site from JSONL.

Inputs:
  jsonl/batch_*.jsonl                     — Pass II enriched entries
  manifest/framework_catalog_v4_2.csv     — authoritative for carry-forward fields

Output:
  docs/                                   — static site for GitHub Pages
    index.html
    entries/{slug}.html
    static/styles.css
    static/filter.js
    .nojekyll

Design:
  - Pure stdlib (no Jinja2, no external deps).
  - HTML built via small render_*() functions taking dict → string.
  - Carry-forward override: manifest is authoritative for 7 fields; JSONL is
    authoritative for everything else. Mirrors the rule in
    reference/backend_build_commitments.md.

Run from the repo root:
  python3 tools/build_site.py
"""

import csv
import html
import json
import re
import shutil
import sys
import unicodedata
from pathlib import Path
from collections import Counter

CARRY_FORWARD_FIELDS = [
    "name", "aliases", "type", "origin_discipline",
    "rigor_band", "band_notes", "one_line_summary",
]

REPO_ROOT = Path(__file__).resolve().parent.parent
JSONL_DIR = REPO_ROOT / "jsonl"
MANIFEST_CSV = REPO_ROOT / "manifest" / "framework_catalog_v4_2.csv"
TEMPLATE_DIR = REPO_ROOT / "tools" / "templates"
STATIC_DIR = REPO_ROOT / "tools" / "static"
OUTPUT_DIR = REPO_ROOT / "docs"


# ---------------------------------------------------------------------------
# Data loading & override
# ---------------------------------------------------------------------------

def load_entries():
    """Load every JSONL entry, applying manifest override on carry-forward fields."""
    manifest = {}
    with open(MANIFEST_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            manifest[row["name"]] = row

    entries = []
    seen = set()
    # Glob *.jsonl rather than batch_*.jsonl so pass2_test_batch.jsonl is included
    for batch_file in sorted(JSONL_DIR.glob("*.jsonl")):
        with open(batch_file, encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError as e:
                    print(f"  ! parse error in {batch_file.name}:{line_num}: {e}",
                          file=sys.stderr)
                    continue

                name = entry.get("name", "")
                if name in seen:
                    print(f"  ! duplicate name skipped: {name}", file=sys.stderr)
                    continue
                seen.add(name)

                # Carry-forward override: manifest wins on the 7 fields
                if name in manifest:
                    for field in CARRY_FORWARD_FIELDS:
                        if field in manifest[name]:
                            entry[field] = manifest[name][field]

                entry["_slug"] = slugify(name)
                entry["_source_batch"] = batch_file.name
                entries.append(entry)

    entries.sort(key=lambda e: e["name"].lower())
    return entries


def slugify(name):
    """Convert an entry name to a URL-safe slug. Preserves enough to be readable.

    Diacritics are stripped (Café → cafe) so URLs stay ASCII. Display names
    in HTML retain their original Unicode characters.
    """
    # NFKD normalization decomposes combined chars (é → e + combining acute);
    # then drop combining marks. Result is ASCII-ish for most Latin scripts.
    s = unicodedata.normalize("NFKD", name)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = re.sub(r"['\u2019]", "", s)         # apostrophes drop entirely
    s = re.sub(r"[^a-z0-9]+", "-", s)        # everything else → hyphen
    s = re.sub(r"-+", "-", s).strip("-")
    return s or "entry"


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------

def esc(s):
    """Escape for HTML text content."""
    return html.escape(str(s or ""), quote=True)


def confidence_badge(level):
    """Render a small confidence indicator. CSS handles the visual treatment."""
    level = (level or "").lower()
    if level not in ("high", "medium", "low"):
        return f'<span class="conf conf-missing">{esc(level)}</span>'
    return f'<span class="conf conf-{level}">{esc(level)}</span>'


def semicolon_list(value, render_item=esc):
    """Render a semicolon-separated string as a comma-joined list of escaped items."""
    if not value:
        return ""
    items = [item.strip() for item in str(value).split(";") if item.strip()]
    return ", ".join(render_item(item) for item in items)


def lineage_links(value, slug_lookup):
    """Render lineage references with links to the target entry where it exists."""
    if not value:
        return ""
    parts = []
    for item in [s.strip() for s in str(value).split(";") if s.strip()]:
        target = slug_lookup.get(item.lower())
        if target:
            parts.append(f'<a href="{target}.html">{esc(item)}</a>')
        else:
            parts.append(f'<span class="lineage-unresolved">{esc(item)}</span>')
    return ", ".join(parts)


def needs_verification_marker(entry):
    if entry.get("needs_verification") in (True, "true", "True"):
        return ' <span class="needs-verify-marker" title="Flagged for verification">⚑</span>'
    return ""


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

def load_template(name):
    return (TEMPLATE_DIR / name).read_text(encoding="utf-8")


def render_entry_page(entry, slug_lookup, template):
    nv = entry.get("needs_verification") in (True, "true", "True")

    fields_html = f"""
<header class="entry-header">
  <p class="breadcrumb"><a href="../index.html">← Catalog</a></p>
  <h1>{esc(entry["name"])}{needs_verification_marker(entry)}</h1>
  {f'<p class="aliases">Also known as: {esc(entry["aliases"])}</p>' if entry.get("aliases") else ""}
  <p class="meta">
    <span class="meta-type">{esc(entry.get("type", ""))}</span> ·
    <span class="meta-discipline">{esc(entry.get("origin_discipline", ""))}</span> ·
    <span class="meta-band">{esc(entry.get("rigor_band", ""))}</span>
  </p>
  <p class="one-liner">{esc(entry.get("one_line_summary", ""))}</p>
</header>

<section class="extended-summary">
  <p>{esc(entry.get("extended_summary", ""))}</p>
</section>

<section class="metadata-grid">
  <div class="field">
    <h3>Originators</h3>
    <p>{esc(entry.get("originators", "—"))} {confidence_badge(entry.get("originators_confidence"))}</p>
  </div>
  <div class="field">
    <h3>Year / Decade</h3>
    <p>{esc(entry.get("year_or_decade", "—"))} {confidence_badge(entry.get("year_confidence"))}</p>
  </div>
  <div class="field">
    <h3>Primary sources</h3>
    <p>{semicolon_list(entry.get("primary_sources", ""))} {confidence_badge(entry.get("sources_confidence"))}</p>
  </div>
  {('<div class="field"><h3>Band notes</h3><p>' + esc(entry.get("band_notes", "")) + "</p></div>") if entry.get("band_notes") else ""}
</section>

<section class="field-block">
  <h3>Core components</h3>
  <ul>{"".join(f"<li>{esc(c.strip())}</li>" for c in entry.get("core_components", "").split(";") if c.strip())}</ul>
</section>

<section class="field-block">
  <h3>Primary use case</h3>
  <p>{esc(entry.get("primary_use_case", ""))}</p>
</section>

<section class="field-block">
  <h3>Common criticisms</h3>
  <ul>{"".join(f"<li>{esc(c.strip())}</li>" for c in entry.get("common_criticisms", "").split(";") if c.strip())}</ul>
</section>

<section class="lineage">
  <h3>Lineage</h3>
  <dl>
    {('<dt>Parent of</dt><dd>' + lineage_links(entry.get("parent_of",""), slug_lookup) + '</dd>') if entry.get("parent_of") else ''}
    {('<dt>Child of</dt><dd>' + lineage_links(entry.get("child_of",""), slug_lookup) + '</dd>') if entry.get("child_of") else ''}
    {('<dt>Siblings</dt><dd>' + lineage_links(entry.get("siblings",""), slug_lookup) + '</dd>') if entry.get("siblings") else ''}
    {('<dt>Derived from</dt><dd>' + lineage_links(entry.get("derived_from",""), slug_lookup) + '</dd>') if entry.get("derived_from") else ''}
  </dl>
</section>

{('<aside class="needs-verify-banner">This entry is flagged for verification. Originator, date, or source attribution is uncertain.</aside>') if nv else ''}

<footer class="entry-footer">
  <p>Source batch: <code>{esc(entry.get("_source_batch", ""))}</code></p>
</footer>
"""
    return (template
        .replace("<!--TITLE-->", esc(entry["name"]) + " — Framework Catalog")
        .replace("<!--STATIC_PREFIX-->", "../static")
        .replace("<!--CONTENT-->", fields_html))


def render_index_page(entries, template):
    """Render the searchable/filterable index page."""
    # Build the option lists for filter dropdowns
    disciplines = sorted({e.get("origin_discipline", "") for e in entries if e.get("origin_discipline")})
    types = sorted({e.get("type", "") for e in entries if e.get("type")})
    bands = sorted({e.get("rigor_band", "") for e in entries if e.get("rigor_band")})

    def options(values):
        return "".join(f'<option value="{esc(v)}">{esc(v)}</option>' for v in values)

    # Each entry card
    cards = []
    for e in entries:
        nv = e.get("needs_verification") in (True, "true", "True")
        cards.append(f"""
<article class="entry-card"
  data-discipline="{esc(e.get('origin_discipline',''))}"
  data-type="{esc(e.get('type',''))}"
  data-band="{esc(e.get('rigor_band',''))}"
  data-orig-conf="{esc(e.get('originators_confidence',''))}"
  data-year-conf="{esc(e.get('year_confidence',''))}"
  data-src-conf="{esc(e.get('sources_confidence',''))}"
  data-needs-verify="{'true' if nv else 'false'}"
  data-search="{esc((e.get('name','') + ' ' + e.get('aliases','') + ' ' + e.get('one_line_summary','')).lower())}">
  <h2><a href="entries/{e['_slug']}.html">{esc(e['name'])}</a>{needs_verification_marker(e)}</h2>
  <p class="card-meta">
    <span>{esc(e.get('type',''))}</span> ·
    <span>{esc(e.get('origin_discipline',''))}</span> ·
    <span>{esc(e.get('rigor_band',''))}</span>
  </p>
  <p class="card-summary">{esc(e.get('one_line_summary',''))}</p>
  <p class="card-conf">
    orig {confidence_badge(e.get('originators_confidence'))}
    year {confidence_badge(e.get('year_confidence'))}
    src {confidence_badge(e.get('sources_confidence'))}
  </p>
</article>""")

    filters_html = f"""
<section class="filters">
  <input type="search" id="search" placeholder="Search name, alias, or summary..." autocomplete="off" />
  <select id="filter-discipline"><option value="">All disciplines</option>{options(disciplines)}</select>
  <select id="filter-type"><option value="">All types</option>{options(types)}</select>
  <select id="filter-band"><option value="">All rigor bands</option>{options(bands)}</select>

  <fieldset class="conf-filters">
    <legend>Min confidence level (each must be at least)</legend>
    <label>Originators
      <select id="filter-orig-conf">
        <option value="">any</option><option value="high">high</option>
        <option value="medium">medium+</option><option value="low">low+</option>
      </select>
    </label>
    <label>Year
      <select id="filter-year-conf">
        <option value="">any</option><option value="high">high</option>
        <option value="medium">medium+</option><option value="low">low+</option>
      </select>
    </label>
    <label>Sources
      <select id="filter-src-conf">
        <option value="">any</option><option value="high">high</option>
        <option value="medium">medium+</option><option value="low">low+</option>
      </select>
    </label>
  </fieldset>

  <fieldset class="verify-filter">
    <legend>Verification status</legend>
    <label><input type="radio" name="verify" value="" checked /> all</label>
    <label><input type="radio" name="verify" value="true" /> flagged only</label>
    <label><input type="radio" name="verify" value="false" /> unflagged only</label>
  </fieldset>

  <p class="filter-status"><span id="result-count">{len(entries)}</span> of {len(entries)} entries shown</p>
</section>
"""

    index_html = f"""
<header class="site-header">
  <h1>Framework Catalog</h1>
  <p class="subtitle">{len(entries)} entries across {len(disciplines)} disciplines. Pass II enrichment baseline.</p>
</header>
{filters_html}
<section class="entry-list">
{"".join(cards)}
</section>
"""
    return (template
        .replace("<!--TITLE-->", "Framework Catalog")
        .replace("<!--STATIC_PREFIX-->", "static")
        .replace("<!--CONTENT-->", index_html))


# ---------------------------------------------------------------------------
# Build orchestration
# ---------------------------------------------------------------------------

def build():
    print(f"Loading entries...")
    entries = load_entries()
    print(f"  {len(entries)} entries loaded")

    # Build slug lookup for lineage resolution (case-insensitive on name)
    slug_lookup = {e["name"].lower(): "../entries/" + e["_slug"] for e in entries}

    # Clean output dir
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    (OUTPUT_DIR / "entries").mkdir(parents=True)
    (OUTPUT_DIR / "static").mkdir(parents=True)

    # Copy static assets
    for static_file in STATIC_DIR.iterdir():
        shutil.copy(static_file, OUTPUT_DIR / "static" / static_file.name)
    print(f"  static assets copied")

    # Load templates
    base_template = load_template("base.html")

    # Render entries
    for entry in entries:
        page = render_entry_page(entry, slug_lookup, base_template)
        (OUTPUT_DIR / "entries" / f"{entry['_slug']}.html").write_text(page, encoding="utf-8")
    print(f"  {len(entries)} entry pages rendered")

    # Index uses a different slug-lookup prefix (no ../)
    index_slug_lookup = {k: v.replace("../entries/", "entries/") for k, v in slug_lookup.items()}
    index_page = render_index_page(entries, base_template)
    # Fix the prefix in the rendered index (lineage in cards isn't used yet but future-proof)
    (OUTPUT_DIR / "index.html").write_text(index_page, encoding="utf-8")
    print(f"  index page rendered")

    # Nojekyll for GitHub Pages (so it doesn't try to process us as Jekyll)
    (OUTPUT_DIR / ".nojekyll").write_text("", encoding="utf-8")

    # Summary stats
    print()
    print(f"Output: {OUTPUT_DIR.relative_to(REPO_ROOT)}/")
    disciplines = Counter(e.get("origin_discipline", "") for e in entries)
    print(f"Disciplines: {len(disciplines)}")
    nv_count = sum(1 for e in entries
                   if e.get("needs_verification") in (True, "true", "True"))
    print(f"needs_verification flagged: {nv_count}")


if __name__ == "__main__":
    build()
