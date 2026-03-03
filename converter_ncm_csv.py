import csv

# Caminhos dos arquivos
input_path = 'Tabela_NCM_Vigente_20260225.csv'  # CSV gerado da planilha oficial
output_path = 'NCM_import.csv'

def limpar_codigo(codigo):
    """Remove pontos, traços e espaços, retorna apenas se tiver exatamente 8 dígitos."""
    digitos = ''.join(c for c in codigo if c.isdigit())
    return digitos if len(digitos) == 8 else None

with open(input_path, encoding='utf-8-sig') as infile, \
     open(output_path, 'w', newline='', encoding='utf-8') as outfile:

    writer = csv.writer(outfile)
    writer.writerow(['codigo', 'nome'])

    reader = csv.reader(infile, delimiter=';')
    next(reader)  # pula o cabeçalho

    count = 0
    for row in reader:
        if len(row) < 2:
            continue

        codigo = limpar_codigo(row[0].strip())
        nome = row[1].strip().strip('"').strip()

        if codigo and nome:
            writer.writerow([codigo, nome])
            count += 1

print(f'Total de NCMs exportados: {count}')