#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from cadastros.models import EstagioDesenvolvimento

print('=' * 70)
print('CONTAGEM DE ESTÁGIOS IMPORTADOS')
print('=' * 70)

# Templates (padrão do sistema)
templates = EstagioDesenvolvimento.objects.filter(
    eh_template=True,
    empresa__isnull=True
)

print(f'\n📊 Total de Templates Padrão: {templates.count()}')
print('\nDetalhamento por Praga:')

pragas = templates.values('praga__nome_comum').distinct().order_by('praga__nome_comum')
for item in pragas:
    praga_nome = item['praga__nome_comum']
    qty = templates.filter(praga__nome_comum=praga_nome).count()
    print(f'  • {praga_nome}: {qty} estágios')
    
    # Listar estágios
    estagios = templates.filter(praga__nome_comum=praga_nome).order_by('ordem_ciclo')
    for e in estagios:
        print(f'      - {e.descricao} (Duração: {e.duracao_minima_dias}-{e.duracao_maxima_dias} dias)')

print('\n' + '=' * 70)

# Estágios copiados para empresas
cópias = EstagioDesenvolvimento.objects.filter(
    template_original__isnull=False
)

print(f'\n🔗 Estágios Copiados para Empresas: {cópias.count()}')
if cópias.exists():
    empresas_com_copies = cópias.values('empresa__nome').distinct().order_by('empresa__nome')
    for item in empresas_com_copies:
        empresa = item['empresa__nome']
        qty = cópias.filter(empresa__nome=empresa).count()
        print(f'  • {empresa}: {qty} estágios copiados')

print('\n' + '=' * 70)
print('\n✅ RESUMO:')
print(f'   Total de Templates no Sistema: {templates.count()}')
print(f'   Total de Cópias para Empresas: {cópias.count()}')
print('=' * 70)
