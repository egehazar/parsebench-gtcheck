# ParseBench 2 answer-key checker: plan (written 2026-11-20 21:38 UTC, before looking at any case)

## What it is
A tool that ranks ParseBench 2 test cases by how likely their answer key is wrong, using two kinds of evidence that
are not anyone's opinion:
1. **Cross-parser agreement.** About 59 published parsers' outputs for every page are public. When nearly all of
   them disagree with the answer key in the same way, the key is suspect.
2. **The PDF's own text layer.** For born-digital pages, the words in the PDF are a fact. A word the key expects that
   the PDF does not contain, or a word the PDF and the parsers agree on that the key lacks, is evidence.

The output is a short ranked list with a page crop for each candidate, for LlamaIndex's reviewers to confirm or
reject against the source, the way they already review corrections.

## Why this, given what LlamaIndex already does
Their staff correct the key almost daily (v2.02-v2.07, 14-20 Nov 2026), check every change against the source PDF,
and ran an all-parser review in v2.03 that covered FORMS. Their own text-scoring doc says self-consistency "does not
prove that an annotation matches its PDF". No all-parser or text-layer check of TEXT or TABLES is published. So the
tool targets text (508 cases) and tables (1,753 cases), always against the newest revision on Hugging Face main.

## Steps
1. Reproduce one leaderboard row from published outputs (rescore.py) within 0.5 points. If it fails, stop and say so.
2. Download all published outputs; build the per-rule pass/fail matrix (rule x parser) for text and tables.
3. Text-layer check for born-digital pages (PyMuPDF).
4. Rank candidates; write crops; read the top of the list with the PDF open, then confirm or drop each one.
5. File the confirmed cases where LlamaIndex takes corrections (an HF dataset discussion, as outside reports were
   answered there), with the tool linked so they can run it themselves.

## Predictions (mine, before looking)
- Text: 10-40 candidates after the filters; about half confirmed against the PDF.
- Tables: 20-80 candidates; about half confirmed.
- LlamaIndex replies within 7 days: 60%. Confirms at least 5 errors: 45%.

## Done means
LlamaIndex confirms or merges corrections from this list, or adopts the checker. Anything less is reported as
what it is.
