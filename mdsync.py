"""On text pages where expected_markdown (the published .md) differs from the scored original_md, which copy is
closer to the page? Closeness = word-level similarity (difflib ratio) to the PDF text layer (born-digital pages) and
the median similarity to the published outputs.

  python mdsync.py   -> work/mdsync.json and a summary
"""
import difflib, json, os, statistics
import gtcheck, wdiff

def sim(a, b):
    return difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()

rows = []
O = gtcheck.outputs('text')
for line in open(os.path.join(gtcheck.GT, 'text.jsonl'), encoding='utf-8'):
    r = json.loads(line)
    rules = json.loads(r['test_rules']) if isinstance(r['test_rules'], str) else r['test_rules']
    scored = gtcheck.scored_reference(r['expected_markdown'], rules)
    if scored == r['expected_markdown']: continue
    md, om = wdiff.words(r['expected_markdown']), wdiff.words(scored)
    pdf = os.path.join(gtcheck.GT, r['document'])
    born = not gtcheck.scanned(pdf, 0)
    P = wdiff.words(gtcheck.pdf_text(pdf, 0)) if born else []
    H = [wdiff.words(o[r['id']]) for o in O.values() if (o.get(r['id']) or '').strip()]
    row = {'id': r['id'], 'born_digital': born, 'md_words': len(md), 'original_md_words': len(om),
           'pdf_md': round(sim(md, P), 4) if len(P) > 30 else None, 'pdf_original_md': round(sim(om, P), 4) if len(P) > 30 else None,
           'parsers_md': round(statistics.median(sim(md, h) for h in H), 4), 'parsers_original_md': round(statistics.median(sim(om, h) for h in H), 4)}
    rows.append(row)
json.dump(rows, open(os.path.join(gtcheck.OUT, 'mdsync.json'), 'w', encoding='utf-8'), indent=1)
closer = lambda a, b: 'original_md' if b > a + 0.002 else ('md' if a > b + 0.002 else 'same')
by_parsers = [closer(x['parsers_md'], x['parsers_original_md']) for x in rows]
by_pdf = [closer(x['pdf_md'], x['pdf_original_md']) for x in rows if x['pdf_md'] is not None]
from collections import Counter
print('pages', len(rows), '| closer to the parsers:', dict(Counter(by_parsers)), '| closer to the PDF text (born-digital):', dict(Counter(by_pdf)))
