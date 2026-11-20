"""Show one suspect token's context in the answer key, the PDF text layer, and a tally of what the parsers wrote there."""
import collections, glob, json, re, sys
import gtcheck

def probe(cid, token, width=100):
    subset = cid.split('/')[0]
    rows = {json.loads(l)['id']: json.loads(l) for l in open(f'data/gt_main/{subset}.jsonl', encoding='utf-8')}
    r = rows[cid]; ref = r['expected_markdown']; pdf = gtcheck.pdf_text('data/gt_main/' + r['document']).replace('\r\n', ' ')
    print(f'=== {cid} | token {token!r} | scanned={gtcheck.scanned("data/gt_main/" + r["document"])}')
    for m in list(re.finditer(re.escape(token), ref))[:4]:
        print('  KEY:', ref[max(0, m.start() - width):m.end() + width // 2].replace('\n', ' / '))
    hits = list(re.finditer(re.escape(token), pdf))
    for m in hits[:3]: print('  PDF:', pdf[max(0, m.start() - width):m.end() + width // 2])
    if not hits: print('  PDF: (not in text layer)')
    n_with = collections.Counter()
    for f in glob.glob(f'data/results/results/*/{subset}.jsonl'):
        for line in open(f, encoding='utf-8'):
            if cid.split('/')[-1] not in line: continue
            o = json.loads(line).get('output') or {}
            if o.get('example_id') == cid: n_with[(o.get('markdown') or '').count(token)] += 1
    print('  parsers by count of token in their output:', dict(sorted(n_with.items())))

if __name__ == '__main__':
    probe(sys.argv[1], sys.argv[2])
