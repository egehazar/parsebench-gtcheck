"""ExtractBench answer key (HF main) and every pipeline's eval-tier outputs (results/, not raw/ or traces/)."""
import time
from huggingface_hub import snapshot_download
t = time.time()
snapshot_download('llamaindex/ExtractBench', repo_type='dataset', revision='main', local_dir='data/gt')
print('gt done', round(time.time() - t), 's', flush=True)
snapshot_download('llamaindex/ExtractBench-results', repo_type='dataset', revision='main', local_dir='data/results',
                  allow_patterns=['results/*', 'tools/*', 'data_manifest.json', 'pipelines.jsonl', 'schema/*', 'README.md'])
print('results done', round(time.time() - t), 's', flush=True)
