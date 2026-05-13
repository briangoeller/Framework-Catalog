# Framework Catalog Pass 2 Enrichment Methodology

This document captures the methodology, schema, and operating standards established through enriching the v4 manifest (556 entries across 23 disciplines, 32 batches). It is intended for use as project knowledge for subsequent manifests using the same enrichment process.

---

## Project context

The framework catalog is a cross-disciplinary inventory of frameworks, tools, practices, and techniques. Each manifest is a CSV with seven fields per entry. Pass 2 enrichment expands each entry from those seven carry-forward fields to a full 22-field JSON record capturing originators, dating, components, criticisms, sources, and lineage.

The manifest is the source of truth for what entries exist. Do not invent new entries during enrichment. The closed universe of entry names is fixed before pass 2 begins.

---

## Schema (22 fields per record)

The seven carry-forward fields, copied verbatim from the manifest:

- `name` — entry name (used as foreign key for lineage)
- `aliases` — alternative names, comma-separated
- `type` — framework, tool, technique, practice, etc.
- `origin_discipline` — primary disciplinary home
- `rigor_band` — organizing-schema, doctrinal-institutional, structured-empirical, formal-scientific (or whatever bands the manifest uses)
- `band_notes` — manifest-provided caveats about empirical support; carry forward verbatim
- `one_line_summary` — manifest-provided one-liner

The fifteen new fields produced during enrichment:

- `extended_summary` — substantive description, 3-5 sentences, ~500-800 characters; not marketing copy
- `originators` — semicolon-separated list of foundational figures; include intellectual antecedents where substantial
- `originators_confidence` — high/medium/low (see confidence discipline below)
- `year_or_decade` — when the framework was articulated; can include precursor and codification dates
- `year_confidence` — high/medium/low
- `core_components` — semicolon-separated list of the framework's substantive elements
- `primary_use_case` — what the framework is actually used for
- `common_criticisms` — semicolon-separated; real published or practitioner critiques, not generic hedging
- `primary_sources` — title-and-date format, e.g., "Porter, M.E. (1980). Competitive Strategy"; not descriptions of contents
- `sources_confidence` — high/medium/low
- `parent_of` — semicolon-separated names of entries this framework parents
- `child_of` — semicolon-separated names of entries this framework descends from
- `siblings` — semicolon-separated names of entries at parallel level
- `derived_from` — semicolon-separated; intellectual ancestry references
- `needs_verification` — boolean; flag any record where any field is low confidence or multiple are medium

---

## Workflow per batch

Per batch (typically 8-25 entries grouped by discipline):

1. **Pull batch entries from the plan**, inspecting the seven carry-forward fields. Identify candidate lineage relationships and contested empirical claims that will need honest treatment.

2. **Brief judgment-call preview to the user** before drafting — surface lineage decisions, contested-empirics issues, and any spelling or attribution oddities. This catches misalignments before substantial drafting.

3. **Draft records as Python module files**. For batches under ~7 entries, a single records file works. For larger batches, split into A and B halves to stay under the bash heredoc ~100KB command-argument limit. Use `create_file` rather than heredoc for large content.

4. **Build a runner script** that imports the record lists, applies the carry-forward override pattern (see below), validates schema completeness and lineage references against the manifest, and writes the JSONL only if validation passes.

5. **Run the runner**, address any validation errors. The validator must report zero errors before writing.

6. **Use `present_files`** to surface the JSONL to the user.

7. **Provide a judgment-call summary** identifying lineage decisions, contested-empirics treatments, and any needs_verification flags with reasoning. Keep it focused; not exhaustive rationalization.

---

## The carry-forward override pattern (mandatory)

This is the single most important methodological standard. It was established at batch 18 after the validator caught 28 records where carry-forward fields had drifted from manifest values during drafting.

In the runner script, before writing JSONL output, override the seven carry-forward fields on every record with the manifest values:

```python
for r in RECORDS:
    m = manifest[r['name']]
    for f in ['aliases','type','origin_discipline','rigor_band','band_notes','one_line_summary']:
        r[f] = m[f]
```

This is non-negotiable. Drafting drift on carry-forward fields is common and silent. The override pattern makes the manifest authoritative regardless of what was typed during drafting. Never silently change `rigor_band` — if a record's rigor band seems wrong, flag it for human review rather than overriding.

---

## Lineage rules

**Closed universe within the active manifest.** Lineage references (`parent_of`, `child_of`, `siblings`, `derived_from`) must reference only entries that exist in the current manifest. Use full manifest names verbatim — case-sensitive, including any typographical variants the manifest contains.

