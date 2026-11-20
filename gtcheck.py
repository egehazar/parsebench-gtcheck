"""ParseBench 2 answer-key checker.

Flags numbers (the scorer's "critical" tokens) where the answer key disagrees with the PDF's own text layer, and
records how many published parsers side with the PDF. Uses ParseBench's own tokenizer, so a token here is a token
to the scorer.

  python gtcheck.py pdf SUBSET [SUBSET ...]      -> work/pdfcheck_<subset>.json (answer key vs text layer)
  python gtcheck.py consensus SUBSET [...]        -> work/candidates_<subset>.json (adds parser agreement)

Evidence, not opinion: a candidate needs the text layer AND most parsers against the key. A person then confirms
each one on the rendered page.
"""
import collections, glob, json, os, sys
import pypdfium2 as pdfium

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ParseBench', 'src'))
from parse_bench.evaluation.metrics.parse.text_next import tokenize  # noqa: E402

GT = os.path.join(os.path.dirname(__file__), 'data', 'gt_main')
RES = os.path.join(os.path.dirname(__file__), 'data', 'results', 'results')
OUT = os.path.join(os.path.dirname(__file__), 'work')
MIN_LAYER = 0.6      # share of the key's numbers the text layer must contain to count as a usable text layer
MIN_AGREE = 0.9      # share of parsers (with output for the page) that must side with the text layer


def crit(md):
    toks, _ = tokenize(md or '')
    return collections.Counter(t.key for t in toks if t.crit)


def pdf_text(path, page_index=0):
    doc = pdfium.PdfDocument(path)
    try:
        page = doc[page_index]
        return page.get_textpage().get_text_range()
    finally:
        doc.close()


def scanned(path, page_index=0, cover=0.6):
    """True if one image covers most of the page: the text layer, if any, is OCR, not the document's own text."""
    doc = pdfium.PdfDocument(path)
    try:
        page = doc[page_index]; w, h = page.get_size()
        for obj in page.get_objects(max_depth=2):
            if obj.type == pdfium.raw.FPDF_PAGEOBJ_IMAGE:
                l, b, r, t = obj.get_bounds()
                if (r - l) * (t - b) >= cover * w * h: return True
        return False
    finally:
        doc.close()


def scored_reference(expected_markdown, rules):
    """What the text scorer reads: a text rule's `original_md` when present, else expected_markdown
    (text_next.reference_markdown). Table scoring reads expected_markdown."""
    for rule in rules or ():
        if rule.get('type') == 'unexpected_sentence_percent' and isinstance(rule.get('original_md'), str) and rule['original_md']:
            return rule['original_md']
    return expected_markdown


def cases(subset):
    """(id, pdf path, the reference the scorer reads for this subset, metadata)."""
    for line in open(os.path.join(GT, f'{subset}.jsonl'), encoding='utf-8'):
        r = json.loads(line)
        meta = json.loads(r['metadata']) if isinstance(r.get('metadata'), str) else (r.get('metadata') or {})
        rules = json.loads(r['test_rules']) if isinstance(r.get('test_rules'), str) else (r.get('test_rules') or [])
        ref = scored_reference(r['expected_markdown'], rules) if r.get('dimension') == 'text' or subset == 'text' else r['expected_markdown']
        yield r['id'], os.path.join(GT, r['document']), ref, meta


