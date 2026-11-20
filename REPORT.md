# ParseBench 2: four answer-key errors that cap the best possible score on their page

Dataset: `llamaindex/ParseBench-2` at Hugging Face main, revision `51c6bc2abf2e6c49617ce700b5a7967b552b650e`
(newest changelog entry v2.07). Parser outputs: `llamaindex/ParseBench-2-results` main (59 published rows).
Subsets checked: text, tables, complex_table_headers, financial_tables, insurance_filing_tables, dense_tables.

## The four errors

| Page | What is wrong | Best score on the page today -> after the fix | Page mean over 59 parsers |
|---|---|---|---|
| `insurance_filing_tables/ae0ff0f4c0c49dbf_p21` | The key's last four rows (Large Risk Property, Mortgage Fire, Aurora, Superior Protected Risk) are not on the page, which ends at "Water Districts". The key took the sheet range A9:J25. | 0.75 -> 1.00 (35 parsers go from exactly 0.75 to 1.00) | +22.5 points; 58 up, 0 down |
| `insurance_filing_tables/49192203046c0ef0_p8` | The key's second table (PRIOR2, PRIOR1, RECENT, PROJECTED/SUMMARY, mostly zeros) is not on the page. The record's metadata shows it comes from another, empty sheet of the same workbook (`Template3` A12:H30, table_id `serff_0347_2cc10ddd5a`); the page shows `Template1` A11:H30. | 0.63 -> 1.00 (10 parsers) | +31.2 points; 54 up, 1 down |
| `text/text_simple__disclaimer` | The page prints "THIS REGISTRATION DOCUMENT IS VALID FOR A PERIOD OF 12 MONTHS FROM THE DATE HEREOF." twice in a row (two positions in the text layer, not an overprint). The key, including the rule's `original_md` that the text scorer reads, has it once. Precedent: v2.06 TXT-005 restored printed repeated wording. | 0.95 -> 1.00 (46 parsers) | +5.1 points; 59 up, 0 down |
| `complex_table_headers/complex_header_018` | In both "versus" tables, the first data row has values copied from the row below into cells that are empty on the page: 1.025 in "ACTUAL 2024 versus PROJECTED 2024"; 1.000 twice in "PROJECTED 2026 versus ACTUAL 2024". The same rows hold `-` cells that are blank on the page (no score effect: the table metric treats `-` as empty). | small: a correctness fix | +0.7 points; 23 up, 8 down (28 score 0 either way) |

Crops of each page are in `evidence/`. The exact corrections are in `fixes_confirmed.json` as find/replace pairs; for
the text page the same replacement goes into the `.md` and into `original_md` in the `.test.json`.

**Scale.** These are page scores. Over the subsets: about +0.13 points on insurance_filing_tables (412 pages),
+0.005 on complex_table_headers, +0.01 on text. No ranking changes.

**Who goes down, and why.** On p8, one parser writes all four boxed blocks of the page as a single table. With two
key tables the scorer splits it and matches both pieces; with one it charges the other blocks as invented rows (0.567
to 0.116). The key covers only the first block by design, so that is the key's scope rule, not this fix. On 018 the
eight that lose have row misalignments of their own.

## A question, with no score effect
On 57 of the 508 text pages, `expected_markdown` (and the published `<name>.md`, which the dataset README calls the
reference Markdown) differs from the `original_md` on the page's `unexpected_sentence_percent` rule. The text
scorer reads `original_md` (`text_next.reference_markdown`). On three of those pages the `.md` disagrees with the PDF
where `original_md` agrees:
- `text_dense__legalRef`: the `.md` has MAMP 4939 "01/06/2012" (page: 17/06/2012) and MAMP 3525 MP-44 "09/06/2012"
  (page: 02/5/2012).
- `text_multilang__japanese5`: the `.md` writes the 18 phone numbers with hyphens; the page prints "・"
  (710・1475, 042・722・3111).
- `text_multilang__greek`: the `.md` lacks the printed italic caption above the photo.

Anyone who reads the `.md` as the reference sees the wrong text. Is the `.md` meant to be kept in sync? The other 54
pages were not checked.

## How the errors were found and checked
1. **Flagged by `gtcheck.py`.** A number in the scored reference that the PDF's own text layer has fewer times
   (born-digital pages only; a page covered by one large image is treated as a scan, whose OCR layer can be wrong),
   where at least 90% of the parsers with output for the page also have it fewer times. A table row whose tokens
   are absent from the text layer, with each page token able to match only once, and absent from 90% of parsers.
2. **Read on the rendered page**, crop by crop.
3. **Scored** with ParseBench's own per-page function (`next_metrics.compute_next_metrics`) on each published
   record, before and after the correction (`impact.py`). The same scoring reproduces LlamaParse (Agentic Plus)'s
   leaderboard row: Tables 94.72 (published 94.72), Text 90.31 (published 90.22) (`reproduce.py`).
4. **Re-checked independently** by a second reviewer (Fable 5.2, an AI model) from the raw files. That review
   caught three earlier claims of mine that were wrong as scored errors (they are the question above): I had
   compared text pages against `expected_markdown`, not the `original_md` the scorer reads. The checker now uses
   the scored reference.

## Limits
- The checker sees numbers and whole table rows. On 018 it found the copied numbers and missed the `-` cells in the
  same rows. The list is a lower bound.
- Parser agreement is how a page gets flagged, not proof: many rows share a model family or an OCR front end. The
  page crop is the evidence.
- Charts, layout, forms and the formatting subsets were not checked.

## Not errors (looked like errors, are not)
- `text_ocr__santacruz`: "Revised: 11/2006 / 12/2009 / 12/2012" is real, deliberately degraded text in the page's
  corner. The key is right; parsers miss it.
- Handwritten notes on scanned letters (`text_ocr__ref`, `text_ocr__skew`): the key transcribes them, parsers skip.
- `complex_header_050`: the scan's OCR text layer reads "(0.29)]" where the image shows "(0.24)". The key is right.
- Table pages that repeat a title or footer line the page prints once (for example `complex_header_006`'s footer):
  the table metric does not score prose, so no effect.
