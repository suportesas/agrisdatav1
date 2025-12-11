from decimal import Decimal
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import Area, Fazenda


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
