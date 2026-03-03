#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para criar formas de pagamento padrão no sistema
Boleto, PIX, Transferência, Cheque, etc
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from financeiro.models import FormaPagemento
from decimal import Decimal

# Definir formas de pagamento padrão
formas_padrao = [
    {
        'nome': 'PIX',
        'descricao': 'Transferência instantânea por PIX - Processamento imediato',
        'dias_processamento': 0,
        'taxa_administrativa': Decimal('0.00'),
        'ordem_exibicao': 1,
    },
    {
        'nome': 'Transferência Bancária',
        'descricao': 'Transferência eletrônica (TED/DOC) - 1 a 2 dias úteis',
        'dias_processamento': 1,
        'taxa_administrativa': Decimal('0.00'),
        'ordem_exibicao': 2,
    },
    {
        'nome': 'Boleto',
        'descricao': 'Boleto bancário - Processamento em até 3 dias úteis',
        'dias_processamento': 2,
        'taxa_administrativa': Decimal('1.50'),
        'ordem_exibicao': 3,
    },
    {
        'nome': 'Cheque',
        'descricao': 'Cheque pré-datado ou à vista',
        'dias_processamento': 1,
        'taxa_administrativa': Decimal('0.50'),
        'ordem_exibicao': 4,
    },
    {
        'nome': 'Dinheiro',
        'descricao': 'Pagamento em dinheiro à vista',
        'dias_processamento': 0,
        'taxa_administrativa': Decimal('0.00'),
        'ordem_exibicao': 5,
    },
    {
        'nome': 'Cartão de Crédito',
        'descricao': 'Cartão de crédito - Processamento em 1-2 dias úteis',
        'dias_processamento': 1,
        'taxa_administrativa': Decimal('2.50'),
        'ordem_exibicao': 6,
    },
    {
        'nome': 'Crediário',
        'descricao': 'Crediário próprio da empresa',
        'dias_processamento': 0,
        'taxa_administrativa': Decimal('5.00'),
        'ordem_exibicao': 7,
    },
]

# Criar ou atualizar formas de pagamento
for forma_data in formas_padrao:
    forma, created = FormaPagemento.objects.get_or_create(
        nome=forma_data['nome'],
        defaults={
            'descricao': forma_data['descricao'],
            'dias_processamento': forma_data['dias_processamento'],
            'taxa_administrativa': forma_data['taxa_administrativa'],
            'ordem_exibicao': forma_data['ordem_exibicao'],
            'ativo': True,
        }
    )
    
    status = '✅ CRIADA' if created else '⏸️  JÁ EXISTS'
    print(f"{status}: {forma.nome}")
    
    if not created:
        # Atualizar alguns campos se já existe
        forma.descricao = forma_data['descricao']
        forma.dias_processamento = forma_data['dias_processamento']
        forma.ordem_exibicao = forma_data['ordem_exibicao']
        forma.save()

print(f"\n✅ Total de formas de pagamento: {FormaPagemento.objects.count()}")
print("\n📋 Formas de pagamento disponíveis:")
for forma in FormaPagemento.objects.all().order_by('ordem_exibicao'):
    print(f"   • {forma.nome} - {forma.descricao}")
