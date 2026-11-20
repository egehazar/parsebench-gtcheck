"""Word-level differences between a text page's scored reference and its PDF text layer, kept only where at least
90% of the published outputs side with the PDF (contain the PDF's wording in context and not the key's).

  python wdiff.py text/<stem> [...]      -> printed differences
  python wdiff.py --all text             -> work/wdiff_text.json for every page `gtcheck.py spans` flagged
"""
import difflib, json, os, re, sys, unicodedata
import gtcheck


def words(text):
    t = unicodedata.normalize('NFKC', text or '')
    t = re.sub(r'<[^>]+>|!\[[^\]]*\]\([^)]*\)', ' ', t)
    t = re.sub(r'-\s*\n\s*', '', t)
    return re.findall(r'\w+', t.lower())


def has(seq, sub):
    n = len(sub)
    return any(seq[i:i + n] == sub for i in range(len(seq) - n + 1)) if n else True


def diffs(cid, ctx=3, min_parsers=20):
    subset = cid.split('/')[0]
    r = next(json.loads(l) for l in open(os.path.join(gtcheck.GT, f'{subset}.jsonl'), encoding='utf-8') if f'"{cid}"' in l)
    rules = json.loads(r['test_rules']) if isinstance(r['test_rules'], str) else r['test_rules']
    K = words(gtcheck.scored_reference(r['expected_markdown'], rules))
    P = words(gtcheck.pdf_text(os.path.join(gtcheck.GT, r['document']), 0))
    O = gtcheck.outputs(subset)
    H = [words(o[cid]) for o in O.values() if (o.get(cid) or '').strip()]
    if len(H) < min_parsers: return []
    out = []
    for op, a0, a1, b0, b1 in difflib.SequenceMatcher(None, K, P, autojunk=False).get_opcodes():
        if op == 'equal' or (a1 - a0) + (b1 - b0) > 40: continue          # skip big moves/reorders
        left, right = K[max(0, a0 - ctx):a0], K[a1:a1 + ctx]
        key_v, pdf_v = left + K[a0:a1] + right, left + P[b0:b1] + right
        with_pdf = sum(has(h, pdf_v) and not has(h, key_v) for h in H)
        if with_pdf / len(H) >= gtcheck.MIN_AGREE:
            out.append({'id': cid, 'op': op, 'key': ' '.join(K[max(0, a0 - ctx):a1 + ctx]),
                        'pdf': ' '.join(left + P[b0:b1] + right), 'parsers_with_pdf': with_pdf, 'parsers': len(H)})
    return out


if __name__ == '__main__':
    if sys.argv[1] == '--all':
        subset = sys.argv[2]
        flagged = [f['id'] for f in json.load(open(os.path.join(gtcheck.OUT, f'spans_{subset}.json'), encoding='utf-8'))]
        allr = []
        for cid in flagged:
            try: d = diffs(cid)
            except Exception as e: print(cid, 'ERROR', e); continue
            allr += d
            for x in d: print(f"{cid} | {x['op']} | KEY: {x['key']} | PDF: {x['pdf']} | {x['parsers_with_pdf']}/{x['parsers']}")
        json.dump(allr, open(os.path.join(gtcheck.OUT, f'wdiff_{subset}.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
        print(len(allr), 'differences on', len({x['id'] for x in allr}), 'pages')
    else:
        for cid in sys.argv[1:]:
            for x in diffs(cid): print(x)
