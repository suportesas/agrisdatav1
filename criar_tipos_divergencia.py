"""
Script para criar tipos de divergência padrão para cada empresa
Execute após makemigrations e migrate
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from compras.models import TipoDivergencia
from empresas.models import Empresa

# Tipos padrão de divergência
TIPOS_PADRAO = [
    {
        'codigo': 'DANO_EXT',
        'nome': 'Danos Externos',
        'descricao': 'Caixa, embalagem ou produto com danos visíveis na parte externa',
        'severidade': 'LEVE'
    },
    {
        'codigo': 'LACRE_ROMPIDO',
        'nome': 'Lacre Rompido',
        'descricao': 'Lacre de segurança quebrado ou danificado indicando violação',
        'severidade': 'GRAVE'
    },
    {
        'codigo': 'SUJEIRA',
        'nome': 'Sujeira / Contaminação',
        'descricao': 'Produto sujo, com manchas, resíduos ou sinais de contaminação',
        'severidade': 'MEDIO'
    },
    {
        'codigo': 'VENCIDO',
        'nome': 'Produto Vencido',
        'descricao': 'Produto com vencimento expirado ou próximo de vencer',
        'severidade': 'GRAVE'
    },
    {
        'codigo': 'QTD_DIFERENTE',
        'nome': 'Quantidade Diferente',
        'descricao': 'Quantidade recebida não corresponde à nota fiscal ou pedido',
        'severidade': 'MEDIO'
    },
    {
        'codigo': 'PRODUTO_ERRADO',
        'nome': 'Produto Errado',
        'descricao': 'Produto entregue não corresponde ao solicitado ou nota fiscal',
        'severidade': 'GRAVE'
    },
    {
        'codigo': 'DEFEITO',
        'nome': 'Defeito de Fabricação',
        'descricao': 'Produto com defeito, quebrado ou não funciona conforme esperado',
        'severidade': 'GRAVE'
    },
    {
        'codigo': 'TEMP_RUIM',
        'nome': 'Problemas de Temperatura',
        'descricao': 'Produto refrigerado chegou aquecido ou congelado chegou descongelado',
        'severidade': 'GRAVE'
    },
    {
        'codigo': 'DOCUMENTACAO',
        'nome': 'Problema com Documentação',
        'descricao': 'NF-e, comprovante ou documentação ausente ou incorreta',
        'severidade': 'LEVE'
    },
    {
        'codigo': 'DIVERGENCIA_PRECO',
        'nome': 'Divergência de Preço',
        'descricao': 'Valor cobrado diferente do solicitado ou cotação aprovada',
        'severidade': 'MEDIO'
    },
]

def criar_tipos_padrao():
    """Cria os tipos de divergência padrão para todas as empresas"""
    empresas = Empresa.objects.filter(ativo=True)
    
    if not empresas.exists():
        print('❌ Nenhuma empresa ativa encontrada!')
        return
    
    for empresa in empresas:
        print(f'\n📦 Criando tipos de divergência para: {empresa.nome}')
        
        criados = 0
        for tipo_dados in TIPOS_PADRAO:
            tipo, created = TipoDivergencia.objects.get_or_create(
                empresa=empresa,
                codigo=tipo_dados['codigo'],
                defaults={
                    'nome': tipo_dados['nome'],
                    'descricao': tipo_dados['descricao'],
                    'severidade': tipo_dados['severidade'],
                }
            )
            
            if created:
                print(f'  ✅ {tipo.nome} ({tipo.severidade})')
                criados += 1
            else:
                print(f'  ℹ️  {tipo.nome} (já existia)')
        
        print(f'  Total criado: {criados}/{len(TIPOS_PADRAO)}')
    
    print('\n✨ Tipos de divergência configurados com sucesso!')
    print('\nVocê pode agora:')
    print('  1. Acessar http://127.0.0.1:8000/admin/compras/tipodivergencia/')
    print('  2. Editar ou adicionar mais tipos de divergência')
    print('  3. Usar os tipos ao conferir recebimentos')

if __name__ == '__main__':
    criar_tipos_padrao()
