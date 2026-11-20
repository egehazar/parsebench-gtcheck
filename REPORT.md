# ParseBench 2: answer-key errors found with the PDF text layer and the published outputs

Dataset: `llamaindex/ParseBench-2` at Hugging Face main, revision `51c6bc2abf2e6c49617ce700b5a7967b552b650e`
(newest changelog entry v2.07). Parser outputs: `llamaindex/ParseBench-2-results` main (59 published rows).
Subsets checked: text, tables, complex_table_headers, financial_tables, insurance_filing_tables, dense_tables.

## Batch 1 (posted as run-llama/ParseBench#316): four errors

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

## Batch 2: the text reference differs from what the page prints (15 pages)

Found with `wdiff.py`: word-level differences between the scored reference and the PDF's text layer where at least
90% of the published outputs side with the PDF. Every page was then read at high zoom; on all of them the drawn text
matches the text layer. Each correction was scored like batch 1, applied to `expected_markdown` and `original_md`
(`fixes_wording.json`, `fixes_nextpage.json`).

**Text from the next page.** `text/text_simple__boldanditalic` ends mid-sentence at "is required by the Governmental
Accounting" (then the page number). The reference completes the sentence with text that is not on the page
("Standards Board, who considers it ... historical context."). Best score 0.90 -> 1.00; page mean +9.6 points,
59 of 59 up.

**The reference has different wording from the page.** ParseBench has no written policy on typos, but its v2.06
fixes all restore printed wording (TXT-005 repeated words, TXT-010 added diacritics removed, TXT-013 "mid July"
kept without "in", TXT-014 a clipped "t" kept). On these pages the reference has wording the page does not print:

| Page | The page prints | The reference has | Best score today -> after | Page mean |
|---|---|---|---|---|
| `text_misc__crash` | APPORTIONED LICENSE PLAT OF R584245 | PLATE | 0.90 -> 1.00 | +8.8 |
| `text_simple__aitools` | Check out own Custom GPTs | Check out our own | 0.90 -> 0.95 | +4.9 |
| `text_multicolumns__3cools` | Group President and Chief Executive (Aliko Dangote) | ... Chief Executive Officer | 0.95 -> 1.00 | +4.5 |
| `text_simple__checkbox` | interventions aimed and decreasing gun violence | aimed at | 1.00 -> 1.00 | +4.5 |
| `text_simple__green` | discolouration and degradation to prevent | degradation and to prevent | 0.95 -> 1.00 | +4.3 |
| `text_simple__paper1page` | mappings are concentrated the Low Priority Zone | concentrated in the | 1.00 -> 1.00 | +4.3 |
| `text_multicolumns__2colrep` | low-complexity that are fast-to-value | low-complexity projects that | 0.95 -> 1.00 | +4.3 |
| `text_dense__livingWord` | in our community as leader, advocate and protector | as a leader | 0.92 -> 0.93 | +2.9 |
| `text_multicolumns__pap_2col` | to study RNNs through the lens of dynamical systems theory [25–32] | the phrase is missing | 0.95 -> 1.00 | +2.4 |
| `text_multicolumns__simple2col` | capacity limits for sites | for all sites | 0.95 -> 1.00 | +1.8 |
| `text_simple__eu` | (Gerard Laprat) | Gérard | 0.99 -> 1.00 | +0.9 |
| `text_simple__hca` | To access providers alerts | provider alerts | 0.99 -> 1.00 | +0.9 |
| `text_multicolumns__sbi` | Information System audits | Systems | 0.99 -> 1.00 | +0.9 |

Each row: 54 to 59 of 59 parsers go up. Several look like pattern-completion from neighbouring lines (the next
signatory prints "Officer"; the next line prints "LICENSE PLATE"). A question rather than a claim:
`text_simple__dividend` prints "right to such Dividends Equivalents" where the reference has "Dividend"; that page
was reviewed in v2.06 (TXT-019/020) and the wording kept, so it may be a deliberate choice (+0.9 if changed).

