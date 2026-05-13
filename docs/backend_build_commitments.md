# Framework Catalog — Back End Build Commitments

This document captures the schema and architectural decisions made before back-end build work begins. It is intended for use as project knowledge in the build thread so the decisions don't get re-litigated under build pressure.

The reasoning behind each commitment is explicit because future build conversations may want to revisit specific calls — but the burden of proof should rest on changes from these defaults, not on defending them.

---

## Context

The framework catalog at the time of this document is v4.2 (747 entries: 556 carried forward from v4 + 191 added in Manifest II). Pass II enrichment produces a 22-field JSON record per entry. Pass III is anticipated but not yet defined.

The catalog has two distinct intended uses:

1. **Practitioner reference** — browsing, search, lineage navigation, cross-discipline discovery. The alpha reader serves this audience.
2. **Cross-discipline meta-analysis** — structural and network-analytic study of frameworks themselves as a corpus. This is a longer-term direction enabled by the catalog's structured shape, particularly its rigor-band tagging and lineage assertions.

The schema commitments below are designed to support both uses. The meta-analytical use case has stricter normalization requirements than the practitioner use case alone would justify, but the commitments don't compromise the practitioner case — they just require slightly more careful ingestion.

---

## Architectural commitments

### Storage substrate

**SQLite as the canonical database.** Single file, no server, full-text search built in, scales easily past 100k entries, portable to Postgres if needed later. Anyone advocating for Postgres or graph databases at this scale is over-engineering.

**JSONL files remain the production source of truth for content.** The database is built by ingesting JSONL files; the JSONL files are not derived from the database. This keeps the existing pass II workflow intact and ensures the catalog can be rebuilt from scratch if the database is corrupted.

**Manifest CSV remains the carry-forward source for the seven core fields.** Per the pass II methodology document's carry-forward override pattern: the manifest is authoritative for `name`, `aliases`, `type`, `origin_discipline`, `rigor_band`, `band_notes`, and `one_line_summary`. Ingestion applies this override.

### Deployment

**Static site generation is preferred for the alpha reader** unless dynamic features specifically require an API. At 750 entries with infrequent updates, static generation produces a faster, cheaper, more durable surface than a live-queried API. Migration to dynamic later is straightforward; starting dynamic adds complexity without clear benefit at current scale.

**Public deployment from day one.** The catalog is meant to be shared. Local-only is not the target.

---

## Schema commitments (non-negotiable)

These are the schema decisions where future flexibility depends on getting them right at ingestion time. Migration from these patterns later is painful; locking them now is essentially free.

### 1. Lineage as edges, not strings

**Decision:** A `lineage_edges` table with one row per directed lineage relationship: `(source_entry, target_entry, relation_type)`, where `relation_type` is one of `parent_of`, `child_of`, `siblings`, `derived_from`.

**Reasoning:** Storing lineage as semicolon-separated strings on the entries table works for rendering individual entries but kills graph queries. Every analytical use case — graph traversal, betweenness centrality, lineage depth, cross-discipline bridge detection, ancestry chains — requires lineage to be queryable as a graph. The edge table is the foundational normalization that makes all downstream analytical work possible.

**Implementation note:** Ingestion parses the four lineage fields from each enriched JSON record into edge rows. The validator confirms every target_entry exists in the entries table before commit. The original semicolon-separated strings can be retained as denormalized columns on entries for direct rendering, but the edge table is the source of truth for queries.

### 2. Disciplines and rigor bands as lookup tables

**Decision:** `disciplines` and `rigor_bands` tables, each with rows for the canonical values, foreign-keyed from the entries table.

**Reasoning:** Treating them as free strings is fragile (typos go undetected) and forecloses adding metadata to disciplines and bands themselves later. Lookup tables let us attach descriptions, related-discipline pointers, parent disciplines, band-specific styling, and other metadata to these as first-class entities.

**Implementation note:** Ingestion validates that every entry's discipline and rigor_band already exists in the lookup tables. Adding new disciplines or bands requires explicit insertion into the lookup tables first, which catches accidental drift.

### 3. Originators as a separate table

**Decision:** A `people` table with one row per unique originator (name + optional metadata like discipline of origin, lifespan), and an `entry_originators` table joining entries to people.

**Reasoning:** Storing originators as semicolon-separated strings prevents queries like "all frameworks originated by Herbert Simon," "highest-betweenness originators across disciplines," "decade distribution of originators per discipline," or "originators who appear in three or more disciplines." These are core meta-analytical queries.

**Implementation note:** Ingestion is harder here because the same person can be referenced with name variations across entries (e.g., "Herbert Simon" vs "Herbert A. Simon" vs "H.A. Simon"). The ingestion script needs a name-normalization step with a manual disambiguation file for known cases. This is one of the places where ingestion judgment matters most.

### 4. Criticisms as structured items, not concatenated strings

**Decision:** A `criticisms` table with one row per criticism per entry, with optional fields for `cited_author`, `cited_year`, `cited_work`, and `criticism_text`.

**Reasoning:** Pass II produced semicolon-separated criticism strings often containing named scholars and embedded citations. Parsing these into structured rows enables queries like "what proportion of management frameworks have substantial published critique," "which scholars are cited as critics across the most disciplines," and "what is the time distribution of when frameworks first received documented critique." These are central to the calibration-of-epistemic-claims meta-analysis use case.

