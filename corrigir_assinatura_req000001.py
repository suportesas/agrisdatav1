# Script de correção para assinatura única na REQ-000001
# Executa apenas para a requisição informada, sem alterar outras partes do sistema


# Script para rodar diretamente via: python corrigir_assinatura_req000001.py
# Aplica a assinatura do produto já assinado para os demais produtos pendentes da REQ-000001
# NÃO altera nenhuma outra parte do sistema

import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from cadastros.models import EmprestimoProdutor, Requisicao
from django.core.files.base import ContentFile

numero_requisicao = "REQ-000001"

try:
    requisicao = Requisicao.objects.get(numero=numero_requisicao)
    emprestimos = EmprestimoProdutor.objects.filter(requisicao=requisicao)
    emprestimo_assinado = emprestimos.filter(assinatura_produtor_datahora__isnull=False).first()

    if emprestimo_assinado:
        for emp in emprestimos.filter(assinatura_produtor_datahora__isnull=True):
            emp.assinatura_produtor_usuario = emprestimo_assinado.assinatura_produtor_usuario
            emp.assinatura_produtor_nome = emprestimo_assinado.assinatura_produtor_nome
            emp.assinatura_produtor_datahora = emprestimo_assinado.assinatura_produtor_datahora
            if emprestimo_assinado.assinatura_produtor_imagem:
                emp.assinatura_produtor_imagem.save(
                    f"assinatura_produtor_{emp.pk}.png",
                    ContentFile(emprestimo_assinado.assinatura_produtor_imagem.read()),
                    save=False
                )
            emp.save(update_fields=[
                'assinatura_produtor_usuario',
                'assinatura_produtor_nome',
                'assinatura_produtor_datahora',
                'assinatura_produtor_imagem',
                'atualizado_em',
            ])
        print("Correção aplicada com sucesso.")
    else:
        print("Nenhum produto assinado encontrado para copiar os dados.")
except Exception as e:
    print(f"Erro ao aplicar correção: {e}")
