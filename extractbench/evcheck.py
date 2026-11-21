"""ExtractBench evidence check: does each answer-key evidence quote appear where its box says?

For every evidence entry with a quote, a page and a box (word or line layer, not coarse), on born-digital pages:
- IN_BOX:      the quote is in the PDF text inside the box (with a small margin)   -> fine
- ELSEWHERE:   not in the box, but on the same page                                 -> the box may be wrong
- OTHER_PAGE:  not on that page, but on another page                                -> the page number may be wrong
- NOWHERE:     not in the document's text layer at all                              -> the quote (or value) may be wrong
Matching ignores case, spaces and punctuation.

  python evcheck.py [short medium long]   -> work/evcheck.json and a summary
"""
import collections, json, os, re, sys, unicodedata
import pypdfium2 as pdfium

GT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'gt')
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'work')
MARGIN = 0.01


def norm(s):
    return re.sub(r'\W+', '', unicodedata.normalize('NFKC', s or '').lower())


def scanned(page, cover=0.6):
    w, h = page.get_size()
    for obj in page.get_objects(max_depth=2):
        if obj.type == pdfium.raw.FPDF_PAGEOBJ_IMAGE:
            l, b, r, t = obj.get_bounds()
            if (r - l) * (t - b) >= cover * w * h: return True
    return False


def walk_rules(rules, prefix=''):
    """Yield (field path, evidence entry) from the nested field_rules mapping."""
    if isinstance(rules, dict):
        for k, v in rules.items():
            if k == 'evidence' and isinstance(v, list):
                for e in v:
                    if isinstance(e, dict): yield prefix, e
            elif isinstance(v, (dict, list)):
                yield from walk_rules(v, f'{prefix}.{k}' if prefix else k)
    elif isinstance(rules, list):
        for i, v in enumerate(rules):
            yield from walk_rules(v, f'{prefix}[{i}]')


def check(splits):
    rows, counts = [], collections.Counter()
    for split in splits:
        for line in open(os.path.join(GT, f'{split}.jsonl'), encoding='utf-8'):
            r = json.loads(line)
            rules = json.loads(r['field_rules']) if isinstance(r['field_rules'], str) else r['field_rules']
            doc = pdfium.PdfDocument(os.path.join(GT, r['pdf']))
            try:
                pages, texts, is_scan = {}, {}, {}
                def page_text(i):
                    if i not in texts:
                        p = doc[i]; pages[i] = p; is_scan[i] = scanned(p)
                        texts[i] = norm(p.get_textpage().get_text_range())
                    return texts[i]
                for path, e in walk_rules(rules):
                    q, pg, bb = e.get('quote'), e.get('page'), e.get('bbox')
                    if not q or not isinstance(pg, int) or not bb or e.get('coarse') or len(norm(q)) < 3: continue
                    i = pg - 1
                    if i < 0 or i >= len(doc): counts['page out of range'] += 1; continue
                    full = page_text(i)
                    if is_scan[i]: counts['scanned page'] += 1; continue
                    p = pages[i]; W, H = p.get_size(); x, y, w, h = bb
                    box = norm(p.get_textpage().get_text_bounded(left=(x - MARGIN) * W, bottom=H - (y + h + MARGIN) * H,
                                                                 right=(x + w + MARGIN) * W, top=H - (y - MARGIN) * H))
                    nq = norm(q)
                    if nq in box: verdict = 'IN_BOX'
                    elif nq in full: verdict = 'ELSEWHERE'
                    elif any(nq in page_text(j) for j in range(len(doc)) if j != i): verdict = 'OTHER_PAGE'
                    else: verdict = 'NOWHERE'
                    counts[verdict] += 1
                    if verdict != 'IN_BOX':
                        rows.append({'id': r['id'], 'field': path, 'page': pg, 'bbox': bb, 'quote': q, 'value': e.get('value'),
                                     'layer': e.get('layer'), 'verdict': verdict, 'box_text': box[:120]})
            finally:
                doc.close()
    os.makedirs(OUT, exist_ok=True)
    json.dump(rows, open(os.path.join(OUT, 'evcheck.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    print(dict(counts)); print('flagged entries:', len(rows), 'on', len({x['id'] for x in rows}), 'documents')


if __name__ == '__main__':
    check(sys.argv[1:] or ['short', 'medium', 'long'])
