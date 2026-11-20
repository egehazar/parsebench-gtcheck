"""Chart check for ParseBench 2's charts subset.

On a born-digital chart that prints its values (most of the key's values for that chart are in the PDF text layer),
a key value that is NOT in the text layer, and that at least 90% of the published outputs do not contain either,
is a candidate typo in the answer key. Values are compared as numbers written the same way after removing thousands
separators, currency and percent signs.

  python gtcheck_charts.py   -> work/charts_candidates.json
"""
import json, os, re
import gtcheck

NUM = re.compile(r'[-−–]?\d[\d,]*(?:\.\d+)?')


def nums(text):
    out = []
    for m in NUM.finditer(text or ''):
        s = m.group(0).replace('−', '-').replace('–', '-').replace(',', '')
        out.append(s)
    return out


def norm_value(v):
    s = str(v).strip().replace('−', '-').replace('–', '-').replace(',', '')
    s = re.sub(r'[%$€£¥\s]', '', s)
    return s if NUM.fullmatch(s) else None


def run(min_parsers=20, min_printed=0.7):
    O = gtcheck.outputs('charts')
    found, n_charts = [], 0
    for line in open(os.path.join(gtcheck.GT, 'charts.jsonl'), encoding='utf-8'):
        r = json.loads(line)
        meta = json.loads(r['metadata']) if isinstance(r['metadata'], str) else (r['metadata'] or {})
        pdf = os.path.join(gtcheck.GT, r['document'])
        try:
            if gtcheck.scanned(pdf, 0): continue
            P = set(nums(gtcheck.pdf_text(pdf, 0)))
        except Exception: continue
        if not P: continue
        H = [set(nums(o[r['id']])) for o in O.values() if (o.get(r['id']) or '').strip()]
        if len(H) < min_parsers: continue
        for ti, t in enumerate(meta.get('chart_tables') or []):
            vals = [(s.get('name'), c, norm_value(v)) for s in t.get('series') or []
                    for c, v in zip(t.get('categories') or [], s.get('values') or [])]
            vals = [x for x in vals if x[2] and x[2] not in ('0',)]
            if len(vals) < 3: continue
            printed = sum(v in P for _, _, v in vals) / len(vals)
            if printed < min_printed: continue          # this chart does not print (most of) its values
            n_charts += 1
            for series, cat, v in vals:
                if v in P: continue
                lacking = sum(v not in h for h in H)
                if lacking / len(H) >= gtcheck.MIN_AGREE:
                    found.append({'id': r['id'], 'chart': ti, 'title': t.get('title'), 'series': series, 'category': cat,
                                  'key_value': v, 'printed_share': round(printed, 2), 'parsers': len(H), 'parsers_lacking': lacking})
    json.dump(found, open(os.path.join(gtcheck.OUT, 'charts_candidates.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    print(f'charts: {n_charts} born-digital charts that print their values -> {len(found)} key values not printed and '
          f'missing from 90% of parsers, on {len({f["id"] for f in found})} pages')


if __name__ == '__main__':
    run()