**Who goes down.** 11 parser rows score lower after these corrections; 9 of them wrote the reference's wording
(for example dots.ocr 1.5 and Chandra 2 write "aimed at" where the page prints "aimed and"), so the current
reference rewards making the same edit. Two are scorer realignments: LlamaParse (Agentic Plus) on livingWord writes
"as leader" correctly, but the reference's spare "a" had been matched to an "a" in its image alt text, and once
removed the alt text is charged as one invented passage; jinaocr on pap_2col is the same kind of realignment. That
alt text is charged at all seems to conflict with text-v21.md ("image alt descriptions ... are not" text).

**Scale.** Together (14 pages, the dividend question excluded) about +0.11 points on the Text mean; with batch 1's
disclaimer, about +0.12. No ranking changes.

## Batch 3: table cells that differ from the page (4 pages)

Found with `wdiff.py` on the table subsets, read on the rendered page, and re-checked independently
(`fixes_tables_batch2.json`). Tables are scored against `expected_markdown` by `table_next`.

| Page | The page prints | The key has | Best score today -> after | Page mean over 59 |
|---|---|---|---|---|
| `financial_tables/tu-2026-08-13_page1` | Appendix 3, EMEAA, Removals: (3,302) | (3,143), the Greater China value from the row below. The page's arithmetic confirms 3,302: 12,983 − 3,302 = 9,681, and 7,127 + 3,302 + 3,143 = 13,572 (Global) | 0.83 -> 0.90 | +6.4; 56 up, 0 down |
| `financial_tables/annual-report-2024-3-2026-08-21_page299` | Other Respiratory: 586 (6) (1) 147 ... | (7) as the third value | 0.90 -> 1.00 | +7.1; 56 up, 0 down |
| `financial_tables/ppt3-2026-08-14_page1` | Responsible AI policy: "Pages 12 and 124" (a typo in the source; neighbouring rows run 119/120, 121/122, 126) | "Pages 123 and 124" | 0.98 -> 1.00 | +8.2; 52 up, 3 down (the 3 wrote "123") |
| `financial_tables/marsh-2026-08-14_page2` | Total (row label) | Tota | 0.98 -> 1.00 | +1.9; 56 up, 0 down |

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
- Formatting subsets (headings, strikeout, underline) are defined by rules, not Markdown. `gtcheck_rules.py`
  checked that each of their 499 rule texts appears on its born-digital page or in at least 10% of the outputs:
  all do.
- Charts: `gtcheck_charts.py` flags key values a chart does not print. Its 14 flags were all values drawn but not
  labelled on the chart (for example the 2014 points of a 2014-vs-2022 chart, where only 2022 is labelled), so the
  key's values cannot be checked against printed text. Charts are out of reach of this method.
- Layout and forms were not checked (LlamaIndex's own v2.03 review covered forms).

## Not errors (looked like errors, are not)
- Page headers and footers drawn as logos or letterheads (`text_simple__cap`, `text_simple__cmn`,
  `text_multicolumns__tableinmiddle2cols`): the reference transcribes them; many outputs put headers in separate
  layout fields rather than their Markdown, which the scorer adds back.
- Margin line numbers on pleading paper (`text_simple__linenum`) and code-block language labels
  (`text_misc__justcode`): handled by the scorer.
- `text_ocr__santacruz`: "Revised: 11/2006 / 12/2009 / 12/2012" is real, deliberately degraded text in the page's
  corner. The key is right; parsers miss it.
- Handwritten notes on scanned letters (`text_ocr__ref`, `text_ocr__skew`): the key transcribes them, parsers skip.
- `complex_header_050`: the scan's OCR text layer reads "(0.29)]" where the image shows "(0.24)". The key is right.
- Table pages that repeat a title or footer line the page prints once (for example `complex_header_006`'s footer):
  the table metric does not score prose, so no effect.
