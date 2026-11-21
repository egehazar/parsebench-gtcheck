"""ExtractBench value check: answer-key cells nearly every published pipeline misses, and what they agree on instead.

Every pipeline's published output is scored through ExtractBench's own path
(evaluators.extract.prepare_extract_scoring_inputs(...).compute_unified_metrics(value_cells)), which records, for each
Value-F1 leaf, the ground-truth path it was aligned to and whether the value matched (with the OR-acceptable
evidence values and the field normalizers). A candidate is a ground-truth cell that:
- at least 20 pipelines were aligned to,
- at least 90% of them got wrong,
- and at least 60% of all aligned pipelines wrote the same alternative value (after light normalization).
Each candidate is then checked against the PDF text layer by hand.

  python valcheck.py   -> work/valcheck.json and a summary
"""
import collections, json, os, re, sys, unicodedata
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
SIDE = HERE / 'data' / 'sidecar'
RES = HERE / 'data' / 'results' / 'results'


def get(obj, path):
    for seg in re.findall(r'[^.\[\]]+|\[\d+\]', path):
        if seg.startswith('['):
            i = int(seg[1:-1])
            if not isinstance(obj, list) or i >= len(obj): return None
            obj = obj[i]
        else:
            if not isinstance(obj, dict): return None
            obj = obj.get(seg)
    return obj


def key(v):
    if v is None: return None
    s = unicodedata.normalize('NFKC', json.dumps(v, ensure_ascii=False) if not isinstance(v, str) else v)
    return re.sub(r'\s+', ' ', s).strip().lower()


def load_records(split):
    out = {}
    skip = set(filter(None, os.environ.get('EXCLUDE', '').split(',')))
    for d in sorted(RES.iterdir()):
        f = d / f'{split}.jsonl'
        if not f.exists() or d.name in skip: continue
        recs = {}
        for line in open(f, encoding='utf-8'):
            r = json.loads(line)
            recs[(r.get('request') or {}).get('example_id') or (r.get('output') or {}).get('example_id')] = (r.get('output') or {}).get('extracted_data')
        out[d.name] = recs
    return out


def check_doc(args):
    split, stem, preds = args
    from extract_bench.test_cases.loader import load_test_case
    from extract_bench.evaluation.evaluators.extract import prepare_extract_scoring_inputs
    tj = next((SIDE / split).rglob(f'{stem}.test.json'))
    tc = load_test_case(tj.with_name(f'{stem}.pdf'), tj)
    seen, wrong, alt, gtv = collections.Counter(), collections.Counter(), collections.defaultdict(collections.Counter), {}
    for pipe, data in preds.items():
        if data is None: continue
        try:
            inp = prepare_extract_scoring_inputs(tc, data, [])
            cells = []; inp.compute_unified_metrics(cells)
        except Exception:
            continue
        for c in cells:
            if c.gt_path is None: continue
            seen[c.gt_path] += 1
            gtv.setdefault(c.gt_path, get(inp.expected_output, c.gt_path))
            if not c.value_correct:
                wrong[c.gt_path] += 1
                if c.pred_path is not None:
                    alt[c.gt_path][key(get(inp.extracted_data, c.pred_path))] += 1
    found = []
    for p, n in seen.items():
        if n < 20 or wrong[p] / n < 0.9 or not alt[p]: continue
        v, k = alt[p].most_common(1)[0]
        if v is None or k / n < 0.6: continue
        found.append({'id': f'{split}/{stem}', 'path': p, 'gt': gtv.get(p), 'consensus': v, 'agree': k, 'wrong': wrong[p], 'aligned': n})
    return found


def main(splits=('short', 'medium', 'long'), tag=''):
    jobs = []
    for split in splits:
        recs = load_records(split)
        for tj in sorted((SIDE / split).rglob('*.test.json')):
            stem = tj.name.removesuffix('.test.json'); eid = f'{split}/{stem}'
            jobs.append((split, stem, {pipe: r.get(eid) for pipe, r in recs.items() if eid in r}))
    allf = []
    with ProcessPoolExecutor(max_workers=6) as ex:
        for i, f in enumerate(ex.map(check_doc, jobs, chunksize=2)):
            allf += f
            if i % 50 == 0: print(f'[{i}/{len(jobs)}] candidates so far {len(allf)}', flush=True)
    json.dump(allf, open(HERE / 'work' / f'valcheck{tag}.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0, default=str)
    print('candidates', len(allf), 'on', len({f['id'] for f in allf}), 'documents')


if __name__ == '__main__':
    sp = sys.argv[1:] or ['short', 'medium', 'long']
    main(sp, '' if len(sp) == 3 else '_' + '_'.join(sp))