**Implementation note:** Parsing isn't perfectly clean. Some criticisms cite specific authors and years; others are general. The schema should allow null `cited_author`/`cited_year` for unattributed criticisms. The ingestion script's parsing should be conservative — when in doubt, treat the whole criticism as text without extracting citation, rather than producing wrong attribution.

### 5. Primary sources as their own table

**Decision:** A `sources` table with one row per unique source (author, year, title, type), and an `entry_sources` table joining entries to sources.

**Reasoning:** Same pattern as originators and criticisms. Citation analysis becomes possible — which sources are cited by the most entries, which sources bridge disciplines, which periods produced foundational works that still anchor multiple frameworks. Without normalization, these queries require parsing semicolon-separated strings every time.

**Implementation note:** Source `type` is one of `book`, `article`, `dissertation`, `standards_document`, `report`, or `other`. Ingestion infers type from format heuristics with manual override available. Same de-duplication challenge as people — "Porter, M.E. (1980). Competitive Strategy" and "Porter, Michael E. (1980). Competitive Strategy" need to resolve to the same source row.

### 6. Per-field confidence and metadata preserved as queryable fields

**Decision:** All confidence flags (`originators_confidence`, `year_confidence`, `sources_confidence`), the `needs_verification` boolean, `band_notes`, and `manifest_version_added` flow into the database as first-class queryable columns on the entries table. None of these get collapsed or discarded during ingestion.

**Reasoning:** Meta-analytical questions like "what proportion of structured-empirical entries have low source confidence" or "which disciplines have the highest proportion of needs_verification flags" require these fields to be queryable. Treating them as ingestion-time logging that doesn't survive into the database loses substantial signal.

---

## Schema commitments (strong defaults, revisable with reason)

These are decisions where the default is clear but a build conversation might surface reasons to change. The defaults should hold unless explicit reasoning argues otherwise.

### Full-text search index

A FTS5 virtual table covering `name`, `aliases`, `one_line_summary`, `extended_summary`, `core_components`, `primary_use_case`, and `common_criticisms`. Search is the most common practitioner interaction; FTS5 is built into SQLite and handles this scale trivially.

### Composite indexes

Indexes on `(origin_discipline, rigor_band)` and `(rigor_band, type)` for common filter combinations. Other indexes added only if specific queries surface as slow during use.

### No denormalized convenience columns

Resist the urge to add denormalized fields "to make the reader faster." At 750 entries, joins are essentially free, and denormalization creates synchronization problems that bite later. If a query is genuinely slow, fix it with an index, not denormalization. The reader's performance budget is not the constraining factor at this scale.

### Audit trail

A `ingestion_log` table recording every ingestion run with timestamp, source files processed, entries added/updated, and any validation warnings. This is the audit trail for the catalog as it evolves through pass III and beyond.

---

## Anti-patterns to avoid

Things the build thread should explicitly not do:

**Don't fold lineage into the entries table for "simplicity."** The edge table is the single most important schema decision. Anything that argues for collapsing it back is wrong, full stop.

**Don't treat originators, criticisms, or sources as free strings in the database.** Even if the ingestion parsing is imperfect, structured rows with some null fields are far better than strings that will need re-parsing every time a query touches them.

**Don't optimize the reader's load time before the reader exists.** Premature optimization at this scale is uniformly counterproductive.

**Don't build authentication, editing, or comments in the alpha.** It's a reader, not a wiki. Editing happens by updating JSONL and re-running ingestion.

**Don't re-derive the JSONL from the database.** The JSONL files are the source of truth for content; the database is derived. Reversing this couples the schema to the database in ways that break the existing pass II workflow.

**Don't commit to a specific tech stack before considering deployment target.** The static-vs-dynamic call should be made early in the build conversation, not assumed. Both are viable; the trade-offs depend on update frequency and whether LLM-mediated query is in scope for the alpha.

---

## What to bring to the build conversation

When the build conversation starts, the user should bring:

1. **The complete v4.2 manifest CSV** (or confirmation that it's accessible to the build conversation).
2. **The full collection of pass II JSONL batch files** for both v4 (32 batches, ~556 entries) and Manifest II additions (estimated 8-12 batches, 191 entries).
3. **A domain decision** — where the catalog will be deployed.
4. **Any schema clarifications or amendments** to this document based on what was learned during the v4.2 enrichment that wasn't visible when this document was written.

The build conversation will produce:

1. **Database schema** as a SQL file.
2. **Ingestion script** that reads the manifest CSV and JSONL files and populates the database, with the validator integrated.
3. **Static site generator** that produces the alpha reader from the database.
4. **Reader templates** for entry detail, discipline index, and search/filter pages.
5. **Deployment configuration** for the chosen host.

Estimated effort: 8-15 hours of focused work for the full build, distributed across one weekend or two evenings.

---

## A note on the meta-analytical direction

The meta-analytical use case is genuinely interesting and the schema commitments above are designed to support it. But the build thread should resist the temptation to start building meta-analytical features before the practitioner reader exists. The reader is what generates the audience that makes the scholarly work matter.

The right sequence is:

1. Build the alpha reader on the v4.2 enriched corpus (this build).
2. Ship and share. Get usage and feedback.
3. Run pass III to tighten lineage and add cross-discipline annotations.
4. Re-ingest the pass III data into the same schema (no migration needed because the schema was designed for this).
5. Begin meta-analytical work, either as additional reader features or as a separate research surface.

The schema commitments make step 4 trivial and step 5 possible. Step 1 should not wait on either.
