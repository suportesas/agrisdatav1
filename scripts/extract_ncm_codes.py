import csv, sys, re, io
from unicodedata import normalize
path = sys.argv[1]
out = sys.argv[2] if len(sys.argv)>2 else 'c:\\erp_agricola\\arq_ncm\\ncm_extracted.csv'

with open(path, 'r', encoding='utf-8', errors='replace') as fh:
    text = fh.read()

# detect delimiter
from csv import Sniffer
try:
    delim = Sniffer().sniff(text[:8192]).delimiter
except Exception:
    delim = ','

reader = csv.DictReader(io.StringIO(text), delimiter=delim)

rows = []
for r in reader:
    # get codigo-like key
    keys = list(r.keys())
    # normalize keys
    norm_keys = {normalize('NFKD', k).encode('ascii','ignore').decode().lower(): k for k in keys}
    codigo_key = None
    nome_key = None
    for k in ['codigo','cod','ncm','codigo_ncm']:
        if k in norm_keys:
            codigo_key = norm_keys[k]
            break
    for k in ['descricao','nome','descri','descrição']:
        if k in norm_keys:
            nome_key = norm_keys[k]
            break
    # fallback to first two columns
    if not codigo_key:
        codigo_key = keys[0]
    if not nome_key and len(keys)>1:
        nome_key = keys[1]
    codigo_raw = (r.get(codigo_key) or '').strip()
    nome_raw = (r.get(nome_key) or '').strip() if nome_key else ''
    codigo_norm = re.sub(r'\D','', codigo_raw)
    if len(codigo_norm)==8:
        rows.append({'codigo': codigo_norm, 'nome': nome_raw})

# write out
with open(out, 'w', newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, fieldnames=['codigo','nome'])
    w.writeheader()
    for row in rows:
        w.writerow(row)

print('Extracted', len(rows), 'full NCMs to', out)
if len(rows):
    print('Sample:', rows[:10])
