"""Score impact of an ExtractBench answer-key correction through the official path.

The document's sidecar (.test.json, rebuilt with ExtractBench's own _write_sidecar) is copied, the correction is
applied as exact JSON string-value replacements ('"OLD"' -> '"NEW"', so only whole values change, in
expected_output and in the evidence lists alike), and every published pipeline is scored on both versions with
evaluators.extract.prepare_extract_scoring_inputs(...).compute_unified_metrics(): document Value F1 before/after.

  python eb_impact.py FIXES.json   -> work/eb_impact_<FIXES>.json and a summary
FIXES.json: [{"id": "<split>/<stem>", "what": "...", "replace": [["OLD", "NEW"], ...]}]
"""
import json, os, re, shutil, statistics, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SIDE = HERE / 'data' / 'sidecar'
RES = HERE / 'data' / 'results' / 'results'



def _segs(path):
    return [int(x[1:-1]) if x.startswith('[') else x for x in re.findall(r'[^.\[\]]+|\[\d+\]', path)]


def apply_set(d, path, new):
    """Set one field everywhere the key stores it: expected_output, the per-cell rule at `path` (evidence value, and
    quote when it equals the old value), and any row-level evidence whose row equals the old row."""
    import copy
    segs = _segs(path); obj = d['expected_output']
    for s in segs[:-1]: obj = obj[s]
    old_row = copy.deepcopy(obj); old = obj.get(segs[-1]) if isinstance(obj, dict) else obj[segs[-1]]
    obj[segs[-1]] = new
    n_rule, n_rows = 0, 0
    for k, r in (d.get('_field_rules') or {}).items():
        if not isinstance(r, dict): continue
        for e in r.get('evidence') or []:
            if k == path:
                if e.get('value') == old: e['value'] = new; n_rule += 1
                if e.get('quote') == old and isinstance(new, str): e['quote'] = new
            elif isinstance(e.get('value'), dict) and e['value'] == old_row:
                e['value'][segs[-1]] = new; n_rows += 1
    return {'old': old, 'cell_rule_entries': n_rule, 'row_evidence_entries': n_rows}


def apply_sets(d, sets):
    """Many apply_set calls in one pass over the rules (for corrections touching thousands of cells)."""
    import copy
    changes = {}                                     # path -> (old, new, old_row, leaf)
    for path, new in sets:
        segs = _segs(path); obj = d['expected_output']
        for s in segs[:-1]: obj = obj[s]
        old_row = copy.deepcopy(obj); old = obj.get(segs[-1]) if isinstance(obj, dict) else obj[segs[-1]]
        obj[segs[-1]] = new; changes[path] = (old, new, old_row, segs[-1])
    rows = {}
    for path, (old, new, old_row, leaf) in changes.items():
        rows.setdefault(json.dumps(old_row, sort_keys=True, ensure_ascii=False), []).append((leaf, new))
    n_rule = n_rows = 0
    for k, r in (d.get('_field_rules') or {}).items():
        if not isinstance(r, dict): continue
        ch = changes.get(k)
        for e in r.get('evidence') or []:
            if ch is not None:
                if e.get('value') == ch[0]: e['value'] = ch[1]; n_rule += 1
                if e.get('quote') == ch[0] and isinstance(ch[1], str): e['quote'] = ch[1]
            elif isinstance(e.get('value'), dict):
                hit = rows.get(json.dumps(e['value'], sort_keys=True, ensure_ascii=False))
                if hit:
                    for leaf, new in hit: e['value'][leaf] = new
                    n_rows += 1
    return {'cells': len(changes), 'cell_rule_entries': n_rule, 'row_evidence_entries': n_rows}


def value_f1(tc, data):
    from extract_bench.evaluation.evaluators.extract import prepare_extract_scoring_inputs
    inp = prepare_extract_scoring_inputs(tc, data, [])
    for m in inp.compute_unified_metrics(None):
        if m.metric_name == 'extract_unified_value_f1': return m.value
    return None


