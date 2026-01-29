import csv
import re
from pathlib import Path

src = Path('tmp_cfop_converted.csv')
dst = Path('tmp_cfop_fixed2.csv')

pattern = re.compile(r"\s+(\d)\.(\d{3})\s*-\s*")

with src.open(newline='', encoding='utf-8') as s, dst.open('w', newline='', encoding='utf-8') as d:
    reader = csv.DictReader(s)
    writer = csv.DictWriter(d, fieldnames=['codigo','nome','descricao'])
    writer.writeheader()
    for row in reader:
        codigo = row['codigo'].strip()
        nome = row.get('nome','').strip()
        descricao = row.get('descricao','').strip()
        m = pattern.search(nome)
        if m:
            # split at match
            start = m.start()
            code_part = m.group(1) + m.group(2)
            before = nome[:start].strip()
            after = nome[m.end():].strip()
            # write original trimmed
            writer.writerow({'codigo': codigo, 'nome': before, 'descricao': descricao})
            # write new split code row
            writer.writerow({'codigo': code_part, 'nome': after, 'descricao': ''})
        else:
            writer.writerow({'codigo': codigo, 'nome': nome, 'descricao': descricao})

print('wrote', dst)
