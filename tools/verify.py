#!/usr/bin/env python3
"""Tier 1 mechanical scanner for pass-II enriched JSONL.

Checks (no facts, just shape and tone):
  1. JSON validity, schema completeness
  2. Field-length sanity (extended_summary 500-800 chars per methodology)
  3. Confidence-flag distribution
  4. AI-tone marker frequency
  5. Primary-sources format consistency
  6. Lineage internal consistency (within sampled set)
  7. Repeated phrasing across entries
  8. Placeholder text / blanks in required fields
"""

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

REQUIRED_FIELDS = [
    "name", "type", "origin_discipline", "rigor_band", "one_line_summary",
    "extended_summary", "originators", "originators_confidence",
    "year_or_decade", "year_confidence", "core_components",
    "primary_use_case", "common_criticisms", "primary_sources",
    "sources_confidence", "needs_verification",
]

# AI-tone markers. Each is a regex; case-insensitive.
# These are tells, not crimes — flagging frequency, not banning words.
AI_TONE_MARKERS = {
    "delve_into": r"\bdelv(e|es|ing) into\b",
    "navigate_complexities": r"navigat\w+ the complex",
    "tapestry": r"\btapestr(y|ies)\b",
    "testament_to": r"\btestament to\b",
    "in_todays_world": r"in today'?s [a-z\- ]{3,30}(world|landscape|environment)",
    "robust_modifier": r"\brobust\b",
    "powerful_modifier": r"\bpowerful\b",
    "cutting_edge": r"\bcutting[- ]edge\b",
    "comprehensive": r"\bcomprehensive\b",
    "leverage_verb": r"\bleverag(e|es|ing|ed)\b",
    "multifaceted": r"\bmultifaceted\b",
    "underscore": r"\bunderscor(e|es|ed|ing)\b",
    "showcase_verb": r"\bshowcas(e|es|ed|ing)\b",
    "intricate": r"\bintricate\b",
    "furthermore_start": r"(?m)^Furthermore[,\s]",
    "moreover_start": r"(?m)^Moreover[,\s]",
    "worth_noting": r"worth noting that",
    "it_is_important": r"it is important to",
    "ever_evolving": r"ever[- ]evolving",
    "paradigm_shift": r"paradigm shift",
    "seamless": r"\bseamless(ly)?\b",
    "holistic": r"\bholistic\b",
}

# Reasonable patterns for primary_sources field
SOURCE_YEAR_PATTERN = re.compile(r"\(\d{4}[a-z]?\)")  # "Porter (1980)" style

PLACEHOLDER_PATTERNS = [
    r"\bTBD\b", r"\bTODO\b", r"\[placeholder\]",
    r"\bunknown\b", r"\bn/?a\b",  # might be legitimate in some fields, but flag for review
]


def scan_entry(entry, source_file, line_num):
    issues = []

    # Schema completeness
    missing = [f for f in REQUIRED_FIELDS if f not in entry]
    if missing:
        issues.append(("schema_missing", f"missing fields: {missing}"))

    # Required-text-field emptiness
    for f in ["name", "extended_summary", "originators", "primary_sources",
              "primary_use_case", "common_criticisms"]:
        if f in entry and not str(entry[f]).strip():
            issues.append(("empty_required", f"empty: {f}"))

    # Extended summary length (methodology: 500-800 chars)
    es = entry.get("extended_summary", "")
    if es:
        L = len(es)
        if L < 400:
            issues.append(("summary_too_short", f"extended_summary {L} chars"))
        elif L > 1000:
            issues.append(("summary_too_long", f"extended_summary {L} chars"))

    # Primary sources format check: should contain at least one "(YYYY)" pattern
    ps = entry.get("primary_sources", "")
    if ps and not SOURCE_YEAR_PATTERN.search(ps):
        issues.append(("source_no_year", f"primary_sources has no (YYYY): '{ps[:80]}'"))

    # Placeholder text in any text field
    for f, v in entry.items():
        if isinstance(v, str):
            for pat in PLACEHOLDER_PATTERNS:
                if re.search(pat, v, re.IGNORECASE):
                    # Don't flag legitimate-looking n/a in confidence fields
                    if f in ["originators_confidence", "year_confidence", "sources_confidence"]:
                        continue
                    issues.append(("placeholder", f"'{pat}' in {f}"))
                    break

    return issues


def scan_file(path):
    results = {
        "file": path.name,
        "entry_count": 0,
        "parse_errors": [],
        "entry_issues": [],
        "confidence_counts": {
            "originators_confidence": Counter(),
            "year_confidence": Counter(),
            "sources_confidence": Counter(),
        },
        "needs_verification_true": 0,
        "ai_tone_hits": Counter(),
        "ai_tone_entries_with_hits": Counter(),  # per marker: how many entries contain it at least once
        "summary_lengths": [],
        "all_summaries": [],  # for repeated-phrase detection
        "lineage_refs": defaultdict(list),  # name -> list of (source_entry, relation)
        "entry_names": set(),
    }

    with open(path) as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError as e:
                results["parse_errors"].append((line_num, str(e)))
                continue

            results["entry_count"] += 1
            name = entry.get("name", f"<line {line_num}>")
            results["entry_names"].add(name)

            # Confidence distribution
            for cf in ["originators_confidence", "year_confidence", "sources_confidence"]:
                v = entry.get(cf, "missing")
                results["confidence_counts"][cf][v] += 1

            if entry.get("needs_verification") is True:
                results["needs_verification_true"] += 1

            es = entry.get("extended_summary", "")
            if es:
                results["summary_lengths"].append(len(es))
                results["all_summaries"].append((name, es))

            # AI tone scan across all narrative text fields
            text_blob = " ".join([
                str(entry.get(f, "")) for f in
                ["extended_summary", "primary_use_case", "common_criticisms", "core_components"]
            ])
            for marker, pat in AI_TONE_MARKERS.items():
                hits = len(re.findall(pat, text_blob, re.IGNORECASE))
                if hits:
                    results["ai_tone_hits"][marker] += hits
                    results["ai_tone_entries_with_hits"][marker] += 1

            # Lineage references (just collect targets; full validation needs whole corpus)
            for rel in ["parent_of", "child_of", "siblings", "derived_from"]:
                v = entry.get(rel, "")
                if v:
                    for target in [t.strip() for t in v.split(";") if t.strip()]:
                        results["lineage_refs"][target].append((name, rel))

            issues = scan_entry(entry, path.name, line_num)
            for kind, msg in issues:
                results["entry_issues"].append((name, kind, msg))

    return results


