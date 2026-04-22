import logging
from django.db.models.signals import pre_save
from django.dispatch import receiver
from produtos.models import Produto

logger = logging.getLogger('estoque.auditoria')

@receiver(pre_save, sender=Produto)
def log_estoque_atual_alterado(sender, instance, **kwargs):
    if not instance.pk:
        return  # Novo produto, ignora
    try:
        old = Produto.objects.get(pk=instance.pk)
    except Produto.DoesNotExist:
        return
    if old.estoque_atual != instance.estoque_atual:
        logger.warning(f"Alteração manual de estoque_atual: Produto {instance.id} - {instance.nome} | de {old.estoque_atual} para {instance.estoque_atual}")