def pdf_check(subset):
    rows, skipped = [], collections.Counter()
    for cid, pdf, ref, meta in cases(subset):
        R = crit(ref)
        if not R: skipped['no numbers in key'] += 1; continue
        try: P = crit(pdf_text(pdf, 0))
        except Exception as e: skipped[f'pdf error {type(e).__name__}'] += 1; continue
        cover = sum(min(R[k], P[k]) for k in R) / sum(R.values())
        if cover < MIN_LAYER: skipped['no usable text layer'] += 1; continue
        extra = {k: (R[k], P[k]) for k in R if R[k] > P[k]}          # in the key more often than in the PDF
        missing = {k: (R[k], P[k]) for k in P if P[k] > R[k]}        # in the PDF more often than in the key
        rows.append({'id': cid, 'cover': round(cover, 3), 'scanned': scanned(pdf, 0), 'n_key': sum(R.values()),
                     'extra': extra, 'missing': missing})
    os.makedirs(OUT, exist_ok=True)
    json.dump({'subset': subset, 'checked': len(rows), 'skipped': skipped, 'rows': rows},
              open(os.path.join(OUT, f'pdfcheck_{subset}.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    n_extra = sum(bool(r['extra']) for r in rows)
    print(f'{subset}: {len(rows)} checked, skipped {dict(skipped)}; cases with key numbers missing from the PDF: {n_extra}')


def outputs(subset):
    """pipeline -> {case id: markdown} from the published results."""
    out = {}
    for f in glob.glob(os.path.join(RES, '*', f'{subset}.jsonl')):
        pipe = os.path.basename(os.path.dirname(f)); d = {}
        for line in open(f, encoding='utf-8'):
            if not line.strip(): continue
            r = json.loads(line)
            d[record_id(r)] = record_markdown(r)
        out[pipe] = d
    return out


def crop(pdf_path, needle, out_png, page_index=0, pad=60, scale=2.0):
    """Render the page region around the first occurrence of `needle` in the text layer; returns True if found."""
    doc = pdfium.PdfDocument(pdf_path)
    try:
        page = doc[page_index]; tp = page.get_textpage()
        hit = tp.search(needle, match_case=False, match_whole_word=True).get_next()
        if not hit: return False
        i, n = hit
        boxes = [tp.get_charbox(j) for j in range(i, i + n)]
        l, b = min(x[0] for x in boxes), min(x[1] for x in boxes)
        r, t = max(x[2] for x in boxes), max(x[3] for x in boxes)
        w, h = page.get_size()
        img = page.render(scale=scale).to_pil()
        # PDF y grows upwards; the image's grows downwards
        box = (max(0, (l - pad * 3)) * scale, max(0, (h - t - pad)) * scale,
               min(w, r + pad * 3) * scale, min(h, h - b + pad) * scale)
        img.crop(tuple(int(v) for v in box)).save(out_png)
        return True
    finally:
        doc.close()


def record_id(r):
    return (r.get('output') or {}).get('example_id') or (r.get('request') or {}).get('example_id')


def record_markdown(r):
    return (r.get('output') or {}).get('markdown') or ''


def consensus(subset, min_parsers=20):
    """Adds parser agreement to the text-layer check. A candidate: a number the key has more often than the text
    layer, where at least MIN_AGREE of the parsers with output for the page also have it less often than the key."""
    d = json.load(open(os.path.join(OUT, f'pdfcheck_{subset}.json'), encoding='utf-8'))
    O = outputs(subset)
    refs = {cid: ref for cid, _, ref, _ in cases(subset)}
    cands, n_cases = [], 0
    for r in d['rows']:
        ux = unexplained(r['extra'], r['missing'])
        if not ux: continue
        n_cases += 1
        R = crit(refs[r['id']])
        H = [crit(o[r['id']]) for o in O.values() if (o.get(r['id']) or '').strip()]
        if len(H) < min_parsers: continue
        for k, (in_key, in_pdf) in ux.items():
            agree = sum(h[k] < R[k] for h in H)
            same_as_key = sum(h[k] >= R[k] for h in H)
            if agree / len(H) >= MIN_AGREE:
                cands.append({'id': r['id'], 'scanned': r['scanned'], 'token': k, 'in_key': in_key, 'in_pdf': in_pdf,
                              'parsers': len(H), 'parsers_with_fewer': agree, 'parsers_like_key': same_as_key})
    json.dump(cands, open(os.path.join(OUT, f'candidates_{subset}.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    print(f'{subset}: {n_cases} cases with unexplained key-only numbers -> {len(cands)} candidate tokens on '
          f'{len({c["id"] for c in cands})} cases ({sum(not c["scanned"] for c in cands)} on born-digital pages)')


def unexplained(extra, missing):
    """Key-only numbers that no text-layer artifact explains: footnote letters glued on, a number split or joined
    across lines, ordinal suffixes, or bare symbols. Returns {key: (in_key, in_pdf)}."""
    strip = lambda k: k.lstrip('#')
    miss = [strip(m) for m in missing]
    out = {}
    for k, v in extra.items():
        s = strip(k)
        if not any(c.isdigit() for c in s): continue                         # $, %, symbols, words
        if any(s != m and (s.startswith(m) or m.startswith(s)) and len(s) - len(m) in (-3, -2, -1, 1, 2, 3)
               and not (s[len(m):] if len(s) > len(m) else m[len(s):]).replace('.', '').isdigit() for m in miss):
            continue                                                         # glued footnote letters, ordinals, units
        if any(s.replace(',', '') == m.replace(',', '') for m in miss): continue
        joined = ''.join(miss)
        if len(s) >= 4 and s in joined and s not in miss: continue           # split across lines in the text layer
        if any(len(m) >= 4 and m in s for m in miss): continue
        out[k] = v
    return out

def words(text):
    toks, _ = tokenize(text or '')
    return collections.Counter(t.key for t in toks)


def key_rows(ref):
    """(table index, row index, cell texts) for every <tr> of every HTML table in the answer key."""
    import html as _h, re as _re
    for ti, t in enumerate(_re.findall(r'<table.*?</table>', ref, _re.S)):
        for ri, tr in enumerate(_re.findall(r'<tr[^>]*>(.*?)</tr>', t, _re.S)):
            cells = [_h.unescape(_re.sub(r'<[^>]+>', ' ', c)).strip()
                     for c in _re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', tr, _re.S)]
            yield ti, ri, cells


def phantom(subset, min_tokens=4, max_present=0.5, min_parsers=20):
    """Key table rows that are not on the page: on a born-digital page, at most `max_present` of the row's tokens are
    in the text layer, and at least MIN_AGREE of the parsers lack them too. -> work/phantom_<subset>.json"""
    O = outputs(subset)
    found, n_pages = [], 0
    for cid, pdf, ref, meta in cases(subset):
        if '<table' not in ref: continue
        try:
            if scanned(pdf, 0): continue
            P = words(pdf_text(pdf, 0))
        except Exception: continue
        if sum(P.values()) < 50: continue
        n_pages += 1
        H = [words(o[cid]) for o in O.values() if (o.get(cid) or '').strip()]
        if len(H) < min_parsers: continue
        Pb = collections.Counter(P)                      # each token on the page can match one key token only
        Hb = [collections.Counter(h) for h in H]
        for ti, ri, cells in key_rows(ref):
            W = words(' '.join(cells))
            n = sum(W.values())
            got = sum(min(W[k], Pb[k]) for k in W)
            for k in W: Pb[k] -= min(W[k], Pb[k])
            lacking = 0
            for hb in Hb:
                g = sum(min(W[k], hb[k]) for k in W)
                for k in W: hb[k] -= min(W[k], hb[k])
                lacking += n > 0 and g / n <= max_present
            if n < min_tokens or got / n > max_present: continue
            if lacking / len(H) >= MIN_AGREE:
                found.append({'id': cid, 'table': ti, 'row': ri, 'cells': cells[:10], 'in_pdf': round(got / n, 2),
                              'parsers': len(H), 'parsers_lacking': lacking})
    json.dump(found, open(os.path.join(OUT, f'phantom_{subset}.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    print(f'{subset}: {n_pages} born-digital pages with tables -> {len(found)} phantom rows on '
          f'{len({f["id"] for f in found})} pages')


def omissions(subset, min_parsers=20):
    """Numbers the born-digital page has more often than the key, where at least MIN_AGREE of the parsers also have
    them more often than the key: text the key may have dropped. -> work/omissions_<subset>.json"""
    d = json.load(open(os.path.join(OUT, f'pdfcheck_{subset}.json'), encoding='utf-8'))
    O = outputs(subset)
    refs = {cid: ref for cid, _, ref, _ in cases(subset)}
    found = []
    for r in d['rows']:
        if r['scanned']: continue
        miss = {k: v for k, v in r['missing'].items() if any(c.isdigit() for c in k)}
        miss = unexplained(miss, r['extra'])          # same artifact filters, with the roles swapped
        if not miss: continue
        R = crit(refs[r['id']])
        H = [crit(o[r['id']]) for o in O.values() if (o.get(r['id']) or '').strip()]
        if len(H) < min_parsers: continue
        for k, (in_pdf, in_key) in ((k, (v[1], v[0])) for k, v in miss.items()):
            more = sum(h[k] > R[k] for h in H)
            if more / len(H) >= MIN_AGREE:
                found.append({'id': r['id'], 'token': k, 'in_key': R[k], 'in_pdf': in_pdf, 'parsers': len(H),
                              'parsers_with_more': more})
    json.dump(found, open(os.path.join(OUT, f'omissions_{subset}.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    print(f'{subset}: {len(found)} numbers the key may have dropped, on {len({f["id"] for f in found})} pages')


def _wordseq(text):
    import re as _re, unicodedata as _u
    t = _u.normalize('NFKC', text or '').lower()
    t = _re.sub(r'<[^>]+>|!\[[^\]]*\]\([^)]*\)|[*_#|`>]', ' ', t)
    t = _re.sub(r'-\s*\n\s*', '', t)                        # words hyphenated across lines
    return _re.findall(r'\w+', t)


def _shingles(words, n=8):
    return collections.Counter(tuple(words[i:i + n]) for i in range(len(words) - n + 1))


def spans(subset, n=8, min_parsers=20, min_shingles=3):
    """Text the key dropped or added, at the level of 8-word runs, on born-digital pages:
    dropped = runs the PDF has more often than the key, and >= MIN_AGREE of the parsers also have more often;
    added   = runs the key has more often than the PDF, and >= MIN_AGREE of the parsers also have less often.
    Keeps pages with at least `min_shingles` such runs. -> work/spans_<subset>.json"""
    O = outputs(subset)
    found = []
    for cid, pdf, ref, meta in cases(subset):
        try:
            if scanned(pdf, 0): continue
            P = _shingles(_wordseq(pdf_text(pdf, 0)), n)
        except Exception: continue
        if sum(P.values()) < 30: continue
        R = _shingles(_wordseq(ref), n)
        H = [_shingles(_wordseq(o[cid]), n) for o in O.values() if (o.get(cid) or '').strip()]
        if len(H) < min_parsers: continue
        dropped = [k for k in P if P[k] > R[k] and sum(h[k] > R[k] for h in H) / len(H) >= MIN_AGREE]
        added = [k for k in R if R[k] > P[k] and sum(h[k] < R[k] for h in H) / len(H) >= MIN_AGREE]
        if len(dropped) >= min_shingles or len(added) >= min_shingles:
            found.append({'id': cid, 'dropped': len(dropped), 'added': len(added),
                          'dropped_examples': [' '.join(k) for k in dropped[:3]], 'added_examples': [' '.join(k) for k in added[:3]]})
    json.dump(found, open(os.path.join(OUT, f'spans_{subset}.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    print(f'{subset}: {len(found)} pages where the key dropped or added runs of text')



if __name__ == '__main__':
    cmd, subsets = sys.argv[1], sys.argv[2:]
    for s in subsets:
        {'pdf': pdf_check, 'consensus': consensus, 'phantom': phantom, 'omissions': omissions, 'spans': spans}[cmd](s)
