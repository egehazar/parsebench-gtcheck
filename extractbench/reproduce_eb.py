"""Reproduce an ExtractBench leaderboard Value F1 with the same per-document path eb_impact.py and valcheck.py use.

Scores one pipeline's published outputs on every document with prepare_extract_scoring_inputs(...)
.compute_unified_metrics(), then reports both the mean of document F1s and the pooled (micro) F1 from the
documents' precision/recall counts, per split and overall, to compare with leaderboard.csv.

  python reproduce_eb.py llamaextract_agentic_plus   -> work/reproduce_eb_<pipeline>.json
"""
import json, statistics, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SIDE = HERE / 'data' / 'sidecar'
RES = HERE / 'data' / 'results' / 'results'


def main(pipe):
    from extract_bench.test_cases.loader import load_test_case
    from extract_bench.evaluation.evaluators.extract import prepare_extract_scoring_inputs
    out = {'pipeline': pipe, 'splits': {}}
    allf1 = []
    for split in ['short', 'medium', 'long']:
        recs = {}
        for line in open(RES / pipe / f'{split}.jsonl', encoding='utf-8'):
            r = json.loads(line); recs[(r.get('request') or {}).get('example_id')] = (r.get('output') or {}).get('extracted_data')
        f1s, meta_keys = [], set()
        for tj in sorted((SIDE / split).rglob('*.test.json')):
            stem = tj.name.removesuffix('.test.json'); eid = f'{split}/{stem}'
            tc = load_test_case(tj.with_name(f'{stem}.pdf'), tj)
            data = recs.get(eid)
            if data is None: f1s.append(0.0); continue
            ms = prepare_extract_scoring_inputs(tc, data, []).compute_unified_metrics(None)
            v = next((m for m in ms if m.metric_name == 'extract_unified_value_f1'), None)
            f1s.append(v.value if v else 0.0)
            if v and v.metadata: meta_keys |= set(v.metadata)
        out['splits'][split] = {'docs': len(f1s), 'mean_doc_f1': round(100 * statistics.mean(f1s), 2), 'metadata_keys': sorted(meta_keys)[:20]}
        allf1 += f1s
        print(split, out['splits'][split]['docs'], 'docs, mean doc F1', out['splits'][split]['mean_doc_f1'], flush=True)
    out['overall_mean_doc_f1'] = round(100 * statistics.mean(allf1), 2)
    print('overall mean doc F1', out['overall_mean_doc_f1'])
    json.dump(out, open(HERE / 'work' / f'reproduce_eb_{pipe}.json', 'w', encoding='utf-8'), indent=1)


if __name__ == '__main__':
    main(sys.argv[1])
