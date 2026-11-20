"""Score impact of an answer-key correction, through ParseBench's own per-page scoring.

Each published parser's record is loaded as a ParseBench InferenceResult, and the page is scored twice with
parse_bench.evaluation.metrics.parse.next_metrics.compute_next_metrics: once with the test case as published, once
with the correction applied. That is the function the harness calls for every page, so the reference it scores
against (the rules' `original_md` when present, else `expected_markdown`), the parser text it reads and the page
flags are the official ones.

A correction is applied everywhere its text occurs in the test case: `expected_markdown` and every text rule's
`original_md`. A correction whose text is not in the scored reference is reported as having no score effect.

  python impact.py FIXES.json   -> work/impact_<FIXES>.json and a printed summary

FIXES.json: [{"id": "<subset>/<stem>", "what": "...", "find": "<exact text>", "replace": "<new text>"}, ...]
"""
import glob, json, os, statistics, sys
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'ParseBench', 'src'))
from parse_bench.test_cases.loader import load_test_case  # noqa: E402
from parse_bench.schemas.pipeline_io import InferenceResult  # noqa: E402
from parse_bench.evaluation.metrics.parse.next_metrics import compute_next_metrics  # noqa: E402

GT = os.path.join(HERE, 'data', 'gt_main')
RES = os.path.join(HERE, 'data', 'results', 'results')
HEADLINE = {'text': 'text_next', 'tables': 'table_next', 'complex_table_headers': 'table_next',
            'financial_tables': 'table_next', 'insurance_filing_tables': 'table_next', 'dense_tables': 'table_next'}


def records(cid):
    subset = cid.split('/')[0]; out = {}
    for f in sorted(glob.glob(os.path.join(RES, '*', f'{subset}.jsonl'))):
        for line in open(f, encoding='utf-8'):
            if cid not in line: continue
            r = json.loads(line)
            if (r.get('output') or {}).get('example_id') == cid:
                out[os.path.basename(os.path.dirname(f))] = InferenceResult.model_validate(r)
    return out


def corrected(tc, fixes):
    """A copy of the test case with every fix applied to expected_markdown and to each rule's original_md."""
    new = tc.model_copy(deep=True)
    hits = {'expected_markdown': 0, 'original_md': 0}
    for f in fixes:
        if f['find'] in (new.expected_markdown or ''):
            assert new.expected_markdown.count(f['find']) == 1, (tc.test_id, f['what'])
            new.expected_markdown = new.expected_markdown.replace(f['find'], f['replace']); hits['expected_markdown'] += 1
        for rule in new.test_rules or []:
            om = getattr(rule, 'original_md', None)
            if isinstance(om, str) and f['find'] in om:
                assert om.count(f['find']) == 1, (tc.test_id, f['what'], 'original_md')
                rule.original_md = om.replace(f['find'], f['replace']); hits['original_md'] += 1
    return new, hits


def headline(tc, ir, metric):
    for m in compute_next_metrics(ir, tc):
        if m.metric_name == metric: return m.value
    return None


def main(fixes_path):
    fixes = json.load(open(fixes_path, encoding='utf-8'))
    by_id = {}
    for f in fixes: by_id.setdefault(f['id'], []).append(f)
    report = []
    for cid, fs in by_id.items():
        tc = load_test_case(Path(GT) / (cid + '.pdf'))
        new, hits = corrected(tc, fs)
        metric = HEADLINE[cid.split('/')[0]]
        rows = []
        for pipe, ir in records(cid).items():
            a, b = headline(tc, ir, metric), headline(new, ir, metric)
            if a is None or b is None: continue
            rows.append({'pipeline': pipe, 'before': round(a, 4), 'after': round(b, 4), 'delta': round(b - a, 4)})
        d = [r['delta'] for r in rows]
        rep = {'id': cid, 'metric': metric, 'what': [f['what'] for f in fs], 'applied_to': hits, 'parsers': len(rows),
               'mean_before': round(100 * statistics.mean(r['before'] for r in rows), 2) if rows else None,
               'mean_delta_points': round(100 * statistics.mean(d), 2) if d else None,
               'parsers_up': sum(x > 0.0005 for x in d), 'parsers_down': sum(x < -0.0005 for x in d),
               'max_delta_points': round(100 * max(d), 2) if d else None, 'rows': rows}
        report.append(rep)
        print(f"{cid} [{metric}; fix applied to {hits}]: {rep['parsers']} parsers, page mean {rep['mean_before']} -> "
              f"{rep['mean_delta_points']:+} points (up {rep['parsers_up']}, down {rep['parsers_down']}, "
              f"largest {rep['max_delta_points']:+})")
    name = os.path.splitext(os.path.basename(fixes_path))[0]
    json.dump(report, open(os.path.join(HERE, 'work', f'impact_{name}.json'), 'w', encoding='utf-8'), indent=1)


if __name__ == '__main__':
    main(sys.argv[1])
