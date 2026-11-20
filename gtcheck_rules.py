"""Rule-text check for ParseBench 2's rule-defined subsets (headings, strikeout, underline).

A rule's text (or a heading's text) that is absent from a born-digital page's text layer AND from at least 90% of
the published outputs cannot be satisfied by anyone who reads the page correctly: a candidate answer-key error.
Matching ignores case, spacing, punctuation and markdown.

  python gtcheck_rules.py SUBSET ...   -> work/ruletext_<subset>.json
"""
import json, os, re, sys, unicodedata
import gtcheck

def norm(s):
    s = unicodedata.normalize('NFKC', s or '').lower()
    s = re.sub(r'<[^>]+>|[*_~`#>|\\\\]', ' ', s)
    s = re.sub(r'-\s*\n\s*', '', s)
    return re.sub(r'\W+', '', s)

def rule_texts(rules):
    for x in rules:
        if isinstance(x.get('text'), str) and x['text'].strip():
            yield x.get('type'), x['text']
        for h in x.get('headings') or []:
            if isinstance(h, dict) and (h.get('text') or '').strip():
                yield 'heading', h['text']

def run(subset, min_parsers=20):
    O = gtcheck.outputs(subset)
    found, n_rules, n_pages = [], 0, 0
    for line in open(os.path.join(gtcheck.GT, f'{subset}.jsonl'), encoding='utf-8'):
        r = json.loads(line)
        rules = json.loads(r['test_rules']) if isinstance(r['test_rules'], str) else r['test_rules']
        pdf = os.path.join(gtcheck.GT, r['document'])
        try:
            if gtcheck.scanned(pdf, 0): continue
            P = norm(gtcheck.pdf_text(pdf, 0))
        except Exception: continue
        if len(P) < 50: continue
        n_pages += 1
        H = [norm(o[r['id']]) for o in O.values() if (o.get(r['id']) or '').strip()]
        if len(H) < min_parsers: continue
        for kind, text in rule_texts(rules):
            t = norm(text)
            if len(t) < 6: continue
            n_rules += 1
            if t in P: continue
            lacking = sum(t not in h for h in H)
            if lacking / len(H) >= gtcheck.MIN_AGREE:
                found.append({'id': r['id'], 'rule': kind, 'text': text, 'parsers': len(H), 'parsers_lacking': lacking})
    json.dump(found, open(os.path.join(gtcheck.OUT, f'ruletext_{subset}.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    print(f'{subset}: {n_pages} born-digital pages, {n_rules} rule texts -> {len(found)} not on the page and missing from 90% of parsers')

if __name__ == '__main__':
    for s in sys.argv[1:]: run(s)
