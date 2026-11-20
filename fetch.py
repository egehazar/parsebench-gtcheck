"""Download the newest ParseBench 2 answer key and all published parser outputs for the text and table subsets."""
import sys, time
from huggingface_hub import snapshot_download
SUBSETS = ['text', 'tables', 'complex_table_headers', 'financial_tables', 'insurance_filing_tables', 'dense_tables']
t = time.time()
gt = snapshot_download('llamaindex/ParseBench-2', repo_type='dataset', revision='main', local_dir='data/gt_main',
                       allow_patterns=[f'{s}/*' for s in SUBSETS] + [f'{s}.jsonl' for s in SUBSETS] + ['README.md', 'CHANGELOG.md'])
print('gt done', round(time.time() - t), 's', flush=True)
res = snapshot_download('llamaindex/ParseBench-2-results', repo_type='dataset', revision='main', local_dir='data/results',
                        allow_patterns=[f'results/*/{s}.jsonl' for s in SUBSETS] + ['README.md', '*.py', 'results/*/failed.json'])
print('results done', round(time.time() - t), 's', flush=True)
