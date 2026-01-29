import sys, csv, io
path = sys.argv[1]
text = open(path, 'r', encoding='utf-8', errors='replace').read()
sample = text[:8192]
import csv
sniffer = csv.Sniffer()
try:
    dialect = sniffer.sniff(sample)
    delim = dialect.delimiter
except Exception:
    delim = ','
reader = csv.DictReader(io.StringIO(text), delimiter=delim)
from unicodedata import normalize

def norm(s):
    s = normalize('NFKD', s)
    s = ''.join(ch for ch in s if not ch in '́`^~')
    return s

for i, r in enumerate(reader):
    if i>=50: break
    # print keys
    keys = list(r.keys())
    # try various keys
    candidate = None
    for k in keys:
        if k.lower().replace('í','i').replace('ó','o').strip().startswith('cod'):
            candidate = k
            break
    print(i+1, 'keys:', keys[:6], 'candidate_key=', candidate, 'value=', r.get(candidate))
