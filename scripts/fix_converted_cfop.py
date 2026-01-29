import csv
from pathlib import Path

src = Path('tmp_cfop_converted.csv')
dst = Path('tmp_cfop_fixed.csv')

with src.open(newline='', encoding='utf-8') as s, dst.open('w', newline='', encoding='utf-8') as d:
    reader = csv.DictReader(s)
    writer = csv.DictWriter(d, fieldnames=['codigo','nome','descricao'])
    writer.writeheader()
    for row in reader:
        codigo = row['codigo'].strip()
        nome = row.get('nome','').strip()
        descricao = row.get('descricao','').strip()
        # If codigo is more than 4 digits and consists of concatenated 4-digit codes, split
        if codigo.isdigit() and len(codigo) % 4 == 0 and len(codigo) > 4:
            parts = [codigo[i:i+4] for i in range(0, len(codigo), 4)]
            for p in parts:
                writer.writerow({'codigo': p, 'nome': nome, 'descricao': descricao})
        else:
            writer.writerow({'codigo': codigo, 'nome': nome, 'descricao': descricao})

print('fixed written to', dst)
