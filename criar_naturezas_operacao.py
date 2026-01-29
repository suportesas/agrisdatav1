import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from produtos.models import NaturezaOperacao

naturezas_data = [
    {'codigo': 'VENDA', 'descricao': 'Venda de mercadoria adquirida ou recebida de terceiros', 'tipo': 'SAIDA'},
    {'codigo': 'VENDA-PROD', 'descricao': 'Venda de produção do estabelecimento', 'tipo': 'SAIDA'},
    {'codigo': 'COMPRA', 'descricao': 'Compra para comercialização', 'tipo': 'ENTRADA'},
    {'codigo': 'COMPRA-USO', 'descricao': 'Compra para uso ou consumo', 'tipo': 'ENTRADA'},
    {'codigo': 'DEVOLUCAO', 'descricao': 'Devolução de mercadoria', 'tipo': 'AMBOS'},
    {'codigo': 'TRANSFERENCIA', 'descricao': 'Transferência entre estabelecimentos', 'tipo': 'AMBOS'},
    {'codigo': 'REMESSA-DEP', 'descricao': 'Remessa em depósito fechado', 'tipo': 'SAIDA'},
    {'codigo': 'RETORNO-DEP', 'descricao': 'Retorno de mercadoria em depósito', 'tipo': 'ENTRADA'},
    {'codigo': 'BONIFICACAO', 'descricao': 'Remessa por bonificação', 'tipo': 'SAIDA'},
    {'codigo': 'DEMONSTRACAO', 'descricao': 'Remessa para demonstração', 'tipo': 'SAIDA'},
    {'codigo': 'CONSIGNACAO', 'descricao': 'Remessa em consignação mercantil', 'tipo': 'SAIDA'},
    {'codigo': 'INDUSTRIALIZACAO', 'descricao': 'Remessa para industrialização', 'tipo': 'SAIDA'},
]

print("=== Criando Naturezas de Operação ===\n")

for nat_data in naturezas_data:
    natureza, created = NaturezaOperacao.objects.get_or_create(
        codigo=nat_data['codigo'],
        defaults={
            'descricao': nat_data['descricao'],
            'tipo': nat_data['tipo']
        }
    )
    status = '✅ Criada' if created else '⚠️  Já existe'
    print(f"{status}: {natureza.codigo} - {natureza.descricao}")

print(f"\n✅ Total de naturezas: {NaturezaOperacao.objects.count()}")