def main(path):
    from extract_bench.test_cases.loader import load_test_case
    fixes = json.load(open(path, encoding='utf-8')); report = []
    for fx in fixes:
        split, stem = fx['id'].split('/', 1)
        tj = next((SIDE / split).rglob(f'{stem}.test.json')); pdf = tj.with_name(f'{stem}.pdf')
        raw = tj.read_text(encoding='utf-8'); new = raw; applied = {}
        for old, rep in fx.get('replace', []):
            o, n = json.dumps(old, ensure_ascii=False), json.dumps(rep, ensure_ascii=False)
            applied[old] = new.count(o); new = new.replace(o, n)
        for old, rep in fx.get('raw', []):                       # exact text, e.g. a whole name/class pair
            applied['raw:' + old[:40]] = new.count(old); new = new.replace(old, rep)
        if fx.get('set'):
            dd = json.loads(new)
            if len(fx['set']) > 50: applied['set_many'] = apply_sets(dd, fx['set'])
            else:
                for pth, val in fx['set']: applied['set:' + pth] = apply_set(dd, pth, val)
            new = json.dumps(dd, ensure_ascii=False)
        if fx.get('accept'):                                     # also accept another reading: extra evidence value
            dd = json.loads(new); n = 0; rx = re.compile(fx['accept']['path_regex']); mp = fx['accept']['map']
            for k, r in (dd.get('_field_rules') or {}).items():
                if not rx.fullmatch(k) or not isinstance(r, dict): continue
                ev = r.get('evidence') or []
                for e in list(ev):
                    v = e.get('value')
                    if isinstance(v, str) and v in mp and not any(x.get('value') == mp[v] for x in ev):
                        alt = dict(e); alt['value'] = mp[v]; ev.append(alt); n += 1
            applied['accepted_alternates'] = n; new = json.dumps(dd, ensure_ascii=False)
        if fx.get('add_alternate'):                              # also accept a value beside the key's (e.g. a marker beside null)
            dd = json.loads(new); fr = dd.setdefault('_field_rules', {}); n = 0
            for pth, val in fx['add_alternate']:
                r = fr.setdefault(pth, {'evidence': []}); ev = r.setdefault('evidence', [])
                base = dict(ev[0]) if ev else {}
                base.update({'value': val, 'quote': val}); ev.append(base); n += 1
            applied['added_alternates'] = n; new = json.dumps(dd, ensure_ascii=False)
        tmp = Path(tempfile.mkdtemp()); shutil.copyfile(pdf, tmp / pdf.name); (tmp / tj.name).write_text(new, encoding='utf-8')
        tc0, tc1 = load_test_case(pdf, tj), load_test_case(tmp / pdf.name, tmp / tj.name)
        rows = []
        for d in sorted(RES.iterdir()):
            f = d / f'{split}.jsonl'
            if not f.exists(): continue
            for line in open(f, encoding='utf-8'):
                if stem not in line: continue
                r = json.loads(line)
                if (r.get('request') or {}).get('example_id') != fx['id']: continue
                data = (r.get('output') or {}).get('extracted_data')
                if data is None: continue
                a, b = value_f1(tc0, data), value_f1(tc1, data)
                if a is not None and b is not None:
                    rows.append({'pipeline': d.name, 'before': round(a, 4), 'after': round(b, 4), 'delta': round(b - a, 4)})
        dd = [x['delta'] for x in rows]
        rep = {'id': fx['id'], 'what': fx['what'], 'replacements_applied': applied, 'pipelines': len(rows),
               'mean_before': round(100 * statistics.mean(x['before'] for x in rows), 2),
               'mean_delta_points': round(100 * statistics.mean(dd), 2), 'up': sum(x > 0.0005 for x in dd),
               'down': sum(x < -0.0005 for x in dd), 'best_before': max(x['before'] for x in rows),
               'best_after': max(x['after'] for x in rows), 'rows': rows}
        report.append(rep)
        print(f"{fx['id']}: applied {applied}; {len(rows)} pipelines, doc Value F1 mean {rep['mean_before']} -> "
              f"{rep['mean_delta_points']:+} points (up {rep['up']}, down {rep['down']}), best {rep['best_before']} -> {rep['best_after']}")
    name = Path(path).stem
    json.dump(report, open(HERE / 'work' / f'eb_impact_{name}.json', 'w', encoding='utf-8'), indent=1)


if __name__ == '__main__':
    main(sys.argv[1])
