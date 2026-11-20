"""Reproduce a leaderboard row's Text and Tables dimensions with the same per-page scoring impact.py uses.

Ground truth: the revision the leaderboard is pinned to (leaderboard/results-v2.yaml data_revision), as downloaded
by rescore.py into ParseBench/.cache/leaderboard-gt/<rev>. Outputs: the row's pinned results revision
(data/rescore/hf/results/<pipeline>). A page with no usable output scores 0, as in the harness. Dimension weights
follow the ParseBench README: Text = the text subset; Tables = tables 1/2, complex_table_headers, financial_tables,
insurance_filing_tables and dense_tables 1/8 each.

  python reproduce.py llamaparse_agentic_plus   -> work/reproduce_<pipeline>.json
"""
import glob, json, os, statistics, sys
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'ParseBench', 'src'))
from parse_bench.test_cases.loader import load_test_case  # noqa: E402
from parse_bench.schemas.pipeline_io import InferenceResult  # noqa: E402
from parse_bench.evaluation.metrics.parse.next_metrics import compute_next_metrics  # noqa: E402

REV = '2d9a2344660647e87dc272458ea1978428f895eb'
GT = os.path.join(HERE, 'ParseBench', '.cache', 'leaderboard-gt', REV)
WEIGHTS = {'text': {'text': 1.0},
           'tables': {'tables': 0.5, 'complex_table_headers': 0.125, 'financial_tables': 0.125,
                      'insurance_filing_tables': 0.125, 'dense_tables': 0.125}}
METRIC = {'text': 'text_next', 'tables': 'table_next'}


def subset_mean(pipeline, subset, metric):
    recs = {}
    f = os.path.join(HERE, 'data', 'rescore', 'hf', 'results', pipeline, f'{subset}.jsonl')
    for line in open(f, encoding='utf-8'):
        r = json.loads(line); recs[(r.get('output') or {}).get('example_id')] = r
    scores, n_missing, n_na = [], 0, 0
    for pdf in sorted(glob.glob(os.path.join(GT, subset, '*.pdf'))):
        tc = load_test_case(Path(pdf))
        if tc is None: continue
        r = recs.get(tc.test_id)
        if r is None or not ((r.get('output') or {}).get('markdown') or '').strip():
            n_missing += 1; scores.append(0.0); continue
        vals = [m.value for m in compute_next_metrics(InferenceResult.model_validate(r), tc) if m.metric_name == metric]
        if not vals: n_na += 1; continue
        scores.append(vals[0])
    return statistics.mean(scores), len(scores), n_missing, n_na


if __name__ == '__main__':
    pipe = sys.argv[1]; out = {'pipeline': pipe, 'data_revision': REV, 'subsets': {}, 'dimensions': {}}
    for dim, ws in WEIGHTS.items():
        tot = 0.0
        for subset, w in ws.items():
            m, n, miss, na = subset_mean(pipe, subset, METRIC[dim])
            out['subsets'][subset] = {'mean': round(100 * m, 2), 'pages': n, 'no_output': miss, 'metric_not_applicable': na}
            print(f'{subset}: {100 * m:.2f} over {n} pages ({miss} without output, {na} not applicable)', flush=True)
            tot += w * m
        out['dimensions'][dim] = round(100 * tot, 2)
        print(f'== {dim}: {100 * tot:.2f}', flush=True)
    json.dump(out, open(os.path.join(HERE, 'work', f'reproduce_{pipe}.json'), 'w', encoding='utf-8'), indent=1)
