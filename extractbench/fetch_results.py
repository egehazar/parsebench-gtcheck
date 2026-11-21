"""ExtractBench-results eval tier only (results/<pipeline>/*.jsonl) plus pipeline metadata."""
import time
from huggingface_hub import snapshot_download
t = time.time()
snapshot_download('llamaindex/ExtractBench-results', repo_type='dataset', revision='main', local_dir='data/results',
                  allow_patterns=['results/*', 'tools/*', 'data_manifest.json', 'pipelines.jsonl', 'README.md'], max_workers=4)
print('results done', round(time.time() - t), 's', flush=True)
