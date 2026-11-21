"""One command: run every ParseBench 2 answer-key check and write one review list.

  python audit.py                       # all text and table subsets at Hugging Face main
  python audit.py --subsets text,tables # some subsets

Runs fetch.py (if data/ is missing), then gtcheck.py pdf / consensus / omissions / phantom / spans and wdiff.py on the
flagged pages, and writes work/REVIEW.md: one section per flagged page with what the reference says, what the page
and most published outputs say, and a link to the page in the dataset. Nothing is decided automatically: every
entry is a candidate for a person to confirm on the page image, then to score with impact.py.
"""
import argparse, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
TEXT = ['text']
TABLES = ['tables', 'complex_table_headers', 'financial_tables', 'insurance_filing_tables', 'dense_tables']
HF = 'https://huggingface.co/datasets/llamaindex/ParseBench-2/blob/main/'


def run(*args):
    print('$', ' '.join(args), flush=True)
    subprocess.run([PY, '-X', 'utf8', *args], cwd=HERE, check=True)


def load(name):
    p = os.path.join(HERE, 'work', name)
    return json.load(open(p, encoding='utf-8')) if os.path.exists(p) else []


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--subsets', default=','.join(TEXT + TABLES)); a = ap.parse_args()
    subsets = [s for s in a.subsets.split(',') if s]
    if not os.path.isdir(os.path.join(HERE, 'data', 'gt_main')): run('fetch.py')
    for s in subsets:
        run('gtcheck.py', 'pdf', s); run('gtcheck.py', 'consensus', s)
        if s not in TABLES: run('gtcheck.py', 'omissions', s)   # table keys hold only the tables: page prose is not missing
        if s in TABLES: run('gtcheck.py', 'phantom', s)
        run('gtcheck.py', 'spans', s); run('wdiff.py', '--all', s)
    pages = {}
    for s in subsets:
        for c in load(f'candidates_{s}.json'):
            pages.setdefault(c['id'], []).append(f"number `{c['token'].lstrip('#')}`: reference has it {c['in_key']}x, page {c['in_pdf']}x; "
                                                 f"{c['parsers_with_fewer']}/{c['parsers']} outputs side with the page{' (scanned page)' if c['scanned'] else ''}")
        for c in (load(f'omissions_{s}.json') if s not in TABLES else []):
            pages.setdefault(c['id'], []).append(f"number `{c['token'].lstrip('#')}`: page has it {c['in_pdf']}x, reference {c['in_key']}x; "
                                                 f"{c['parsers_with_more']}/{c['parsers']} outputs side with the page")
        for c in load(f'phantom_{s}.json'):
            pages.setdefault(c['id'], []).append(f"table {c['table']} row {c['row']} not on the page ({c['in_pdf']:.0%} of its words found): "
                                                 f"{' | '.join(x[:30] for x in c['cells'][:5])}; {c['parsers_lacking']}/{c['parsers']} outputs lack it")
        for c in load(f'wdiff_{s}.json'):
            if s in TABLES and c['op'] == 'insert': continue    # page text outside the tables
            pages.setdefault(c['id'], []).append(f"wording ({c['op']}): reference `{c['key']}` / page `{c['pdf']}`; "
                                                 f"{c['parsers_with_pdf']}/{c['parsers']} outputs side with the page")
    out = ['# ParseBench 2 answer-key review list', '',
           f'{len(pages)} pages flagged in {", ".join(subsets)}. Every entry is a candidate: confirm it on the page image '
           'before calling it an error, then score the correction with impact.py.', '']
    for pid in sorted(pages):
        out += [f'## {pid}', f'[{pid}.pdf]({HF}{pid}.pdf)', ''] + [f'- {x}' for x in pages[pid]] + ['']
    open(os.path.join(HERE, 'work', 'REVIEW.md'), 'w', encoding='utf-8').write('\n'.join(out))
    print(f'wrote work/REVIEW.md: {len(pages)} pages')


if __name__ == '__main__':
    main()