**Cross-batch lineage within the manifest is acceptable.** A psychology entry can reference a management entry if both are in the same manifest. The validator will catch out-of-manifest references.

**Cross-manifest references should not be asserted as formal lineage** unless the project explicitly authorizes it. If a substantive intellectual ancestor exists in a different manifest, note the connection in `extended_summary` text rather than in lineage fields. This keeps the validator's closed-universe check meaningful.

**Only assert lineage you are confident about.** Empty fields are better than guesses. The lineage graph is more useful when sparse and accurate than when dense and speculative.

**For diffuse-origin frameworks**, assert the most defensible single relationship and note alternatives in extended_summary. If no clean relationship exists, leave the lineage fields empty and flag `needs_verification = True`.

---

## Confidence discipline

Mark `originators_confidence`, `year_confidence`, and `sources_confidence` honestly using these semantics:

- **High** — you would stake your reputation on the specific claim. Foundational text and date are well-documented; attribution is uncontested in the discipline.
- **Medium** — the general direction is right but specific details (exact year, full author list, correct citation format) may not be. Common when frameworks have multiple foundational works or when attribution is contested.
- **Low** — you are filling the field but it should be treated as a placeholder. Common for diffuse-origin frameworks (workshop traditions, practitioner methodologies, frameworks with multiple parallel originators).

**Set `needs_verification = True` if any field is low confidence, or if multiple fields are medium.** Err toward marking lower rather than higher. It is much better to flag uncertainty than to produce confidently wrong output that surfaces later in pass 3 review.

The `needs_verification` flag is not a failure mode. Some entries genuinely have diffuse origins and the catalog is more credible when this is acknowledged rather than papered over.

---

## Honest treatment standard

**Common criticisms must be real, named critiques** — published papers, named scholarly debates, documented empirical limitations, specific commercial concerns. Generic hedging ("some critics argue this may not work in all contexts") adds nothing and dilutes the catalog.

When real critiques exist, cite them by author and year inline: "Greenhalgh-Howick-Maskrey 2014 BMJ 'Evidence Based Medicine: A Movement in Crisis?'" or "Pfeffer and Sutton's *Hard Facts* (2006) substantially questioned the empirical track record." This treatment is what makes the catalog useful — practitioners need to know which frameworks have substantial published challenges.

**Differentiate criticism style by rigor band:**

- *Formal-scientific entries* — applicability boundaries, foundational debates, mathematical limitations. Examples: Arrow's Impossibility Theorem's restrictive conditions; the replication crisis affecting DoE applications; recent challenges to Universal Grammar from large language models.

- *Structured-empirical entries* — empirical track record, methodological limitations, replication concerns, named scholarly debates. Examples: HBM's modest predictive power in meta-analyses; Modern Synthesis vs Extended Evolutionary Synthesis debate.

- *Doctrinal-institutional entries* — empirical track record, scholarly contestation, recent doctrinal evolution, regulatory and political pressures. Examples: COIN's empirical reckoning post-Afghanistan; EBO's 2008 Mattis repudiation; stare decisis erosion in recent Supreme Court terms.

- *Organizing-schema entries* — operational vagueness concerns, commercial co-option, scholarly alternatives, cross-cultural applicability. Examples: Design Thinking's "boondoggle" critique (Vinsel 2018); Soft Power's measurement difficulties.

- *Wisdom-tradition / contemplative entries* — intra-tradition debates and scholarly disputes, not scientific-validity language. Treat with appropriate seriousness; avoid Western-academic flattening.

**Do not soften the manifest's `band_notes`.** If the manifest flags an entry as having weak empirical support or contested foundations, the enriched entry should reflect that honestly in `common_criticisms`. The manifest band_notes is a guide for how to write criticisms, not a hint to be ignored.

**Treat both sides evenhandedly on contested topics.** If you apply substantial critique to one tradition, apply equivalent critique to its competitors. Originalism's "convenient policy alignment" problem is paralleled by Living Constitutionalism's. Apply the same standard.

---

## Anti-patterns

Things to avoid:

- **Inventing entries.** The manifest is the closed universe. If something seems missing, it's missing on purpose for this manifest.

- **Padding extended_summary with filler.** 3-5 sentences of substantive description; not 8 sentences of marketing copy. If you can't fill the target length with substance, the entry is genuinely shorter than expected and that's fine.

- **Generic hedging in common_criticisms.** "Some practitioners disagree" is worthless. Either cite a real critique or omit the line.

- **Per-entry conversational commentary in the JSONL output.** Produce JSONL only. Conversational summary belongs in the chat response, not in the records.

