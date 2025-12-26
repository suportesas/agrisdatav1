from decimal import Decimal
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import Area, Fazenda
from .models import Talhao, HistoricoTalhao
from django.db.models.signals import pre_save
from django.utils import timezone


def _recalcular_area_agricultavel(fazenda):
    """Recalcula a área agricultável da fazenda como soma de area_plantavel das áreas."""
    try:
        from django.db.models import Sum
        soma = Area.objects.filter(fazenda_id=fazenda.pk).aggregate(total=Sum('area_plantavel'))['total'] or Decimal('0')
        # quantize para duas casas conforme uso no modelo de Fazenda
        fazenda.area_agricultavel = soma.quantize(Decimal('0.01'))
        fazenda.save(update_fields=['area_agricultavel'])
    except Exception:
        # Em caso de erro, não interrompe a operação principal
        pass


@receiver(post_save, sender=Area)
def area_post_save(sender, instance, created, **kwargs):
    if instance and instance.fazenda:
        _recalcular_area_agricultavel(instance.fazenda)


@receiver(post_delete, sender=Area)
def area_post_delete(sender, instance, **kwargs):
    # Ao deletar, busca a fazenda do banco para evitar caches em instância
    if instance and getattr(instance, 'fazenda_id', None):
        try:
            fazenda = Fazenda.objects.get(pk=instance.fazenda_id)
            _recalcular_area_agricultavel(fazenda)
        except Fazenda.DoesNotExist:
            pass


# ------------------------------
# Criação automática de Histórico
# ------------------------------


@receiver(pre_save, sender=Talhao)
def talhao_pre_save(sender, instance, **kwargs):
    """Armazena o status anterior para comparação no post_save."""
    if instance and instance.pk:
        try:
            old = sender.objects.get(pk=instance.pk)
            instance._pre_save_status = old.status
        except sender.DoesNotExist:
            instance._pre_save_status = None


@receiver(post_save, sender=Talhao)
def talhao_post_save(sender, instance, created, **kwargs):
    """Ao mudar para PLANTADO, cria um registro de HistoricoTalhao se necessário."""
    prev = getattr(instance, '_pre_save_status', None)

    # Se entrou em estado PLANTADO agora (ou foi criado já plantado)
    if instance.status == 'PLANTADO' and prev != 'PLANTADO':
        try:
            data_plantio = instance.data_plantio_atual or timezone.now().date()

            # Evita duplicatas: mesmo talhão + mesma data + mesma cultura
            exists = HistoricoTalhao.objects.filter(
                talhao=instance,
                data_plantio=data_plantio,
                cultura=instance.cultura_atual
            ).exists()

            if not exists and instance.cultura_atual:
                HistoricoTalhao.objects.create(
                    talhao=instance,
                    cultura=instance.cultura_atual,
                    variedade=instance.cultura_atual.variedade or '',
                    data_plantio=data_plantio,
                    empresa=instance.empresa
                )
        except Exception:
            # Não propagar erro do sinal
            pass
