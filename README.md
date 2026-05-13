# Framework Catalog

A cross-disciplinary catalog of frameworks, tools, practices, and techniques across 23 disciplines. The current corpus is v4.2 (747 entries: 556 carried forward from v4 + 191 added in Manifest II).

## Repository layout

```
.
├── jsonl/        Pass II enriched entries — production source of truth for content
├── manifest/     Carry-forward CSVs — authoritative for the seven core fields
└── docs/         Methodology and architectural decisions
```

## Source of truth

Per `docs/backend_build_commitments.md`:

- **JSONL files** are the production source of truth for enriched entry content.
- **The manifest CSV** is authoritative for the seven carry-forward fields: `name`, `aliases`, `type`, `origin_discipline`, `rigor_band`, `band_notes`, `one_line_summary`. Ingestion applies this override.
- **SQLite** (built downstream from JSONL) is a derived artifact, not a primary store. It can be rebuilt from these files at any time.

## Status

Pass II enrichment complete across 44 batches. Pass III is anticipated but not yet scoped. The backend build (schema, ingestion, alpha reader) is the next planned phase — see `docs/backend_build_commitments.md` for the schema decisions already committed.