- **Asserting lineage you don't have evidence for.** Empty fields beat speculative ones.

- **Confidence inflation.** Marking high confidence on year/originators when they're actually contested or diffuse. The downstream cost of wrong-but-confident is much higher than the cost of correctly flagging uncertainty.

- **Silently changing carry-forward fields during drafting.** Use the override pattern. Trust the manifest.

- **Conflating intellectual antecedents with formal lineage.** Note antecedents in `originators` and `extended_summary`; only assert `parent_of`/`child_of` when both entries are in the manifest and the relationship is uncontested.

- **Re-writing the manifest's one-line summary.** It carries forward verbatim, even if you'd phrase it differently.

---

## Practical operating notes

**Batch size**: ~13-25 entries works well; smaller batches for densely interconnected disciplines, larger for parallel structures. Single discipline per batch where possible to maintain lineage coherence.

**File-size limits**: bash heredoc has a ~100KB command-argument limit. Batch records files with substantial content (extended summaries, criticisms) typically exceed this. Use `create_file` for record files, splitting into `_records_a.py` and `_records_b.py` halves for batches over ~7 detailed entries. Then a `_runner.py` imports both and produces the JSONL.

**Output convention**: `/mnt/user-data/outputs/batch_NN.jsonl` with zero-padded batch numbers. Use `present_files` after each successful batch.

**Validator script structure**: The runner should (1) load the manifest as a name-keyed dict; (2) apply the carry-forward override; (3) check schema completeness on every record; (4) check that every name in lineage fields exists in the manifest; (5) only write the JSONL if errors == 0; (6) report errors with record name and field for fast debugging.

**Judgment-call summary format**: After each batch, surface the consequential decisions — lineage choices, contested-empirics treatments, needs_verification flags with reasoning. Keep it readable; not exhaustive. The summary serves both as audit trail for pass 3 review and as ongoing methodology calibration with the user.

---

## Decision points for a new manifest

Before starting pass 2 on a new manifest, make these explicit:

**Cross-manifest lineage policy.** Will entries in the new manifest be allowed to reference entries from earlier manifests? The default in this methodology is no — closed universe within each manifest. If the new manifest is substantively related to an existing one, you may want to relax this, but make the policy explicit upfront. If allowed, the validator needs to load multiple manifests as the closed universe.

**Rigor band structure.** The v4 manifest used four bands (organizing-schema, doctrinal-institutional, structured-empirical, formal-scientific). If the new manifest uses different or additional bands, the rigor-band-specific honest-criticism guidance above will need adjustment.

**Discipline overlap with existing manifests.** If the new tier 1 domains substantively overlap with v4 disciplines, decide whether overlapping frameworks should appear in both manifests, in only the newer one, or be consolidated. Cross-manifest duplication is acceptable if explicit; accidental duplication is not.

**Test batch.** A small (~15-25 entry) test batch produced before bulk enrichment helps calibrate schema interpretation, criticism style, and lineage decisions with the user. The v4 test batch was substantially useful for setting expectations; the new manifest should include one.

**Schema evolution.** If the schema needs new fields (e.g., for tier 1 domains with characteristics not captured in the existing fields), add them to the test batch and lock the schema before bulk enrichment. Schema drift across batches is much harder to fix than schema decisions made upfront.

---

## Lessons learned from v4

A few non-obvious things that emerged through 556 entries:

The single biggest source of validation errors was carry-forward field drift during drafting. The override pattern eliminated this class of error. Establish it from batch 1, not batch 18.

Lineage decisions are easier when you preview them to the user before drafting. Several v4 batches had to be redrafted because lineage choices made during drafting didn't match the user's mental model. The pre-batch judgment-call preview saves substantial rework.

Diffuse-origin frameworks (workshop traditions, practitioner methodologies, frameworks with parallel originators) are common — roughly 1 in every 30-40 entries needed `needs_verification = True` on the origin or year fields. Plan for this rather than treating it as failure.

Honest criticism with named published critiques takes substantial source-knowledge effort but is the single feature that makes the catalog distinctive. Generic hedging would have produced a less useful artifact regardless of how thorough the rest of the schema was.

Wisdom-tradition entries require different handling than scientific-empirical ones. Don't apply scientific-validity language to contemplative traditions; apply intra-tradition scholarly debate language instead. Reverse for formal-scientific entries — applicability boundaries and mathematical limitations are the right register.

The user as reviewer is the limiting resource. Tight judgment-call summaries that surface consequential decisions are more valuable than exhaustive justification of every choice.
