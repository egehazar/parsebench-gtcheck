# parsebench-gtcheck

Answer-key checks for two LlamaIndex benchmarks: [ParseBench 2](#parsebench-2) (document parsing) and
[ExtractBench](extractbench/REPORT.md) (schema-guided extraction).

## ParseBench 2

Finds likely mistakes in the answer key of [ParseBench 2](https://github.com/run-llama/ParseBench), LlamaIndex's
benchmark for document parsers, and measures what each mistake costs the parsers, with ParseBench's own scorer.

**Findings: [REPORT.md](REPORT.md)**, on the newest revision (v2.07):
- Batch 1 ([run-llama/ParseBench#316](https://github.com/run-llama/ParseBench/issues/316)): four errors, each of
  which caps the best possible score on its page (a perfect parse of one insurance page scores 0.75 today).
- Batch 2: 15 text pages where the reference differs from what the page prints: one page completes its last
  sentence with next-page text, and 13 have wording the page does not print ("LICENSE PLATE" where the page prints
  "PLAT", "aimed at" where it prints "aimed and"). On most of them the best possible score is below 1.00 today.
- Batch 3: four table cells that differ from the page (a value copied from the row below, a mistyped figure,
  a corrected source typo, a truncated label).
- A question about 57 text pages whose published Markdown differs from what the scorer reads.

## How it works
Evidence that is not anyone's opinion:
1. **The PDF's own text.** On a born-digital page the text layer is what the document says. A page covered by one
   large image is treated as a scan: its OCR text layer can be wrong and is not used.
2. **The published parsers.** About 59 leaderboard rows have their per-page outputs public. When at least 90% of
   them side with the PDF against the answer key, the page is flagged.
3. **The page image.** Every flagged page is read on a rendered crop before it is called an error.
4. **ParseBench's scorer.** Each correction is scored on every published output with
   `next_metrics.compute_next_metrics`, the per-page function the harness uses, before and after the fix.

Checks in `gtcheck.py`:
- `pdf` / `consensus`: numbers (the scorer's critical tokens, via its own tokenizer) the reference has more often
  than the text layer, with parser agreement; artifact filters for footnote letters glued to numbers, numbers split
  across lines, ordinals and bare symbols.
- `omissions`: numbers the text layer and the parsers have more often than the reference.
- `wdiff.py`: word-level differences between the reference and the text layer where 90% of outputs side with the
  page (after `gtcheck.py spans` flags candidate pages).
- `phantom`: table rows whose words are not on the page (each page token can match once, so a pasted copy of real
  vocabulary still shows up).
- Text pages are compared against the reference the text scorer reads: a rule's `original_md` when present, else
  `expected_markdown` (`text_next.reference_markdown`).

## Checking the checker
- `reproduce.py` scores a whole leaderboard row with the same per-page function and ParseBench's dimension
  weights. LlamaParse (Agentic Plus) at the leaderboard's pinned revision: Tables 94.72 here against 94.72
  published; Text 90.31 against 90.22.
- A second reviewer (an AI model, Fable 5.2) re-checked every claimed error from the raw files before anything was
  reported, and caught three that were wrong as scored errors (see REPORT.md).

## Running it
One command runs every check on the newest dataset revision and writes one review list (`work/REVIEW.md`): each
flagged page, what the reference says, what the page and most outputs say, and a link to the PDF.
```
python audit.py                                   # all text and table subsets; --subsets text,tables for some
```
The individual steps:
```
python fetch.py                                   # answer key (HF main) + published outputs, text and table subsets
python gtcheck.py pdf SUBSET ...                  # reference vs text layer
python gtcheck.py consensus SUBSET ...            # + parser agreement
python gtcheck.py omissions SUBSET ...
python gtcheck.py phantom SUBSET ...
python impact.py fixes_confirmed.json             # score effect of each correction
python reproduce.py llamaparse_agentic_plus       # reproduce a leaderboard row (needs the pinned ground truth)
```
It needs a ParseBench checkout in `ParseBench/` (for the tokenizer, metrics and test-case loader) with its
environment (`uv sync`), plus `pillow`.

## Credits
- ParseBench 2 dataset, results and scoring code: LlamaIndex, Apache-2.0
  (github.com/run-llama/ParseBench, huggingface.co/datasets/llamaindex/ParseBench-2). The crops in `evidence/` are
  renders of pages from that dataset. This project imports ParseBench's code from a checkout and does not copy it.
- Built with AI assistants (Claude, with Fable as an independent reviewer).

## ExtractBench
`extractbench/`: the same approach for LlamaIndex's extraction benchmark ([REPORT](extractbench/REPORT.md)). Every
published pipeline is scored through ExtractBench's own path, and answer-key cells that 90% of pipelines miss are
read against the PDF and the field's schema description. 24 documents have key cells that contradict the document
or the schema (1,941 printed '0's stored as null in a 13F the schema names, legend codes the document never prints on
1,814 adverse-event cells, masked SSNs on nine W-2s, lowercase table kinds the schema requires in Title Case, ...), each
measured on Value F1 with the official scorer. The same
path reproduces LlamaExtract Agentic Plus's row (overall 96.14 vs 96.17 published).
