# Script de migração para copiar assinaturas dos produtos para a requisição
# Uso: python manage.py shell < scripts/migrar_assinaturas_requisicao.py

from cadastros.models import EmprestimoProdutor, Requisicao
from django.db import transaction

count = 0
with transaction.atomic():
    for req in Requisicao.objects.all():
        # Busca um produto da requisição que tenha assinatura de liberação
        emp = EmprestimoProdutor.objects.filter(requisicao=req).exclude(assinatura_liberador_imagem='').first()
        if emp and not req.assinatura_liberacao_interna_imagem:
            req.assinatura_liberacao_interna_imagem = emp.assinatura_liberador_imagem
            req.assinatura_liberacao_interna_nome = emp.assinatura_liberador_nome
            req.assinatura_liberacao_interna_datahora = emp.assinatura_liberador_datahora
            req.assinatura_liberacao_interna_usuario = emp.liberado_por
            req.save(update_fields=[
                'assinatura_liberacao_interna_imagem',
                'assinatura_liberacao_interna_nome',
                'assinatura_liberacao_interna_datahora',
                'assinatura_liberacao_interna_usuario',
            ])
            count += 1
        # Busca um produto da requisição que tenha assinatura do produtor
        emp_prod = EmprestimoProdutor.objects.filter(requisicao=req).exclude(assinatura_produtor_imagem='').first()
        if emp_prod and not req.assinatura_produtor_imagem:
            req.assinatura_produtor_imagem = emp_prod.assinatura_produtor_imagem
            req.assinatura_produtor_nome = emp_prod.assinatura_produtor_nome
            req.assinatura_produtor_datahora = emp_prod.assinatura_produtor_datahora
            req.assinatura_produtor_usuario = emp_prod.assinatura_produtor_usuario
            req.save(update_fields=[
                'assinatura_produtor_imagem',
                'assinatura_produtor_nome',
                'assinatura_produtor_datahora',
                'assinatura_produtor_usuario',
            ])
            count += 1
print(f"Migração concluída. Assinaturas copiadas para {count} requisições.")
