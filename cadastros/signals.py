from decimal import Decimal
from django.conf import settings
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


# ---------------------------------------------
# Sincronização de endereços do Fornecedor
# ---------------------------------------------
from .models import FornecedorEndereco, Fornecedor


@receiver(post_save, sender=FornecedorEndereco)
def fornecedor_endereco_post_save(sender, instance, created, **kwargs):
    """Quando um endereço é salvo com `padrao=True`, atualiza os campos espelhados do Fornecedor."""
    if instance.padrao:
        data = {
            'cep': instance.cep or '',
            'endereco': instance.logradouro or '',
            'numero': instance.numero or '',
            'complemento': instance.complemento or '',
            'bairro': instance.bairro or '',
            'cidade': instance.cidade or '',
            'uf': instance.uf or '',
            'pais': instance.pais or ''
        }
        qs = Fornecedor.objects.filter(pk=instance.fornecedor_id)
        fornecedor = qs.first()
        if fornecedor:
            needs_update = any((getattr(fornecedor, k) or '') != v for k, v in data.items())
            if needs_update:
                qs.update(**data)


@receiver(post_delete, sender=FornecedorEndereco)
def fornecedor_endereco_post_delete(sender, instance, **kwargs):
    """Se o endereço padrão é deletado, promove outro endereço e atualiza o fornecedor (ou limpa campos)."""
    if instance.padrao:
        next_fe = FornecedorEndereco.objects.filter(fornecedor=instance.fornecedor).first()
        if next_fe:
            # Tornar o próximo endereço como padrão (isso acionará post_save e atualizará o fornecedor)
            next_fe.padrao = True
            next_fe.save()
        else:
            # Não há mais endereços: limpa campos do fornecedor
            Fornecedor.objects.filter(pk=instance.fornecedor_id).update(
                cep='', endereco='', numero='', complemento='', bairro='', cidade='', uf='', pais=''
            )


# ============================================================================
# AUTO-CÓPIA DE ESTÁGIOS TEMPLATE PARA NOVAS EMPRESAS
# ============================================================================

@receiver(post_save, sender='empresas.Empresa')
def copiar_estagios_template_para_nova_empresa(sender, instance, created, **kwargs):
    """
    Quando uma nova empresa é criada, copia automaticamente os estágios template
    para que a empresa já comece com estágios padrão pré-configurados.
    """
    if not created:
        return  # Só executa na criação, não em atualizações
    
    # Import aqui para evitar circular imports
    from cadastros.models import EstagioDesenvolvimento
    
    # Buscar todos os estágios template (sem empresa específica)
    estagios_template = EstagioDesenvolvimento.objects.filter(
        eh_template=True,
        empresa__isnull=True  # Estágios de sistema (templates)
    )
    
    if not estagios_template.exists():
        return  # Se não houver templates, não faz nada
    
    # Copiar cada template para a nova empresa
    for estagio_template in estagios_template:
        EstagioDesenvolvimento.objects.create(
            empresa=instance,
            praga=estagio_template.praga,
            tipo_estagio=estagio_template.tipo_estagio,
            descricao=estagio_template.descricao,
            duracao_minima_dias=estagio_template.duracao_minima_dias,
            duracao_maxima_dias=estagio_template.duracao_maxima_dias,
            ordem_ciclo=estagio_template.ordem_ciclo,
            eh_fase_critica=estagio_template.eh_fase_critica,
            observacoes=estagio_template.observacoes,
            ativo=estagio_template.ativo,
            eh_template=False,  # Cópia não é template
            template_original=estagio_template,  # Rastrear origem
        )


# ============================================================================
# UPLOAD DE IMAGENS DE SAFRA NO SUPABASE STORAGE
# ============================================================================

@receiver(post_save, sender='cadastros.Safra')
def safra_post_save_upload_imagem(sender, instance, created, **kwargs):
    """
    Quando uma safra com imagem é salva, envia a imagem para Supabase Storage
    e atualiza o campo com a URL pública.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    if getattr(settings, 'SUPABASE_STORAGE_USE_AS_DEFAULT', False):
        return

    if not instance.imagem:
        return  # Sem imagem, não faz nada
    
    try:
        from core.storage import storage_helper
        
        # Se não tem URL pública (foi novo upload), fazer upload para Supabase
        if not instance.imagem.name.startswith('http'):
            file_obj = instance.imagem.open('rb')
            file_path = f"safra/{instance.fazenda.pk}/{instance.pk}/{instance.imagem.name.split('/')[-1]}"
            
            # Upload para Supabase
            url = storage_helper.upload_file(file_obj, 'safra-imagens', file_path)
            
            if url:
                logger.info(f"Imagem de safra {instance.pk} enviada para Supabase: {url}")
    except Exception as e:
        logger.error(f"Erro ao fazer upload de imagem de safra {instance.pk}: {e}")
        # Não interrompe o fluxo se houver erro no upload


# ============================================================================
# UPLOAD DE IMAGENS DE CULTURA NO SUPABASE STORAGE
# ============================================================================

@receiver(post_save, sender='cadastros.Cultura')
def cultura_post_save_upload_imagem(sender, instance, created, **kwargs):
    """
    Quando uma cultura com imagem é salva, envia a imagem para Supabase Storage
    e armazena a URL pública.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    if getattr(settings, 'SUPABASE_STORAGE_USE_AS_DEFAULT', False):
        return

    if not instance.imagem:
        return  # Sem imagem, não faz nada
    
    try:
        from core.storage import storage_helper
        
        # Se não tem URL pública (foi novo upload), fazer upload para Supabase
        if not instance.imagem.name.startswith('http'):
            file_obj = instance.imagem.open('rb')
            file_path = f"cultura/{instance.empresa.pk}/{instance.pk}/{instance.imagem.name.split('/')[-1]}"
            
            # Upload para Supabase
            url = storage_helper.upload_file(file_obj, 'cultura-imagens', file_path)
            
            if url:
                logger.info(f"Imagem de cultura {instance.pk} enviada para Supabase: {url}")
    except Exception as e:
        logger.error(f"Erro ao fazer upload de imagem de cultura {instance.pk}: {e}")
        # Não interrompe o fluxo se houver erro no upload

