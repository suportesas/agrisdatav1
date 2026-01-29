from pathlib import Path
import re
import csv

src = Path('arq_cfop/C.csv')
dst = Path('tmp_cfop_fixed2.csv')

def clean_field(s):
    # strip outer quotes and whitespace, collapse doubled quotes
    s = s.strip()
    if s.startswith('"') and s.endswith('"'):
        s = s[1:-1]
    s = s.replace('""','"')
    return s.strip()

out_rows = []
with src.open(encoding='utf-8') as f:
    for raw in f:
        raw = raw.strip()
        if not raw:
            continue
        # remove surrounding double quotes if present
        line = raw
        if line.startswith('"') and line.endswith('"'):
            line = line[1:-1]
        # Now split on the first semicolon
        if ';' in line:
            code_part, name_part = line.split(';', 1)
        else:
            # fallback: try whitespace split
            parts = line.split(None,1)
            code_part = parts[0]
            name_part = parts[1] if len(parts)>1 else ''
        code = re.sub(r'\D','', code_part)
        name = clean_field(name_part)
        # If code is concatenation of multiple 4-digit codes, split
        if code.isdigit() and len(code) > 4 and len(code) % 4 == 0:
            parts = [code[i:i+4] for i in range(0,len(code),4)]
            for p in parts:
                out_rows.append({'codigo': p, 'nome': name, 'descricao': ''})
        else:
            out_rows.append({'codigo': code, 'nome': name, 'descricao': ''})

# write out
with dst.open('w', newline='', encoding='utf-8') as d:
    writer = csv.DictWriter(d, fieldnames=['codigo','nome','descricao'])
    writer.writeheader()
    for r in out_rows:
        writer.writerow(r)

print('wrote', dst, 'with', len(out_rows),'rows')
