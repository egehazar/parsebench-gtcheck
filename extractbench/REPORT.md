# ExtractBench: answer-key cells that contradict the document or the field's own schema description

Dataset: `llamaindex/ExtractBench` at Hugging Face main, revision `f9b910906c` (2026-10-21). Outputs:
`llamaindex/ExtractBench-results` main, `results/` tier (51 pipelines). Splits checked: short and medium (350 of the
370 documents) and long (the other 20; the Datalab Accurate pipeline was left out of the long check because its
545 MB long output stalls the row matcher).

## How they were found and checked
1. **Flagged by `valcheck.py`.** Every published output is scored through ExtractBench's own path
   (`evaluators.extract.prepare_extract_scoring_inputs(...).compute_unified_metrics(value_cells)`), which records
   for each Value-F1 cell the ground-truth path it was aligned to and whether it matched. A candidate is a cell that
   at least 90% of the aligned pipelines miss, where at least 60% agree on one other value.
2. **Read against the PDF and the field's schema description.** For an extraction benchmark the schema description
   is part of the contract, so a key value that contradicts it counts even when it is printed somewhere.
3. **Scored** with the same official path on the original and the corrected sidecar (`eb_impact.py`): document
   Value F1 before and after, for every published pipeline. A correction is applied everywhere the key stores the
   value: `expected_output`, the per-cell rule's evidence, and the row-level evidence.
4. **Checked independently** by a second reviewer (Fable 5.2, an AI model) from the raw files; that review found
   several of these and corrected two of my claims (see "Not counted").

Note on matching: Value F1 compares strings exactly after collapsing whitespace runs (case-sensitive); it does not
use the declared `comparator`. That is why a key that differs from the printed text by a space or by case marks
every faithful pipeline wrong.

The same scoring path reproduces LlamaExtract Agentic Plus's leaderboard row: short 97.03 (published 97.02), medium
94.30 (94.30), long 93.95 (94.65), overall 96.14 (96.17). The long gap is likely the 30-minute cutoff, which this
replay does not model.

## Errors, short and medium splits (18 documents)

| Document | What is wrong | Doc Value F1, mean over pipelines | Best pipeline |
|---|---|---|---|
| 9 W-2s `short/passcoag-2020-w2-p0002-r2` ... `p0006-r3` | `employee_ssn` is "XXX-XX-XXXXX" (five X). The schema: "if the tail is fully masked/overstruck, return exactly 'XXX-XX-XXXX' (canonical 4-X form) - do NOT try to count the struck-out X characters". 11 sibling W-2 keys use the 4-X form. | +1.4 to +2.3 each; 32-46 up, at most 1 down | 0.97-0.98 -> 1.00 |
| `short/budget_appendix_legis` | All 9 `tables[*].table_number` kinds are lowercase ("... \| employment summary"); the schema: "exactly one of 'Program and Financing', 'Object Classification', 'Employment Summary'" (Title Case). 50 of 50 pipelines miss each. | +3.0; 45 up, 0 down | 0.956 -> 0.992 |
| `medium/gov_clin_schedule_0035` | CLIN 0001 unit price prints "(b) (5), (b) (4)"; key "(b) (4)". | +3.6; 31 up, 4 down | |
| `medium/gov_clin_schedule_0033` | CLIN 0004 quantity and unit price print "(b) (4)" and the schema says return the FOIA marker verbatim; key null. | +1.4; 39 up, 1 down | 0.991 -> 1.00 |
| `short/cbp_7501_continuation_0002` | `line_items[0..1].description_of_merchandise` include "CAFTA,(P+)17011150-2106909; ", which the schema lists verbatim as an annotation row to exclude. | +1.0; 35 up, 3 down | 0.949 -> 0.966 |
| `medium/gsa_mas_it_labor_0011` | `sin` on rows 93-105 is "Ancillary"; page 37 prints "SIN ANCILLARY" and the schema says capture it as printed. Row 57's title is "Programmer Analyst Associate" from the descriptions section; the schema says use the rate table, which prints "Programmer Analyst Asc" (p35), and keep abbreviations. | +0.8; 38 up, 1 down | 0.880 -> 0.893 |
| `short/sec_13f_0019_soros_fund_management` | 36 `title_of_class` cells written without the printed space ("COM CLA" for "COM CL A", "CLA COM", "CAP STK CLA", ...; the key uses "CL A" on 7 other rows), and FERMI INC's CUSIP is 31491108 (8 characters) where the filing prints 314911108. | +0.8; 42 up, 3 down | 0.9915 -> 0.9994 |
| `medium/erie_county_2017_single_audit` | `awards[10..21].program_title` use the federal header title, but their rows are labelled 'Northeast CDBG', 'County CDBG', 'Edinboro CDBG', ...; the schema says to use such sub-grantee labels (its own example is 'Millcreek CDBG', which the key uses in the 14.218 block). | +0.5; 35 up, 4 down | |
| `short/sec_13f_0009_coatue_management` | Three CHIME FINL INC rows: "CL A" is printed in the Title of Class column (wrapped under "COM SHS"); the key moves it into `name_of_issuer`. | +0.18; 42 up, 0 down | 0.9969 -> 0.9992 |
| `medium/bar-lev-2022` | `form_1116.countries[0]`: `column_label` is "VARIOUS" and `country_name` null; the schema says column_label is the column letter, and the page prints "VARIOUS" on line i under column A. | +0.1; 24 up, 0 down | |

