import csv

src = 'arq_cfop/C.csv'
dst = 'tmp_cfop_converted.csv'

with open(src, newline='', encoding='utf-8') as s, open(dst, 'w', newline='', encoding='utf-8') as d:
    reader = csv.reader(s, delimiter=';', quotechar='"')
    writer = csv.writer(d)
    writer.writerow(['codigo','nome','descricao'])
    for row in reader:
        if not row:
            continue
        codigo = row[0].strip()
        nome = row[1].strip() if len(row) > 1 else ''
        descricao = ''
        writer.writerow([codigo, nome, descricao])

print('converted', dst)