def repeated_phrase_check(all_summaries, n=6, min_occurrences=3):
    """Find n-gram phrases that recur across multiple entries' summaries.
    A high count of recurring 6-grams is a template-generation tell.
    """
    ngram_to_entries = defaultdict(set)
    for name, summary in all_summaries:
        # Tokenize crudely on whitespace, normalize case
        tokens = re.findall(r"\w+", summary.lower())
        for i in range(len(tokens) - n + 1):
            gram = " ".join(tokens[i:i+n])
            ngram_to_entries[gram].add(name)
    recurring = {g: names for g, names in ngram_to_entries.items()
                 if len(names) >= min_occurrences}
    # Filter out the boring ones (every entry will share some natural English phrases)
    return sorted(recurring.items(), key=lambda x: -len(x[1]))


def report(all_results):
    print("=" * 72)
    print("TIER 1 MECHANICAL SCAN — SAMPLE")
    print("=" * 72)

    total_entries = sum(r["entry_count"] for r in all_results)
    total_parse_errors = sum(len(r["parse_errors"]) for r in all_results)
    total_issues = sum(len(r["entry_issues"]) for r in all_results)
    total_nv = sum(r["needs_verification_true"] for r in all_results)

    print(f"\nFiles scanned: {len(all_results)}")
    print(f"Total entries: {total_entries}")
    print(f"Parse errors:  {total_parse_errors}")
    print(f"Mechanical issues flagged: {total_issues}")
    print(f"needs_verification=true:   {total_nv} ({100*total_nv/total_entries:.1f}%)")

    # Issue breakdown
    issue_kinds = Counter()
    for r in all_results:
        for name, kind, msg in r["entry_issues"]:
            issue_kinds[kind] += 1
    if issue_kinds:
        print("\nIssue type breakdown:")
        for kind, count in issue_kinds.most_common():
            print(f"  {kind:24s} {count}")

    # Confidence distribution
    print("\nConfidence flag distribution (combined across sampled files):")
    combined_conf = {
        "originators_confidence": Counter(),
        "year_confidence": Counter(),
        "sources_confidence": Counter(),
    }
    for r in all_results:
        for cf, counter in r["confidence_counts"].items():
            combined_conf[cf].update(counter)
    for cf, counter in combined_conf.items():
        total = sum(counter.values())
        breakdown = ", ".join(f"{k}={v} ({100*v/total:.0f}%)"
                              for k, v in counter.most_common())
        print(f"  {cf:28s} {breakdown}")

    # Extended summary length stats
    all_lengths = [L for r in all_results for L in r["summary_lengths"]]
    if all_lengths:
        all_lengths.sort()
        n = len(all_lengths)
        median = all_lengths[n // 2]
        p10 = all_lengths[n // 10]
        p90 = all_lengths[9 * n // 10]
        in_range = sum(1 for L in all_lengths if 500 <= L <= 800)
        print(f"\nExtended summary length: median={median}, p10={p10}, p90={p90}")
        print(f"  within methodology range (500-800): {in_range}/{n} ({100*in_range/n:.0f}%)")

    # AI tone
    combined_tone_hits = Counter()
    combined_tone_entries = Counter()
    for r in all_results:
        combined_tone_hits.update(r["ai_tone_hits"])
        combined_tone_entries.update(r["ai_tone_entries_with_hits"])
    if combined_tone_hits:
        print(f"\nAI-tone markers (total hits / entries containing at least one):")
        for marker, count in combined_tone_hits.most_common():
            entries_w = combined_tone_entries[marker]
            pct = 100 * entries_w / total_entries
            print(f"  {marker:28s} {count:4d} hits / {entries_w} entries ({pct:.0f}%)")
    else:
        print("\nAI-tone markers: none detected")

    # Repeated phrasing
    all_summaries = [s for r in all_results for s in r["all_summaries"]]
    recurring = repeated_phrase_check(all_summaries, n=6, min_occurrences=3)
    if recurring:
        print(f"\nRepeated 6-grams (appearing in >=3 entries' summaries):")
        for gram, names in recurring[:15]:
            print(f"  {len(names):3d}× '{gram}'")
    else:
        print("\nRepeated 6-grams: none above threshold (good sign)")

    # Sample of specific issues (most useful for the user)
    print("\n" + "=" * 72)
    print("SAMPLE OF SPECIFIC ENTRIES FLAGGED")
    print("=" * 72)
    shown = 0
    for r in all_results:
        for name, kind, msg in r["entry_issues"][:5]:
            print(f"  [{r['file']}] {name}: {kind} — {msg}")
            shown += 1
            if shown >= 20:
                break
        if shown >= 20:
            break


if __name__ == "__main__":
    files = [Path(p) for p in sys.argv[1:]]
    all_results = [scan_file(p) for p in files]
    report(all_results)