## Errors, long split (6 documents)

| Document | What is wrong | Doc Value F1, mean over pipelines | Best pipeline |
|---|---|---|---|
| `long/real_sm0801_ae_full` | `relationship`, `action`, `outcome` are "decoded via the legend", with no enum in the schema (only `severity` has one). The legend prints "4=Probably Related", "2=Other Drug Therapy", "1=Recovered", ...; the key uses codes the document never prints (PROBABLY_RELATED, OTHER_DRUG_THERAPY, RECOVERED). Fix: accept the legend wording as well (1,814 cells; accepting the upper-case form "NOT RELATED" too gives +7.6). | +7.2; 35 up, 0 down | 0.939 -> 0.995 |
| `long/dd1155_schedule_continuation_0011` | `quantity_ordered` null on CLINs 2100, 2200, 6000, 6100, which print "21,640.00 Labor Hours"; the schema returns null only when no quantity is printed, and its own example is '21,640.00 Labor Hours' -> 21640.0. Other option CLINs carry their quantity. | +2.9; 46 up, 0 down | 0.968 -> 1.00 |
| `long/sec_13f_0010_renaissance_technologies` | The OTHER MANAGER column prints 0 on every one of the 3,213 printed rows, and the schema says "Renaissance Technologies prints '0' instead of leaving blank; preserve '0' as the string '0'". The key has null on 1,941 of its 3,063 rows ('0' on the rest). The key also lacks 150 printed rows (e.g. WALMART 931142103; not measured). | +2.2; 31 up | 0.919 -> 0.967 |
| `long/sf1449_supplies_services_0059` | `quantity` null on 21 Optional Task / Agile Delivery rows that print "XX EA"; the schema says return placeholders verbatim, and the key has 'XX' on 14 such rows. | +2.2; 33 up, 3 down | 0.968 -> 0.991 |
| `long/real_credit_strategies_full` | `par_currency` and `shares_or_par_thousands` null on rows that print them after the dot leaders (Fibercop SpA 4.75%, 06/30/30: ".... EUR 128 152,852"). 52 rows fixed here by matching the printed text; about a dozen more look the same. | +0.8; 32 up, 2 down | 0.974 -> 0.987 |
| `long/gov_clin_schedule_0005` | CLIN 0012 unit price prints "(b) (4)" on a black box; the key accepts only null here, while CLINs 0001 and 0013 accept the marker beside null. Fix: accept the marker too. (Its quantity "1" is not printed either; the cell is a black box.) | +0.4; 34 up, 0 down | 0.987 -> 0.994 |

Corrections: `fixes_eb_schema.json`, `fixes_13f.json`, `fixes_13f_coatue.json`, `fixes_eb_long.json`, `fixes_13f_rentec.json`, `fixes_ae_legend.json`, `fixes_credit_strategies.json` (paths and new values, or values to accept as well). Crops:
`evidence/`. Following ExtractBench's practice in issue #123, a key that contradicts its schema can be fixed by
accepting the schema-conforming value as an additional evidence value rather than by changing the schema.

**Scale.** About +0.12 points on a pipeline's overall Value F1 on average (24 documents of 370); no ranking changes.

## Not counted
- `medium/real_blackrock_muni_bmn` state subtotals: the key's per-state values sum the two printed section subtotals
  (Alabama 9,059,447 = 3,849,820 + 5,209,627), a sum printed nowhere. But the field is described as "Summed value for
  the state" with `source_policy: inferred`, so it is defensible. Underspecified rather than wrong.
- `long/gov_clin_schedule_0031` NET AMT: the line prints "(b) (4)", but that field has no redaction policy, so null is defensible (accepting the marker would add +1.4).
- `medium/nport__dunham_funds`: two balances carry four decimals where the page prints two; no score effect.
- Closing disclosures (cfpb, 3 documents): the key prints en dashes and curly apostrophes as the page does, while the
  schema's examples use ASCII ('- $0.01'). A schema/key mismatch worth accepting both forms for, not a wrong value.
- Probable but arguable: United Way San Antonio awards[2..3] program title; cabrera-2021 Schedule E (one S
  corporation whose name wraps over grid rows A and B is two key rows).
- `evcheck.py` (does each evidence quote sit inside its box?): 98% of 21,468 short-split quotes are in their boxes;
  the rest are composite quotes, field labels and enum values, not errors.
