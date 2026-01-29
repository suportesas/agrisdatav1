import sys
import csv
import io
import re

path = sys.argv[1]
print('Path:', path)

# Try encodings
encodings = ['utf-8', 'latin-1', 'cp1252']
text = None
for enc in encodings:
    try:
        with open(path, 'r', encoding=enc, errors='replace') as fh:
            text = fh.read()
        print('decoded with', enc)
        break
    except Exception as e:
        print('failed encoding', enc, e)

if text is None:
    print('Could not decode file')
    sys.exit(1)

# Try JSON
import json
try:
    parsed = json.loads(text)
    if isinstance(parsed, list):
        rows = parsed
    elif isinstance(parsed, dict) and isinstance(parsed.get('data'), list):
        rows = parsed.get('data')
    else:
        rows = None
    if rows is not None:
        print('Detected JSON with', len(rows), 'rows')
        # Normalize with accent-insensitive keys
        import unicodedata
        def norm(s):
            if s is None:
                return ''
            s = str(s)
            s = unicodedata.normalize('NFKD', s)
            s = ''.join(ch for ch in s if not unicodedata.combining(ch))
            return s.lower().strip()
        def get_field(d, candidates):
            for c in candidates:
                if c in d and d[c] is not None:
                    return str(d[c]).strip()
            norm_map = {norm(k): k for k in d.keys()}
            for c in candidates:
                if norm(c) in norm_map:
                    k = norm_map[norm(c)]
                    if d.get(k) is not None:
                        return str(d.get(k)).strip()
            for k in d.keys():
                if norm(k) in ['codigo','cod','ncm','codigo_ncm']:
                    if d.get(k) is not None:
                        return str(d.get(k)).strip()
            return ''
        valid = 0
        invalid = 0
        invalid_samples = []
        valid_samples = []
        for r in rows:
            codigo = get_field(r, ['codigo','Codigo','CÓDIGO','cod','Código'])
            codigo_norm = re.sub(r"\D", '', codigo)
            if len(codigo_norm)==8:
                valid += 1
                if len(valid_samples)<10:
                    valid_samples.append(codigo_norm)
            else:
                invalid += 1
                if len(invalid_samples)<10:
                    invalid_samples.append(codigo)
        print('valid:', valid, 'invalid:', invalid)
        if valid_samples:
            print('valid samples:', valid_samples)
        if invalid_samples:
            print('invalid samples:', invalid_samples)
        sys.exit(0)
except Exception as e:
    pass

# Fallback to CSV
sniffer = csv.Sniffer()
try:
    dialect = sniffer.sniff(text[:8192])
    delim = dialect.delimiter
    print('Detected delimiter:', repr(delim))
except Exception:
    delim = ','
    print('Using default delimiter ,')

reader = csv.DictReader(io.StringIO(text), delimiter=delim)
rows = list(reader)
print('CSV rows:', len(rows))
valid = 0
invalid = 0
invalid_samples = []
for r in rows:
    codigo = ''
    for k in ('codigo','Codigo','CÓDIGO','cod','ncm'):
        if k in r and r[k] is not None:
            codigo = str(r[k] or '').strip()
            break
    codigo_norm = re.sub(r"\D", '', codigo)
    if len(codigo_norm)==8:
        valid += 1
    else:
        invalid += 1
        if len(invalid_samples)<10:
            invalid_samples.append(codigo)
print('valid:', valid, 'invalid:', invalid)
if invalid_samples:
    print('invalid samples:', invalid_samples)
