"""Download the newest answer key and all published outputs for the chart and formatting subsets."""
import time
from huggingface_hub import snapshot_download
SUBSETS = ['charts', 'headings', 'strikeout', 'underline']
t = time.time()
snapshot_download('llamaindex/ParseBench-2', repo_type='dataset', revision='main', local_dir='data/gt_main',
                  allow_patterns=[f'{s}/*' for s in SUBSETS] + [f'{s}.jsonl' for s in SUBSETS])
print('gt done', round(time.time() - t), 's', flush=True)
snapshot_download('llamaindex/ParseBench-2-results', repo_type='dataset', revision='main', local_dir='data/results',
                  allow_patterns=[f'results/*/{s}.jsonl' for s in SUBSETS])
print('results done', round(time.time() - t), 's', flush=True)
